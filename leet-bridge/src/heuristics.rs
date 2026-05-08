//! Keyword heuristics — fallback path for projection.
//!
//! NOTE (v0.5.1): the rules below were originally calibrated for v0.4 axis
//! semantics (e.g. "rollback" mapped to G4 when the axis had a different name). After the
//! v0.5.1 axis substitution, some rules now point at axes whose semantics
//! shifted (G4 became TEMPORALITY). The wire format and indices are correct;
//! only the semantic crispness of these heuristics is reduced. Calibrated W
//! (PROMPT_06) is the long-term replacement. Do NOT delete these rules
//! before W is in place — they remain the active fallback.

/// Axis indices (v0.5.1 names).
pub mod axes {
    pub const D1_CONNECTION_WEIGHT: usize = 8;   // was D1_STATE
    pub const D2_LEARNING_RATE:     usize = 9;   // was D2_PROCESS
    pub const D6_PROPAGATION:       usize = 13;  // renamed from v0.4
    pub const G4_TEMPORALITY:       usize = 19;  // renamed from v0.4
    pub const G8_GRADIENT:          usize = 23;  // was G8_URGENCY
    pub const P3_COMPRESSION:       usize = 26;  // was P3_ANOMALY
    pub const P7_ACTION:            usize = 30;
}

/// A single keyword heuristic rule.
pub struct Rule {
    pub keywords: &'static [&'static str],
    pub axis: usize,
    pub sem_value: f32,
}

/// All heuristic rules, evaluated in order.
pub const RULES: &[Rule] = &[
    Rule { keywords: &["caiu", "falhou", "erro", "down", "crash"], axis: axes::D1_CONNECTION_WEIGHT, sem_value: 0.9  },
    Rule { keywords: &["caiu", "falhou", "erro", "down", "crash"], axis: axes::P3_COMPRESSION,       sem_value: 0.9  },
    Rule { keywords: &["deploy", "processo", "pipeline", "rodando"], axis: axes::D2_LEARNING_RATE,   sem_value: 0.85 },
    Rule { keywords: &["deploy", "processo", "pipeline", "rodando"], axis: axes::P7_ACTION,           sem_value: 0.8  },
    Rule { keywords: &["reverter", "desfazer", "rollback", "undo"], axis: axes::G4_TEMPORALITY,      sem_value: 0.9  },
    Rule { keywords: &["reverter", "desfazer", "rollback", "undo"], axis: axes::P7_ACTION,            sem_value: 0.85 },
    Rule { keywords: &["urgente", "crítico", "agora", "imediato"], axis: axes::G8_GRADIENT,           sem_value: 0.95 },
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
