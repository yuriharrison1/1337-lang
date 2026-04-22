//! Projector trait and built-in implementations.

use leet_core::{Cogon, LeetError, SemVec};
use uuid::Uuid;

/// Trait for text ↔ semantic vector translation.
pub trait BridgeProjector: Send + Sync {
    /// Project human text into a COGON.
    fn project(&self, text: &str) -> Result<Cogon, LeetError>;

    /// Reconstruct human text from a COGON.
    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError>;
}

/// Deterministic mock projector for tests — no network, no API.
///
/// Uses keyword heuristics to fill semantic axes, mirroring the Python
/// `MockProjector` in `python/leet/bridge.py`.
pub struct MockProjector;

impl BridgeProjector for MockProjector {
    fn project(&self, text: &str) -> Result<Cogon, LeetError> {
        let lower = text.to_lowercase();
        let mut sem: SemVec = [0.5_f32; 32];
        let mut unc: SemVec = [0.2_f32; 32];

        // D1_ESTADO / P3_ANOMALIA — error/down keywords
        if lower.contains("caiu")
            || lower.contains("falhou")
            || lower.contains("erro")
            || lower.contains("down")
        {
            sem[8] = 0.9;   // D1_ESTADO
            sem[26] = 0.9;  // P3_ANOMALIA
            sem[13] = 0.15; // D6_VALENCIA_ONT (negative)
            unc[8] = 0.1;
            unc[26] = 0.1;
        }

        // D2_PROCESSO / P7_ACAO — process keywords
        if lower.contains("deploy")
            || lower.contains("processo")
            || lower.contains("pipeline")
        {
            sem[9] = 0.85;  // D2_PROCESSO
            sem[30] = 0.8;  // P7_ACAO (active process)
            unc[9] = 0.1;
        }

        // G4_REVERSIBILIDADE / P7_ACAO — rollback keywords
        if lower.contains("reverter")
            || lower.contains("desfazer")
            || lower.contains("rollback")
        {
            sem[19] = 0.9;  // G4_REVERSIBILIDADE
            sem[30] = 0.85; // P7_ACAO
            unc[19] = 0.1;
        }

        // G8_URGENCIA — urgency keywords
        if lower.contains("urgente") || lower.contains("crítico") || lower.contains("agora") {
            sem[23] = 0.95; // G8_URGENCIA
            unc[23] = 0.05;
        }

        Ok(Cogon {
            id: Uuid::new_v4(),
            sem,
            unc,
            stamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos() as i64)
                .unwrap_or(0),
            raw: None,
        })
    }

    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError> {
        // Find top-3 activated axes and build a label string
        let mut indexed: Vec<(usize, f32)> = cogon
            .sem
            .iter()
            .enumerate()
            .map(|(i, &v)| (i, v))
            .collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        let top3: Vec<String> = indexed
            .iter()
            .take(3)
            .filter(|(_, v)| *v > 0.5)
            .map(|(i, v)| format!("axis[{}]={:.2}", i, v))
            .collect();

        if top3.is_empty() {
            Ok("[neutral cogon]".to_string())
        } else {
            Ok(format!("[cogon: {}]", top3.join(", ")))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_project_error_keywords() {
        let proj = MockProjector;
        let cogon = proj.project("o servidor caiu").unwrap();
        assert!(cogon.sem[8] > 0.8);  // D1_ESTADO
        assert!(cogon.sem[26] > 0.8); // P3_ANOMALIA
        assert!(cogon.sem[13] < 0.3); // D6_VALENCIA_ONT negative
    }

    #[test]
    fn test_mock_reconstruct_non_empty() {
        let proj = MockProjector;
        let cogon = proj.project("deploy do pipeline").unwrap();
        let text = proj.reconstruct(&cogon).unwrap();
        assert!(!text.is_empty());
        assert!(text.contains("axis["));
    }

    #[test]
    fn test_mock_project_neutral() {
        let proj = MockProjector;
        let cogon = proj.project("").unwrap();
        // All axes should be at baseline 0.5
        assert!(cogon.sem.iter().all(|&v| (v - 0.5).abs() < 0.01));
    }
}
