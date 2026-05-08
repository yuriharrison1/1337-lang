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
    /// True for the 3 bipolar axes whose neutral baseline is 0.5
    /// (G3 AFFINITY, G4 TEMPORALITY, G8 GRADIENT).
    pub bipolar: bool,
}

/// All 32 canonical axes in index order (v0.5.1).
pub const CANONICAL_AXES: [AxisInfo; 32] = [
    // ── Block S — Semantics (0–7) ──────────────────────────────────────────
    AxisInfo { index: 0,  code: "S1", name: "INTENTION",         group: AxisGroup::S, bipolar: false, description: "Directional purpose carried by the concept" },
    AxisInfo { index: 1,  code: "S2", name: "AMBIGUITY",         group: AxisGroup::S, bipolar: false, description: "Multiplicity of possible interpretations" },
    AxisInfo { index: 2,  code: "S3", name: "LOCAL_CONTEXT",     group: AxisGroup::S, bipolar: false, description: "Dependency on immediate surroundings" },
    AxisInfo { index: 3,  code: "S4", name: "GLOBAL_CONTEXT",    group: AxisGroup::S, bipolar: false, description: "Anchoring in accumulated system history" },
    AxisInfo { index: 4,  code: "S5", name: "ENTROPY",           group: AxisGroup::S, bipolar: false, description: "Intrinsic informational uncertainty" },
    AxisInfo { index: 5,  code: "S6", name: "DENSITY",           group: AxisGroup::S, bipolar: false, description: "Meaning compressed per unit" },
    AxisInfo { index: 6,  code: "S7", name: "COHERENCE",         group: AxisGroup::S, bipolar: false, description: "Internal logical consistency" },
    AxisInfo { index: 7,  code: "S8", name: "ALIGNMENT",         group: AxisGroup::S, bipolar: false, description: "Shared understanding between agents" },
    // ── Block D — Dynamics (8–15) ──────────────────────────────────────────
    AxisInfo { index: 8,  code: "D1", name: "CONNECTION_WEIGHT", group: AxisGroup::D, bipolar: false, description: "Strength of the bond with other COGONs" },
    AxisInfo { index: 9,  code: "D2", name: "LEARNING_RATE",     group: AxisGroup::D, bipolar: false, description: "Plasticity — speed of absorbing new data" },
    AxisInfo { index: 10, code: "D3", name: "DECAY",             group: AxisGroup::D, bipolar: false, description: "Loss of relevance without reinforcement" },
    AxisInfo { index: 11, code: "D4", name: "STABILITY",         group: AxisGroup::D, bipolar: false, description: "Tendency toward equilibrium" },
    AxisInfo { index: 12, code: "D5", name: "HYSTERESIS",        group: AxisGroup::D, bipolar: false, description: "Dependency on prior state" },
    AxisInfo { index: 13, code: "D6", name: "PROPAGATION",       group: AxisGroup::D, bipolar: false, description: "Influence over neighboring COGONs" },
    AxisInfo { index: 14, code: "D7", name: "CAUSALITY",         group: AxisGroup::D, bipolar: false, description: "Identifiability of concept's origin (v0.5.1: replaces SATURATION)" },
    AxisInfo { index: 15, code: "D8", name: "INERTIA",           group: AxisGroup::D, bipolar: false, description: "Resistance to state change" },
    // ── Block G — Gravity (16–23) ─────────────────────────────────────────
    AxisInfo { index: 16, code: "G1", name: "MASS",              group: AxisGroup::G, bipolar: false, description: "Relevance and accumulated confidence" },
    AxisInfo { index: 17, code: "G2", name: "TEMPORAL_ANCHOR",   group: AxisGroup::G, bipolar: false, description: "Degree of temporal anchoring (v0.5.1: replaces DISTANCE)" },
    AxisInfo { index: 18, code: "G3", name: "AFFINITY",          group: AxisGroup::G, bipolar: true,  description: "Bipolar association with surroundings (0=repulsion · 0.5=neutral · 1=attraction)" },
    AxisInfo { index: 19, code: "G4", name: "TEMPORALITY",       group: AxisGroup::G, bipolar: true,  description: "Bipolar temporal orientation (0=past · 0.5=present · 1=future)" },
    AxisInfo { index: 20, code: "G5", name: "LOCAL_FIELD",       group: AxisGroup::G, bipolar: false, description: "Dominance within the semantic cluster" },
    AxisInfo { index: 21, code: "G6", name: "GLOBAL_FIELD",      group: AxisGroup::G, bipolar: false, description: "Centrality in the global network" },
    AxisInfo { index: 22, code: "G7", name: "K_INTERACTION",     group: AxisGroup::G, bipolar: false, description: "Adaptive local gain — field sensitivity" },
    AxisInfo { index: 23, code: "G8", name: "GRADIENT",          group: AxisGroup::G, bipolar: true,  description: "Bipolar change direction/intensity (0=decelerating · 0.5=stable · 1=accelerating)" },
    // ── Block P — Precision (24–31) ───────────────────────────────────────
    AxisInfo { index: 24, code: "P1", name: "QUANTIZATION",      group: AxisGroup::P, bipolar: false, description: "Rounding level controlled by Pillars 6 and 7" },
    AxisInfo { index: 25, code: "P2", name: "GRANULARITY",       group: AxisGroup::P, bipolar: false, description: "Decomposable resolution" },
    AxisInfo { index: 26, code: "P3", name: "COMPRESSION",       group: AxisGroup::P, bipolar: false, description: "Compression of representation" },
    AxisInfo { index: 27, code: "P4", name: "NOISE",             group: AxisGroup::P, bipolar: false, description: "Noise vs signal ratio" },
    AxisInfo { index: 28, code: "P5", name: "RESOLUTION",        group: AxisGroup::P, bipolar: false, description: "Adaptive fineness" },
    AxisInfo { index: 29, code: "P6", name: "CONFIDENCE",        group: AxisGroup::P, bipolar: false, description: "Global fidelity (v0.5.1: replaces unc[32])" },
    AxisInfo { index: 30, code: "P7", name: "ACTION",            group: AxisGroup::P, bipolar: false, description: "Demand for active response (v0.5.1: replaces COST)" },
    AxisInfo { index: 31, code: "P8", name: "LATENCY",           group: AxisGroup::P, bipolar: false, description: "Representation update delay" },
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

/// Return the 3 bipolar axes (neutral baseline 0.5: G3 AFFINITY, G4 TEMPORALITY, G8 GRADIENT).
pub fn bipolar_axes() -> Vec<&'static AxisInfo> {
    CANONICAL_AXES.iter().filter(|ax| ax.bipolar).collect()
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
    fn three_bipolar_axes() {
        let v = bipolar_axes();
        assert_eq!(v.len(), 3, "v0.5.1 has 3 bipolar axes");
        let indices: Vec<usize> = v.iter().map(|a| a.index).collect();
        assert!(indices.contains(&18), "G3 AFFINITY should be bipolar");
        assert!(indices.contains(&19), "G4 TEMPORALITY should be bipolar");
        assert!(indices.contains(&23), "G8 GRADIENT should be bipolar");
    }

    #[test]
    fn s1_is_intention_not_essence() {
        let s1 = axis_by_code("S1").unwrap();
        assert_eq!(s1.name, "INTENTION", "v0.5.1: S1 must be INTENTION");
    }

    #[test]
    fn p6_is_confidence_not_temporal_vector() {
        let p6 = axis_by_code("P6").unwrap();
        assert_eq!(p6.name, "CONFIDENCE", "v0.5.1: P6 must be CONFIDENCE");
    }

    #[test]
    fn axis_by_index_works() {
        let ax = axis_by_index(0).unwrap();
        assert_eq!(ax.code, "S1");
        assert_eq!(ax.name, "INTENTION");
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
        assert_eq!(ax.name, "GRADIENT");
    }

    #[test]
    fn axis_by_code_not_found() {
        assert!(axis_by_code("Z99").is_none());
    }

    #[test]
    fn last_axis_is_p8() {
        let last = axis_by_index(31).unwrap();
        assert_eq!(last.code, "P8");
        assert_eq!(last.name, "LATENCY");
    }

    #[test]
    fn d7_is_causality() {
        let ax = axis_by_code("D7").unwrap();
        assert_eq!(ax.name, "CAUSALITY");
    }
}
