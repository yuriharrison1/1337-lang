//! Transport Layer — ZeroMQ e WebSocket
//!
//! Este módulo implementa as camadas de transporte para comunicação
//! entre agentes 1337 via ZeroMQ (TCP/IPC) e WebSocket.

pub mod zmq;

pub use zmq::{ZmqTransport, ZmqTransportBuilder, ZmqSocketType};

use async_trait::async_trait;

/// Trait unificado para transportes
#[async_trait]
pub trait Transport: Send + Sync {
    /// Envia uma mensagem 1337
    async fn send(&self, msg: TransportMessage) -> anyhow::Result<()>;
    
    /// Recebe uma mensagem (bloqueante)
    async fn recv(&self) -> anyhow::Result<TransportMessage>;
    
    /// Fecha o transporte
    async fn close(&self) -> anyhow::Result<()>;
}

/// Mensagem do transporte (envelope para MSG_1337)
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TransportMessage {
    /// ID da mensagem
    pub id: String,
    /// ID do remetente
    pub sender: String,
    /// ID do destinatário (ou "BROADCAST")
    pub receiver: String,
    /// Payload serializado (JSON ou binário)
    #[serde(with = "serde_bytes")]
    pub payload: Vec<u8>,
    /// Timestamp
    pub stamp: i64,
}

impl TransportMessage {
    pub fn new(
        sender: String,
        receiver: String,
        payload: Vec<u8>,
    ) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            sender,
            receiver,
            payload,
            stamp: chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0),
        }
    }
}
