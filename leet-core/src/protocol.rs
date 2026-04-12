//! Protocol support: 5 anchor COGONs, C5 handshake factory methods.
//!
//! This module adds the 1337 v0.5.1 session-layer on top of the core types:
//!   - Five immutable anchor COGONs used for canonical alignment
//!   - Msg1337 factory constructors for the C5 handshake phases
//!   - `compute_align_hash` — deterministic fingerprint per agent

use std::collections::HashMap;

use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::types::{C5Block, Cogon, Intent, Msg1337, Payload, RawField, RawRole, Receiver, SurfaceBlock};

// ── Anchor COGONs ─────────────────────────────────────────────────────────────

/// Names of the 5 immutable anchor concepts (transmitted in ECHO phase).
pub const ANCHOR_NAMES: [&str; 5] = [
    "presence",    // Something exists now
    "absence",     // Something does not exist
    "change",      // Previous state ≠ current state
    "agency",      // There is an actor causing something
    "uncertainty", // Degree of unknowing
];

/// Generate the nth anchor COGON.
///
/// Each anchor has a distinctive semantic fingerprint on the 32 axes
/// so agents can orient themselves in the canonical space.
pub fn anchor_cogon(index: usize) -> Cogon {
    let mut sem = [0.3_f32; 32];
    let mut unc = [0.2_f32; 32];

    match index {
        0 => {
            // presence — S1 ESSENCIA high, D1 ESTADO high, G3 COMPLETUDE high
            sem[0] = 0.95; unc[0] = 0.05;  // S1
            sem[8] = 0.90; unc[8] = 0.05;  // D1
            sem[18] = 0.90; unc[18] = 0.05; // G3
            sem[13] = 0.75; unc[13] = 0.1;  // D6 VALENCIA_ONT positive
        }
        1 => {
            // absence — S1 low, D1 low, G3 low, D6 negative valence
            sem[0] = 0.05; unc[0] = 0.05;
            sem[8] = 0.05; unc[8] = 0.05;
            sem[18] = 0.15; unc[18] = 0.1;
            sem[13] = 0.15; unc[13] = 0.1;  // D6 negative
        }
        2 => {
            // change — S3 VIBRACAO high, D2 PROCESSO high, G2 ANCORA_TEMPORAL future
            sem[2] = 0.95; unc[2] = 0.05;  // S3
            sem[9] = 0.90; unc[9] = 0.05;  // D2
            sem[17] = 0.80; unc[17] = 0.1;  // G2 future-leaning
            sem[14] = 0.70; unc[14] = 0.1;  // D7 CAUSALIDADE
        }
        3 => {
            // agency — S7 GENERO high, S6 CAUSA_EFEITO high, P7 ACAO high
            sem[6] = 0.90; unc[6] = 0.05;  // S7
            sem[5] = 0.90; unc[5] = 0.05;  // S6
            sem[30] = 0.90; unc[30] = 0.05; // P7
            sem[24] = 0.70; unc[24] = 0.1;  // P1 IMPACTO
        }
        4 => {
            // uncertainty — G7 VALENCIA_EPIST inconclusive, unc high everywhere
            sem[22] = 0.45; unc[22] = 0.05; // G7 near neutral (inconclusive)
            for (i, u) in unc.iter_mut().enumerate() {
                if i != 22 { *u = 0.75; }
            }
        }
        _ => {} // out of range: baseline sem/unc
    }

    Cogon {
        id: Uuid::new_v4(),
        sem,
        unc,
        stamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as i64)
            .unwrap_or(0),
        raw: Some(RawField {
            content_type: "text/plain".to_string(),
            content: serde_json::Value::String(
                ANCHOR_NAMES.get(index).copied().unwrap_or("unknown").to_string(),
            ),
            role: RawRole::Evidence,
        }),
    }
}

/// Generate all 5 anchor COGONs.
pub fn all_anchors() -> [Cogon; 5] {
    [
        anchor_cogon(0),
        anchor_cogon(1),
        anchor_cogon(2),
        anchor_cogon(3),
        anchor_cogon(4),
    ]
}

// ── Align hash ────────────────────────────────────────────────────────────────

/// Compute the canonical align_hash for an agent.
///
/// `align_hash = SHA256("1337:v0.5.1:" || agent_name)`
///
/// Deterministic: the server can re-derive it to verify the agent knows
/// the canonical schema without storing any secret.
pub fn compute_align_hash(agent_name: &str) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(b"1337:v0.5.1:");
    h.update(agent_name.as_bytes());
    let result = h.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&result);
    out
}

// ── Msg1337 factory methods ───────────────────────────────────────────────────

impl Msg1337 {
    /// PROBE phase: initial SYNC — "I exist, here is who I am."
    ///
    /// Agent name and role are embedded in the payload's raw field.
    pub fn new_sync(agent_id: Uuid, agent_name: &str, role: &str) -> Self {
        let mut cogon = Cogon::zero();
        cogon.id = agent_id;
        cogon.raw = Some(RawField {
            content_type: "application/json".to_string(),
            content: serde_json::json!({
                "name": agent_name,
                "role": role,
                "schema_ver": "0.5.1"
            }),
            role: RawRole::Bridge,
        });

        Self {
            id: Uuid::new_v4(),
            sender: agent_id,
            receiver: Receiver::Broadcast,
            intent: Intent::Sync,
            ref_hash: None,
            patch: None,
            payload: Payload::Cogon(cogon),
            c5: C5Block {
                zone_fixed: [0.5_f32; 32],
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash: [0u8; 32],
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "pt".to_string(),
            },
        }
    }

    /// VERIFY phase: ACK with computed align_hash.
    pub fn new_ack(agent_id: Uuid, align_hash: [u8; 32]) -> Self {
        Self {
            id: Uuid::new_v4(),
            sender: agent_id,
            receiver: Receiver::Broadcast,
            intent: Intent::Ack,
            ref_hash: None,
            patch: None,
            payload: Payload::Cogon(Cogon::zero()),
            c5: C5Block {
                zone_fixed: [0.5_f32; 32],
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash,
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "pt".to_string(),
            },
        }
    }

    /// Construct a COGON_ZERO broadcast — "I AM" identity assertion.
    pub fn new_cogon_zero(agent_id: Uuid) -> Self {
        Self {
            id: Uuid::new_v4(),
            sender: agent_id,
            receiver: Receiver::Broadcast,
            intent: Intent::Assert,
            ref_hash: None,
            patch: None,
            payload: Payload::Cogon(Cogon::zero()),
            c5: C5Block {
                zone_fixed: [1.0_f32; 32],
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash: [0u8; 32],
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "pt".to_string(),
            },
        }
    }

    /// Build an ASSERT message carrying a text payload in a COGON's raw field.
    ///
    /// Used by agents that communicate in natural language.
    pub fn new_nl_message(
        sender_id: Uuid,
        receiver: Receiver,
        cogon: Cogon,
        align_hash: [u8; 32],
        lang: &str,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            sender: sender_id,
            receiver,
            intent: Intent::Assert,
            ref_hash: None,
            patch: None,
            payload: Payload::Cogon(cogon),
            c5: C5Block {
                zone_fixed: [0.5_f32; 32],
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash,
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: lang.to_string(),
            },
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_anchors_have_correct_names() {
        let anchors = all_anchors();
        for (i, cogon) in anchors.iter().enumerate() {
            let raw = cogon.raw.as_ref().expect("anchor must have raw field");
            let name = raw.content.as_str().expect("raw content must be string");
            assert_eq!(name, ANCHOR_NAMES[i]);
        }
    }

    #[test]
    fn test_anchor_presence_has_high_essencia() {
        let cogon = anchor_cogon(0);
        assert!(cogon.sem[0] > 0.8, "presence: S1_ESSENCIA should be > 0.8");
        assert!(cogon.sem[8] > 0.8, "presence: D1_ESTADO should be > 0.8");
    }

    #[test]
    fn test_anchor_absence_has_low_essencia() {
        let cogon = anchor_cogon(1);
        assert!(cogon.sem[0] < 0.2, "absence: S1_ESSENCIA should be < 0.2");
    }

    #[test]
    fn test_anchor_change_has_high_vibracao() {
        let cogon = anchor_cogon(2);
        assert!(cogon.sem[2] > 0.8, "change: S3_VIBRACAO should be > 0.8");
    }

    #[test]
    fn test_anchor_uncertainty_has_high_unc() {
        let cogon = anchor_cogon(4);
        let avg_unc: f32 = cogon.unc.iter().sum::<f32>() / 32.0;
        assert!(avg_unc > 0.5, "uncertainty anchor should have high avg_unc");
    }

    #[test]
    fn test_compute_align_hash_deterministic() {
        let h1 = compute_align_hash("ATLAS");
        let h2 = compute_align_hash("ATLAS");
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_compute_align_hash_different_names() {
        let h_atlas = compute_align_hash("ATLAS");
        let h_cipher = compute_align_hash("CIPHER");
        assert_ne!(h_atlas, h_cipher);
    }

    #[test]
    fn test_new_sync_has_agent_info() {
        let agent_id = Uuid::new_v4();
        let msg = Msg1337::new_sync(agent_id, "ATLAS", "Strategic planner");
        assert_eq!(msg.sender, agent_id);
        assert!(matches!(msg.intent, Intent::Sync));
        // The agent name should be in the payload's raw field
        if let Payload::Cogon(cogon) = &msg.payload {
            let raw = cogon.raw.as_ref().unwrap();
            let name = raw.content["name"].as_str().unwrap();
            assert_eq!(name, "ATLAS");
        } else {
            panic!("expected Cogon payload");
        }
    }

    #[test]
    fn test_new_ack_embeds_hash() {
        let agent_id = Uuid::new_v4();
        let hash = compute_align_hash("FORGE");
        let msg = Msg1337::new_ack(agent_id, hash);
        assert!(matches!(msg.intent, Intent::Ack));
        assert_eq!(msg.c5.align_hash, hash);
    }
}
