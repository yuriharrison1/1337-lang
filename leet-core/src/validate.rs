//! Validation of MSG_1337 against rules R1–R21.
//!
//! Rules that require multi-message agent state (R13, R15, R16, R18) are
//! enforced at the operator/bridge layer, not here. This module validates
//! the structural integrity of a single message.

use std::collections::HashSet;

use crate::error::LeetError;
use crate::types::{Intent, Msg1337, Payload, RawRole};

/// Validate a MSG_1337 against all applicable structural rules.
///
/// Returns `Ok(())` if the message is valid, or the first rule violation found.
pub fn validate(msg: &Msg1337) -> Result<(), LeetError> {
    r2_delta_ref(msg)?;
    r3_dag_nodes_exist(msg)?;
    r4_no_cycles(msg)?;
    r5_low_confidence(msg)?;
    r6_urgency(msg)?;
    r7_zone_emergent_align_hash(msg)?;
    r8_broadcast(msg)?;
    r9_evidence_coherence(msg)?;
    r10_vector_dims(msg)?;
    r11_zone_emergent_append_only(msg)?;
    r12_emergent_no_reuse(msg)?;
    r14_dag_parents_first(msg)?;
    r17_canonical_serializable(msg)?;
    r19_inheritance_depth(msg)?;
    r20_cogon_zero_structure(msg)?;
    r21_bridge_no_exposure(msg)?;
    Ok(())
}

/// Returns low-confidence flag (R5) — triggered when P6_VETOR_TEMPORAL < 0.1.
pub fn check_confidence(msg: &Msg1337) -> Vec<LeetError> {
    let mut flags = Vec::new();
    let check = |c: &crate::types::Cogon| {
        if c.is_low_confidence() {
            Some(LeetError::R5LowConfidence { dim: 29, value: c.sem[29] })
        } else {
            None
        }
    };
    match &msg.payload {
        Payload::Cogon(c) => {
            if let Some(e) = check(c) { flags.push(e); }
        }
        Payload::Dag(dag) => {
            for node in &dag.nodes {
                if let Some(e) = check(node) { flags.push(e); }
            }
        }
    }
    flags
}

// ─── R2 ──────────────────────────────────────────────────────────────────────

fn r2_delta_ref(msg: &Msg1337) -> Result<(), LeetError> {
    let is_delta = msg.intent == Intent::Delta;
    if is_delta {
        if msg.ref_hash.is_none() || msg.patch.is_none() {
            return Err(LeetError::R2DeltaRefMismatch);
        }
    } else if msg.patch.is_some() {
        return Err(LeetError::R2NonDeltaPatch);
    }
    Ok(())
}

// ─── R3 ──────────────────────────────────────────────────────────────────────

fn r3_dag_nodes_exist(msg: &Msg1337) -> Result<(), LeetError> {
    if let Payload::Dag(dag) = &msg.payload {
        let node_ids: HashSet<_> = dag.nodes.iter().map(|n| n.id).collect();
        for edge in &dag.edges {
            if !node_ids.contains(&edge.from) {
                return Err(LeetError::R3MissingNode(edge.from));
            }
            if !node_ids.contains(&edge.to) {
                return Err(LeetError::R3MissingNode(edge.to));
            }
        }
    }
    Ok(())
}

// ─── R4 ──────────────────────────────────────────────────────────────────────

fn r4_no_cycles(msg: &Msg1337) -> Result<(), LeetError> {
    if let Payload::Dag(dag) = &msg.payload {
        // Clone to get mutable access for topo cache
        let mut dag_clone = dag.clone();
        dag_clone.topological_order()?;
    }
    Ok(())
}

// ─── R5 ──────────────────────────────────────────────────────────────────────

fn r5_low_confidence(_msg: &Msg1337) -> Result<(), LeetError> {
    // R5 produces warnings via check_confidence(), not hard validation errors.
    Ok(())
}

// ─── R6 ──────────────────────────────────────────────────────────────────────

fn r6_urgency(msg: &Msg1337) -> Result<(), LeetError> {
    if msg.surface.human_required && msg.surface.urgency.is_none() {
        return Err(LeetError::R6MissingUrgency);
    }
    Ok(())
}

// ─── R7 ──────────────────────────────────────────────────────────────────────

fn r7_zone_emergent_align_hash(msg: &Msg1337) -> Result<(), LeetError> {
    // If zone_emergent is non-empty, align_hash must be non-zero.
    if !msg.c5.zone_emergent.is_empty() {
        let zero = [0u8; 32];
        if msg.c5.align_hash == zero {
            return Err(LeetError::R7UnregisteredEmergent(uuid::Uuid::nil()));
        }
    }
    Ok(())
}

// ─── R8 ──────────────────────────────────────────────────────────────────────

fn r8_broadcast(msg: &Msg1337) -> Result<(), LeetError> {
    use crate::types::Receiver;
    if matches!(msg.receiver, Receiver::Broadcast) {
        let allowed = matches!(msg.intent, Intent::Anomaly | Intent::Sync);
        if !allowed {
            return Err(LeetError::R8InvalidBroadcast);
        }
    }
    Ok(())
}

// ─── R9 ──────────────────────────────────────────────────────────────────────

fn r9_evidence_coherence(msg: &Msg1337) -> Result<(), LeetError> {
    let check = |cogon: &crate::types::Cogon| -> Result<(), LeetError> {
        if let Some(raw) = &cogon.raw {
            if raw.role == RawRole::Evidence {
                if cogon.sem.iter().all(|&v| v < 0.01) {
                    return Err(LeetError::R9IncoherentEvidence);
                }
            }
        }
        Ok(())
    };
    match &msg.payload {
        Payload::Cogon(c) => check(c)?,
        Payload::Dag(dag) => {
            for node in &dag.nodes {
                check(node)?;
            }
        }
    }
    Ok(())
}

// ─── R10 ─────────────────────────────────────────────────────────────────────

fn r10_vector_dims(msg: &Msg1337) -> Result<(), LeetError> {
    // SemVec is [f32; 32] — compile-time guarantee. No runtime check needed.
    // This function exists to mirror the Python implementation explicitly.
    let _ = msg;
    Ok(())
}

// ─── R11 ─────────────────────────────────────────────────────────────────────

fn r11_zone_emergent_append_only(msg: &Msg1337) -> Result<(), LeetError> {
    for key in msg.c5.zone_emergent.keys() {
        // Emergent axes start from index 32 (fixed axes occupy 0-31).
        // zone_emergent uses Uuid keys in Rust, so all are valid by type.
        // The index constraint is enforced by EmergentRecord.index >= 32.
        let _ = key;
    }
    Ok(())
}

// ─── R12 ─────────────────────────────────────────────────────────────────────

fn r12_emergent_no_reuse(_msg: &Msg1337) -> Result<(), LeetError> {
    // Rust's HashMap<Uuid, f32> in C5Block naturally prevents key duplication.
    Ok(())
}

// ─── R14 ─────────────────────────────────────────────────────────────────────

fn r14_dag_parents_first(msg: &Msg1337) -> Result<(), LeetError> {
    if let Payload::Dag(dag) = &msg.payload {
        let mut dag_clone = dag.clone();
        let order = dag_clone.topological_order()?;

        // Build parent map
        let mut parents: std::collections::HashMap<uuid::Uuid, HashSet<uuid::Uuid>> =
            dag.nodes.iter().map(|n| (n.id, HashSet::new())).collect();
        for edge in &dag.edges {
            parents.entry(edge.to).or_default().insert(edge.from);
        }

        let mut processed = HashSet::new();
        for node_id in &order {
            if let Some(node_parents) = parents.get(node_id) {
                if !node_parents.is_subset(&processed) {
                    return Err(LeetError::R14ParentNotAbsorbed(*node_id));
                }
            }
            processed.insert(*node_id);
        }
    }
    Ok(())
}

// ─── R17 ─────────────────────────────────────────────────────────────────────

fn r17_canonical_serializable(msg: &Msg1337) -> Result<(), LeetError> {
    serde_json::to_string(msg)
        .map(|_| ())
        .map_err(|e| LeetError::SerializationError(e.to_string()))
}

// ─── R19 ─────────────────────────────────────────────────────────────────────

fn r19_inheritance_depth(msg: &Msg1337) -> Result<(), LeetError> {
    // Inheritance chain depth is tracked externally (agent history).
    // Structural check: a single message cannot exceed depth by itself.
    let _ = msg;
    Ok(())
}

// ─── R20 ─────────────────────────────────────────────────────────────────────

fn r20_cogon_zero_structure(msg: &Msg1337) -> Result<(), LeetError> {
    let check = |cogon: &crate::types::Cogon| -> Result<(), LeetError> {
        if cogon.id == uuid::Uuid::nil() {
            // This is COGON_ZERO — verify structure using is_zero()
            if !cogon.is_zero() {
                return Err(LeetError::R20MissingCogonZero);
            }
        }
        Ok(())
    };
    match &msg.payload {
        Payload::Cogon(c) => check(c)?,
        Payload::Dag(dag) => {
            for node in &dag.nodes {
                check(node)?;
            }
        }
    }
    Ok(())
}

// ─── R21 ─────────────────────────────────────────────────────────────────────

fn r21_bridge_no_exposure(msg: &Msg1337) -> Result<(), LeetError> {
    // Internal 1337 fields that must not appear in raw.content for bridge messages.
    const INTERNAL_KEYS: &[&str] = &["sem", "unc", "stamp", "cogon_id", "align_hash", "zone_fixed"];

    let check = |cogon: &crate::types::Cogon| -> Result<(), LeetError> {
        if let Some(raw) = &cogon.raw {
            if let serde_json::Value::Object(map) = &raw.content {
                for key in INTERNAL_KEYS {
                    if map.contains_key(*key) {
                        return Err(LeetError::R21BridgeExposure);
                    }
                }
            }
        }
        Ok(())
    };

    match &msg.payload {
        Payload::Cogon(c) => check(c)?,
        Payload::Dag(dag) => {
            for node in &dag.nodes {
                check(node)?;
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::*;
    use uuid::Uuid;

    fn base_msg(payload: Payload) -> Msg1337 {
        Msg1337 {
            id: Uuid::new_v4(),
            sender: Uuid::new_v4(),
            receiver: Receiver::Agent(Uuid::new_v4()),
            intent: Intent::Assert,
            ref_hash: None,
            patch: None,
            payload,
            c5: C5Block {
                zone_fixed: [0.5_f32; 32],
                zone_emergent: std::collections::HashMap::new(),
                schema_ver: "0.4.0".to_string(),
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

    fn simple_cogon() -> Cogon {
        Cogon {
            id: Uuid::new_v4(),
            sem: [0.5_f32; 32],
            stamp: 1_000_000,
            raw: None,
        }
    }

    #[test]
    fn test_valid_message_passes() {
        let msg = base_msg(Payload::Cogon(simple_cogon()));
        assert!(validate(&msg).is_ok());
    }

    #[test]
    fn test_r2_delta_requires_ref_and_patch() {
        let mut msg = base_msg(Payload::Cogon(simple_cogon()));
        msg.intent = Intent::Delta;
        assert!(matches!(validate(&msg), Err(LeetError::R2DeltaRefMismatch)));
    }

    #[test]
    fn test_r2_non_delta_no_patch() {
        let mut msg = base_msg(Payload::Cogon(simple_cogon()));
        msg.patch = Some([0.0_f32; 32]);
        assert!(matches!(validate(&msg), Err(LeetError::R2NonDeltaPatch)));
    }

    #[test]
    fn test_r6_urgency_required() {
        let mut msg = base_msg(Payload::Cogon(simple_cogon()));
        msg.surface.human_required = true;
        assert!(matches!(validate(&msg), Err(LeetError::R6MissingUrgency)));
    }

    #[test]
    fn test_r8_broadcast_only_anomaly_sync() {
        let mut msg = base_msg(Payload::Cogon(simple_cogon()));
        msg.receiver = Receiver::Broadcast;
        assert!(matches!(validate(&msg), Err(LeetError::R8InvalidBroadcast)));
        msg.intent = Intent::Anomaly;
        assert!(validate(&msg).is_ok());
    }

    #[test]
    fn test_r17_serializable() {
        let msg = base_msg(Payload::Cogon(simple_cogon()));
        assert!(validate(&msg).is_ok());
    }

    #[test]
    fn test_r21_bridge_no_exposure() {
        let mut cogon = simple_cogon();
        let content = serde_json::json!({
            "sem": vec![0.5_f32; 32],
            "other": "ok"
        });
        cogon.raw = Some(RawField {
            content_type: "application/json".to_string(),
            content,
            role: RawRole::Bridge,
        });
        let msg = base_msg(Payload::Cogon(cogon));
        assert!(matches!(validate(&msg), Err(LeetError::R21BridgeExposure)));
    }

    #[test]
    fn test_check_confidence_no_flag_for_normal() {
        let msg = base_msg(Payload::Cogon(simple_cogon()));
        // sem[29] = 0.5 (baseline) — not low confidence
        let flags = check_confidence(&msg);
        assert!(flags.is_empty());
    }

    #[test]
    fn test_check_confidence_flag_when_p6_below_threshold() {
        let mut cogon = simple_cogon();
        cogon.sem[29] = 0.05; // P6_VETOR_TEMPORAL below 0.1
        let msg = base_msg(Payload::Cogon(cogon));
        let flags = check_confidence(&msg);
        assert_eq!(flags.len(), 1);
    }
}
