//! Projection engine — text → semantic vector and reconstruction.
//!
//! Uses the same keyword heuristics as leet-bridge/src/heuristics.rs.

use leet_core::axes::CANONICAL_AXES;

/// Project human text into (sem[32], unc[32]).
pub fn project(text: &str, _agent_id: &str) -> (Vec<f32>, Vec<f32>) {
    let lower = text.to_lowercase();
    let mut sem = vec![0.5_f32; 32];
    let mut unc = vec![0.2_f32; 32];

    // A8_ESTADO / C5_ANOMALIA — error/down keywords
    if lower.contains("caiu")
        || lower.contains("falhou")
        || lower.contains("erro")
        || lower.contains("down")
        || lower.contains("crash")
    {
        sem[8] = 0.9;   // A8_ESTADO
        sem[26] = 0.9;  // C5_ANOMALIA
        sem[13] = 0.15; // A13_VALENCIA_ONTOLOGICA (negative)
        unc[8] = 0.1;
        unc[26] = 0.1;
        unc[13] = 0.1;
    }

    // A9_PROCESSO / C9_NATUREZA — process keywords
    if lower.contains("deploy")
        || lower.contains("processo")
        || lower.contains("pipeline")
        || lower.contains("rodando")
    {
        sem[9] = 0.85;  // A9_PROCESSO
        sem[30] = 0.8;  // C9_NATUREZA (verb/action)
        unc[9] = 0.1;
        unc[30] = 0.15;
    }

    // B5_REVERSIBILIDADE / C3_ACAO — rollback keywords
    if lower.contains("reverter")
        || lower.contains("desfazer")
        || lower.contains("rollback")
        || lower.contains("undo")
    {
        sem[17] = 0.9;  // B5_REVERSIBILIDADE
        sem[24] = 0.85; // C3_ACAO
        unc[17] = 0.1;
        unc[24] = 0.1;
    }

    // C1_URGENCIA — urgency keywords
    if lower.contains("urgente")
        || lower.contains("crítico")
        || lower.contains("agora")
        || lower.contains("imediato")
    {
        sem[22] = 0.95; // C1_URGENCIA
        unc[22] = 0.05;
    }

    (sem, unc)
}

/// Reconstruct a text description from sem/unc vectors.
/// Finds the top-3 most activated axes and returns a textual description.
pub fn reconstruct(sem: &[f32], _unc: &[f32], lang: &str) -> String {
    if sem.is_empty() {
        return "[empty cogon]".to_string();
    }

    // Sort axes by sem value descending
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
            let axis_name = CANONICAL_AXES.get(*i)
                .map(|a| a.name)
                .unwrap_or("UNKNOWN");
            if lang == "pt" || lang.starts_with("pt") {
                format!("{}={:.2}", axis_name, v)
            } else {
                format!("axis[{}]={:.2}", i, v)
            }
        })
        .collect();

    if top3.is_empty() {
        "[neutral cogon]".to_string()
    } else {
        format!("[cogon: {}]", top3.join(", "))
    }
}

/// Projection engine struct (for use with BatchQueue).
pub struct Engine;

impl Engine {
    pub fn new() -> Self {
        Engine
    }

    pub fn project(&self, text: &str, agent_id: &str) -> (Vec<f32>, Vec<f32>) {
        project(text, agent_id)
    }

    pub fn reconstruct(&self, sem: &[f32], unc: &[f32], lang: &str) -> String {
        reconstruct(sem, unc, lang)
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
        let (sem, unc) = project("hello world", "agent1");
        assert_eq!(sem.len(), 32);
        assert_eq!(unc.len(), 32);
    }

    #[test]
    fn test_project_urgente_activates_c1() {
        let (sem, _) = project("urgente agora", "agent1");
        assert!(sem[22] > 0.9, "C1_URGENCIA should be activated");
    }

    #[test]
    fn test_project_erro_activates_anomalia() {
        let (sem, _) = project("erro no sistema", "agent1");
        assert!(sem[26] > 0.8, "C5_ANOMALIA should be activated");
        assert!(sem[8] > 0.8, "A8_ESTADO should be activated");
    }

    #[test]
    fn test_reconstruct_returns_string() {
        let sem = vec![0.5_f32; 32];
        let unc = vec![0.2_f32; 32];
        let result = reconstruct(&sem, &unc, "en");
        assert!(!result.is_empty());
    }
}
