//! ZeroMQ Transport — TCP/IPC para comunicação inter-agente
//!
//! Implementa padrões: REQ/REP (RPC), PUB/SUB (broadcast), PUSH/PULL (work queue)

use async_trait::async_trait;

use super::{Transport, TransportMessage};

/// Tipos de socket ZeroMQ suportados
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ZmqSocketType {
    /// Request (cliente RPC)
    Req,
    /// Reply (servidor RPC)
    Rep,
    /// Publish (broadcast)
    Pub,
    /// Subscribe (recebe broadcast)
    Sub,
    /// Push (envia para workers)
    Push,
    /// Pull (recebe de producers)
    Pull,
    /// Dealer (async request/reply)
    Dealer,
    /// Router (async request/reply com routing)
    Router,
}

impl ZmqSocketType {
    /// Retorna a string do tipo para ZeroMQ
    pub fn as_zmq_str(&self) -> &'static str {
        match self {
            ZmqSocketType::Req => "REQ",
            ZmqSocketType::Rep => "REP",
            ZmqSocketType::Pub => "PUB",
            ZmqSocketType::Sub => "SUB",
            ZmqSocketType::Push => "PUSH",
            ZmqSocketType::Pull => "PULL",
            ZmqSocketType::Dealer => "DEALER",
            ZmqSocketType::Router => "ROUTER",
        }
    }
}

/// Configuração do transporte ZeroMQ
#[derive(Debug, Clone)]
pub struct ZmqConfig {
    /// Endereço de bind (ex: "tcp://*:5555")
    pub bind_addr: String,
    /// Endereço de connect (ex: "tcp://localhost:5555")
    pub connect_addr: Option<String>,
    /// Tipo de socket
    pub socket_type: ZmqSocketType,
    /// Timeout em ms
    pub timeout_ms: u64,
}

impl Default for ZmqConfig {
    fn default() -> Self {
        Self {
            bind_addr: "tcp://*:5555".to_string(),
            connect_addr: None,
            socket_type: ZmqSocketType::Rep,
            timeout_ms: 5000,
        }
    }
}

/// Transporte ZeroMQ (stub simplificado para compilação)
pub struct ZmqTransport {
    config: ZmqConfig,
}

impl ZmqTransport {
    /// Cria um novo transporte ZeroMQ
    pub fn new(config: ZmqConfig) -> anyhow::Result<Self> {
        Ok(Self { config })
    }

    /// Inicializa o socket (bind ou connect)
    pub async fn init(&self) -> anyhow::Result<()> {
        tracing::info!(
            "ZeroMQ transport initialized: {:?} on {}",
            self.config.socket_type,
            self.config.bind_addr
        );
        Ok(())
    }
}

#[async_trait]
impl Transport for ZmqTransport {
    async fn send(&self, msg: TransportMessage) -> anyhow::Result<()> {
        tracing::debug!("ZeroMQ send: {} -> {}", msg.sender, msg.receiver);
        // Implementação real usaria zmq::Socket
        Ok(())
    }

    async fn recv(&self) -> anyhow::Result<TransportMessage> {
        // Stub — implementação real bloquearia no socket.recv()
        tracing::debug!("ZeroMQ recv (stub)");
        Err(anyhow::anyhow!("ZeroMQ recv not implemented in stub mode"))
    }

    async fn close(&self) -> anyhow::Result<()> {
        tracing::info!("ZeroMQ transport closed");
        Ok(())
    }
}

/// Builder para ZmqTransport
pub struct ZmqTransportBuilder {
    config: ZmqConfig,
}

impl ZmqTransportBuilder {
    pub fn new() -> Self {
        Self {
            config: ZmqConfig::default(),
        }
    }

    pub fn bind_addr(mut self, addr: &str) -> Self {
        self.config.bind_addr = addr.to_string();
        self
    }

    pub fn connect_addr(mut self, addr: &str) -> Self {
        self.config.connect_addr = Some(addr.to_string());
        self
    }

    pub fn socket_type(mut self, ty: ZmqSocketType) -> Self {
        self.config.socket_type = ty;
        self
    }

    pub fn timeout_ms(mut self, ms: u64) -> Self {
        self.config.timeout_ms = ms;
        self
    }

    pub fn build(self) -> anyhow::Result<ZmqTransport> {
        ZmqTransport::new(self.config)
    }
}

impl Default for ZmqTransportBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zmq_socket_type() {
        assert_eq!(ZmqSocketType::Req.as_zmq_str(), "REQ");
        assert_eq!(ZmqSocketType::Pub.as_zmq_str(), "PUB");
        assert_eq!(ZmqSocketType::Router.as_zmq_str(), "ROUTER");
    }

    #[tokio::test]
    async fn test_zmq_transport_stub() {
        let transport = ZmqTransportBuilder::new()
            .bind_addr("tcp://*:5555")
            .socket_type(ZmqSocketType::Rep)
            .build()
            .unwrap();

        transport.init().await.unwrap();

        let msg = TransportMessage::new(
            "agent1".to_string(),
            "agent2".to_string(),
            vec![1, 2, 3],
        );

        transport.send(msg).await.unwrap();
        transport.close().await.unwrap();
    }
}
