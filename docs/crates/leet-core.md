# leet-core

Rust crate for types, validation, operators, and binary codec of the 1337 protocol.

## Responsibility

`leet-core` is the executable specification of the protocol — no other crate defines types or rules. It does no I/O and makes no network calls.

## Main Types

### `Cogon`

```rust
pub struct Cogon {
    pub id:    Uuid,
    pub sem:   SemVec,       // [f32; 32], all in [0.0, 1.0]
    pub stamp: i64,          // Unix ms
    pub raw:   Option<RawField>,
}
```

Methods:
- `Cogon::zero()` — returns the canonical COGON_ZERO (spec § 2)
- `cogon.is_zero()` — verifies the exact structure of COGON_ZERO
- `cogon.is_low_confidence()` — `sem[29] < 0.1` (R5)
- `cogon.to_bytes()` — 96-byte binary serialization
- `Cogon::from_bytes(data)` — deserialization with CRC32 verification

### `Dag`

Directed acyclic graph of COGONs — the "semantic sentence."

```rust
pub struct Dag {
    pub root:  Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
}
```

Methods:
- `dag.add_node(cogon)` — invalidates the topological cache
- `dag.add_edge(edge)` — invalidates the topological cache
- `dag.topological_order()` — Kahn's algorithm, cached

### `Msg1337`

The complete message envelope:

```rust
pub struct Msg1337 {
    pub id:       Uuid,
    pub sender:   Uuid,
    pub receiver: Receiver,     // Agent(Uuid) | Broadcast
    pub intent:   Intent,       // ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK
    pub ref_hash: Option<[u8; 32]>,   // required for DELTA (R2)
    pub patch:    Option<SemVec>,      // required for DELTA (R2)
    pub payload:  Payload,      // Cogon | Dag
    pub c5:       C5Block,
    pub surface:  SurfaceBlock,
}
```

### `C5Block`

Canonical space block for handshake and alignment between agents:

```rust
pub struct C5Block {
    pub zone_fixed:    SemVec,              // 32 fixed axes
    pub zone_emergent: HashMap<Uuid, f32>,  // emergent axes
    pub schema_ver:    String,              // semver
    pub align_hash:    [u8; 32],            // SHA256 of the alignment
}
```

### `EdgeType`

Semantic edge types in a DAG:

| Value | Meaning |
|-------|-------------|
| `CAUSA` | causal relation |
| `CONDICIONA` | conditional relation |
| `CONTRADIZ` | contradiction |
| `REFINA` | refinement/specialization |
| `EMERGE` | emergence |

## Axes

```rust
use leet_core::axes::{CANONICAL_AXES, axis_by_code, axis_by_index, bipolar_axes};

let ax = axis_by_code("G8").unwrap();  // GRADIENT, index 23
let ax = axis_by_index(29).unwrap();   // CONFIDENCE
let bipolar = bipolar_axes();          // [G3, G4, G8]
```

The 3 bipolar axes have a neutral baseline at 0.5:

| Code | Name | Scale |
|--------|------|--------|
| G3 | AFFINITY | 0=repulsion · 0.5=neutral · 1=attraction |
| G4 | TEMPORALITY | 0=past · 0.5=present · 1=future |
| G8 | GRADIENT | 0=decelerating · 0.5=stable · 1=accelerating |

## Operators

```rust
use leet_core::operators::{blend, delta, dist, focus, anomaly_score};

// BLEND — semantic fusion with per-axis rules
let c = blend(&c1, &c2, 0.7);

// DELTA — element-wise difference (can be negative)
let patch: SemVec = delta(&c_prev, &c_curr);

// DIST — cosine distance [0, 2], weighted by P6
let d = dist(&c1, &c2);

// FOCUS — projects onto a subset of dimensions
let c_focused = focus(&cogon, &[8, 23, 26]);

// ANOMALY_SCORE — distance to the historical centroid
let score = anomaly_score(&cogon, &history);
```

## Validation (R1–R23)

```rust
use leet_core::validate;

validate::validate(&msg)?;            // validates full structure
let warnings = validate::check_confidence(&msg);  // R5 warnings
```

Implemented structural rules:

| Rule | Check |
|-------|-------------|
| R2 | DELTA requires `ref_hash` and `patch`; non-DELTA cannot have `patch` |
| R3 | All DAG edges reference existing nodes |
| R4 | DAG has no cycles (Kahn's algorithm) |
| R5 | P6_TEMPORAL_VECTOR < 0.1 → low-confidence warning |
| R6 | `human_required=true` requires an `urgency` field |
| R7 | `zone_emergent` not empty → `align_hash` not null |
| R8 | Broadcast allowed only for ANOMALY and SYNC |
| R9 | COGON with role EVIDENCE cannot have all sem values < 0.01 |
| R14 | In the DAG, parents are processed before children |
| R17 | Message is JSON-serializable |
| R20 | id=nil_UUID → must be exactly COGON_ZERO |
| R21 | raw.content does not expose internal protocol keys |
| R22 | All sem values in [0.0, 1.0] |
| R23 | stamp ≥ 0 |

Rules that depend on multi-message state (R13, R15, R16, R18) are the responsibility of the bridge/operator layer.

## Binary Codec

```rust
use leet_core::codec::{encode_cogon, decode_cogon, TOTAL_SIZE};

let bytes = encode_cogon(&cogon);    // 96 bytes, always
let cogon = decode_cogon(&bytes)?;  // verifies magic, version, CRC32
```

Format (96 bytes):

```
Offset  Size  Field
0       2        magic = 0x1337
2       1        version_flags = 0x20 (VERSION=2)
3       1        reserved = 0x00
4       16       UUID (id)
20      32       quantized sem (uint8, [0..255])
52      32       reserved zeros (was unc in v0.4)
84      8        stamp big-endian i64
92      4        CRC32 of bytes 0..92
```

Compatibility: v0.4 frames with non-zero bytes in the reserved region are accepted (CRC must be valid).

## Dependencies

```toml
[dependencies]
serde       = { version = "1", features = ["derive"] }
serde_json  = "1"
uuid        = { version = "1", features = ["v4", "serde"] }
crc32fast   = "1"
```

## Tests

```bash
cargo test -p leet-core   # 69 tests
```
