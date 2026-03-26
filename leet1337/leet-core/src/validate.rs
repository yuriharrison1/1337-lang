use uuid::Uuid;

use crate::error::{LeetError, LeetResult};
use crate::types::{Intent, Msg1337, Payload, RawRole, Receiver};
use crate::FIXED_DIMS;

pub struct Validator;

impl Validator {
    /// Validate a MSG_1337 against rules R1-R21.
    /// Returns Ok(()) if valid, Err with the first violation found.
    pub fn validate(msg: &Msg1337) -> LeetResult<()> {
        Self::r2_delta_ref(msg)?;
        Self::r3_declared_nodes(msg)?;
        Self::r4_no_cycles(msg)?;
        Self::r6_urgency(msg)?;
        Self::r8_broadcast(msg)?;
        Self::r9_evidence_coherence(msg)?;
        Self::r10_vector_dims(msg)?;
        Ok(())
    }

    /// Soft confidence warnings — does NOT fail validation.
    /// Returns (cogon_id, dim_index, unc_value) for each low-confidence dimension.
    pub fn check_confidence(msg: &Msg1337) -> Vec<(Uuid, usize, f32)> {
        let mut warnings = Vec::new();
        match &msg.payload {
            Payload::Single(cogon) => {
                for (i, &u) in cogon.unc.iter().enumerate() {
                    if u > crate::LOW_CONFIDENCE_THRESHOLD {
                        warnings.push((cogon.id, i, u));
                    }
                }
            }
            Payload::Graph(dag) => {
                for cogon in &dag.nodes {
                    for (i, &u) in cogon.unc.iter().enumerate() {
                        if u > crate::LOW_CONFIDENCE_THRESHOLD {
                            warnings.push((cogon.id, i, u));
                        }
                    }
                }
            }
        }
        warnings
    }

    /// R2: DELTA requires ref+patch; non-DELTA forbids patch.
    fn r2_delta_ref(msg: &Msg1337) -> LeetResult<()> {
        if msg.intent == Intent::Delta {
            if msg.ref_hash.is_none() || msg.patch.is_none() {
                return Err(LeetError::R2DeltaRequiresRef);
            }
        } else if msg.patch.is_some() {
            return Err(LeetError::R2NonDeltaHasPatch);
        }
        Ok(())
    }

    /// R3: Every COGON referenced in a DAG must be in that DAG's nodes.
    fn r3_declared_nodes(msg: &Msg1337) -> LeetResult<()> {
        if let Payload::Graph(dag) = &msg.payload {
            let ids: std::collections::HashSet<Uuid> =
                dag.nodes.iter().map(|n| n.id).collect();
            // Check root is declared
            if !ids.contains(&dag.root) {
                return Err(LeetError::R3UndeclaredNode(dag.root.to_string()));
            }
            // Check all edge endpoints are declared
            for edge in &dag.edges {
                if !ids.contains(&edge.from) {
                    return Err(LeetError::R3UndeclaredNode(edge.from.to_string()));
                }
                if !ids.contains(&edge.to) {
                    return Err(LeetError::R3UndeclaredNode(edge.to.to_string()));
                }
            }
        }
        Ok(())
    }

    /// R4: DAG must be acyclic.
    fn r4_no_cycles(msg: &Msg1337) -> LeetResult<()> {
        if let Payload::Graph(dag) = &msg.payload {
            dag.topological_order()?;
        }
        Ok(())
    }

    /// R6: human_required=true requires urgency declared.
    fn r6_urgency(msg: &Msg1337) -> LeetResult<()> {
        if msg.surface.human_required && msg.surface.urgency.is_none() {
            return Err(LeetError::R6UrgencyRequired);
        }
        Ok(())
    }

    /// R8: BROADCAST only for ANOMALY or SYNC.
    fn r8_broadcast(msg: &Msg1337) -> LeetResult<()> {
        if msg.receiver.is_broadcast() {
            match msg.intent {
                Intent::Anomaly | Intent::Sync => {}
                _ => {
                    return Err(LeetError::R8InvalidBroadcast(
                        format!("{:?}", msg.intent),
                    ));
                }
            }
        }
        Ok(())
    }

    /// R9: RAW EVIDENCE must have non-zero semantic vector.
    fn r9_evidence_coherence(msg: &Msg1337) -> LeetResult<()> {
        let check_cogon = |cogon: &crate::types::Cogon| -> LeetResult<()> {
            if let Some(raw) = &cogon.raw {
                if raw.role == RawRole::Evidence {
                    let all_zero = cogon.sem.iter().all(|&s| s.abs() < 1e-10);
                    if all_zero {
                        return Err(LeetError::R9EvidenceIncoherent);
                    }
                }
            }
            Ok(())
        };

        match &msg.payload {
            Payload::Single(cogon) => check_cogon(cogon)?,
            Payload::Graph(dag) => {
                for cogon in &dag.nodes {
                    check_cogon(cogon)?;
                }
            }
        }
        Ok(())
    }

    /// R10: All VECTOR[32] must have exactly 32 dimensions.
    fn r10_vector_dims(msg: &Msg1337) -> LeetResult<()> {
        let check_vec = |v: &[f32], label: &str| -> LeetResult<()> {
            if v.len() != FIXED_DIMS {
                return Err(LeetError::R10DimensionMismatch(FIXED_DIMS, v.len()));
            }
            let _ = label;
            Ok(())
        };

        check_vec(&msg.c5.zone_fixed, "c5.zone_fixed")?;

        if let Some(patch) = &msg.patch {
            check_vec(patch, "patch")?;
        }

        match &msg.payload {
            Payload::Single(cogon) => {
                check_vec(&cogon.sem, "cogon.sem")?;
                check_vec(&cogon.unc, "cogon.unc")?;
            }
            Payload::Graph(dag) => {
                for cogon in &dag.nodes {
                    check_vec(&cogon.sem, "dag.node.sem")?;
                    check_vec(&cogon.unc, "dag.node.unc")?;
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use uuid::Uuid;

    use super::*;
    use crate::types::{
        CanonicalSpace, Cogon, Dag, Edge, EdgeType, Intent, Msg1337, Payload, Receiver, Surface,
    };

    fn make_valid_msg(intent: Intent) -> Msg1337 {
        let cogon = Cogon::new(vec![0.5f32; 32], vec![0.1f32; 32]);
        Msg1337 {
            id: Uuid::new_v4(),
            sender: Uuid::new_v4(),
            receiver: Receiver::Agent(Uuid::new_v4()),
            intent,
            ref_hash: None,
            patch: None,
            payload: Payload::Single(cogon),
            c5: CanonicalSpace {
                zone_fixed: vec![0.5f32; 32],
                zone_emergent: HashMap::new(),
                schema_ver: "0.4.0".to_string(),
                align_hash: "abc123".to_string(),
            },
            surface: Surface {
                human_required: false,
                urgency: None,
                reconstruct_depth: 3,
                lang: "pt".to_string(),
            },
        }
    }

    #[test]
    fn test_valid_assert() {
        let msg = make_valid_msg(Intent::Assert);
        assert!(Validator::validate(&msg).is_ok());
    }

    #[test]
    fn test_r2_delta_without_ref() {
        let mut msg = make_valid_msg(Intent::Delta);
        msg.ref_hash = None;
        msg.patch = None;
        assert!(matches!(
            Validator::validate(&msg),
            Err(LeetError::R2DeltaRequiresRef)
        ));
    }

    #[test]
    fn test_r2_non_delta_with_patch() {
        let mut msg = make_valid_msg(Intent::Assert);
        msg.patch = Some(vec![0.1f32; 32]);
        assert!(matches!(
            Validator::validate(&msg),
            Err(LeetError::R2NonDeltaHasPatch)
        ));
    }

    #[test]
    fn test_r2_delta_with_ref_ok() {
        let mut msg = make_valid_msg(Intent::Delta);
        msg.ref_hash = Some("deadbeef".to_string());
        msg.patch = Some(vec![0.0f32; 32]);
        assert!(Validator::validate(&msg).is_ok());
    }

    #[test]
    fn test_r4_dag_cycle() {
        let a = Cogon::new(vec![0.5f32; 32], vec![0.1f32; 32]);
        let b = Cogon::new(vec![0.5f32; 32], vec![0.1f32; 32]);
        let a_id = a.id;
        let b_id = b.id;

        let mut dag = Dag::from_root(a);
        dag.add_node(b);
        dag.add_edge(Edge { from: a_id, to: b_id, edge_type: EdgeType::Causa, weight: 0.9 });
        dag.add_edge(Edge { from: b_id, to: a_id, edge_type: EdgeType::Causa, weight: 0.9 }); // cycle!

        let mut msg = make_valid_msg(Intent::Assert);
        msg.payload = Payload::Graph(dag);
        assert!(matches!(Validator::validate(&msg), Err(LeetError::R4DagCycle)));
    }

    #[test]
    fn test_r6_human_required_no_urgency() {
        let mut msg = make_valid_msg(Intent::Assert);
        msg.surface.human_required = true;
        msg.surface.urgency = None;
        assert!(matches!(
            Validator::validate(&msg),
            Err(LeetError::R6UrgencyRequired)
        ));
    }

    #[test]
    fn test_r6_human_required_with_urgency_ok() {
        let mut msg = make_valid_msg(Intent::Assert);
        msg.surface.human_required = true;
        msg.surface.urgency = Some(0.85);
        assert!(Validator::validate(&msg).is_ok());
    }

    #[test]
    fn test_r8_broadcast_assert_fails() {
        let mut msg = make_valid_msg(Intent::Assert);
        msg.receiver = Receiver::Broadcast;
        assert!(matches!(
            Validator::validate(&msg),
            Err(LeetError::R8InvalidBroadcast(_))
        ));
    }

    #[test]
    fn test_r8_broadcast_anomaly_ok() {
        let mut msg = make_valid_msg(Intent::Anomaly);
        msg.receiver = Receiver::Broadcast;
        assert!(Validator::validate(&msg).is_ok());
    }

    #[test]
    fn test_r8_broadcast_sync_ok() {
        let mut msg = make_valid_msg(Intent::Sync);
        msg.receiver = Receiver::Broadcast;
        assert!(Validator::validate(&msg).is_ok());
    }

    #[test]
    fn test_r10_wrong_dims() {
        let cogon = Cogon::new(vec![0.5f32; 16], vec![0.1f32; 16]); // wrong dims
        let mut msg = make_valid_msg(Intent::Assert);
        msg.payload = Payload::Single(cogon);
        assert!(matches!(
            Validator::validate(&msg),
            Err(LeetError::R10DimensionMismatch(32, 16))
        ));
    }
}
