//! Keyword-to-axis heuristics for the MockProjector.
//!
//! Each entry maps a set of keywords to an axis index and the activation
//! value to apply. Used by `MockProjector::project()`.

/// Axis indices (v0.5.1 names).
pub mod axes {
    pub const D1_ESTADO: usize = 8;
    pub const D2_PROCESSO: usize = 9;
    pub const D6_VALENCIA_ONT: usize = 13;
    pub const G4_REVERSIBILIDADE: usize = 19;
    pub const G8_URGENCIA: usize = 23;
    pub const P3_ANOMALIA: usize = 26;
    pub const P7_ACAO: usize = 30;
}

/// A single keyword heuristic rule.
pub struct Rule {
    pub keywords: &'static [&'static str],
    pub axis: usize,
    pub sem_value: f32,
}

/// All heuristic rules, evaluated in order.
pub const RULES: &[Rule] = &[
    Rule { keywords: &["caiu", "falhou", "erro", "down", "crash"], axis: axes::D1_ESTADO,   sem_value: 0.9  },
    Rule { keywords: &["caiu", "falhou", "erro", "down", "crash"], axis: axes::P3_ANOMALIA, sem_value: 0.9  },
    Rule { keywords: &["deploy", "processo", "pipeline", "rodando"], axis: axes::D2_PROCESSO, sem_value: 0.85 },
    Rule { keywords: &["deploy", "processo", "pipeline", "rodando"], axis: axes::P7_ACAO,    sem_value: 0.8  },
    Rule { keywords: &["reverter", "desfazer", "rollback", "undo"], axis: axes::G4_REVERSIBILIDADE, sem_value: 0.9  },
    Rule { keywords: &["reverter", "desfazer", "rollback", "undo"], axis: axes::P7_ACAO,            sem_value: 0.85 },
    Rule { keywords: &["urgente", "crítico", "agora", "imediato"], axis: axes::G8_URGENCIA,  sem_value: 0.95 },
];

/// Apply all matching heuristic rules to a sem vector.
pub fn apply_rules(text: &str, sem: &mut [f32; 32]) {
    let lower = text.to_lowercase();
    for rule in RULES {
        if rule.keywords.iter().any(|kw| lower.contains(kw)) {
            sem[rule.axis] = rule.sem_value;
        }
    }
}
