use crate::types::{Cogon, SemVec};
use uuid::Uuid;

/// FOCUS — project COGON onto a dimensional subset.
/// Selected dims keep their values; others get sem=0, unc=1.0 (max uncertainty).
pub fn focus(c: &Cogon, dims: &[usize]) -> Cogon {
    let mut sem = [0.0_f32; 32];
    let mut unc = [1.0_f32; 32];
    for &d in dims {
        if d < 32 {
            sem[d] = c.sem[d];
            unc[d] = c.unc[d];
        }
    }
    Cogon {
        id: Uuid::new_v4(),
        sem,
        unc,
        stamp: c.stamp,
        raw: None,
    }
}

/// DELTA — element-wise difference between two semantic states.
/// Returns a 32-dim vector of signed deltas (not clamped).
pub fn delta(c_prev: &Cogon, c: &Cogon) -> SemVec {
    let mut d = [0.0_f32; 32];
    for i in 0..32 {
        d[i] = c.sem[i] - c_prev.sem[i];
    }
    d
}

/// BLEND — interpolated semantic fusion.
/// sem = α·c1.sem + (1-α)·c2.sem
/// unc = element-wise max(c1.unc, c2.unc)  (conservative)
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> Cogon {
    let alpha = alpha.clamp(0.0, 1.0);
    let mut sem = [0.0_f32; 32];
    let mut unc = [0.0_f32; 32];
    for i in 0..32 {
        sem[i] = alpha * c1.sem[i] + (1.0 - alpha) * c2.sem[i];
        unc[i] = c1.unc[i].max(c2.unc[i]);
    }
    Cogon {
        id: Uuid::new_v4(),
        sem,
        unc,
        stamp: c1.stamp.max(c2.stamp),
        raw: None,
    }
}

/// DIST — cosine distance weighted by (1-unc).
/// Dimensions with high uncertainty contribute less.
/// Returns value in [0, 2] (0 = identical direction, 1 = orthogonal, 2 = opposite).
pub fn dist(c1: &Cogon, c2: &Cogon) -> f32 {
    // weight = 1 - max(unc1, unc2)
    let weights: [f32; 32] = std::array::from_fn(|i| {
        (1.0 - c1.unc[i].max(c2.unc[i])).max(0.0)
    });

    let dot: f32 = (0..32).map(|i| weights[i] * c1.sem[i] * c2.sem[i]).sum();
    let norm1: f32 = (0..32)
        .map(|i| weights[i] * c1.sem[i] * c1.sem[i])
        .sum::<f32>()
        .sqrt();
    let norm2: f32 = (0..32)
        .map(|i| weights[i] * c2.sem[i] * c2.sem[i])
        .sum::<f32>()
        .sqrt();

    if norm1 == 0.0 || norm2 == 0.0 {
        return 1.0; // max distance when a vector is zero
    }

    let cosine = (dot / (norm1 * norm2)).clamp(-1.0, 1.0);
    1.0 - cosine // distance = 1 - similarity
}

/// ANOMALY_SCORE — mean distance from a cogon to the historical centroid.
/// Returns 0.5 (neutral) for empty history — no baseline for comparison.
pub fn anomaly_score(c: &Cogon, history: &[Cogon]) -> f32 {
    if history.is_empty() {
        return 0.5; // neutral: no baseline
    }
    let centroid = compute_centroid(history);
    dist(c, &centroid)
}

fn compute_centroid(history: &[Cogon]) -> Cogon {
    let n = history.len() as f32;
    let mut sem = [0.0_f32; 32];
    let mut unc = [0.0_f32; 32];
    for c in history {
        for i in 0..32 {
            sem[i] += c.sem[i];
            unc[i] += c.unc[i];
        }
    }
    for i in 0..32 {
        sem[i] /= n;
        unc[i] /= n;
    }
    Cogon {
        id: Uuid::nil(),
        sem,
        unc,
        stamp: 0,
        raw: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Cogon;

    fn make_cogon(sem_val: f32, unc_val: f32) -> Cogon {
        Cogon {
            id: Uuid::new_v4(),
            sem: [sem_val; 32],
            unc: [unc_val; 32],
            stamp: 0,
            raw: None,
        }
    }

    #[test]
    fn blend_alpha_1_returns_c1() {
        let c1 = make_cogon(0.8, 0.1);
        let c2 = make_cogon(0.2, 0.3);
        let result = blend(&c1, &c2, 1.0);
        for i in 0..32 {
            assert!((result.sem[i] - 0.8).abs() < 1e-6, "dim {i}");
        }
    }

    #[test]
    fn blend_alpha_0_returns_c2() {
        let c1 = make_cogon(0.8, 0.1);
        let c2 = make_cogon(0.2, 0.3);
        let result = blend(&c1, &c2, 0.0);
        for i in 0..32 {
            assert!((result.sem[i] - 0.2).abs() < 1e-6, "dim {i}");
        }
    }

    #[test]
    fn blend_unc_is_conservative_max() {
        let c1 = make_cogon(0.5, 0.1);
        let c2 = make_cogon(0.5, 0.7);
        let result = blend(&c1, &c2, 0.5);
        for i in 0..32 {
            assert!((result.unc[i] - 0.7).abs() < 1e-6, "dim {i}: unc should be max");
        }
    }

    #[test]
    fn blend_midpoint() {
        let c1 = make_cogon(1.0, 0.0);
        let c2 = make_cogon(0.0, 0.0);
        let result = blend(&c1, &c2, 0.5);
        for i in 0..32 {
            assert!((result.sem[i] - 0.5).abs() < 1e-6, "dim {i}");
        }
    }

    #[test]
    fn dist_identical_cogons_is_zero() {
        let c = make_cogon(0.6, 0.1);
        let d = dist(&c, &c);
        assert!(d.abs() < 1e-5, "dist to self should be ~0, got {d}");
    }

    #[test]
    fn dist_symmetric() {
        let c1 = make_cogon(0.7, 0.1);
        let c2 = make_cogon(0.3, 0.2);
        let d12 = dist(&c1, &c2);
        let d21 = dist(&c2, &c1);
        assert!((d12 - d21).abs() < 1e-5, "dist not symmetric: {d12} vs {d21}");
    }

    #[test]
    fn dist_zero_vec_returns_1() {
        let c1 = make_cogon(0.0, 0.0);
        let c2 = make_cogon(0.5, 0.0);
        let d = dist(&c1, &c2);
        assert_eq!(d, 1.0);
    }

    #[test]
    fn dist_cogon_zero_to_itself() {
        let z = Cogon::zero();
        // COGON_ZERO has sem=[1]*32, unc=[0]*32 — should be 0 distance to itself
        let d = dist(&z, &z);
        assert!(d.abs() < 1e-5);
    }

    #[test]
    fn focus_keeps_selected_dims() {
        let c = make_cogon(0.9, 0.1);
        let result = focus(&c, &[0, 5, 22]);
        assert!((result.sem[0] - 0.9).abs() < 1e-6);
        assert!((result.sem[5] - 0.9).abs() < 1e-6);
        assert!((result.sem[22] - 0.9).abs() < 1e-6);
        // others should be zeroed
        assert_eq!(result.sem[1], 0.0);
        assert_eq!(result.sem[31], 0.0);
    }

    #[test]
    fn focus_unselected_dims_have_max_unc() {
        let c = make_cogon(0.9, 0.1);
        let result = focus(&c, &[0]);
        assert_eq!(result.unc[1], 1.0); // unselected
        assert!((result.unc[0] - 0.1).abs() < 1e-6); // selected
    }

    #[test]
    fn focus_empty_dims_all_zero() {
        let c = make_cogon(0.9, 0.1);
        let result = focus(&c, &[]);
        assert!(result.sem.iter().all(|&v| v == 0.0));
        assert!(result.unc.iter().all(|&v| v == 1.0));
    }

    #[test]
    fn delta_returns_difference() {
        let c_prev = make_cogon(0.3, 0.0);
        let c_curr = make_cogon(0.7, 0.0);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - 0.4).abs() < 1e-6, "dim {i}");
        }
    }

    #[test]
    fn delta_zero_for_identical() {
        let c = make_cogon(0.5, 0.1);
        let d = delta(&c, &c);
        assert!(d.iter().all(|&v| v.abs() < 1e-6));
    }

    #[test]
    fn delta_negative_when_decreasing() {
        let c_prev = make_cogon(0.8, 0.0);
        let c_curr = make_cogon(0.2, 0.0);
        let d = delta(&c_prev, &c_curr);
        for i in 0..32 {
            assert!((d[i] - (-0.6)).abs() < 1e-6, "dim {i}");
        }
    }

    #[test]
    fn anomaly_score_empty_history_is_neutral() {
        let c = make_cogon(0.5, 0.0);
        assert_eq!(anomaly_score(&c, &[]), 0.5); // neutral without baseline
    }

    #[test]
    fn anomaly_score_same_as_history_is_low() {
        let c = make_cogon(0.5, 0.0);
        let history = vec![
            make_cogon(0.5, 0.0),
            make_cogon(0.5, 0.0),
            make_cogon(0.5, 0.0),
        ];
        let score = anomaly_score(&c, &history);
        assert!(score < 0.01, "score should be near 0, got {score}");
    }

    #[test]
    fn anomaly_score_different_from_history_is_high() {
        // Use different values across dimensions for meaningful distance
        let mut c = make_cogon(0.0, 0.0);
        c.sem[0] = 0.9; c.sem[1] = 0.1; c.sem[2] = 0.5;
        
        let mut h1 = make_cogon(0.0, 0.0);
        h1.sem[0] = 0.1; h1.sem[1] = 0.9; h1.sem[2] = 0.2;
        
        let mut h2 = make_cogon(0.0, 0.0);
        h2.sem[0] = 0.2; h2.sem[1] = 0.8; h2.sem[2] = 0.3;
        
        let history = vec![h1, h2];
        let score = anomaly_score(&c, &history);
        assert!(score > 0.1, "score should be non-trivial, got {score}");
    }
}
