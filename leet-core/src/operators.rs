//! Algebra of 1337 operators (v0.5.1).
//!
//! - FOCUS(c, dims)              — project onto a subset of dimensions
//! - DELTA(c_prev, c)            — element-wise sem difference
//! - BLEND(c1, c2, α)            — semantic fusion with per-block rules
//! - DIST(c1, c2)                — cosine distance weighted by P6_TEMPORAL_VECTOR
//! - ANOMALY_SCORE(c, history)   — distance to G1_TEMPORALITY-weighted centroid
//!
//! All operators apply clamp_all() on outputs (R22).

use crate::types::{Cogon, SemVec};
use uuid::Uuid;

const P6_TEMPORAL_VECTOR: usize = 29;
const G1_TEMPORALITY: usize = 16;
const D4_SIGNAL: usize = 11;
const G7_EPISTEMIC_VALENCE: usize = 22;

#[inline]
fn clamp_all(v: &mut SemVec) {
    for x in v.iter_mut() {
        *x = x.clamp(0.0, 1.0);
    }
}

// ── FOCUS ─────────────────────────────────────────────────────────────────────

/// FOCUS — project COGON onto a dimensional subset.
/// Selected dims keep their values; others get sem=0.0.
pub fn focus(c: &Cogon, dims: &[usize]) -> Cogon {
    let mut sem = [0.0_f32; 32];
    for &d in dims {
        if d < 32 {
            sem[d] = c.sem[d];
        }
    }
    clamp_all(&mut sem);
    Cogon {
        id: Uuid::new_v4(),
        sem,
        stamp: c.stamp,
        raw: None,
    }
}

// ── DELTA ────────────────────────────────���────────────────────────────────────

/// DELTA — element-wise sem difference (not clamped; can be negative).
pub fn delta(c_prev: &Cogon, c: &Cogon) -> SemVec {
    let mut d = [0.0_f32; 32];
    for ((di, &a), &b) in d.iter_mut().zip(c.sem.iter()).zip(c_prev.sem.iter()) {
        *di = a - b;
    }
    d
}

// ── BLEND ─────────────────────────────────────────────────────────────────────

/// BLEND — semantic fusion with per-block rules.
///
/// Default: sem[i] = α·c1.sem[i] + (1-α)·c2.sem[i]
///
/// Exceptions by axis:
/// - D4_SIGNAL (11) = min(c1, c2)        — conservative
/// - G1_TEMPORALITY        (16) = clamp(c1+c2, 0, 1) — accumulating
/// - G7_EPISTEMIC_VALENCE  (22) = max(c1, c2)        — higher gain wins
/// - P6_TEMPORAL_VECTOR    (29) = min(c1, c2)        — conservative
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> Cogon {
    let alpha = alpha.clamp(0.0, 1.0);
    let mut sem = [0.0_f32; 32];

    for (i, v) in sem.iter_mut().enumerate() {
        *v = match i {
            D4_SIGNAL            => c1.sem[i].min(c2.sem[i]),
            G1_TEMPORALITY       => (c1.sem[i] + c2.sem[i]).clamp(0.0, 1.0),
            G7_EPISTEMIC_VALENCE => c1.sem[i].max(c2.sem[i]),
            P6_TEMPORAL_VECTOR   => c1.sem[i].min(c2.sem[i]),
            _                    => alpha * c1.sem[i] + (1.0 - alpha) * c2.sem[i],
        };
    }
    clamp_all(&mut sem);

    Cogon {
        id: Uuid::new_v4(),
        sem,
        stamp: c1.stamp.max(c2.stamp),
        raw: None,
    }
}

// ── DIST ──────────────────────────────────────────────────────────────────────

/// DIST — cosine distance weighted by P6_TEMPORAL_VECTOR average.
/// Returns value in [0, 2]: 0 = identical, 1 = orthogonal, 2 = opposite.
pub fn dist(c1: &Cogon, c2: &Cogon) -> f32 {
    let w = ((c1.sem[P6_TEMPORAL_VECTOR] + c2.sem[P6_TEMPORAL_VECTOR]) / 2.0).max(0.0);

    let dot: f32 = (0..32).map(|i| c1.sem[i] * c2.sem[i]).sum::<f32>() * w;
    let norm1: f32 = (0..32).map(|i| c1.sem[i] * c1.sem[i]).sum::<f32>().sqrt() * w.sqrt();
    let norm2: f32 = (0..32).map(|i| c2.sem[i] * c2.sem[i]).sum::<f32>().sqrt() * w.sqrt();

    if norm1 == 0.0 || norm2 == 0.0 {
        return 1.0;
    }

    let cosine = (dot / (norm1 * norm2)).clamp(-1.0, 1.0);
    1.0 - cosine
}

// ── ANOMALY_SCORE ─────────────────────────────────────────────────────────────

/// ANOMALY_SCORE — distance from cogon to G1_TEMPORALITY-weighted historical centroid.
/// Returns 0.5 for empty history (neutral).
pub fn anomaly_score(c: &Cogon, history: &[Cogon]) -> f32 {
    if history.is_empty() {
        return 0.5;
    }
    let centroid = compute_weighted_centroid(history);
    dist(c, &centroid)
}

/// Weighted centroid: each historical COGON contributes in proportion to its G1_TEMPORALITY.
/// Falls back to uniform average if total mass is zero.
pub fn compute_weighted_centroid(history: &[Cogon]) -> Cogon {
    let total_mass: f32 = history.iter().map(|c| c.sem[G1_TEMPORALITY]).sum();

    let mut sem = [0.0_f32; 32];

    if total_mass > f32::EPSILON {
        for c in history {
            let w = c.sem[G1_TEMPORALITY] / total_mass;
            for (s, &cv) in sem.iter_mut().zip(c.sem.iter()) {
                *s += w * cv;
            }
        }
    } else {
        let n = history.len() as f32;
        for c in history {
            for (s, &cv) in sem.iter_mut().zip(c.sem.iter()) {
                *s += cv / n;
            }
        }
    }
    clamp_all(&mut sem);

    Cogon {
        id: Uuid::nil(),
        sem,
        stamp: 0,
        raw: None,
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Cogon;

    fn make_cogon(sem_val: f32) -> Cogon {
        Cogon {
            id: Uuid::new_v4(),
            sem: [sem_val; 32],
            stamp: 0,
            raw: None,
        }
    }

    // ── BLEND ─────────────────────────────────���───────────────────���────────

    #[test]
    fn blend_alpha_1_returns_c1() {
        let c1 = make_cogon(0.8);
        let c2 = make_cogon(0.2);
        let r = blend(&c1, &c2, 1.0);
        assert!((r.sem[0] - 0.8).abs() < 1e-6);
    }

    #[test]
    fn blend_alpha_0_returns_c2() {
        let c1 = make_cogon(0.8);
        let c2 = make_cogon(0.2);
        let r = blend(&c1, &c2, 0.0);
        assert!((r.sem[0] - 0.2).abs() < 1e-6);
    }

    #[test]
    fn blend_d4_signal_takes_min() {
        let mut c1 = make_cogon(0.5);
        c1.sem[D4_SIGNAL] = 0.9;
        let mut c2 = make_cogon(0.5);
        c2.sem[D4_SIGNAL] = 0.2;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[D4_SIGNAL], 0.2, "D4 must be min");
    }

    #[test]
    fn blend_g1_temporality_accumulates() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_TEMPORALITY] = 0.4;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_TEMPORALITY] = 0.5;
        let r = blend(&c1, &c2, 0.5);
        assert!((r.sem[G1_TEMPORALITY] - 0.9).abs() < 1e-6, "G1 must accumulate");
    }

    #[test]
    fn blend_g1_temporality_saturates_at_one() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_TEMPORALITY] = 0.8;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_TEMPORALITY] = 0.7;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[G1_TEMPORALITY], 1.0, "G1 must clamp at 1.0");
    }

    #[test]
    fn blend_g7_epistemic_valence_takes_max() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G7_EPISTEMIC_VALENCE] = 0.1;
        let mut c2 = make_cogon(0.5);
        c2.sem[G7_EPISTEMIC_VALENCE] = 0.8;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[G7_EPISTEMIC_VALENCE], 0.8, "G7 must be max");
    }

    #[test]
    fn blend_p6_temporal_vector_takes_min() {
        let mut c1 = make_cogon(0.5);
        c1.sem[P6_TEMPORAL_VECTOR] = 0.9;
        let mut c2 = make_cogon(0.5);
        c2.sem[P6_TEMPORAL_VECTOR] = 0.3;
        let r = blend(&c1, &c2, 0.5);
        assert_eq!(r.sem[P6_TEMPORAL_VECTOR], 0.3, "P6 must be conservative (min)");
    }

    #[test]
    fn blend_midpoint() {
        let c1 = make_cogon(1.0);
        let c2 = make_cogon(0.0);
        let r = blend(&c1, &c2, 0.5);
        assert!((r.sem[0] - 0.5).abs() < 1e-6);
    }

    #[test]
    fn blend_result_always_in_01() {
        let c1 = make_cogon(0.9);
        let c2 = make_cogon(0.9);
        let r = blend(&c1, &c2, 0.5);
        for i in 0..32 {
            assert!(r.sem[i] >= 0.0 && r.sem[i] <= 1.0, "dim {i} out of range");
        }
    }

    // ── DIST ───────────────────────────────────────────────────────────────

    #[test]
    fn dist_identical_cogons_is_zero() {
        let mut c = make_cogon(0.6);
        c.sem[P6_TEMPORAL_VECTOR] = 1.0;
        let d = dist(&c, &c);
        assert!(d.abs() < 1e-5, "dist to self ~0, got {d}");
    }

    #[test]
    fn dist_symmetric() {
        let mut c1 = make_cogon(0.7);
        c1.sem[P6_TEMPORAL_VECTOR] = 0.8;
        let mut c2 = make_cogon(0.3);
        c2.sem[P6_TEMPORAL_VECTOR] = 0.8;
        let d12 = dist(&c1, &c2);
        let d21 = dist(&c2, &c1);
        assert!((d12 - d21).abs() < 1e-5);
    }

    #[test]
    fn dist_zero_vec_returns_1() {
        let c_zero = make_cogon(0.0);
        let c_half = make_cogon(0.5);
        assert_eq!(dist(&c_zero, &c_half), 1.0);
    }

    #[test]
    fn dist_cogon_zero_to_itself() {
        let z = crate::types::Cogon::zero();
        let d = dist(&z, &z);
        assert!(d < 1.0, "COGON_ZERO vs itself must not be max dist");
    }

    // ── ANOMALY_SCORE ──────────────────────────────────────────────────────

    #[test]
    fn anomaly_score_empty_history_is_neutral() {
        let c = make_cogon(0.5);
        assert_eq!(anomaly_score(&c, &[]), 0.5);
    }

    #[test]
    fn anomaly_score_same_as_history_is_low() {
        let mut c = make_cogon(0.5);
        c.sem[G1_TEMPORALITY] = 1.0;
        c.sem[P6_TEMPORAL_VECTOR] = 1.0;
        let history = vec![c.clone(), c.clone()];
        let score = anomaly_score(&c, &history);
        assert!(score < 0.1, "identical history score should be low, got {score}");
    }

    #[test]
    fn anomaly_score_different_from_history_is_high() {
        let mut c = make_cogon(0.9);
        c.sem[G1_TEMPORALITY] = 1.0;
        c.sem[P6_TEMPORAL_VECTOR] = 1.0;
        let mut h = make_cogon(0.1);
        h.sem[G1_TEMPORALITY] = 1.0;
        h.sem[P6_TEMPORAL_VECTOR] = 1.0;
        let score = anomaly_score(&c, &[h]);
        assert!(score > 0.1, "different history score should be nonzero, got {score}");
    }

    #[test]
    fn anomaly_score_heavy_cogon_dominates_centroid() {
        let mut heavy = make_cogon(0.5);
        heavy.sem[0] = 0.9;
        heavy.sem[G1_TEMPORALITY] = 1.0;
        heavy.sem[P6_TEMPORAL_VECTOR] = 1.0;

        let mut light = make_cogon(0.5);
        light.sem[0] = 0.1;
        light.sem[G1_TEMPORALITY] = 0.05;
        light.sem[P6_TEMPORAL_VECTOR] = 1.0;

        let mut history = vec![heavy];
        for _ in 0..10 {
            history.push(light.clone());
        }

        let centroid = compute_weighted_centroid(&history);
        assert!(centroid.sem[0] > 0.55, "heavy cogon should dominate centroid, got {}", centroid.sem[0]);
    }

    #[test]
    fn anomaly_score_all_zero_mass_falls_back_to_uniform() {
        let mut c1 = make_cogon(0.5);
        c1.sem[G1_TEMPORALITY] = 0.0;
        c1.sem[0] = 0.2;
        let mut c2 = make_cogon(0.5);
        c2.sem[G1_TEMPORALITY] = 0.0;
        c2.sem[0] = 0.8;

        let centroid = compute_weighted_centroid(&[c1, c2]);
        assert!((centroid.sem[0] - 0.5).abs() < 1e-6, "uniform fallback");
    }

    // ── FOCUS ──────────────────────────────────────────────────────────────

    #[test]
    fn focus_keeps_selected_dims() {
        let c = make_cogon(0.9);
        let r = focus(&c, &[0, 5, 22]);
        assert!((r.sem[0] - 0.9).abs() < 1e-6);
        assert!((r.sem[5] - 0.9).abs() < 1e-6);
        assert!((r.sem[22] - 0.9).abs() < 1e-6);
        assert_eq!(r.sem[1], 0.0);
        assert_eq!(r.sem[31], 0.0);
    }

    #[test]
    fn focus_empty_dims_all_zero() {
        let c = make_cogon(0.9);
        let r = focus(&c, &[]);
        assert!(r.sem.iter().all(|&v| v == 0.0));
    }

    // ── DELTA ──────────────────────────────────────────────────────────────

    #[test]
    fn delta_returns_difference() {
        let c_prev = make_cogon(0.3);
        let c_curr = make_cogon(0.7);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - 0.4).abs() < 1e-6);
        }
    }

    #[test]
    fn delta_zero_for_identical() {
        let c = make_cogon(0.5);
        let d = delta(&c, &c);
        assert!(d.iter().all(|&v| v.abs() < 1e-6));
    }

    #[test]
    fn delta_negative_when_decreasing() {
        let c_prev = make_cogon(0.8);
        let c_curr = make_cogon(0.2);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - (-0.6)).abs() < 1e-6);
        }
    }
}
