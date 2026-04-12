//! Agent client — connects to a LeetServer via TCP.
//!
//! Implements the C5 handshake and provides send/receive primitives
//! for exchanging Msg1337 messages over the wire.

use std::time::Instant;

use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::TcpStream;
use uuid::Uuid;

use leet_core::{
    protocol::compute_align_hash,
    types::{Cogon, Msg1337, RawField, RawRole, Receiver},
};
use leet_bridge::nl_translator::nl_to_cogon;

use crate::tcp_server::WireMsg;

/// Client error type.
#[derive(Debug)]
pub enum AgentError {
    Io(std::io::Error),
    Json(serde_json::Error),
    Protocol(String),
}

impl std::fmt::Display for AgentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e)       => write!(f, "io: {}", e),
            Self::Json(e)     => write!(f, "json: {}", e),
            Self::Protocol(s) => write!(f, "protocol: {}", s),
        }
    }
}

impl From<std::io::Error> for AgentError {
    fn from(e: std::io::Error) -> Self { Self::Io(e) }
}
impl From<serde_json::Error> for AgentError {
    fn from(e: serde_json::Error) -> Self { Self::Json(e) }
}

// ── AgentClient ───────────────────────────────────────────────────────────────

/// A connected agent in the 1337 network.
pub struct AgentClient {
    pub id: Uuid,
    pub name: String,
    pub role: String,
    pub align_hash: [u8; 32],
    reader: Option<BufReader<tokio::net::tcp::OwnedReadHalf>>,
    writer: Option<tokio::net::tcp::OwnedWriteHalf>,
    pub connected_at: Option<Instant>,
}

impl AgentClient {
    /// Create a new (not yet connected) agent client.
    pub fn new(id: Uuid, name: &str, role: &str) -> Self {
        Self {
            id,
            name: name.to_string(),
            role: role.to_string(),
            align_hash: compute_align_hash(name),
            reader: None,
            writer: None,
            connected_at: None,
        }
    }

    /// Connect to a TCP server at `addr` and complete the C5 handshake.
    ///
    /// After this call the client is ready for `send_cogon` / `recv`.
    pub async fn connect(&mut self, addr: &str) -> Result<(), AgentError> {
        let stream = TcpStream::connect(addr).await?;
        let (read_half, write_half) = stream.into_split();
        let mut reader = BufReader::new(read_half);
        let mut writer = write_half;

        // Phase 1 — PROBE: send Register
        let register = WireMsg::Register {
            name: self.name.clone(),
            role: self.role.clone(),
        };
        let msg = serde_json::to_string(&register)? + "\n";
        writer.write_all(msg.as_bytes()).await?;

        // Phase 2 — ECHO: receive Registered + anchors
        let mut line = String::new();
        reader.read_line(&mut line).await?;
        let registered: WireMsg = serde_json::from_str(line.trim())
            .map_err(|e| AgentError::Protocol(format!("expected Registered: {}", e)))?;

        match registered {
            WireMsg::Registered { agent_id, .. } => {
                // Parse the server-assigned UUID
                if let Ok(id) = Uuid::parse_str(&agent_id) {
                    self.id = id;
                }
            }
            WireMsg::Error { message } => {
                return Err(AgentError::Protocol(format!("server error: {}", message)));
            }
            _ => return Err(AgentError::Protocol("unexpected message during ECHO".into())),
        }

        // Phase 3 — ALIGN: send computed hash
        let hash_hex: String = self.align_hash.iter().map(|b| format!("{:02x}", b)).collect();
        let align = WireMsg::Align { hash: hash_hex };
        let msg = serde_json::to_string(&align)? + "\n";
        writer.write_all(msg.as_bytes()).await?;

        // Phase 4 — VERIFY: expect Ready
        line.clear();
        reader.read_line(&mut line).await?;
        let ready: WireMsg = serde_json::from_str(line.trim())
            .map_err(|e| AgentError::Protocol(format!("expected Ready: {}", e)))?;

        match ready {
            WireMsg::Ready => {}
            WireMsg::Error { message } => {
                return Err(AgentError::Protocol(format!("alignment rejected: {}", message)));
            }
            _ => return Err(AgentError::Protocol("unexpected message after ALIGN".into())),
        }

        self.reader = Some(reader);
        self.writer = Some(writer);
        self.connected_at = Some(Instant::now());
        Ok(())
    }

    /// Send a natural language text message to the server as BROADCAST.
    ///
    /// The text is translated to a COGON and embedded with the original text
    /// in the raw field for downstream reconstruction.
    pub async fn send_nl(&mut self, text: &str) -> Result<(), AgentError> {
        let mut cogon = nl_to_cogon(text, "pt");
        cogon.raw = Some(RawField {
            content_type: "text/plain".to_string(),
            content: serde_json::Value::String(text.to_string()),
            role: RawRole::Bridge,
        });

        let msg = leet_core::types::Msg1337::new_nl_message(
            self.id,
            Receiver::Broadcast,
            cogon,
            self.align_hash,
            "pt",
        );
        self.send_msg(&msg).await
    }

    /// Send a pre-built COGON directly to the server as BROADCAST.
    pub async fn send_cogon(&mut self, cogon: &Cogon) -> Result<(), AgentError> {
        let msg = leet_core::types::Msg1337::new_nl_message(
            self.id,
            Receiver::Broadcast,
            cogon.clone(),
            self.align_hash,
            "pt",
        );
        self.send_msg(&msg).await
    }

    /// Send a Msg1337 over the wire.
    pub async fn send_msg(&mut self, msg: &Msg1337) -> Result<(), AgentError> {
        let wire = WireMsg::Msg { data: Box::new(msg.clone()) };
        let json = serde_json::to_string(&wire)? + "\n";
        let writer = self.writer.as_mut()
            .ok_or_else(|| AgentError::Protocol("not connected".into()))?;
        writer.write_all(json.as_bytes()).await?;
        Ok(())
    }

    /// Receive the next message from the server.
    ///
    /// Returns `None` on EOF (server closed connection).
    pub async fn recv(&mut self) -> Result<Option<Msg1337>, AgentError> {
        let reader = self.reader.as_mut()
            .ok_or_else(|| AgentError::Protocol("not connected".into()))?;

        let mut line = String::new();
        let n = reader.read_line(&mut line).await?;
        if n == 0 {
            return Ok(None); // EOF
        }

        let wire: WireMsg = serde_json::from_str(line.trim())?;
        match wire {
            WireMsg::Msg { data } => Ok(Some(*data)),
            WireMsg::Error { message } => Err(AgentError::Protocol(message)),
            _ => Err(AgentError::Protocol("unexpected wire message type".into())),
        }
    }

    /// Receive next message with a timeout.
    ///
    /// Returns `None` if the timeout elapses before a message arrives.
    pub async fn recv_timeout(
        &mut self,
        timeout: std::time::Duration,
    ) -> Result<Option<Msg1337>, AgentError> {
        tokio::time::timeout(timeout, self.recv())
            .await
            .unwrap_or(Ok(None))
    }

    /// Whether the client has completed the handshake.
    pub fn is_connected(&self) -> bool {
        self.reader.is_some()
    }
}
