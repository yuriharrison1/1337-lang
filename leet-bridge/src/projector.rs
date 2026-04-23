//! Projector trait and built-in implementations.
//!
//! Primary path (v0.5.1): calibrated W matrix `W.bin` → sem[32].
//! Loaded once per process via `w_matrix()` (OnceLock).
//!
//! When feature `keyword-fallback` is enabled, falls back to nl_translator
//! heuristic rules if the W matrix is unavailable. Without the feature,
//! absence of W.bin is a hard error.

use std::io::Read as IoRead;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use leet_core::{Cogon, LeetError, SemVec};
use uuid::Uuid;

use crate::error::BridgeError;

/// Trait for text ↔ semantic vector translation.
pub trait BridgeProjector: Send + Sync {
    /// Project human text into a COGON.
    fn project(&self, text: &str) -> Result<Cogon, LeetError>;

    /// Reconstruct human text from a COGON.
    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError>;
}

/// Deterministic mock projector for tests — no network, no API.
///
/// Uses keyword heuristics to fill semantic axes, mirroring the Python
/// `MockProjector` in `python/leet/bridge.py`.
pub struct MockProjector;

impl BridgeProjector for MockProjector {
    fn project(&self, text: &str) -> Result<Cogon, LeetError> {
        let lower = text.to_lowercase();
        let mut sem: SemVec = [0.5_f32; 32];

        // D1_STATE / P3_ANOMALY — error/down keywords
        if lower.contains("caiu")
            || lower.contains("falhou")
            || lower.contains("erro")
            || lower.contains("down")
        {
            sem[8] = 0.9;   // D1_STATE
            sem[26] = 0.9;  // P3_ANOMALY
            sem[13] = 0.15; // D6_ONTOLOGICAL_VALENCE (negative)
        }

        // D2_PROCESS / P7_ACTION — process keywords
        if lower.contains("deploy")
            || lower.contains("processo")
            || lower.contains("pipeline")
        {
            sem[9] = 0.85;  // D2_PROCESS
            sem[30] = 0.8;  // P7_ACTION (active process)
        }

        // G4_REVERSIBILITY / P7_ACTION — rollback keywords
        if lower.contains("reverter")
            || lower.contains("desfazer")
            || lower.contains("rollback")
        {
            sem[19] = 0.9;  // G4_REVERSIBILITY
            sem[30] = 0.85; // P7_ACTION
        }

        // G8_URGENCY — urgency keywords
        if lower.contains("urgente") || lower.contains("crítico") || lower.contains("agora") {
            sem[23] = 0.95; // G8_URGENCY
        }

        Ok(Cogon {
            id: Uuid::new_v4(),
            sem,
            stamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as i64)
                .unwrap_or(0),
            raw: None,
        })
    }

    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError> {
        // Find top-3 activated axes and build a label string
        let mut indexed: Vec<(usize, f32)> = cogon
            .sem
            .iter()
            .enumerate()
            .map(|(i, &v)| (i, v))
            .collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        let top3: Vec<String> = indexed
            .iter()
            .take(3)
            .filter(|(_, v)| *v > 0.5)
            .map(|(i, v)| format!("axis[{}]={:.2}", i, v))
            .collect();

        if top3.is_empty() {
            Ok("[neutral cogon]".to_string())
        } else {
            Ok(format!("[cogon: {}]", top3.join(", ")))
        }
    }
}

// ── W Matrix ──────────────────────────────────────────────────────────────────

/// Calibrated projection matrix [32 × D], row-major f32.
/// D is the embedding dimension used at training time (e.g. 768 or 1536).
pub struct WMatrix {
    pub rows: usize, // always 32
    pub cols: usize, // embedding dim
    pub data: Vec<f32>,
}

impl WMatrix {
    /// Load from binary file.
    /// Format (little-endian): [u32 rows][u32 cols][f32 * rows * cols]
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self, BridgeError> {
        let mut file = std::fs::File::open(path.as_ref())
            .map_err(|e| BridgeError::WLoadError(format!("open: {e}")))?;

        let mut header = [0u8; 8];
        file.read_exact(&mut header)
            .map_err(|e| BridgeError::WLoadError(format!("header: {e}")))?;

        let rows = u32::from_le_bytes([header[0], header[1], header[2], header[3]]) as usize;
        let cols = u32::from_le_bytes([header[4], header[5], header[6], header[7]]) as usize;

        if rows != 32 {
            return Err(BridgeError::WLoadError(format!(
                "expected 32 rows, got {rows}"
            )));
        }

        let n = rows * cols;
        let mut buf = vec![0u8; n * 4];
        file.read_exact(&mut buf)
            .map_err(|e| BridgeError::WLoadError(format!("data: {e}")))?;

        let data = buf
            .chunks_exact(4)
            .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
            .collect();

        Ok(Self { rows, cols, data })
    }

    /// Apply: sem[32] = clamp(W @ embedding, 0, 1)
    pub fn project(&self, embedding: &[f32]) -> Result<[f32; 32], BridgeError> {
        if embedding.len() != self.cols {
            return Err(BridgeError::DimensionMismatch {
                expected: self.cols,
                got: embedding.len(),
            });
        }
        let mut sem = [0.0_f32; 32];
        for (i, v) in sem.iter_mut().enumerate() {
            let row_start = i * self.cols;
            let acc: f32 = self.data[row_start..row_start + self.cols]
                .iter()
                .zip(embedding.iter())
                .map(|(w, e)| w * e)
                .sum();
            *v = acc.clamp(0.0, 1.0);
        }
        Ok(sem)
    }
}

// ── Global W matrix ───────────────────────────────────────────────────────────

static W_MATRIX: OnceLock<Option<WMatrix>> = OnceLock::new();

/// Search order for W.bin:
///   1. `LEET_W_PATH` env variable
///   2. `./calibration/data/W.bin` (local workspace)
///   3. `/usr/share/leetlang/W.bin` (system install)
fn find_w_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("LEET_W_PATH") {
        let pb = PathBuf::from(p);
        if pb.exists() {
            return Some(pb);
        }
    }
    let local = PathBuf::from("calibration/data/W.bin");
    if local.exists() {
        return Some(local);
    }
    let installed = PathBuf::from("/usr/share/leetlang/W.bin");
    if installed.exists() {
        return Some(installed);
    }
    None
}

/// Returns the loaded W matrix, or `None` if it could not be found/loaded.
/// Loads at most once per process.
pub fn w_matrix() -> Option<&'static WMatrix> {
    W_MATRIX
        .get_or_init(|| find_w_path().and_then(|p| WMatrix::load(p).ok()))
        .as_ref()
}

// ── Projection functions ──────────────────────────────────────────────────────

/// Project a pre-computed embedding to sem[32] via the calibrated W matrix.
/// Returns `BridgeError::WMatrixNotAvailable` if W is not loaded.
pub fn project_embedding(embedding: &[f32]) -> Result<[f32; 32], BridgeError> {
    match w_matrix() {
        Some(w) => w.project(embedding),
        None => Err(BridgeError::WMatrixNotAvailable),
    }
}

/// Abstraction for embedding providers (sentence-transformers, OpenAI, mock…).
pub trait EmbeddingProvider: Send + Sync {
    fn embed(&self, text: &str) -> Result<Vec<f32>, BridgeError>;
    fn dim(&self) -> usize;
}

/// Project text to a COGON: provider.embed → W matrix → sem[32].
///
/// With feature `keyword-fallback`: if W is unavailable, falls back to the
/// heuristic keyword rules from `nl_translator`.
/// Without the feature: `BridgeError::WMatrixNotAvailable` is returned.
pub fn project_text(
    text: &str,
    provider: &dyn EmbeddingProvider,
) -> Result<Cogon, BridgeError> {
    let embedding = provider.embed(text)?;

    let sem = match project_embedding(&embedding) {
        Ok(v) => v,
        Err(BridgeError::WMatrixNotAvailable) => project_text_fallback(text)?,
        Err(e) => return Err(e),
    };

    Ok(Cogon {
        id: Uuid::new_v4(),
        sem,
        stamp: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as i64)
            .unwrap_or(0),
        raw: None,
    })
}

#[cfg(feature = "keyword-fallback")]
fn project_text_fallback(text: &str) -> Result<[f32; 32], BridgeError> {
    crate::nl_translator::project_text_via_rules(text)
}

#[cfg(not(feature = "keyword-fallback"))]
fn project_text_fallback(_text: &str) -> Result<[f32; 32], BridgeError> {
    Err(BridgeError::WMatrixNotAvailable)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod w_tests {
    use super::*;

    fn tiny_w(cols: usize, fill: f32) -> WMatrix {
        WMatrix {
            rows: 32,
            cols,
            data: vec![fill; 32 * cols],
        }
    }

    #[test]
    fn project_returns_32_dims_clamped() {
        let w = tiny_w(4, 0.1);
        let sem = w.project(&vec![1.0_f32; 4]).unwrap();
        assert_eq!(sem.len(), 32);
        for &v in &sem {
            assert!(v >= 0.0 && v <= 1.0);
        }
    }

    #[test]
    fn project_clamps_above_one() {
        let w = tiny_w(2, 2.0);
        let sem = w.project(&vec![1.0_f32; 2]).unwrap();
        for &v in &sem {
            assert_eq!(v, 1.0);
        }
    }

    #[test]
    fn project_clamps_below_zero() {
        let w = tiny_w(2, -1.0);
        let sem = w.project(&vec![1.0_f32; 2]).unwrap();
        for &v in &sem {
            assert_eq!(v, 0.0);
        }
    }

    #[test]
    fn project_dimension_mismatch_errors() {
        let w = tiny_w(4, 0.1);
        assert!(w.project(&vec![0.5; 8]).is_err());
    }

    #[test]
    fn project_embedding_without_w_errors() {
        // W is not loaded in test environment (no W.bin on disk).
        // If it happens to be loaded (LEET_W_PATH set), skip.
        if w_matrix().is_some() {
            return;
        }
        assert!(project_embedding(&vec![0.5_f32; 4]).is_err());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_project_error_keywords() {
        let proj = MockProjector;
        let cogon = proj.project("o servidor caiu").unwrap();
        assert!(cogon.sem[8] > 0.8);  // D1_STATE
        assert!(cogon.sem[26] > 0.8); // P3_ANOMALY
        assert!(cogon.sem[13] < 0.3); // D6_ONTOLOGICAL_VALENCE (negative)
    }

    #[test]
    fn test_mock_reconstruct_non_empty() {
        let proj = MockProjector;
        let cogon = proj.project("deploy do pipeline").unwrap();
        let text = proj.reconstruct(&cogon).unwrap();
        assert!(!text.is_empty());
        assert!(text.contains("axis["));
    }

    #[test]
    fn test_mock_project_neutral() {
        let proj = MockProjector;
        let cogon = proj.project("").unwrap();
        // All axes should be at baseline 0.5
        assert!(cogon.sem.iter().all(|&v| (v - 0.5).abs() < 0.01));
    }
}
