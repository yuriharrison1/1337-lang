# Rust Implementation Guide — 1337 v0.4

## Workspace Structure

```
leet1337/
├── Cargo.toml                    # workspace (members: leet-core, leet-bridge)
├── leet-core/
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # re-exports, constants
│       ├── types.rs              # all spec types
│       ├── axes.rs               # 32 canonical axes as statics
│       ├── operators.rs          # 5 operators + apply_patch + tests
│       ├── validate.rs           # Validator, R1-R21 + tests
│       ├── error.rs              # LeetError with thiserror
│       ├── ffi.rs                # C ABI extern "C"
│       └── python.rs             # PyO3 #[pymodule] (feature-gated)
└── leet-bridge/
    ├── Cargo.toml
    └── src/
        ├── lib.rs
        ├── error.rs              # BridgeError
        ├── projector.rs          # SemanticProjector trait + MockProjector
        ├── human_to_1337.rs      # HumanBridge
        └── leet_to_human.rs      # cogon_to_text, dag_to_text, msg_to_text
```

## leet-core/Cargo.toml

```toml
[package]
name = "leet_core"
version = "0.4.0"
edition = "2021"

[lib]
name = "leet_core"
crate-type = ["rlib", "cdylib"]

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4", "serde"] }
sha2 = "0.10"
hex = "0.4"
thiserror = "1"
pyo3 = { version = "0.20", features = ["extension-module"], optional = true }

[features]
default = []
python = ["pyo3"]
```

## leet-bridge/Cargo.toml

```toml
[package]
name = "leet_bridge"
version = "0.4.0"
edition = "2021"

[dependencies]
leet_core = { path = "../leet-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "1"
async-trait = "0.1"
tokio = { version = "1", features = ["rt", "macros"], optional = true }

[features]
default = []
tokio-runtime = ["tokio"]

[dev-dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

## Constants (lib.rs)

```rust
pub const FIXED_DIMS: usize = 32;
pub const MAX_INHERITANCE_DEPTH: usize = 4;
pub const LOW_CONFIDENCE_THRESHOLD: f32 = 0.9;
```

## error.rs — LeetError

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum LeetError {
    #[error("R1: message must have exactly one intent")]
    R1SingleIntent,
    #[error("R2: DELTA intent requires ref and patch")]
    R2DeltaRequiresRef,
    #[error("R2: non-DELTA intent must not include patch")]
    R2NonDeltaHasPatch,
    #[error("R3: COGON {0} referenced in DAG but not in nodes")]
    R3UndeclaredNode(String),
    #[error("R4: DAG contains a cycle — circular cognition")]
    R4DagCycle,
    #[error("R5: COGON {0} has low-confidence dimensions: {1:?}")]
    R5LowConfidence(String, Vec<usize>),
    #[error("R6: human_required=true but urgency not declared")]
    R6UrgencyRequired,
    #[error("R7: zone_emergent references ID not in C5 handshake")]
    R7InvalidEmergentId,
    #[error("R8: BROADCAST only allowed for ANOMALY or SYNC, got {0:?}")]
    R8InvalidBroadcast(String),
    #[error("R9: RAW EVIDENCE must have non-zero semantic vector")]
    R9EvidenceIncoherent,
    #[error("R10: VECTOR must have exactly {0} dimensions, got {1}")]
    R10DimensionMismatch(usize, usize),
    #[error("Dimension mismatch: expected {0}, got {1}")]
    DimensionMismatch(usize, usize),
    #[error("Scalar out of range [0,1]: {0}")]
    ScalarOutOfRange(f32),
    #[error("Serialization error: {0}")]
    Serialization(String),
    #[error("Alignment mismatch: expected {0}, got {1}")]
    AlignmentMismatch(String, String),
}

pub type LeetResult<T> = Result<T, LeetError>;
```

## types.rs — Key Types

```rust
use serde::{Deserialize, Serialize};
use uuid::Uuid;

pub type Scalar = f32;
pub type SemanticVector = Vec<f32>;
pub type Hash = String;
pub type Id = Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RawRole { Evidence, Artifact, Trace, Bridge }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Raw {
    pub content_type: String,
    pub content: serde_json::Value,
    pub role: RawRole,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cogon {
    pub id: Uuid,
    pub sem: Vec<f32>,
    pub unc: Vec<f32>,
    pub stamp: i64,
    pub raw: Option<Raw>,
}

impl Cogon {
    pub fn new(sem: Vec<f32>, unc: Vec<f32>) -> Self { /* generate UUID + timestamp */ }
    pub fn zero() -> Self { /* hardcoded COGON_ZERO */ }
    pub fn is_zero(&self) -> bool { self.id == Uuid::nil() && self.stamp == 0 }
    pub fn low_confidence_dims(&self) -> Vec<usize> {
        self.unc.iter().enumerate()
            .filter(|(_, &u)| u > 0.9)
            .map(|(i, _)| i)
            .collect()
    }
    pub fn with_raw(mut self, raw: Raw) -> Self { self.raw = Some(raw); self }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EdgeType { Causa, Condiciona, Contradiz, Refina, Emerge }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub from: Uuid,
    pub to: Uuid,
    pub edge_type: EdgeType,
    pub weight: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dag {
    pub root: Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
}

impl Dag {
    pub fn from_root(cogon: Cogon) -> Self { /* root = cogon.id */ }
    pub fn add_node(&mut self, cogon: Cogon) { self.nodes.push(cogon); }
    pub fn add_edge(&mut self, edge: Edge) { self.edges.push(edge); }
    pub fn node_ids(&self) -> Vec<Uuid> { self.nodes.iter().map(|n| n.id).collect() }
    pub fn parents_of(&self, id: Uuid) -> Vec<Uuid> { /* edges where to == id */ }
    pub fn topological_order(&self) -> LeetResult<Vec<Uuid>> { /* Kahn's algorithm */ }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Intent { Assert, Query, Delta, Sync, Anomaly, Ack }

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Receiver { Agent(Uuid), Broadcast }

impl Receiver {
    pub fn is_broadcast(&self) -> bool { matches!(self, Receiver::Broadcast) }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Payload { Single(Cogon), Graph(Dag) }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanonicalSpace {
    pub zone_fixed: Vec<f32>,
    pub zone_emergent: std::collections::HashMap<Uuid, f32>,
    pub schema_ver: String,
    pub align_hash: Hash,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Surface {
    pub human_required: bool,
    pub urgency: Option<f32>,
    pub reconstruct_depth: i32,
    pub lang: String,
}

// MSG_1337 — canonical field order via serde
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Msg1337 {
    pub id: Uuid,
    pub sender: Uuid,
    pub receiver: Receiver,
    pub intent: Intent,
    pub ref_hash: Option<Hash>,
    pub patch: Option<Vec<f32>>,
    pub payload: Payload,
    pub c5: CanonicalSpace,
    pub surface: Surface,
}

impl Msg1337 {
    pub fn hash(&self) -> Hash {
        use sha2::{Sha256, Digest};
        let json = serde_json::to_string(self).unwrap();
        let result = Sha256::digest(json.as_bytes());
        hex::encode(result)
    }
}
```

## operators.rs — Formal Definitions

```rust
/// BLEND: sem=α·c1+(1-α)·c2, unc=max(c1,c2)
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> LeetResult<Cogon>

/// DELTA: point-wise difference
pub fn delta(prev: &Cogon, curr: &Cogon) -> LeetResult<Vec<f32>>

/// DIST: cosine distance weighted by (1-unc)
/// Uncertain dimensions contribute less to the distance
pub fn dist(c1: &Cogon, c2: &Cogon) -> LeetResult<f32>

/// FOCUS: zero non-selected dims, set their unc=1.0
pub fn focus(cogon: &Cogon, dims: &[usize]) -> LeetResult<Cogon>

/// ANOMALY_SCORE: mean dist to centroid of history
/// Empty history → 1.0
pub fn anomaly_score(cogon: &Cogon, history: &[Cogon]) -> LeetResult<f32>

/// apply_patch: base.sem + patch, clamped [0,1]
pub fn apply_patch(base: &Cogon, patch: &[f32]) -> LeetResult<Cogon>
```

### DIST implementation detail

```rust
// Weighted cosine: uncertain dims contribute less
let weights: Vec<f32> = (0..FIXED_DIMS)
    .map(|i| 1.0 - c1.unc[i].max(c2.unc[i]))
    .collect();

let dot: f32 = (0..FIXED_DIMS).map(|i| c1.sem[i] * c2.sem[i] * weights[i]).sum();
let norm1: f32 = (0..FIXED_DIMS).map(|i| (c1.sem[i] * weights[i]).powi(2)).sum::<f32>().sqrt();
let norm2: f32 = (0..FIXED_DIMS).map(|i| (c2.sem[i] * weights[i]).powi(2)).sum::<f32>().sqrt();

let similarity = if norm1 * norm2 < 1e-10 { 1.0 } else { dot / (norm1 * norm2) };
1.0 - similarity.clamp(0.0, 1.0)
```

## validate.rs — Validator

```rust
pub struct Validator;

impl Validator {
    pub fn validate(msg: &Msg1337) -> LeetResult<()> {
        Self::r2_delta_ref(msg)?;
        Self::r3_declared_nodes(msg)?;
        Self::r4_no_cycles(msg)?;
        Self::r6_urgency(msg)?;
        Self::r8_broadcast(msg)?;
        Self::r9_evidence_coherence(msg)?;
        Self::r10_vector_dims(msg)?;
        Ok(())
    }

    pub fn check_confidence(msg: &Msg1337) -> Vec<(Uuid, usize, f32)> {
        // Returns soft warnings: (cogon_id, dim_index, unc_value)
        // Does NOT fail validation — just informational
    }
}
```

## ffi.rs — C ABI Contract

```rust
// MEMORY CONTRACT:
// All returned *mut c_char strings are heap-allocated by Rust.
// Caller MUST free them with leet_free_string().
// Passing NULL pointers is undefined behavior.

#[no_mangle]
pub extern "C" fn leet_free_string(s: *mut c_char) {
    unsafe { if !s.is_null() { drop(CString::from_raw(s)) } }
}

#[no_mangle] pub extern "C" fn leet_version() -> *const c_char  // static "0.4.0\0"
#[no_mangle] pub extern "C" fn leet_cogon_zero() -> *mut c_char  // JSON
#[no_mangle] pub extern "C" fn leet_cogon_new(sem: *const f32, unc: *const f32, dims: usize) -> *mut c_char
#[no_mangle] pub extern "C" fn leet_blend(c1_json: *const c_char, c2_json: *const c_char, alpha: f32) -> *mut c_char
#[no_mangle] pub extern "C" fn leet_dist(c1_json: *const c_char, c2_json: *const c_char) -> f32
#[no_mangle] pub extern "C" fn leet_delta(prev_json: *const c_char, curr_json: *const c_char) -> *mut c_char
#[no_mangle] pub extern "C" fn leet_validate(msg_json: *const c_char) -> *mut c_char  // NULL=ok
#[no_mangle] pub extern "C" fn leet_serialize(msg_json: *const c_char) -> *mut c_char
```

## python.rs — PyO3 Module

```rust
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn leet_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cogon_zero, m)?)?;
    m.add_function(wrap_pyfunction!(cogon_new, m)?)?;
    m.add_function(wrap_pyfunction!(blend, m)?)?;
    m.add_function(wrap_pyfunction!(delta, m)?)?;
    m.add_function(wrap_pyfunction!(dist, m)?)?;
    m.add_function(wrap_pyfunction!(focus, m)?)?;
    m.add_function(wrap_pyfunction!(anomaly_score, m)?)?;
    m.add_function(wrap_pyfunction!(apply_patch, m)?)?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}

// All PyO3 functions receive/return JSON strings for interop simplicity.
// Example:
#[cfg(feature = "python")]
#[pyfunction]
/// Returns COGON_ZERO as JSON string.
/// Example: leet_core.cogon_zero()
fn cogon_zero() -> String { ... }
```

## leet-bridge Architecture

```rust
// projector.rs
#[async_trait]
pub trait SemanticProjector: Send + Sync {
    async fn project(&self, text: &str) -> Result<(Vec<f32>, Vec<f32>), BridgeError>;
    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError>;
    async fn reconstruct_dag(&self, dag: &Dag, depth: usize) -> Result<String, BridgeError>;
}

// MockProjector: deterministic, no API needed
// - "urgente" → C1=0.95, C3=0.9
// - "servidor caiu" → A8=0.9, C5=0.9, A13=0.15
// - other → all 0.5, unc=0.3

// human_to_1337.rs
pub struct HumanBridge {
    projector: Box<dyn SemanticProjector>,
}

impl HumanBridge {
    pub async fn text_to_cogon(&self, text: &str) -> Result<Cogon, BridgeError>;
    pub async fn text_to_dag(&self, text: &str) -> Result<Dag, BridgeError>;
    pub async fn text_to_msg(
        &self, text: &str, sender: Uuid, receiver: Receiver, intent: Intent,
    ) -> Result<Msg1337, BridgeError>;
}

// text_to_dag heuristic:
// - single sentence → DAG with one COGON
// - multiple sentences (split on '.') → each becomes a COGON
//   connected with CONDICIONA edges (sequential logic)
```

## Build Commands

```bash
# Standard build (rlib + cdylib with C ABI)
cargo build --release

# Verify C symbols exported
nm -D target/release/libleet_core.so | grep leet_

# Build with Python bindings
cargo build --release --features python
# or via maturin:
cd python && maturin develop --features python

# Run all tests
cargo test

# Run only bridge tests
cargo test -p leet_bridge

# Check for warnings
cargo clippy -- -D warnings
```

## Python Package (leet1337)

```
python/
├── pyproject.toml          # setuptools (pure-python) or maturin (with Rust)
├── leet/
│   ├── __init__.py         # public API + BACKEND detection
│   ├── types.py            # dataclasses mirroring Rust types
│   ├── axes.py             # 32 axes as frozen dataclasses
│   ├── operators.py        # operators: try Rust, fallback to pure-Python
│   ├── validate.py         # R1-R21 validation in Python
│   ├── bridge.py           # SemanticProjector ABC + Mock + Anthropic
│   └── cli.py              # leet encode/decode/validate/zero/blend/dist/axes
└── tests/
    ├── test_types.py
    ├── test_operators.py
    ├── test_validate.py
    ├── test_bridge.py
    ├── test_cli.py
    └── test_e2e.py
```

### Pure-Python fallback pattern

```python
def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    if _rust_backend:
        result_json = _rust_backend.blend(c1.to_json(), c2.to_json(), alpha)
        return Cogon.from_json(result_json)
    # Pure Python fallback:
    sem = [alpha * a + (1 - alpha) * b for a, b in zip(c1.sem, c2.sem)]
    unc = [max(a, b) for a, b in zip(c1.unc, c2.unc)]
    return Cogon(sem=sem, unc=unc)
```

## Testing Strategy

| Layer | Tool | Notes |
|-------|------|-------|
| Rust unit | `cargo test` | in-module `#[cfg(test)]` blocks |
| Rust bridge | `cargo test -p leet_bridge` | uses MockProjector |
| Python unit | `pytest tests/` | pure-python, no API key |
| Python e2e | `pytest tests/test_e2e.py` | MockProjector, 25+ tests |

All tests must pass without any API key or network access.
