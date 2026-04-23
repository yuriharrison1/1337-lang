//! Protocol support: 5 anchor COGONs, C5 handshake factory methods (v0.5.1).
//!
//! - Five immutable anchor COGONs for canonical alignment
//! - Msg1337 factory constructors for the C5 handshake phases
//! - `compute_align_hash` — deterministic fingerprint per agent

use std::collections::HashMap;

use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::types::{
    C5Block, Cogon, Intent, Msg1337, Payload, RawField, RawRole, Receiver, SurfaceBlock,
};

// ── Anchor COGONs ─────────────────────────────────────────────────────────────

/// Names of the 5 immutable anchor concepts (transmitted in ECHO phase).
pub const ANCHOR_NAMES: [&str; 5] = [
    "presence",    // Something exists now
    "absence",     // Something does not exist
    "change",      // Previous state ≠ current state
    "agency",      // There is an actor causing something
    "uncertainty", // Degree of unknowing
];

/// Generate the nth anchor COGON (v0.5.1 projection).
///
/// Each anchor has a distinctive semantic fingerprint on the 32 axes
/// derived from the v0.5.1 spec § 12 table. Axes not listed default to 0.5.
pub fn anchor_cogon(index: usize) -> Cogon {
    let mut sem = [0.5_f32; 32];

    match index {
        0 => {
            // presence
            sem[0]  = 1.0;  // S1 ESSENCE
            sem[4]  = 0.0;  // S5 RHYTHM
            sem[6]  = 1.0;  // S7 GENERATIVITY
            sem[11] = 1.0;  // D4 SIGNAL
            sem[14] = 1.0;  // D7 CAUSALITY
            sem[16] = 1.0;  // G1 TEMPORALITY
            sem[17] = 0.5;  // G2 TEMPORAL_ANCHOR
            sem[19] = 0.5;  // G4 REVERSIBILITY
            sem[27] = 0.0;  // P4 AFFECT
            sem[29] = 1.0;  // P6 TEMPORAL_VECTOR
            sem[30] = 0.0;  // P7 ACTION
        }
        1 => {
            // absence
            sem[0]  = 0.0;  // S1 ESSENCE
            sem[4]  = 0.0;  // S5 RHYTHM
            sem[6]  = 1.0;  // S7 GENERATIVITY
            sem[11] = 1.0;  // D4 SIGNAL
            sem[14] = 0.8;  // D7 CAUSALITY
            sem[16] = 0.3;  // G1 TEMPORALITY
            sem[17] = 0.5;  // G2 TEMPORAL_ANCHOR
            sem[18] = 0.0;  // G3 COMPLETENESS
            sem[19] = 0.5;  // G4 REVERSIBILITY
            sem[29] = 1.0;  // P6 TEMPORAL_VECTOR
            sem[30] = 0.0;  // P7 ACTION
        }
        2 => {
            // change
            sem[0]  = 0.5;  // S1 ESSENCE
            sem[4]  = 0.5;  // S5 RHYTHM
            sem[9]  = 1.0;  // D2 PROCESS
            sem[10] = 0.7;  // D3 RELATION
            sem[11] = 0.0;  // D4 SIGNAL
            sem[14] = 0.3;  // D7 CAUSALITY
            sem[15] = 0.0;  // D8 VERIFIABILITY
            sem[17] = 0.3;  // G2 TEMPORAL_ANCHOR
            sem[19] = 0.5;  // G4 REVERSIBILITY
            sem[23] = 1.0;  // G8 URGENCY
            sem[30] = 0.3;  // P7 ACTION
        }
        3 => {
            // agency
            sem[0]  = 1.0;  // S1 ESSENCE
            sem[4]  = 0.2;  // S5 RHYTHM
            sem[9]  = 0.6;  // D2 PROCESS
            sem[13] = 1.0;  // D6 ONTOLOGICAL_VALENCE
            sem[14] = 0.9;  // D7 CAUSALITY
            sem[16] = 0.8;  // G1 TEMPORALITY
            sem[17] = 0.7;  // G2 TEMPORAL_ANCHOR
            sem[18] = 0.8;  // G3 COMPLETENESS
            sem[23] = 0.7;  // G8 URGENCY
            sem[29] = 0.8;  // P6 TEMPORAL_VECTOR
            sem[30] = 0.9;  // P7 ACTION
        }
        4 => {
            // uncertainty
            sem[4]  = 1.0;  // S5 RHYTHM
            sem[5]  = 0.2;  // S6 CAUSE_EFFECT
            sem[6]  = 0.2;  // S7 GENERATIVITY
            sem[11] = 0.2;  // D4 SIGNAL
            sem[14] = 0.1;  // D7 CAUSALITY
            sem[17] = 0.2;  // G2 TEMPORAL_ANCHOR
            sem[22] = 0.1;  // G7 EPISTEMIC_VALENCE
            sem[24] = 0.9;  // P1 IMPACT
            sem[27] = 0.8;  // P4 AFFECT
            sem[29] = 0.1;  // P6 TEMPORAL_VECTOR
            sem[30] = 0.0;  // P7 ACTION
        }
        _ => {} // out of range: all-neutral 0.5
    }

    Cogon {
        id: Uuid::new_v4(),
        sem,
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
                zone_fixed: crate::axes::boot_vector(),
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash: [0u8; 32],
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "en".to_string(),
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
                zone_fixed: crate::axes::boot_vector(),
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash,
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "en".to_string(),
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
                zone_fixed: crate::axes::boot_vector(),
                zone_emergent: HashMap::new(),
                schema_ver: "0.5.1".to_string(),
                align_hash: [0u8; 32],
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "en".to_string(),
            },
        }
    }

    /// Build an ASSERT message carrying a text payload in a COGON's raw field.
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
                zone_fixed: crate::axes::boot_vector(),
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
        let c = anchor_cogon(0);
        assert_eq!(c.sem[0],  1.0, "S1_ESSENCE");
        assert_eq!(c.sem[16], 1.0, "G1_TEMPORALITY");
        assert_eq!(c.sem[29], 1.0, "P6_TEMPORAL_VECTOR");
    }

    #[test]
    fn test_anchor_absence_has_low_essencia() {
        let c = anchor_cogon(1);
        assert_eq!(c.sem[0],  0.0, "S1_ESSENCE");
        assert_eq!(c.sem[18], 0.0, "G3_COMPLETENESS");
    }

    #[test]
    fn test_anchor_change_has_high_vibracao() {
        let c = anchor_cogon(2);
        assert_eq!(c.sem[9],  1.0, "D2_PROCESS");
        assert_eq!(c.sem[23], 1.0, "G8_URGENCY");
        assert_eq!(c.sem[11], 0.0, "D4_SIGNAL low");
    }

    #[test]
    fn test_anchor_uncertainty_has_p3_anomalia() {
        let c = anchor_cogon(4);
        assert_eq!(c.sem[29], 0.1, "P6_TEMPORAL_VECTOR low");
        assert_eq!(c.sem[4],  1.0, "S5_RHYTHM max");
        assert_eq!(c.sem[27], 0.8, "P4_AFFECT high");
    }

    #[test]
    fn test_anchors_respect_axis_range_0_1() {
        for i in 0..5 {
            let c = anchor_cogon(i);
            for (j, &v) in c.sem.iter().enumerate() {
                assert!(v >= 0.0 && v <= 1.0, "anchor {i} sem[{j}]={v} out of range");
            }
        }
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
        if let Payload::Cogon(cogon) = &msg.payload {
            let raw = cogon.raw.as_ref().unwrap();
            let name = raw.content["name"].as_str().unwrap();
            assert_eq!(name, "ATLAS");
        } else {
            panic!("expected Cogon payload");
        }
    }

    #[test]
    fn test_new_sync_uses_boot_vector_for_zone_fixed() {
        let agent_id = Uuid::new_v4();
        let msg = Msg1337::new_sync(agent_id, "FORGE", "Builder");
        assert_eq!(msg.c5.zone_fixed[24], 0.8, "P1_IMPACT boot");
        assert_eq!(msg.c5.zone_fixed[22], 0.1, "G7_EPISTEMIC_VALENCE boot");
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
