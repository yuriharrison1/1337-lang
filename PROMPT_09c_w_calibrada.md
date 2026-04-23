# PROMPT 09c — W CALIBRADA PLUGADA COM KEYWORD FALLBACK OPT-IN

Conectar a matriz W calibrada (gerada pelo PROMPT_06) no `leet-bridge/src/projector.rs` como caminho primário de projeção `embedding → sem[32]`. Manter as ~80 regras de keyword existentes como **fallback opt-in** atrás de feature flag `keyword-fallback` (desligada por default).

**PRÉ-REQUISITOS**: PROMPT_06 executado (W.bin gerado em `calibration/data/W.bin`). Bloco 1 da Fase A executado. `cargo test --workspace` verde.

**ESCOPO**: `leet-bridge/src/projector.rs`, `leet-bridge/Cargo.toml` (feature flag), possivelmente `leet-bridge/src/lib.rs` se re-export.

**Taskwarrior**: `+prompt09c`.

---

## ARQUITETURA ATUAL

Hoje `leet-bridge/src/projector.rs` deve estar usando o `nl_translator.rs` baseado em heurísticas de keyword (as ~80 regras tipo `Rule { keywords: &["ontem", "yesterday"], axis: G2_TEMPORAL_ANCHOR, value: 0.1 }`). Isso funciona mas:
- É frágil (cobertura limitada)
- Não escala para novos domínios
- Não captura nuances semânticas

A W calibrada em `calibration/data/W.bin` é uma matriz aprendida `[32 × D]` onde D é a dimensão do embedding (tipicamente 768 ou 1536). Projeta:

```
sem[32] = normalize(clamp(W @ embedding[D], 0, 1))
```

Resultado: projeção semântica rica, learned, que captura patterns difíceis de escrever à mão.

---

## ARQUITETURA NOVA

```
┌─────────────────────────────────────────┐
│  project_text(text) -> Cogon            │
│                                         │
│   ┌──────────────────────────────────┐ │
│   │  1. Get embedding from provider  │ │
│   │     (e.g., sentence-transformers)│ │
│   └─────────────┬────────────────────┘ │
│                 │                       │
│   ┌─────────────▼────────────────────┐ │
│   │  2. W @ embedding → sem[32]      │ │ ← caminho primário
│   │     (load W.bin once, cached)    │ │
│   └─────────────┬────────────────────┘ │
│                 │                       │
│   [feature = "keyword-fallback"]        │
│   ┌─────────────▼────────────────────┐ │
│   │  3. If W.bin missing or error:   │ │ ← só se feature ligada
│   │     fallback to nl_translator    │ │
│   │     (keyword rules)              │ │
│   └──────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

Sem a feature flag, se W.bin está missing: erro explícito `WMatrixNotAvailable`. Sem fallback silencioso. A feature `keyword-fallback` é desligada por default — quem quiser o comportamento antigo ativa explicitamente.

---

## ARQUIVO 1 — `leet-bridge/Cargo.toml`

Adicionar feature flag:

```toml
[features]
default = []
keyword-fallback = []  # enables legacy nl_translator rules as fallback

# opcional: feature pra testes determinísticos sem W real
mock-projector = []
```

---

## ARQUIVO 2 — `leet-bridge/src/projector.rs`

Estrutura esperada. Se o arquivo atual difere, adaptar:

```rust
//! Semantic projector: text → COGON via learned W matrix (v0.5.1).
//!
//! Primary path: W @ embedding → sem[32] using the calibrated matrix from
//! `calibration/data/W.bin`. Loads once into a global OnceLock.
//!
//! When feature `keyword-fallback` is enabled, falls back to the heuristic
//! rules in `nl_translator` if the W matrix is unavailable or errors.
//! Otherwise, absence of W is a hard error.

use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::io::Read;

use leet_core::types::Cogon;
use uuid::Uuid;

use crate::error::BridgeError;

/// The calibrated projection matrix [32 × D], row-major.
/// D depends on the embedding provider used at training time.
pub struct WMatrix {
    pub rows: usize,    // always 32
    pub cols: usize,    // embedding dim
    pub data: Vec<f32>,
}

impl WMatrix {
    /// Load from binary file. Expected format (little-endian):
    ///   [u32 rows][u32 cols][f32 * rows * cols]
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self, BridgeError> {
        let mut file = std::fs::File::open(path.as_ref())
            .map_err(|e| BridgeError::WLoadError(format!("open failed: {e}")))?;
        let mut header = [0u8; 8];
        file.read_exact(&mut header)
            .map_err(|e| BridgeError::WLoadError(format!("header read: {e}")))?;
        let rows = u32::from_le_bytes([header[0], header[1], header[2], header[3]]) as usize;
        let cols = u32::from_le_bytes([header[4], header[5], header[6], header[7]]) as usize;

        if rows != 32 {
            return Err(BridgeError::WLoadError(
                format!("expected 32 rows, got {rows}"),
            ));
        }

        let n = rows * cols;
        let mut buf = vec![0u8; n * 4];
        file.read_exact(&mut buf)
            .map_err(|e| BridgeError::WLoadError(format!("data read: {e}")))?;

        let mut data = Vec::with_capacity(n);
        for chunk in buf.chunks_exact(4) {
            data.push(f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]));
        }

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
        for i in 0..32 {
            let mut acc = 0.0;
            for j in 0..self.cols {
                acc += self.data[i * self.cols + j] * embedding[j];
            }
            sem[i] = acc.clamp(0.0, 1.0);
        }
        Ok(sem)
    }
}

/// Global W matrix (loaded once per process).
static W_MATRIX: OnceLock<Option<WMatrix>> = OnceLock::new();

/// Path where W.bin is expected to live. Searched in this order:
///   1. env LEET_W_PATH
///   2. ./calibration/data/W.bin
///   3. /usr/share/leetlang/W.bin (Linux install path)
fn find_w_path() -> Option<PathBuf> {
    if let Ok(p) = std::env::var("LEET_W_PATH") {
        let pb = PathBuf::from(p);
        if pb.exists() { return Some(pb); }
    }
    let local = PathBuf::from("calibration/data/W.bin");
    if local.exists() { return Some(local); }
    let installed = PathBuf::from("/usr/share/leetlang/W.bin");
    if installed.exists() { return Some(installed); }
    None
}

/// Get the loaded W matrix (or None if loading failed / not found).
pub fn w_matrix() -> Option<&'static WMatrix> {
    W_MATRIX
        .get_or_init(|| {
            find_w_path().and_then(|p| WMatrix::load(p).ok())
        })
        .as_ref()
}

/// Project an embedding to sem[32] using the calibrated W matrix.
/// Returns an error if W is unavailable and feature `keyword-fallback` is off.
pub fn project_embedding(embedding: &[f32]) -> Result<[f32; 32], BridgeError> {
    if let Some(w) = w_matrix() {
        return w.project(embedding);
    }

    #[cfg(feature = "keyword-fallback")]
    {
        // Degraded mode: use the keyword heuristics path.
        // Returns a reasonable default sem[32] — caller should know they're in
        // a degraded regime (log at warn level).
        log::warn!(
            "W matrix not available at runtime; degrading to keyword-fallback path. \
             Set LEET_W_PATH or install W.bin under /usr/share/leetlang/"
        );
        return Ok(crate::nl_translator::default_sem_vector());
    }

    #[cfg(not(feature = "keyword-fallback"))]
    {
        Err(BridgeError::WMatrixNotAvailable)
    }
}

/// High-level: project text through an embedding provider, then through W.
/// This is the public entry point for callers.
pub fn project_text(
    text: &str,
    provider: &dyn EmbeddingProvider,
) -> Result<Cogon, BridgeError> {
    // 1. Get embedding.
    let embedding = provider.embed(text)?;

    // 2. Project via W (or fallback).
    let sem = match project_embedding(&embedding) {
        Ok(v) => v,

        #[cfg(feature = "keyword-fallback")]
        Err(BridgeError::WMatrixNotAvailable) => {
            // Fallback to keyword rules directly from text.
            crate::nl_translator::project_text_via_rules(text)?
        }

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

/// Abstraction for embedding providers (sentence-transformers, OpenAI, mock, ...).
pub trait EmbeddingProvider: Send + Sync {
    fn embed(&self, text: &str) -> Result<Vec<f32>, BridgeError>;
    fn dim(&self) -> usize;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_returns_32_dims_clamped() {
        // Build a tiny W in memory for deterministic testing.
        let w = WMatrix {
            rows: 32,
            cols: 4,
            data: vec![0.1; 32 * 4],
        };
        let emb = vec![1.0_f32; 4];
        let sem = w.project(&emb).unwrap();
        assert_eq!(sem.len(), 32);
        for &v in &sem {
            assert!(v >= 0.0 && v <= 1.0);
        }
    }

    #[test]
    fn project_clamps_above_one() {
        let w = WMatrix {
            rows: 32,
            cols: 2,
            data: vec![2.0; 32 * 2],
        };
        let emb = vec![1.0_f32, 1.0];
        let sem = w.project(&emb).unwrap();
        for &v in &sem {
            assert_eq!(v, 1.0);
        }
    }

    #[test]
    fn project_clamps_below_zero() {
        let w = WMatrix {
            rows: 32,
            cols: 2,
            data: vec![-1.0; 32 * 2],
        };
        let emb = vec![1.0_f32, 1.0];
        let sem = w.project(&emb).unwrap();
        for &v in &sem {
            assert_eq!(v, 0.0);
        }
    }

    #[test]
    fn project_dimension_mismatch_errors() {
        let w = WMatrix {
            rows: 32,
            cols: 4,
            data: vec![0.1; 32 * 4],
        };
        let result = w.project(&vec![0.5; 8]);
        assert!(result.is_err());
    }
}
```

Adaptar à estrutura real de `projector.rs` existente. Se o arquivo atual tem outra organização, manter a organização atual mas injetar os símbolos novos: `WMatrix`, `w_matrix()`, `project_embedding()`, `project_text()`.

---

## ARQUIVO 3 — `leet-bridge/src/error.rs` (se existir; senão criar)

Adicionar variantes:

```rust
#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    // existentes...

    #[error("W matrix not available (not found at LEET_W_PATH or default locations); \
             enable feature `keyword-fallback` for degraded mode")]
    WMatrixNotAvailable,

    #[error("W matrix load error: {0}")]
    WLoadError(String),

    #[error("dimension mismatch: expected {expected}, got {got}")]
    DimensionMismatch { expected: usize, got: usize },
}
```

---

## ARQUIVO 4 — `leet-bridge/src/nl_translator.rs`

Para suportar o fallback opt-in, expor publicamente (ou `pub(crate)`) duas helpers:

```rust
/// Default sem vector when W is not available (all 0.5 with boot exceptions).
#[cfg(feature = "keyword-fallback")]
pub fn default_sem_vector() -> [f32; 32] {
    leet_core::axes::boot_vector()
}

/// Project text through keyword rules (legacy path).
#[cfg(feature = "keyword-fallback")]
pub fn project_text_via_rules(text: &str) -> Result<[f32; 32], crate::error::BridgeError> {
    // existing keyword-matching logic extracted to this function
    // ...
}
```

Ajustar conforme nomenclatura já presente.

---

## CLAREZA OPERACIONAL — COMO ATIVAR O FALLBACK

Para quem quiser o comportamento antigo:

```bash
# Em desenvolvimento
cargo build -p leet-bridge --features keyword-fallback

# Em package distribuído
# (leet-service etc. que dependem de leet-bridge precisam passar a feature)
```

Default: **desligado**. Se W.bin não tá no filesystem, o erro é explícito e atua como guard-rail.

---

## VERIFICATION

```bash
# Gate primário
cargo build --workspace
cargo test --workspace

# Feature on
cargo build -p leet-bridge --features keyword-fallback
cargo test -p leet-bridge --features keyword-fallback

# Smoke test: W carrega
LEET_W_PATH=calibration/data/W.bin \
  cargo run --example projector_smoke 2>/dev/null || \
  echo "add a small example that calls project_text with a mock provider"
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt09c "Plug calibrated W matrix into projector, keyword-fallback as opt-in"
# work
task project:1337 +prompt09c done

git add leet-bridge/Cargo.toml \
        leet-bridge/src/projector.rs \
        leet-bridge/src/error.rs \
        leet-bridge/src/nl_translator.rs

git commit -m "feat(bridge): plug calibrated W matrix as primary projection path

- New WMatrix struct loads calibration/data/W.bin (via LEET_W_PATH or
  default locations) once per process into a static OnceLock.
- project_embedding() applies W @ embedding → clamp → sem[32].
- project_text() is the new public entry point: provider.embed() → W.
- Feature flag 'keyword-fallback' (off by default) re-enables the legacy
  nl_translator keyword path as a degraded fallback.
- Absence of W.bin without the feature is a hard error (BridgeError::
  WMatrixNotAvailable) — no silent degradation.

Rationale: the 80+ keyword heuristics were brittle. W calibrada captures
semantics learned from LLM scoring. Keeping keyword rules as opt-in
preserves backward compatibility for users who can't run calibration.

Part of Fase A block 4 (support)."

git push origin main
```

---

**END OF PROMPT_09c**
