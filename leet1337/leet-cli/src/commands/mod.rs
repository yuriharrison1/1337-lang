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
