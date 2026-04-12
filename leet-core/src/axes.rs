/// Axis group classification.
#[derive(Debug, Clone, PartialEq)]
pub enum AxisGroup {
    Ontological,
    Epistemic,
    Pragmatic,
}

/// Metadata for one canonical axis.
#[derive(Debug, Clone)]
pub struct AxisInfo {
    pub index: usize,
    pub code: &'static str,
    pub name: &'static str,
    pub group: AxisGroup,
    pub description: &'static str,
}

/// All 32 canonical axes in index order (R10 — indexed by position).
pub const CANONICAL_AXES: [AxisInfo; 32] = [
    // ── Group A — Ontological (0–13) ──────────────────────────────────────
    AxisInfo {
        index: 0, code: "A0", name: "VIA", group: AxisGroup::Ontological,
        description: "Degree concept exists by itself, independent of external relations",
    },
    AxisInfo {
        index: 1, code: "A1", name: "CORRESPONDÊNCIA", group: AxisGroup::Ontological,
        description: "Degree concept mirrors patterns at other abstraction levels",
    },
    AxisInfo {
        index: 2, code: "A2", name: "VIBRAÇÃO", group: AxisGroup::Ontological,
        description: "Degree concept is in continuous motion/transformation",
    },
    AxisInfo {
        index: 3, code: "A3", name: "POLARIDADE", group: AxisGroup::Ontological,
        description: "Degree concept is positioned on a spectrum between extremes",
    },
    AxisInfo {
        index: 4, code: "A4", name: "RITMO", group: AxisGroup::Ontological,
        description: "Degree concept exhibits cyclic or periodic pattern",
    },
    AxisInfo {
        index: 5, code: "A5", name: "CAUSA E EFEITO", group: AxisGroup::Ontological,
        description: "Degree concept is causal agent vs effect",
    },
    AxisInfo {
        index: 6, code: "A6", name: "GÊNERO", group: AxisGroup::Ontological,
        description: "Degree concept is generative/active vs receptive/passive",
    },
    AxisInfo {
        index: 7, code: "A7", name: "SISTEMA", group: AxisGroup::Ontological,
        description: "Degree concept is a set with emergent behavior",
    },
    AxisInfo {
        index: 8, code: "A8", name: "ESTADO", group: AxisGroup::Ontological,
        description: "Degree concept is a configuration at a given moment",
    },
    AxisInfo {
        index: 9, code: "A9", name: "PROCESSO", group: AxisGroup::Ontological,
        description: "Degree concept is transformation over time",
    },
    AxisInfo {
        index: 10, code: "A10", name: "RELAÇÃO", group: AxisGroup::Ontological,
        description: "Degree concept is connection between entities",
    },
    AxisInfo {
        index: 11, code: "A11", name: "SINAL", group: AxisGroup::Ontological,
        description: "Degree concept is information carrying variation",
    },
    AxisInfo {
        index: 12, code: "A12", name: "ESTABILIDADE", group: AxisGroup::Ontological,
        description: "Degree concept tends toward equilibrium or divergence",
    },
    AxisInfo {
        index: 13, code: "A13", name: "VALÊNCIA ONTOLÓGICA", group: AxisGroup::Ontological,
        description: "Intrinsic sign: 0=negative → 0.5=neutral → 1=positive",
    },
    // ── Group B — Epistemic (14–21) ───────────────────────────────────────
    AxisInfo {
        index: 14, code: "B1", name: "VERIFICABILIDADE", group: AxisGroup::Epistemic,
        description: "Can be externally confirmed?",
    },
    AxisInfo {
        index: 15, code: "B2", name: "TEMPORALIDADE", group: AxisGroup::Epistemic,
        description: "Has defined temporal anchor?",
    },
    AxisInfo {
        index: 16, code: "B3", name: "COMPLETUDE", group: AxisGroup::Epistemic,
        description: "Resolved or open?",
    },
    AxisInfo {
        index: 17, code: "B4", name: "CAUSALIDADE", group: AxisGroup::Epistemic,
        description: "Origin identifiable?",
    },
    AxisInfo {
        index: 18, code: "B5", name: "REVERSIBILIDADE", group: AxisGroup::Epistemic,
        description: "Can be undone?",
    },
    AxisInfo {
        index: 19, code: "B6", name: "CARGA", group: AxisGroup::Epistemic,
        description: "Cognitive resource consumption",
    },
    AxisInfo {
        index: 20, code: "B7", name: "ORIGEM", group: AxisGroup::Epistemic,
        description: "Observed vs inferred vs assumed",
    },
    AxisInfo {
        index: 21, code: "B8", name: "VALÊNCIA EPISTÊMICA", group: AxisGroup::Epistemic,
        description: "0=contradictory → 0.5=inconclusive → 1=confirmatory",
    },
    // ── Group C — Pragmatic (22–31) ───────────────────────────────────────
    AxisInfo {
        index: 22, code: "C1", name: "URGÊNCIA", group: AxisGroup::Pragmatic,
        description: "Requires immediate response?",
    },
    AxisInfo {
        index: 23, code: "C2", name: "IMPACTO", group: AxisGroup::Pragmatic,
        description: "Expected consequences?",
    },
    AxisInfo {
        index: 24, code: "C3", name: "AÇÃO", group: AxisGroup::Pragmatic,
        description: "Requires active response vs alignment only?",
    },
    AxisInfo {
        index: 25, code: "C4", name: "VALOR", group: AxisGroup::Pragmatic,
        description: "Connects with something that truly matters?",
    },
    AxisInfo {
        index: 26, code: "C5", name: "ANOMALIA", group: AxisGroup::Pragmatic,
        description: "Deviation from expected pattern?",
    },
    AxisInfo {
        index: 27, code: "C6", name: "AFETO", group: AxisGroup::Pragmatic,
        description: "Relevant emotional valence?",
    },
    AxisInfo {
        index: 28, code: "C7", name: "DEPENDÊNCIA", group: AxisGroup::Pragmatic,
        description: "Needs another to exist?",
    },
    AxisInfo {
        index: 29, code: "C8", name: "VETOR TEMPORAL", group: AxisGroup::Pragmatic,
        description: "0=past → 0.5=present → 1=future",
    },
    AxisInfo {
        index: 30, code: "C9", name: "NATUREZA", group: AxisGroup::Pragmatic,
        description: "0=noun → 1=verb",
    },
    AxisInfo {
        index: 31, code: "C10", name: "VALÊNCIA DE AÇÃO", group: AxisGroup::Pragmatic,
        description: "0=alert/contractive → 0.5=neutral → 1=confirmation/expansive",
    },
];

/// Return all axes belonging to a group.
pub fn axes_by_group(group: &AxisGroup) -> Vec<&'static AxisInfo> {
    CANONICAL_AXES
        .iter()
        .filter(|ax| &ax.group == group)
        .collect()
}

/// Return axis by zero-based index, or None if out of range.
pub fn axis_by_index(index: usize) -> Option<&'static AxisInfo> {
    CANONICAL_AXES.get(index)
}

/// Return axis by code string (case-insensitive).
pub fn axis_by_code(code: &str) -> Option<&'static AxisInfo> {
    let code_upper = code.to_uppercase();
    CANONICAL_AXES.iter().find(|ax| ax.code == code_upper)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_32_axes_present() {
        assert_eq!(CANONICAL_AXES.len(), 32);
    }

    #[test]
    fn indices_are_sequential() {
        for (i, ax) in CANONICAL_AXES.iter().enumerate() {
            assert_eq!(ax.index, i, "axis at position {} has wrong index", i);
        }
    }

    #[test]
    fn group_a_has_14_axes() {
        let a = axes_by_group(&AxisGroup::Ontological);
        assert_eq!(a.len(), 14);
    }

    #[test]
    fn group_b_has_8_axes() {
        let b = axes_by_group(&AxisGroup::Epistemic);
        assert_eq!(b.len(), 8);
    }

    #[test]
    fn group_c_has_10_axes() {
        let c = axes_by_group(&AxisGroup::Pragmatic);
        assert_eq!(c.len(), 10);
    }

    #[test]
    fn axis_by_index_works() {
        let ax = axis_by_index(0).unwrap();
        assert_eq!(ax.code, "A0");
        assert_eq!(ax.name, "VIA");
    }

    #[test]
    fn axis_by_index_out_of_range() {
        assert!(axis_by_index(32).is_none());
        assert!(axis_by_index(100).is_none());
    }

    #[test]
    fn axis_by_code_works() {
        let ax = axis_by_code("C1").unwrap();
        assert_eq!(ax.index, 22);
        assert_eq!(ax.name, "URGÊNCIA");
    }

    #[test]
    fn axis_by_code_not_found() {
        assert!(axis_by_code("Z99").is_none());
    }

    #[test]
    fn last_axis_is_c10() {
        let last = axis_by_index(31).unwrap();
        assert_eq!(last.code, "C10");
        assert_eq!(last.name, "VALÊNCIA DE AÇÃO");
    }
}
