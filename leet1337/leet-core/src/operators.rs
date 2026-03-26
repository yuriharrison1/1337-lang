use crate::error::{LeetError, LeetResult};
use crate::types::Cogon;
use crate::FIXED_DIMS;

/// FOCUS — project COGON onto a subset of dimensions.
/// Non-selected dims are zeroed with unc=1.0.
pub fn focus(cogon: &Cogon, dims: &[usize]) -> LeetResult<Cogon> {
    if cogon.sem.len() != FIXED_DIMS || cogon.unc.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, cogon.sem.len()));
    }
    let mut sem = vec![0.0f32; FIXED_DIMS];
    let mut unc = vec![1.0f32; FIXED_DIMS];
    for &d in dims {
        if d < FIXED_DIMS {
            sem[d] = cogon.sem[d];
            unc[d] = cogon.unc[d];
        }
    }
    Ok(Cogon::new(sem, unc))
}

/// DELTA — point-wise difference between two states.
pub fn delta(prev: &Cogon, curr: &Cogon) -> LeetResult<Vec<f32>> {
    if prev.sem.len() != FIXED_DIMS || curr.sem.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, prev.sem.len()));
    }
    Ok((0..FIXED_DIMS)
        .map(|i| curr.sem[i] - prev.sem[i])
        .collect())
}

/// BLEND — interpolated semantic fusion.
/// sem = α·c1 + (1-α)·c2
/// unc = max(c1.unc, c2.unc)  [conservative]
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> LeetResult<Cogon> {
    if c1.sem.len() != FIXED_DIMS || c2.sem.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, c1.sem.len()));
    }
    let sem: Vec<f32> = (0..FIXED_DIMS)
        .map(|i| alpha * c1.sem[i] + (1.0 - alpha) * c2.sem[i])
        .collect();
    let unc: Vec<f32> = (0..FIXED_DIMS)
        .map(|i| c1.unc[i].max(c2.unc[i]))
        .collect();
    Ok(Cogon::new(sem, unc))
}

/// DIST — cosine distance weighted by (1 - max_unc).
/// Uncertain dimensions contribute less to the distance.
pub fn dist(c1: &Cogon, c2: &Cogon) -> LeetResult<f32> {
    if c1.sem.len() != FIXED_DIMS || c2.sem.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, c1.sem.len()));
    }
    let weights: Vec<f32> = (0..FIXED_DIMS)
        .map(|i| 1.0 - c1.unc[i].max(c2.unc[i]))
        .collect();

    let dot: f32 = (0..FIXED_DIMS)
        .map(|i| c1.sem[i] * c2.sem[i] * weights[i])
        .sum();
    let norm1: f32 = (0..FIXED_DIMS)
        .map(|i| (c1.sem[i] * weights[i]).powi(2))
        .sum::<f32>()
        .sqrt();
    let norm2: f32 = (0..FIXED_DIMS)
        .map(|i| (c2.sem[i] * weights[i]).powi(2))
        .sum::<f32>()
        .sqrt();

    let similarity = if norm1 * norm2 < 1e-10 {
        1.0
    } else {
        (dot / (norm1 * norm2)).clamp(0.0, 1.0)
    };

    Ok(1.0 - similarity)
}

/// ANOMALY_SCORE — mean distance to the centroid of history.
/// Empty history → 1.0
pub fn anomaly_score(cogon: &Cogon, history: &[Cogon]) -> LeetResult<f32> {
    if history.is_empty() {
        return Ok(1.0);
    }

    // Compute centroid
    let centroid_sem: Vec<f32> = (0..FIXED_DIMS)
        .map(|i| history.iter().map(|c| c.sem[i]).sum::<f32>() / history.len() as f32)
        .collect();
    let centroid_unc: Vec<f32> = vec![0.0f32; FIXED_DIMS];
    let centroid = Cogon::new(centroid_sem, centroid_unc);

    dist(cogon, &centroid)
}

/// apply_patch — add delta patch to base COGON, clamped to [0,1].
pub fn apply_patch(base: &Cogon, patch: &[f32]) -> LeetResult<Cogon> {
    if base.sem.len() != FIXED_DIMS || patch.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, patch.len()));
    }
    let sem: Vec<f32> = (0..FIXED_DIMS)
        .map(|i| (base.sem[i] + patch[i]).clamp(0.0, 1.0))
        .collect();
    Ok(Cogon::new(sem, base.unc.clone()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Cogon;

    fn make_cogon(val: f32, unc: f32) -> Cogon {
        Cogon::new(vec![val; FIXED_DIMS], vec![unc; FIXED_DIMS])
    }

    #[test]
    fn test_cogon_zero() {
        let zero = Cogon::zero();
        assert_eq!(zero.sem.len(), 32);
        assert_eq!(zero.unc.len(), 32);
        assert!(zero.sem.iter().all(|&s| (s - 1.0).abs() < 1e-6));
        assert!(zero.unc.iter().all(|&u| u.abs() < 1e-6));
        assert_eq!(zero.stamp, 0);
        assert!(zero.is_zero());
    }

    #[test]
    fn test_blend_midpoint() {
        let c1 = make_cogon(1.0, 0.0);
        let c2 = make_cogon(0.0, 0.0);
        let result = blend(&c1, &c2, 0.5).unwrap();
        for s in &result.sem {
            assert!((s - 0.5).abs() < 1e-6, "Expected 0.5, got {}", s);
        }
    }

    #[test]
    fn test_blend_conservative_unc() {
        let c1 = make_cogon(0.5, 0.1);
        let c2 = make_cogon(0.5, 0.9);
        let result = blend(&c1, &c2, 0.5).unwrap();
        for u in &result.unc {
            assert!((u - 0.9).abs() < 1e-6, "Expected unc=0.9, got {}", u);
        }
    }

    #[test]
    fn test_delta_computation() {
        let prev = make_cogon(0.5, 0.1);
        let mut curr_sem = vec![0.5f32; FIXED_DIMS];
        curr_sem[22] = 0.95; // C1_URGÊNCIA changed
        let curr = Cogon::new(curr_sem, vec![0.1f32; FIXED_DIMS]);

        let d = delta(&prev, &curr).unwrap();
        assert_eq!(d.len(), 32);
        assert!((d[22] - 0.45).abs() < 1e-4, "Expected delta[22]=0.45, got {}", d[22]);
        for i in 0..32 {
            if i != 22 {
                assert!(d[i].abs() < 1e-6, "Expected delta[{}]=0, got {}", i, d[i]);
            }
        }
    }

    #[test]
    fn test_dist_identical() {
        let c = make_cogon(0.5, 0.0);
        let d = dist(&c, &c).unwrap();
        assert!(d < 1e-6, "Distance from self should be ~0, got {}", d);
    }

    #[test]
    fn test_focus_subset() {
        let c = make_cogon(0.8, 0.1);
        let dims: Vec<usize> = (0..14).collect(); // ontological group
        let focused = focus(&c, &dims).unwrap();

        for i in 0..14 {
            assert!((focused.sem[i] - 0.8).abs() < 1e-6);
            assert!((focused.unc[i] - 0.1).abs() < 1e-6);
        }
        for i in 14..32 {
            assert!((focused.sem[i]).abs() < 1e-6);
            assert!((focused.unc[i] - 1.0).abs() < 1e-6);
        }
    }

    #[test]
    fn test_low_confidence_detection() {
        let unc: Vec<f32> = (0..32)
            .map(|i| if i % 2 == 0 { 0.95 } else { 0.1 })
            .collect();
        let c = Cogon::new(vec![0.5f32; FIXED_DIMS], unc);
        let low = c.low_confidence_dims();
        assert_eq!(low.len(), 16);
        for &i in &low {
            assert_eq!(i % 2, 0);
        }
    }

    #[test]
    fn test_anomaly_score_no_history() {
        let c = make_cogon(0.5, 0.1);
        let score = anomaly_score(&c, &[]).unwrap();
        assert!((score - 1.0).abs() < 1e-6, "Empty history should return 1.0");
    }

    #[test]
    fn test_apply_patch_clamp() {
        let base = make_cogon(0.9, 0.1);
        let patch = vec![0.5f32; FIXED_DIMS]; // 0.9 + 0.5 = 1.4 → clamped to 1.0
        let result = apply_patch(&base, &patch).unwrap();
        for s in &result.sem {
            assert!(*s <= 1.0, "Clamped value should be <= 1.0, got {}", s);
            assert!((s - 1.0).abs() < 1e-6, "Should be clamped to 1.0, got {}", s);
        }
    }

    #[test]
    fn test_apply_patch_negative_clamp() {
        let base = make_cogon(0.1, 0.1);
        let patch = vec![-0.5f32; FIXED_DIMS]; // 0.1 - 0.5 = -0.4 → clamped to 0.0
        let result = apply_patch(&base, &patch).unwrap();
        for s in &result.sem {
            assert!(*s >= 0.0, "Clamped value should be >= 0.0, got {}", s);
        }
    }

    #[test]
    fn test_anomaly_score_normal() {
        let history: Vec<Cogon> = (0..5).map(|_| make_cogon(0.5, 0.0)).collect();
        let normal = make_cogon(0.5, 0.0);
        let score = anomaly_score(&normal, &history).unwrap();
        assert!(score < 0.01, "Normal cogon should have low anomaly score, got {}", score);
    }

    #[test]
    fn test_blend_alpha_extremes() {
        let c1 = make_cogon(1.0, 0.0);
        let c2 = make_cogon(0.0, 0.0);

        let r1 = blend(&c1, &c2, 1.0).unwrap();
        assert!(r1.sem.iter().all(|&s| (s - 1.0).abs() < 1e-6));

        let r0 = blend(&c1, &c2, 0.0).unwrap();
        assert!(r0.sem.iter().all(|&s| s.abs() < 1e-6));
    }
}
