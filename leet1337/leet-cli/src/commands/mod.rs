pub mod axes;
pub mod bench;
pub mod decode;
pub mod dist;
pub mod encode;
pub mod health;
pub mod inspect;
pub mod version;

use leet_core::types::Cogon;
use sha2::{Digest, Sha256};

/// SHA256-based mock projector matching Python's LocalProjector algorithm.
pub fn project_mock(text: &str) -> Cogon {
    let hash = Sha256::digest(text.as_bytes());
    let bytes = hash.as_slice();
    let mut sem = vec![0f32; 32];
    let mut unc = vec![0f32; 32];
    for i in 0..32 {
        let b1 = bytes[i % 32] as u32;
        let b2 = bytes[(i + 1) % 32] as u32;
        let val = ((b1 << 8 | b2) & 0xFFFF) as f32 / 65535.0;
        sem[i] = val;
        unc[i] = 1.0 - (val - 0.5).abs() * 2.0;
    }
    Cogon::new(sem, unc)
}

#[cfg(test)]
mod tests {
    use super::project_mock;

    #[test]
    fn test_project_mock_output_len() {
        let cogon = project_mock("hello world");
        assert_eq!(cogon.sem.len(), 32, "sem must have 32 dims");
        assert_eq!(cogon.unc.len(), 32, "unc must have 32 dims");
    }

    #[test]
    fn test_project_mock_sem_in_range() {
        let cogon = project_mock("urgência crítica no sistema");
        for (i, &v) in cogon.sem.iter().enumerate() {
            assert!(
                v >= 0.0 && v <= 1.0,
                "sem[{i}] = {v} not in [0,1]"
            );
        }
    }

    #[test]
    fn test_project_mock_unc_in_range() {
        let cogon = project_mock("system failure anomaly");
        for (i, &v) in cogon.unc.iter().enumerate() {
            assert!(
                v >= 0.0 && v <= 1.0,
                "unc[{i}] = {v} not in [0,1]"
            );
        }
    }

    #[test]
    fn test_project_mock_deterministic() {
        let c1 = project_mock("same text");
        let c2 = project_mock("same text");
        for i in 0..32 {
            assert_eq!(c1.sem[i], c2.sem[i], "sem[{i}] must be deterministic");
            assert_eq!(c1.unc[i], c2.unc[i], "unc[{i}] must be deterministic");
        }
    }

    #[test]
    fn test_project_mock_distinct_texts_differ() {
        let c1 = project_mock("amor é eterno");
        let c2 = project_mock("sistema instável crítico");
        let all_equal = (0..32).all(|i| c1.sem[i] == c2.sem[i]);
        assert!(!all_equal, "different texts should produce different sem vectors");
    }

    #[test]
    fn test_project_mock_unc_formula() {
        let cogon = project_mock("test unc formula");
        for i in 0..32 {
            let expected_unc = (1.0 - (cogon.sem[i] - 0.5).abs() * 2.0).clamp(0.0, 1.0);
            assert!(
                (cogon.unc[i] - expected_unc).abs() < 1e-6,
                "unc[{i}] = {} but formula gives {expected_unc}",
                cogon.unc[i]
            );
        }
    }

    #[test]
    fn test_project_mock_empty_string() {
        let cogon = project_mock("");
        assert_eq!(cogon.sem.len(), 32);
        for &v in cogon.sem.iter().chain(cogon.unc.iter()) {
            assert!(v.is_finite());
        }
    }

    #[test]
    fn test_project_mock_cogon_has_nonempty_id() {
        let cogon = project_mock("any text");
        // UUID v4 is always non-nil; its string representation is 36 chars
        assert_eq!(cogon.id.to_string().len(), 36);
        assert_ne!(cogon.id.to_string(), "00000000-0000-0000-0000-000000000000");
    }
}
