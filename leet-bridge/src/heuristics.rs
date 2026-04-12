//! Keyword-to-axis heuristics for the MockProjector.
//!
//! Each entry maps a set of keywords to an axis index and the activation
//! value to apply. Used by `MockProjector::project()`.

/// Axis indices (mirrors python/leet/axes.py constants).
pub mod axes {
    pub const A8_ESTADO: usize = 8;
    pub const A9_PROCESSO: usize = 9;
    pub const A13_VALENCIA_ONTOLOGICA: usize = 13;
    pub const B5_REVERSIBILIDADE: usize = 17;
    pub const C1_URGENCIA: usize = 22;
    pub const C3_ACAO: usize = 24;
    pub const C5_ANOMALIA: usize = 26;
    pub const C9_NATUREZA: usize = 30;
}

/// A single keyword heuristic rule.
pub struct Rule {
    pub keywords: &'static [&'static str],
    pub axis: usize,
    pub sem_value: f32,
    pub unc_value: f32,
}

/// All heuristic rules, evaluated in order.
pub const RULES: &[Rule] = &[
    Rule {
        keywords: &["caiu", "falhou", "erro", "down", "crash"],
        axis: axes::A8_ESTADO,
        sem_value: 0.9,
        unc_value: 0.1,
    },
    Rule {
        keywords: &["caiu", "falhou", "erro", "down", "crash"],
        axis: axes::C5_ANOMALIA,
        sem_value: 0.9,
        unc_value: 0.1,
    },
    Rule {
        keywords: &["deploy", "processo", "pipeline", "rodando"],
        axis: axes::A9_PROCESSO,
        sem_value: 0.85,
        unc_value: 0.1,
    },
    Rule {
        keywords: &["deploy", "processo", "pipeline", "rodando"],
        axis: axes::C9_NATUREZA,
        sem_value: 0.8,
        unc_value: 0.15,
    },
    Rule {
        keywords: &["reverter", "desfazer", "rollback", "undo"],
        axis: axes::B5_REVERSIBILIDADE,
        sem_value: 0.9,
        unc_value: 0.1,
    },
    Rule {
        keywords: &["reverter", "desfazer", "rollback", "undo"],
        axis: axes::C3_ACAO,
        sem_value: 0.85,
        unc_value: 0.1,
    },
    Rule {
        keywords: &["urgente", "crítico", "agora", "imediato"],
        axis: axes::C1_URGENCIA,
        sem_value: 0.95,
        unc_value: 0.05,
    },
];

/// Apply all matching heuristic rules to a sem/unc pair.
pub fn apply_rules(text: &str, sem: &mut [f32; 32], unc: &mut [f32; 32]) {
    let lower = text.to_lowercase();
    for rule in RULES {
        if rule.keywords.iter().any(|kw| lower.contains(kw)) {
            sem[rule.axis] = rule.sem_value;
            unc[rule.axis] = rule.unc_value;
        }
    }
}
