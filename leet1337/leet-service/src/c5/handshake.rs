//! C5 Handshake — Protocolo de alinhamento de espaço canônico
//!
//! O handshake C5 é o ritual de entrada de um agente na rede 1337.
//! Segue 4 fases: PROBE → ECHO → ALIGN → VERIFY

use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use uuid::Uuid;

/// As 5 âncoras imutáveis do espaço canônico
pub const ANCHORS: [[f32; 32]; 5] = [
    // ÂNCORA_1: presença — algo existe agora
    [
        1.0, 0.9, 0.8, 0.5, 0.5, 0.6, 0.5, 0.7, 0.9, 0.3, 0.4, 0.6, 0.7, 0.8,
        0.7, 0.9, 0.8, 0.5, 0.4, 0.3, 0.8, 0.7, 0.5, 0.6, 0.4, 0.5, 0.3, 0.4, 0.5, 0.5, 0.3, 0.6,
    ],
    // ÂNCORA_2: ausência — algo não existe
    [
        0.1, 0.2, 0.1, 0.5, 0.5, 0.3, 0.5, 0.2, 0.1, 0.1, 0.3, 0.2, 0.3, 0.2,
        0.4, 0.2, 0.1, 0.3, 0.6, 0.2, 0.3, 0.2, 0.2, 0.1, 0.2, 0.1, 0.2, 0.2, 0.2, 0.1, 0.2, 0.2,
    ],
    // ÂNCORA_3: mudança — estado anterior ≠ atual
    [
        0.5, 0.7, 0.9, 0.6, 0.8, 0.9, 0.6, 0.5, 0.7, 0.9, 0.6, 0.8, 0.4, 0.5,
        0.6, 0.9, 0.5, 0.8, 0.7, 0.5, 0.7, 0.5, 0.7, 0.6, 0.8, 0.5, 0.7, 0.5, 0.9, 0.7, 0.8, 0.6,
    ],
    // ÂNCORA_4: agência — ator causando algo
    [
        0.7, 0.6, 0.7, 0.8, 0.5, 0.9, 0.9, 0.6, 0.5, 0.8, 0.7, 0.6, 0.5, 0.7,
        0.6, 0.7, 0.6, 0.9, 0.5, 0.6, 0.7, 0.6, 0.8, 0.8, 0.9, 0.7, 0.5, 0.6, 0.6, 0.6, 0.9, 0.7,
    ],
    // ÂNCORA_5: incerteza — grau de desconhecimento
    [
        0.3, 0.4, 0.3, 0.5, 0.4, 0.3, 0.5, 0.4, 0.3, 0.3, 0.4, 0.3, 0.2, 0.3,
        0.2, 0.3, 0.2, 0.2, 0.5, 0.7, 0.2, 0.2, 0.4, 0.3, 0.3, 0.2, 0.5, 0.3, 0.2, 0.2, 0.3, 0.3,
    ],
];

/// Versão do schema
pub const SCHEMA_VER: &str = "0.4.0";

/// Estado do handshake C5
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HandshakeState {
    /// Aguardando PROBE
    Idle,
    /// PROBE enviado/recebido, aguardando ECHO
    Probing,
    /// ECHO enviado/recebido, computando ALIGN
    Aligning,
    /// ALIGN enviado/recebido, aguardando VERIFY
    Verifying,
    /// Handshake completo — agente alinhado
    Verified,
    /// Handshake falhou
    Failed,
}

/// Sessão de handshake ativa
#[derive(Debug, Clone)]
pub struct HandshakeSession {
    pub agent_id: Uuid,
    pub state: HandshakeState,
    pub started: Instant,
    pub align_hash: Option<String>,
    pub zone_emergent: HashMap<Uuid, f32>,
}

impl HandshakeSession {
    pub fn new(agent_id: Uuid) -> Self {
        Self {
            agent_id,
            state: HandshakeState::Idle,
            started: Instant::now(),
            align_hash: None,
            zone_emergent: HashMap::new(),
        }
    }

    /// Verifica se o handshake expirou (timeout: 30s)
    pub fn is_expired(&self) -> bool {
        self.started.elapsed() > Duration::from_secs(30)
    }
}

/// Gerenciador de handshakes C5
pub struct C5Handshake {
    sessions: RwLock<HashMap<Uuid, HandshakeSession>>,
    /// Matriz de projeção M (simplificada — na prática seria aprendida)
    projection_matrix: [[f32; 32]; 32],
}

impl C5Handshake {
    pub fn new() -> Self {
        // Inicializa matriz identidade (projeção direta)
        let mut matrix = [[0.0f32; 32]; 32];
        for i in 0..32 {
            matrix[i][i] = 1.0;
        }

        Self {
            sessions: RwLock::new(HashMap::new()),
            projection_matrix: matrix,
        }
    }

    /// Inicia fase PROBE — novo agente quer entrar na rede
    pub async fn probe(&self, agent_id: Uuid) -> anyhow::Result<C5Probe> {
        let mut sessions = self.sessions.write().await;
        let session = HandshakeSession::new(agent_id);
        sessions.insert(agent_id, session);

        Ok(C5Probe {
            agent_id,
            anchors: ANCHORS,
            schema_ver: SCHEMA_VER.to_string(),
        })
    }

    /// Responde com ECHO — rede responde ao PROBE
    pub async fn echo(&self, agent_id: Uuid) -> anyhow::Result<C5Echo> {
        let mut sessions = self.sessions.write().await;
        
        if let Some(session) = sessions.get_mut(&agent_id) {
            if session.is_expired() {
                session.state = HandshakeState::Failed;
                return Err(anyhow::anyhow!("Handshake expired"));
            }
            session.state = HandshakeState::Probing;
        } else {
            return Err(anyhow::anyhow!("No active session for agent"));
        }

        Ok(C5Echo {
            agent_id,
            anchors: ANCHORS,
            zone_fixed: self.compute_zone_fixed(),
            schema_ver: SCHEMA_VER.to_string(),
        })
    }

    /// Fase ALIGN — computa matriz de projeção
    pub async fn align(&self, agent_id: Uuid) -> anyhow::Result<C5Align> {
        let mut sessions = self.sessions.write().await;
        
        if let Some(session) = sessions.get_mut(&agent_id) {
            if session.is_expired() {
                session.state = HandshakeState::Failed;
                return Err(anyhow::anyhow!("Handshake expired"));
            }
            session.state = HandshakeState::Aligning;
            
            // Computa align_hash da matriz de projeção
            let align_hash = self.compute_align_hash();
            session.align_hash = Some(align_hash.clone());

            Ok(C5Align {
                agent_id,
                projection_matrix: self.projection_matrix,
                align_hash,
            })
        } else {
            Err(anyhow::anyhow!("No active session for agent"))
        }
    }

    /// Fase VERIFY — confirma alinhamento
    pub async fn verify(&self, agent_id: Uuid, received_hash: &str) -> anyhow::Result<C5Verify> {
        let mut sessions = self.sessions.write().await;
        
        if let Some(session) = sessions.get_mut(&agent_id) {
            if session.is_expired() {
                session.state = HandshakeState::Failed;
                return Err(anyhow::anyhow!("Handshake expired"));
            }

            let expected_hash = session.align_hash.as_deref().unwrap_or("");
            let success = expected_hash == received_hash;

            session.state = if success {
                HandshakeState::Verified
            } else {
                HandshakeState::Failed
            };

            Ok(C5Verify {
                agent_id,
                success,
                error_threshold: if success { 0.0 } else { 1.0 },
            })
        } else {
            Err(anyhow::anyhow!("No active session for agent"))
        }
    }

    /// Verifica se um agente está verificado
    pub async fn is_verified(&self, agent_id: Uuid) -> bool {
        let sessions = self.sessions.read().await;
        sessions
            .get(&agent_id)
            .map(|s| s.state == HandshakeState::Verified)
            .unwrap_or(false)
    }

    /// Remove sessões expiradas
    pub async fn cleanup(&self) -> usize {
        let mut sessions = self.sessions.write().await;
        let before = sessions.len();
        sessions.retain(|_, s| !s.is_expired() || s.state == HandshakeState::Verified);
        before - sessions.len()
    }

    /// Zona fixa computada a partir das âncoras
    fn compute_zone_fixed(&self) -> [f32; 32] {
        // Média das âncoras
        let mut zone = [0.0f32; 32];
        for anchor in &ANCHORS {
            for i in 0..32 {
                zone[i] += anchor[i];
            }
        }
        for i in 0..32 {
            zone[i] /= ANCHORS.len() as f32;
        }
        zone
    }

    /// Hash da matriz de projeção
    fn compute_align_hash(&self) -> String {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        for row in &self.projection_matrix {
            for val in row {
                hasher.update(&val.to_le_bytes());
            }
        }
        hex::encode(hasher.finalize())
    }
}

impl Default for C5Handshake {
    fn default() -> Self {
        Self::new()
    }
}

// ─── Mensagens do Handshake ─────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct C5Probe {
    pub agent_id: Uuid,
    pub anchors: [[f32; 32]; 5],
    pub schema_ver: String,
}

#[derive(Debug, Clone)]
pub struct C5Echo {
    pub agent_id: Uuid,
    pub anchors: [[f32; 32]; 5],
    pub zone_fixed: [f32; 32],
    pub schema_ver: String,
}

#[derive(Debug, Clone)]
pub struct C5Align {
    pub agent_id: Uuid,
    pub projection_matrix: [[f32; 32]; 32],
    pub align_hash: String,
}

#[derive(Debug, Clone)]
pub struct C5Verify {
    pub agent_id: Uuid,
    pub success: bool,
    pub error_threshold: f32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_c5_full_handshake() {
        let c5 = C5Handshake::new();
        let agent_id = Uuid::new_v4();

        // Fase 1: PROBE
        let probe = c5.probe(agent_id).await.unwrap();
        assert_eq!(probe.agent_id, agent_id);
        assert_eq!(probe.schema_ver, SCHEMA_VER);

        // Fase 2: ECHO
        let echo = c5.echo(agent_id).await.unwrap();
        assert_eq!(echo.agent_id, agent_id);

        // Fase 3: ALIGN
        let align = c5.align(agent_id).await.unwrap();
        assert_eq!(align.agent_id, agent_id);
        assert!(!align.align_hash.is_empty());

        // Fase 4: VERIFY (sucesso)
        let verify = c5.verify(agent_id, &align.align_hash).await.unwrap();
        assert!(verify.success);
        assert!(c5.is_verified(agent_id).await);
    }

    #[tokio::test]
    async fn test_c5_verify_fail() {
        let c5 = C5Handshake::new();
        let agent_id = Uuid::new_v4();

        c5.probe(agent_id).await.unwrap();
        c5.echo(agent_id).await.unwrap();
        c5.align(agent_id).await.unwrap();

        // Hash errado
        let verify = c5.verify(agent_id, "hash_errado").await.unwrap();
        assert!(!verify.success);
        assert!(!c5.is_verified(agent_id).await);
    }
}
