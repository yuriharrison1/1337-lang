/// Axis block classification (v0.5.1).
#[derive(Debug, Clone, PartialEq)]
pub enum AxisGroup {
    S, // Semantic  (0–7)
    D, // Dynamic   (8–15)
    G, // Gravity   (16–23)
    P, // Precision (24–31)
}

/// Metadata for one canonical axis.
#[derive(Debug, Clone)]
pub struct AxisInfo {
    pub index: usize,
    pub code: &'static str,
    pub name: &'static str,
    pub group: AxisGroup,
    pub description: &'static str,
    /// True for the 5 valence axes whose neutral baseline is 0.5.
    pub is_valence: bool,
}

/// All 32 canonical axes in index order (v0.5.1).
pub const CANONICAL_AXES: [AxisInfo; 32] = [
    // ── Block S — Semantic (0–7) ──────────────────────────────────────────
    AxisInfo { index: 0,  code: "S1", name: "ESSENCIA",         group: AxisGroup::S, is_valence: false, description: "Concept exists by itself" },
    AxisInfo { index: 1,  code: "S2", name: "CORRESPONDENCIA",  group: AxisGroup::S, is_valence: false, description: "Mirrors patterns at other abstraction levels" },
    AxisInfo { index: 2,  code: "S3", name: "VIBRACAO",         group: AxisGroup::S, is_valence: false, description: "Continuous movement/transformation" },
    AxisInfo { index: 3,  code: "S4", name: "POLARIDADE",       group: AxisGroup::S, is_valence: false, description: "Position on a spectrum between extremes" },
    AxisInfo { index: 4,  code: "S5", name: "RITMO",            group: AxisGroup::S, is_valence: false, description: "Cyclic or periodic pattern" },
    AxisInfo { index: 5,  code: "S6", name: "CAUSA_EFEITO",     group: AxisGroup::S, is_valence: false, description: "Causal agent vs effect" },
    AxisInfo { index: 6,  code: "S7", name: "GENERO",           group: AxisGroup::S, is_valence: false, description: "Generative/active vs receptive/passive" },
    AxisInfo { index: 7,  code: "S8", name: "SISTEMA",          group: AxisGroup::S, is_valence: false, description: "Set with emergent behavior" },
    // ── Block D — Dynamic (8–15) ──────────────────────────────────────────
    AxisInfo { index: 8,  code: "D1", name: "ESTADO",           group: AxisGroup::D, is_valence: false, description: "Configuration at a moment" },
    AxisInfo { index: 9,  code: "D2", name: "PROCESSO",         group: AxisGroup::D, is_valence: false, description: "Transformation over time" },
    AxisInfo { index: 10, code: "D3", name: "RELACAO",          group: AxisGroup::D, is_valence: false, description: "Connection between entities" },
    AxisInfo { index: 11, code: "D4", name: "SINAL",            group: AxisGroup::D, is_valence: false, description: "Information carrying variation" },
    AxisInfo { index: 12, code: "D5", name: "ESTABILIDADE",     group: AxisGroup::D, is_valence: false, description: "Tendency to equilibrium" },
    AxisInfo { index: 13, code: "D6", name: "VALENCIA_ONT",     group: AxisGroup::D, is_valence: true,  description: "Intrinsic sign: 0=negative, 0.5=neutral, 1=positive" },
    AxisInfo { index: 14, code: "D7", name: "CAUSALIDADE",      group: AxisGroup::D, is_valence: false, description: "Origin identifiable" },
    AxisInfo { index: 15, code: "D8", name: "VERIFICABILIDADE", group: AxisGroup::D, is_valence: false, description: "Externally confirmable" },
    // ── Block G — Gravity (16–23) ─────────────────────────────────────────
    AxisInfo { index: 16, code: "G1", name: "TEMPORALIDADE",    group: AxisGroup::G, is_valence: false, description: "Defined temporal anchor" },
    AxisInfo { index: 17, code: "G2", name: "ANCORA_TEMPORAL",  group: AxisGroup::G, is_valence: true,  description: "Temporal orientation: 0=past, 0.5=present, 1=future" },
    AxisInfo { index: 18, code: "G3", name: "COMPLETUDE",       group: AxisGroup::G, is_valence: false, description: "Resolved or open" },
    AxisInfo { index: 19, code: "G4", name: "REVERSIBILIDADE",  group: AxisGroup::G, is_valence: false, description: "Can be undone" },
    AxisInfo { index: 20, code: "G5", name: "CARGA",            group: AxisGroup::G, is_valence: false, description: "Cognitive load" },
    AxisInfo { index: 21, code: "G6", name: "ORIGEM",           group: AxisGroup::G, is_valence: false, description: "Degree of observation: 0=assumed, 1=observed" },
    AxisInfo { index: 22, code: "G7", name: "VALENCIA_EPIST",   group: AxisGroup::G, is_valence: true,  description: "Epistemic sign: 0=contradictory, 0.5=inconclusive, 1=confirmatory" },
    AxisInfo { index: 23, code: "G8", name: "URGENCIA",         group: AxisGroup::G, is_valence: false, description: "Temporal pressure: 0=none, 1=maximum urgency" },
    // ── Block P — Precision (24–31) ───────────────────────────────────────
    AxisInfo { index: 24, code: "P1", name: "IMPACTO",          group: AxisGroup::P, is_valence: false, description: "Expected consequence" },
    AxisInfo { index: 25, code: "P2", name: "VALOR",            group: AxisGroup::P, is_valence: false, description: "Connects to what truly matters" },
    AxisInfo { index: 26, code: "P3", name: "ANOMALIA",         group: AxisGroup::P, is_valence: false, description: "Deviation from expected pattern" },
    AxisInfo { index: 27, code: "P4", name: "AFETO",            group: AxisGroup::P, is_valence: true,  description: "Emotional valence: 0=negative, 0.5=neutral, 1=positive" },
    AxisInfo { index: 28, code: "P5", name: "DEPENDENCIA",      group: AxisGroup::P, is_valence: false, description: "Needs another to exist" },
    AxisInfo { index: 29, code: "P6", name: "VETOR_TEMPORAL",   group: AxisGroup::P, is_valence: false, description: "Temporal direction: 0=past, 1=future" },
    AxisInfo { index: 30, code: "P7", name: "ACAO",             group: AxisGroup::P, is_valence: false, description: "Active response required: 0=passive, 1=immediate action" },
    AxisInfo { index: 31, code: "P8", name: "VALENCIA_ACAO",    group: AxisGroup::P, is_valence: true,  description: "Action intention: 0=alert, 0.5=query, 1=confirmation" },
];

/// Return all axes belonging to a block.
pub fn axes_by_group(group: &AxisGroup) -> Vec<&'static AxisInfo> {
    CANONICAL_AXES.iter().filter(|ax| &ax.group == group).collect()
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

/// Return the 5 valence axes (neutral baseline 0.5).
pub fn valence_axes() -> Vec<&'static AxisInfo> {
    CANONICAL_AXES.iter().filter(|ax| ax.is_valence).collect()
}

/// Boot vector — the canonical initial zone_fixed for v0.5.1 C5 handshake messages.
/// Equals COGON_ZERO_SEM: Pilar 4 defaults with per-axis semantic priors.
pub fn boot_vector() -> crate::types::SemVec {
    crate::types::COGON_ZERO_SEM
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
    fn each_block_has_8_axes() {
        assert_eq!(axes_by_group(&AxisGroup::S).len(), 8);
        assert_eq!(axes_by_group(&AxisGroup::D).len(), 8);
        assert_eq!(axes_by_group(&AxisGroup::G).len(), 8);
        assert_eq!(axes_by_group(&AxisGroup::P).len(), 8);
    }

    #[test]
    fn five_valence_axes() {
        let v = valence_axes();
        assert_eq!(v.len(), 5);
        // D6, G2, G7, P4, P8
        let indices: Vec<usize> = v.iter().map(|a| a.index).collect();
        assert!(indices.contains(&13));
        assert!(indices.contains(&17));
        assert!(indices.contains(&22));
        assert!(indices.contains(&27));
        assert!(indices.contains(&31));
    }

    #[test]
    fn axis_by_index_works() {
        let ax = axis_by_index(0).unwrap();
        assert_eq!(ax.code, "S1");
        assert_eq!(ax.name, "ESSENCIA");
    }

    #[test]
    fn axis_by_index_out_of_range() {
        assert!(axis_by_index(32).is_none());
        assert!(axis_by_index(100).is_none());
    }

    #[test]
    fn axis_by_code_works() {
        let ax = axis_by_code("G8").unwrap();
        assert_eq!(ax.index, 23);
        assert_eq!(ax.name, "URGENCIA");
    }

    #[test]
    fn axis_by_code_not_found() {
        assert!(axis_by_code("Z99").is_none());
    }

    #[test]
    fn last_axis_is_p8() {
        let last = axis_by_index(31).unwrap();
        assert_eq!(last.code, "P8");
        assert_eq!(last.name, "VALENCIA_ACAO");
    }
}
