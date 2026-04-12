//! TCP + Unix socket 1337 translation daemon.
//!
//! Architecture:
//!   - One `LeetServer` holds the shared agent registry and metrics
//!   - Each connection runs two async tasks: reader and writer
//!   - Messages are routed via per-agent `mpsc::Sender<String>` (JSON lines)
//!   - Broadcast uses tokio's `broadcast::Sender` for fan-out

use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

use serde::{Deserialize, Serialize};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpListener;
use tokio::sync::{mpsc, Mutex, RwLock};
use tracing::{error, info, warn};
use uuid::Uuid;

use leet_core::{
    protocol::{all_anchors, compute_align_hash},
    types::{Msg1337, Receiver},
};

// ── Wire protocol types ───────────────────────────────────────────────────────

/// All messages exchanged on the wire are wrapped in this envelope.
#[derive(Debug, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WireMsg {
    /// Handshake phase 1 — PROBE: client registers with name/role
    Register { name: String, role: String },
    /// Handshake phase 2 — ECHO: server confirms registration + sends anchors
    Registered {
        agent_id: String,
        anchors: Vec<serde_json::Value>,
    },
    /// Handshake phase 3 — ALIGN: client sends computed hash
    Align { hash: String },
    /// Handshake phase 4 — VERIFY: server confirms alignment
    Ready,
    /// Normal operation: a full Msg1337 envelope
    Msg { data: Box<leet_core::types::Msg1337> },
    /// Server-sent error
    Error { message: String },
}

// ── Server metrics ────────────────────────────────────────────────────────────

/// Accumulated server statistics.
#[derive(Debug, Default)]
pub struct ServerMetrics {
    pub total_messages: u64,
    pub total_nl_tokens: u64,
    pub total_cogon_bytes: u64,
    pub total_translations: u64,
    pub agents_peak: u32,
}

// ── Per-agent handle ──────────────────────────────────────────────────────────

/// Per-agent state stored in the server registry.
#[derive(Debug)]
pub struct AgentHandle {
    pub id: Uuid,
    pub name: String,
    pub role: String,
    pub align_hash: [u8; 32],
    /// Channel to push outgoing JSON lines to this agent's write task
    pub tx: mpsc::Sender<String>,
    pub connected_at: Instant,
    pub msgs_sent: Arc<AtomicU64>,
    pub msgs_recv: Arc<AtomicU64>,
}

// ── LeetServer ────────────────────────────────────────────────────────────────

/// Shared server state — wrapped in Arc for multi-task sharing.
pub struct LeetServer {
    pub agents: RwLock<HashMap<Uuid, AgentHandle>>,
    pub metrics: Mutex<ServerMetrics>,
}

impl LeetServer {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            agents: RwLock::new(HashMap::new()),
            metrics: Mutex::new(ServerMetrics::default()),
        })
    }

    /// Start listening on `tcp_addr` (e.g. `"127.0.0.1:1337"`).
    ///
    /// Returns the actual bound `SocketAddr` (useful when port 0 is passed for tests).
    /// This call never returns in the success path — it drives the accept loop.
    pub async fn listen(
        self: Arc<Self>,
        tcp_addr: &str,
    ) -> Result<SocketAddr, Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(tcp_addr).await?;
        let local_addr = listener.local_addr()?;
        info!("leet-server listening on {}", local_addr);

        loop {
            match listener.accept().await {
                Ok((stream, peer)) => {
                    let server = self.clone();
                    tokio::spawn(async move {
                        if let Err(e) = server.handle_connection(stream, peer).await {
                            warn!("connection error from {}: {}", peer, e);
                        }
                    });
                }
                Err(e) => {
                    error!("accept error: {}", e);
                }
            }
        }
    }

    /// Start the listener and return the bound address without blocking the caller.
    ///
    /// A background task drives the accept loop. Used by tests and the binary
    /// to learn the actual port when `"0"` is used.
    pub async fn start_background(
        self: Arc<Self>,
        tcp_addr: &str,
    ) -> Result<SocketAddr, Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(tcp_addr).await?;
        let local_addr = listener.local_addr()?;
        info!("leet-server listening on {} (background)", local_addr);

        tokio::spawn(async move {
            loop {
                match listener.accept().await {
                    Ok((stream, peer)) => {
                        let server = self.clone();
                        tokio::spawn(async move {
                            if let Err(e) = server.handle_connection(stream, peer).await {
                                warn!("connection error from {}: {}", peer, e);
                            }
                        });
                    }
                    Err(e) => {
                        error!("accept error: {}", e);
                        break;
                    }
                }
            }
        });

        Ok(local_addr)
    }

    // ── Connection lifecycle ──────────────────────────────────────────────

    async fn handle_connection(
        self: Arc<Self>,
        stream: tokio::net::TcpStream,
        peer: SocketAddr,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let (read_half, write_half) = stream.into_split();
        let mut reader = BufReader::new(read_half);
        let write_half = Arc::new(tokio::sync::Mutex::new(write_half));

        // ── Handshake ─────────────────────────────────────────────────────

        // Phase 1 — PROBE: read Register message
        let mut line = String::new();
        reader.read_line(&mut line).await?;
        let register_msg: WireMsg = serde_json::from_str(line.trim())?;

        let (agent_name, agent_role) = match register_msg {
            WireMsg::Register { name, role } => (name, role),
            _ => return Err("expected Register message first".into()),
        };

        let agent_id = Uuid::new_v4();
        info!("handshake PROBE from {} as {} ({})", peer, agent_name, agent_role);

        // Phase 2 — ECHO: send Registered with anchors
        let anchors = all_anchors();
        let anchor_vals: Vec<serde_json::Value> = anchors
            .iter()
            .map(|c| serde_json::to_value(c).unwrap_or_default())
            .collect();

        let echo = WireMsg::Registered {
            agent_id: agent_id.to_string(),
            anchors: anchor_vals,
        };
        let echo_json = serde_json::to_string(&echo)? + "\n";
        write_half.lock().await.write_all(echo_json.as_bytes()).await?;

        // Phase 3 — ALIGN: read client hash
        line.clear();
        reader.read_line(&mut line).await?;
        let align_msg: WireMsg = serde_json::from_str(line.trim())?;

        let client_hash_hex = match align_msg {
            WireMsg::Align { hash } => hash,
            _ => return Err("expected Align message".into()),
        };

        // Phase 4 — VERIFY: compute expected hash and compare
        let expected_hash = compute_align_hash(&agent_name);
        let expected_hex: String = expected_hash.iter().map(|b| format!("{:02x}", b)).collect();

        if client_hash_hex != expected_hex {
            let err = WireMsg::Error { message: "align_hash mismatch".to_string() };
            let msg = serde_json::to_string(&err)? + "\n";
            write_half.lock().await.write_all(msg.as_bytes()).await?;
            return Err(format!("align mismatch for agent {}", agent_name).into());
        }

        let ready = WireMsg::Ready;
        let ready_json = serde_json::to_string(&ready)? + "\n";
        write_half.lock().await.write_all(ready_json.as_bytes()).await?;

        info!("handshake COMPLETE: {} ({}) id={}", agent_name, agent_role, agent_id);

        // ── Register agent ────────────────────────────────────────────────

        let (tx, mut rx) = mpsc::channel::<String>(64);
        let msgs_sent = Arc::new(AtomicU64::new(0));
        let msgs_recv = Arc::new(AtomicU64::new(0));

        {
            let mut agents = self.agents.write().await;
            let peak = {
                let mut m = self.metrics.lock().await;
                let count = (agents.len() + 1) as u32;
                if count > m.agents_peak { m.agents_peak = count; }
                count
            };
            agents.insert(agent_id, AgentHandle {
                id: agent_id,
                name: agent_name.clone(),
                role: agent_role.clone(),
                align_hash: expected_hash,
                tx,
                connected_at: Instant::now(),
                msgs_sent: msgs_sent.clone(),
                msgs_recv: msgs_recv.clone(),
            });
            info!("agent {} registered (total: {})", agent_name, peak);
        }

        // ── Writer task ───────────────────────────────────────────────────
        // Drains the mpsc channel and writes to the TCP stream
        let write_half_clone = write_half.clone();
        let msgs_sent_clone = msgs_sent.clone();
        let agent_name_write = agent_name.clone();
        let writer_task = tokio::spawn(async move {
            while let Some(msg_json) = rx.recv().await {
                let mut wh = write_half_clone.lock().await;
                if wh.write_all(msg_json.as_bytes()).await.is_err() {
                    break;
                }
                msgs_sent_clone.fetch_add(1, Ordering::Relaxed);
            }
        });

        // ── Reader loop ───────────────────────────────────────────────────
        let result = self
            .read_loop(agent_id, &agent_name, &mut reader, &msgs_recv)
            .await;

        // Cleanup: remove from registry, stop writer
        self.agents.write().await.remove(&agent_id);
        writer_task.abort();
        info!("agent {} disconnected: {:?}", agent_name_write, result);

        Ok(())
    }

    /// Read messages from an established agent connection and route them.
    async fn read_loop(
        self: &Arc<Self>,
        sender_id: Uuid,
        sender_name: &str,
        reader: &mut BufReader<tokio::net::tcp::OwnedReadHalf>,
        msgs_recv: &Arc<AtomicU64>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut line = String::new();
        loop {
            line.clear();
            let n = reader.read_line(&mut line).await?;
            if n == 0 {
                return Ok(()); // EOF — agent disconnected
            }

            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            let wire: WireMsg = match serde_json::from_str(trimmed) {
                Ok(m) => m,
                Err(e) => {
                    warn!("parse error from {}: {}", sender_name, e);
                    continue;
                }
            };

            msgs_recv.fetch_add(1, Ordering::Relaxed);

            let msg = match wire {
                WireMsg::Msg { data } => *data,
                other => {
                    warn!("unexpected wire message from {}: {:?}", sender_name, other);
                    continue;
                }
            };

            // Update global metrics
            {
                let mut m = self.metrics.lock().await;
                m.total_messages += 1;
                m.total_cogon_bytes += 256; // sem + unc
            }

            self.route(sender_id, msg).await;
        }
    }

    // ── Routing ───────────────────────────────────────────────────────────────

    /// Route a Msg1337 based on its receiver field.
    pub async fn route(self: &Arc<Self>, sender_id: Uuid, msg: Msg1337) {
        match &msg.receiver {
            Receiver::Broadcast => {
                self.broadcast(sender_id, &msg).await;
            }
            Receiver::Agent(target_id) => {
                self.deliver_to(*target_id, &msg).await;
            }
        }
    }

    /// Send `msg` to all connected agents except `exclude_id`.
    pub async fn broadcast(self: &Arc<Self>, exclude_id: Uuid, msg: &Msg1337) {
        let json = match serde_json::to_string(&WireMsg::Msg { data: Box::new(msg.clone()) }) {
            Ok(j) => j + "\n",
            Err(e) => { error!("broadcast serialize error: {}", e); return; }
        };

        let agents = self.agents.read().await;
        for (id, handle) in agents.iter() {
            if *id == exclude_id { continue; }
            if handle.tx.send(json.clone()).await.is_err() {
                warn!("failed to send to agent {}", handle.name);
            }
        }
    }

    /// Deliver `msg` to one specific agent.
    async fn deliver_to(self: &Arc<Self>, target_id: Uuid, msg: &Msg1337) {
        let json = match serde_json::to_string(&WireMsg::Msg { data: Box::new(msg.clone()) }) {
            Ok(j) => j + "\n",
            Err(e) => { error!("deliver serialize error: {}", e); return; }
        };

        let agents = self.agents.read().await;
        if let Some(handle) = agents.get(&target_id) {
            if handle.tx.send(json).await.is_err() {
                warn!("failed to deliver to {}", handle.name);
            }
        } else {
            warn!("target agent {} not found", target_id);
        }
    }

    /// Count currently connected agents.
    pub async fn agent_count(&self) -> usize {
        self.agents.read().await.len()
    }

    /// Get a snapshot of agent names currently connected.
    pub async fn agent_names(&self) -> Vec<String> {
        self.agents.read().await.values().map(|h| h.name.clone()).collect()
    }
}

impl Default for LeetServer {
    fn default() -> Self {
        Self {
            agents: RwLock::new(HashMap::new()),
            metrics: Mutex::new(ServerMetrics::default()),
        }
    }
}
