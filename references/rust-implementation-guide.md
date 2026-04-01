# 1337 — Rust Implementation Guide

## Workspace Structure
```
leet1337/
├── Cargo.toml              # workspace with resolver = "2"
├── leet-core/              # lib — types, operators, validate, wire, ffi, pyo3
├── leet-bridge/            # lib — SemanticProjector, MockProjector, HumanBridge
├── leet-service/           # bin — gRPC server (tonic)
└── leet-cli/               # bin — `leet` developer tool (clap)
```

## leet-core modules

| File | Purpose |
|------|---------|
| `types.rs` | Cogon, Edge, Dag, Msg1337, Intent, EdgeType, RawRole, Raw, Surface, CanonicalSpace |
| `axes.rs` | 32 axis constants (A0_VIA … C10_VALENCIA_ACAO) + AxisDef + CANONICAL_AXES |
| `operators.rs` | focus, delta, blend, dist, anomaly_score, apply_patch, sparse_delta |
| `validate.rs` | validate(msg) → LeetResult<()>; check_confidence → Vec<(Uuid,usize,f32)> |
| `wire.rs` | WireCogon, SparseDelta, SessionId, WireIntent, WireMsg; encode/decode (MsgPack) |
| `error.rs` | LeetError enum (DimensionMismatch, ValidationFailed, Serialization, …) |
| `ffi.rs` | C ABI exports: leet_cogon_zero, leet_blend, leet_dist, leet_validate |
| `python.rs` | PyO3: PyCogon, PyDag, py_blend, py_dist, py_focus |

## leet-bridge modules

| File | Purpose |
|------|---------|
| `projector.rs` | SemanticProjector trait + MockProjector (heuristic keyword→axis) |
| `human_to_1337.rs` | HumanBridge: text_to_cogon, text_to_dag, text_to_msg |
| `leet_to_human.rs` | cogon_to_text, dag_to_text, msg_to_text |
| `error.rs` | BridgeError enum |

## Coding Conventions

### Error handling
```rust
// Always use LeetResult<T> = Result<T, LeetError>
pub fn blend(c1: &Cogon, c2: &Cogon, alpha: f32) -> LeetResult<Cogon> {
    if c1.sem.len() != FIXED_DIMS {
        return Err(LeetError::DimensionMismatch(FIXED_DIMS, c1.sem.len()));
    }
    // ...
}
```

### COGON construction
```rust
// Always use Cogon::new() for auto UUID + timestamp
let cogon = Cogon::new(sem, unc);

// COGON_ZERO explicitly
let zero = Cogon::zero();
assert!(zero.is_zero());
```

### Dimension checks
```rust
// Check at function boundaries, not inside loops
if sem.len() != FIXED_DIMS || unc.len() != FIXED_DIMS {
    return Err(LeetError::DimensionMismatch(FIXED_DIMS, sem.len()));
}
```

### Test patterns
```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn make_cogon(sem_val: f32, unc_val: f32) -> Cogon {
        Cogon::new(vec![sem_val; FIXED_DIMS], vec![unc_val; FIXED_DIMS])
    }

    #[test]
    fn test_blend_midpoint() {
        let c1 = make_cogon(1.0, 0.1);
        let c2 = make_cogon(0.0, 0.1);
        let result = blend(&c1, &c2, 0.5).unwrap();
        for val in &result.sem {
            assert!((val - 0.5).abs() < 1e-6);
        }
    }
}
```

### Wire format
```rust
// Encode: always use positional MsgPack (not named)
let bytes = encode(&wire_msg)?;   // rmp_serde::to_vec (positional)
let msg: WireMsg = decode(&bytes)?;

// unc recompute on receive
let unc = wire_cogon.recompute_unc();
// unc[i] = (1.0 - (sem[i] - 0.5).abs() * 2.0).clamp(0.0, 1.0)
```

## leet-service Architecture

```
Request → BatchQueue (10ms window) → Engine → WMatrix GEMM (SIMD) → Cogon
                                           ↗
                                    LRU Cache (1024 entries)
```

### Config from env
```rust
Config::from_env()
// LEET_PORT=50051, LEET_BACKEND=simd, LEET_STORE=memory
// LEET_BATCH_WINDOW=10, LEET_BATCH_MAX=64
// LEET_EMBED_MODEL=mock, LEET_EMBED_URL=..., LEET_EMBED_KEY=...
```

### Store trait
```rust
pub trait Store: Send + Sync {
    fn add(&self, agent_id: &str, cogon: Cogon) -> LeetResult<()>;
    fn recall(&self, agent_id: &str, query: &[f32;32], k: usize) -> LeetResult<Vec<(Cogon, f32)>>;
}
// Implementations: MemoryStore, SqliteStore, RedisStore
```

## leet-cli Commands
```
leet encode "text" [--json]     → Cogon
leet decode <sem_csv>           → text
leet dist "a" "b"               → SCALAR
leet blend "a" "b" [--alpha F]  → Cogon
leet axes [--group A|B|C]       → table
leet zero                       → COGON_ZERO
leet validate <msg.json>        → R1-R21 result
leet bench [--n N] [--parallel] → latency report
leet inspect <cogon.json>       → semantic interpretation
leet health [--service HOST]    → gRPC health
leet version                    → version info
```

## Running Tests
```bash
# All workspace tests
cargo test --workspace

# Specific crate
cargo test -p leet-core
cargo test -p leet-bridge
cargo test -p leet-service
cargo test -p leet-cli

# With output
cargo test -- --nocapture

# Specific test
cargo test test_blend_midpoint
```

## Build
```bash
cargo build --workspace --release

# Install CLI
cargo install --path leet-cli

# Check without building
cargo check --workspace
```
