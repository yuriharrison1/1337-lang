//! Projection engine — text → semantic vector and reconstruction.
//!
//! Delegates text projection to leet-bridge's nl_translator (80+ heuristic rules).
//! When W.bin is available (LEET_W_PATH or default locations), the calibrated
//! W matrix path in leet-bridge/src/projector.rs takes over automatically.
//!
//! Reconstruction uses canonical axis names from leet-core.

use leet_bridge::nl_to_cogon;
use leet_core::axes::CANONICAL_AXES;

/// Project human text into sem[32] via leet-bridge heuristics.
pub fn project(text: &str, _agent_id: &str) -> Vec<f32> {
    nl_to_cogon(text, "en").sem.to_vec()
}

/// Reconstruct a text description from a sem vector.
///
/// Returns the top-3 activated axes (above 0.5) formatted as
/// `[cogon: AXIS_NAME=value, ...]`, or `[neutral cogon]` if none exceed 0.5.
pub fn reconstruct(sem: &[f32], _lang: &str) -> String {
    if sem.is_empty() {
        return "[empty cogon]".to_string();
    }

    let mut indexed: Vec<(usize, f32)> = sem
        .iter()
        .enumerate()
        .map(|(i, &v)| (i, v))
        .collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    let top3: Vec<String> = indexed
        .iter()
        .take(3)
        .filter(|(_, v)| *v > 0.5)
        .map(|(i, v)| {
            let label = CANONICAL_AXES.get(*i)
                .map(|a| format!("{}_{}", a.code, a.name))
                .unwrap_or_else(|| format!("axis[{}]", i));
            format!("{}={:.2}", label, v)
        })
        .collect();

    if top3.is_empty() {
        "[neutral cogon]".to_string()
    } else {
        format!("[cogon: {}]", top3.join(", "))
    }
}

/// Projection engine struct (for use with BatchQueue and LeetServiceImpl).
pub struct Engine;

impl Engine {
    pub fn new() -> Self {
        Engine
    }

    pub fn project(&self, text: &str, agent_id: &str) -> Vec<f32> {
        project(text, agent_id)
    }

    pub fn reconstruct(&self, sem: &[f32], lang: &str) -> String {
        reconstruct(sem, lang)
    }
}

impl Default for Engine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_returns_32_dims() {
        let sem = project("hello world", "agent1");
        assert_eq!(sem.len(), 32);
    }

    #[test]
    fn test_project_urgente_activates_g8_urgency() {
        let sem = project("urgente agora", "agent1");
        assert!(sem[23] > 0.9, "G8_URGENCY should be activated, got {}", sem[23]);
    }

    #[test]
    fn test_project_erro_activates_p3_anomaly() {
        let sem = project("erro no sistema", "agent1");
        assert!(sem[26] > 0.8, "P3_ANOMALY should be activated, got {}", sem[26]);
    }

    #[test]
    fn test_project_deploy_activates_d2_process() {
        let sem = project("deploy do pipeline", "agent1");
        assert!(sem[9] > 0.8, "D2_PROCESS should be activated, got {}", sem[9]);
    }

    #[test]
    fn test_project_rollback_activates_g4_reversibility() {
        let sem = project("reverter o deploy", "agent1");
        assert!(sem[19] > 0.8, "G4_REVERSIBILITY should be activated, got {}", sem[19]);
    }

    #[test]
    fn test_reconstruct_returns_string() {
        let sem = vec![0.5_f32; 32];
        let result = reconstruct(&sem, "en");
        assert!(!result.is_empty());
    }

    #[test]
    fn test_reconstruct_shows_canonical_axis_names() {
        let mut sem = vec![0.3_f32; 32];
        sem[23] = 0.95; // G8_URGENCY
        let result = reconstruct(&sem, "en");
        assert!(result.contains("G8_URGENCY"), "expected canonical name, got: {}", result);
    }
}
