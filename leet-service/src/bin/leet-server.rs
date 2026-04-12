//! leet-server — 1337 TCP translation daemon.
//!
//! Listens on TCP (default 0.0.0.0:1337) and optionally a Unix socket.
//! Agents connect, complete the C5 handshake, and exchange Msg1337 frames.

use clap::Parser;
use tokio::signal;
use tracing::info;

use leet_service::tcp_server::LeetServer;

#[derive(Parser, Debug)]
#[command(
    name = "leet-server",
    about = "1337 translation daemon — semantic substrate for multi-agent systems",
    version = "0.5.1"
)]
struct Args {
    /// TCP bind address
    #[arg(long, default_value = "0.0.0.0:1337")]
    tcp: String,

    /// Unix socket path (optional, Linux only)
    #[arg(long)]
    unix: Option<String>,

    /// Log level (trace, debug, info, warn, error)
    #[arg(long, default_value = "info")]
    log_level: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args = Args::parse();

    // Init tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(&args.log_level)),
        )
        .init();

    info!("leet-server v0.5.1 starting");
    info!("TCP: {}", args.tcp);
    if let Some(ref path) = args.unix {
        info!("Unix socket: {}", path);
    }

    let server = LeetServer::new();

    // Start background TCP listener
    let addr = server.clone().start_background(&args.tcp).await?;
    info!("leet-server bound to {}", addr);

    // Optional Unix socket listener
    #[cfg(unix)]
    if let Some(ref socket_path) = args.unix {
        let path = socket_path.clone();
        // Remove stale socket if it exists
        let _ = std::fs::remove_file(&path);
        let server_unix = server.clone();
        tokio::spawn(async move {
            if let Err(e) = listen_unix(server_unix, &path).await {
                tracing::error!("Unix socket error: {}", e);
            }
        });
    }

    info!("leet-server ready. Send SIGTERM or Ctrl-C to stop.");

    // Wait for shutdown signal
    signal::ctrl_c().await.expect("failed to listen for ctrl_c");
    info!("shutdown signal received. Goodbye.");

    Ok(())
}

/// Start Unix domain socket listener (Linux/macOS only).
#[cfg(unix)]
async fn listen_unix(
    server: std::sync::Arc<leet_service::tcp_server::LeetServer>,
    path: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use tokio::net::UnixListener;
    use tracing::warn;

    let listener = UnixListener::bind(path)?;
    tracing::info!("Unix socket bound to {}", path);

    loop {
        match listener.accept().await {
            Ok((stream, _)) => {
                // Convert UnixStream to TcpStream-compatible interface via helper
                let server = server.clone();
                tokio::spawn(async move {
                    if let Err(e) = handle_unix_connection(server, stream).await {
                        warn!("unix connection error: {}", e);
                    }
                });
            }
            Err(e) => {
                tracing::error!("unix accept error: {}", e);
                break;
            }
        }
    }
    Ok(())
}

#[cfg(unix)]
async fn handle_unix_connection(
    server: std::sync::Arc<leet_service::tcp_server::LeetServer>,
    stream: tokio::net::UnixStream,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use leet_core::protocol::compute_align_hash;
    use leet_service::tcp_server::WireMsg;
    use leet_core::protocol::all_anchors;
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    use uuid::Uuid;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::sync::Arc;
    use std::time::Instant;
    use tokio::sync::mpsc;
    use tracing::warn;

    let (read_half, write_half) = tokio::io::split(stream);
    let mut reader = BufReader::new(read_half);
    let write_arc = Arc::new(tokio::sync::Mutex::new(write_half));

    // Phase 1 — PROBE
    let mut line = String::new();
    reader.read_line(&mut line).await?;
    let register_msg: WireMsg = serde_json::from_str(line.trim())?;
    let (agent_name, agent_role) = match register_msg {
        WireMsg::Register { name, role } => (name, role),
        _ => return Err("expected Register".into()),
    };

    let agent_id = Uuid::new_v4();

    // Phase 2 — ECHO
    let anchors = all_anchors();
    let anchor_vals: Vec<serde_json::Value> = anchors.iter()
        .map(|c| serde_json::to_value(c).unwrap_or_default()).collect();
    let echo = WireMsg::Registered { agent_id: agent_id.to_string(), anchors: anchor_vals };
    let echo_json = serde_json::to_string(&echo)? + "\n";
    write_arc.lock().await.write_all(echo_json.as_bytes()).await?;

    // Phase 3 — ALIGN
    line.clear();
    reader.read_line(&mut line).await?;
    let align_msg: WireMsg = serde_json::from_str(line.trim())?;
    let client_hash_hex = match align_msg {
        WireMsg::Align { hash } => hash,
        _ => return Err("expected Align".into()),
    };

    // Phase 4 — VERIFY
    let expected_hash = compute_align_hash(&agent_name);
    let expected_hex: String = expected_hash.iter().map(|b| format!("{:02x}", b)).collect();
    if client_hash_hex != expected_hex {
        let err = WireMsg::Error { message: "align_hash mismatch".into() };
        let msg = serde_json::to_string(&err)? + "\n";
        write_arc.lock().await.write_all(msg.as_bytes()).await?;
        return Err("align mismatch".into());
    }
    let ready_json = serde_json::to_string(&WireMsg::Ready)? + "\n";
    write_arc.lock().await.write_all(ready_json.as_bytes()).await?;

    // Register agent
    let (tx, mut rx) = mpsc::channel::<String>(64);
    let msgs_sent = Arc::new(AtomicU64::new(0));
    let msgs_recv = Arc::new(AtomicU64::new(0));
    {
        let mut agents = server.agents.write().await;
        let mut m = server.metrics.lock().await;
        let count = (agents.len() + 1) as u32;
        if count > m.agents_peak { m.agents_peak = count; }
        agents.insert(agent_id, leet_service::tcp_server::AgentHandle {
            id: agent_id,
            name: agent_name.clone(),
            role: agent_role,
            align_hash: expected_hash,
            tx,
            connected_at: Instant::now(),
            msgs_sent: msgs_sent.clone(),
            msgs_recv: msgs_recv.clone(),
        });
    }

    // Writer task
    let wac = write_arc.clone();
    let msc = msgs_sent.clone();
    tokio::spawn(async move {
        while let Some(json) = rx.recv().await {
            if wac.lock().await.write_all(json.as_bytes()).await.is_err() { break; }
            msc.fetch_add(1, Ordering::Relaxed);
        }
    });

    // Reader loop
    loop {
        line.clear();
        let n = reader.read_line(&mut line).await?;
        if n == 0 { break; }
        let trimmed = line.trim();
        if trimmed.is_empty() { continue; }
        let wire: WireMsg = match serde_json::from_str(trimmed) {
            Ok(m) => m,
            Err(e) => { warn!("parse error: {}", e); continue; }
        };
        msgs_recv.fetch_add(1, Ordering::Relaxed);
        if let WireMsg::Msg { data } = wire {
            server.route(agent_id, *data).await;
        }
    }

    server.agents.write().await.remove(&agent_id);
    Ok(())
}
