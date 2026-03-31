//! C5 — Camada de Espaço Canônico
//!
//! O C5 é responsável pelo alinhamento semântico entre agentes.
//! Inclui o handshake de 4 fases (PROBE → ECHO → ALIGN → VERIFY)
//! e a gestão da zona fixa e zona emergente.

pub mod handshake;

pub use handshake::{
    C5Handshake, C5Probe, C5Echo, C5Align, C5Verify,
    HandshakeSession, HandshakeState, ANCHORS, SCHEMA_VER,
};

use std::collections::HashMap;
use uuid::Uuid;

/// Espaço canônico completo (C5)
#[derive(Debug, Clone)]
pub struct CanonicalSpace {
    /// Zona fixa — 32 dimensões padronizadas
    pub zone_fixed: [f32; 32],
    /// Zona emergente — dimensões dinâmicas (índice 32+)
    pub zone_emergent: HashMap<Uuid, f32>,
    /// Versão do schema
    pub schema_ver: String,
    /// Hash de alinhamento
    pub align_hash: String,
}

impl CanonicalSpace {
    pub fn new(zone_fixed: [f32; 32], align_hash: String) -> Self {
        Self {
            zone_fixed,
            zone_emergent: HashMap::new(),
            schema_ver: SCHEMA_VER.to_string(),
            align_hash,
        }
    }

    /// Adiciona uma dimensão emergente
    pub fn register_emergent(&mut self, id: Uuid, value: f32) {
        self.zone_emergent.insert(id, value.clamp(0.0, 1.0));
    }

    /// Obtém valor de dimensão (fixa ou emergente)
    pub fn get(&self, idx: usize) -> Option<f32> {
        if idx < 32 {
            Some(self.zone_fixed[idx])
        } else {
            None // Emergentes são acessadas por UUID, não índice
        }
    }

    /// Verifica alinhamento com outro espaço canônico
    pub fn is_aligned_with(&self, other: &CanonicalSpace) -> bool {
        self.align_hash == other.align_hash && self.schema_ver == other.schema_ver
    }
}

impl Default for CanonicalSpace {
    fn default() -> Self {
        let zone_fixed = [
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
            0.5, 0.5, 0.5, 0.5,
        ];
        Self {
            zone_fixed,
            zone_emergent: HashMap::new(),
            schema_ver: SCHEMA_VER.to_string(),
            align_hash: String::new(),
        }
    }
}
