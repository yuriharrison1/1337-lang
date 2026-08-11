# COGON — Canonical Semantic Vector

**COGON** (Compressed Ontological Graph Object Node) is the core data type of the 1337 protocol. It is a 32-dimensional vector in `[0, 1]^32` that encodes the semantic state of a concept, intention, or context.

## Structure

```
Cogon {
    id:    UUID         -- unique identifier
    sem:   [f32; 32]   -- semantic vector, all in [0.0, 1.0]
    stamp: i64          -- Unix timestamp in milliseconds
    raw:   Option<RawField>  -- optional attachment (evidence, artifact, trace, bridge)
}
```

### RawField

Arbitrary content attached to a COGON without exposing protocol internals (R21):

```
RawField {
    content_type: String        -- MIME type or enum string
    content:      JSON Value    -- arbitrary payload
    role:         RawRole       -- EVIDENCE | ARTIFACT | TRACE | BRIDGE
}
```

## The 32 Canonical Axes

Organized into 4 blocks of 8 axes each. Each axis is indexed by position (R10).

### Block S — Semantic (indices 0–7)

| Index | Code | Name | Description |
|--------|--------|------|-----------|
| 0 | S1 | INTENTION | Directional purpose carried by the concept |
| 1 | S2 | AMBIGUITY | Multiplicity of possible interpretations |
| 2 | S3 | LOCAL_CONTEXT | Dependency on immediate surroundings |
| 3 | S4 | GLOBAL_CONTEXT | Anchoring in accumulated system history |
| 4 | S5 | ENTROPY | Intrinsic informational uncertainty |
| 5 | S6 | DENSITY | Meaning compressed per unit |
| 6 | S7 | COHERENCE | Internal logical consistency |
| 7 | S8 | ALIGNMENT | Shared understanding between agents |

### Block D — Dynamic (indices 8–15)

| Index | Code | Name | Description |
|--------|--------|------|-----------|
| 8 | D1 | CONNECTION_WEIGHT | Strength of the bond with other COGONs |
| 9 | D2 | LEARNING_RATE | Plasticity — speed of absorbing new data |
| 10 | D3 | DECAY | Loss of relevance without reinforcement |
| 11 | D4 | STABILITY | Tendency toward equilibrium |
| 12 | D5 | HYSTERESIS | Dependency on prior state |
| 13 | D6 | PROPAGATION | Influence over neighboring COGONs |
| 14 | D7 | CAUSALITY | Identifiability of the concept's origin |
| 15 | D8 | INERTIA | Resistance to state change |

### Block G — Gravity (indices 16–23)

| Index | Code | Name | Description |
|--------|--------|------|-----------|
| 16 | G1 | MASS | Relevance and accumulated confidence |
| 17 | G2 | TEMPORAL_ANCHOR | Degree of temporal anchoring |
| 18 | G3 | AFFINITY ★ | Bipolar association with surroundings: 0=repulsion, 0.5=neutral, 1=attraction |
| 19 | G4 | TEMPORALITY ★ | Bipolar temporal orientation: 0=past, 0.5=present, 1=future |
| 20 | G5 | LOCAL_FIELD | Dominance within the semantic cluster |
| 21 | G6 | GLOBAL_FIELD | Centrality in the global network |
| 22 | G7 | K_INTERACTION | Adaptive local gain — field sensitivity |
| 23 | G8 | GRADIENT ★ | Bipolar change direction/intensity: 0=decelerating, 0.5=stable, 1=accelerating |

### Block P — Precision (indices 24–31)

| Index | Code | Name | Description |
|--------|--------|------|-----------|
| 24 | P1 | QUANTIZATION | Rounding level controlled by Pillars 6 and 7 |
| 25 | P2 | GRANULARITY | Decomposable resolution |
| 26 | P3 | COMPRESSION | Compression of the representation |
| 27 | P4 | NOISE | Noise-to-signal ratio |
| 28 | P5 | RESOLUTION | Adaptive fineness |
| 29 | P6 | CONFIDENCE | Global fidelity |
| 30 | P7 | ACTION | Demand for active response |
| 31 | P8 | LATENCY | Representation update delay |

★ **Bipolar axes** — neutral baseline at 0.5 (G3 AFFINITY, G4 TEMPORALITY, G8 GRADIENT).

## COGON_ZERO

The canonical null COGON (spec v0.5.1 § 2). Used as the initial state in the C5 handshake.

```
id:    00000000-0000-0000-0000-000000000000
stamp: 0
sem:   [1.0, 0.0, 0.0, 0.0,  0.0, 1.0, 1.0, 1.0,   -- S
         0.5, 0.0, 0.0, 1.0,  0.0, 1.0, 1.0, 0.0,   -- D
         1.0, 0.5, 1.0, 0.5,  0.5, 1.0, 0.1, 0.0,   -- G
         0.8, 0.0, 1.0, 0.0,  0.5, 1.0, 0.0, 0.0]   -- P
```

## Compact Notation

To display COGONs inline, use only the axes with meaningful activation:

```
⟨G8=0.95 P3=0.90 D1=0.85⟩
```

Convention: list axes with value > 0.3, in descending order.

## Operators

### FOCUS(c, dims)

Projects a COGON onto a subset of dimensions. Unselected dimensions are set to 0.

```rust
focus(&cogon, &[8, 23, 26])  // only D1, G8, P3
```

### DELTA(c_prev, c)

Element-wise difference of the semantic vector. Can be negative (not clamped).

```rust
let patch: SemVec = delta(&c_prev, &c_curr);
```

### BLEND(c1, c2, α)

Semantic fusion with per-block rules:

| Axis | Rule |
|------|------|
| D4 (STABILITY) | `min(c1, c2)` — conservative |
| G1 (MASS) | `clamp(c1 + c2, 0, 1)` — accumulating |
| G7 (K_INTERACTION) | `max(c1, c2)` — higher gain wins |
| P6 (CONFIDENCE) | `min(c1, c2)` — conservative |
| others | `α·c1 + (1-α)·c2` — linear interpolation |

```rust
blend(&c1, &c2, 0.7)  // 70% c1, 30% c2
```

### DIST(c1, c2)

Cosine distance weighted by P6_CONFIDENCE. Returns `[0, 2]`:
- `0` = identical
- `1` = orthogonal
- `2` = opposite

```rust
let d = dist(&c1, &c2);
// d < 0.05 → skip re-send (information already present)
```

### ANOMALY_SCORE(c, history)

Distance from `c` to the historical centroid weighted by G1_MASS.
Returns `0.5` for empty history (neutral).

## Confidence

A COGON is flagged as **low confidence** (R5) when `P6_CONFIDENCE < 0.1`.
This raises a warning, not a validation error.

## Binary Codec

Wire format: **fixed 96 bytes** with CRC32.

```
[HEADER 4B][PAYLOAD 88B][CHECKSUM 4B]

Header:   magic=0x1337 | version=0x02 | reserved
Payload:  UUID (16B) | quantized sem (32B) | reserved zeros (32B) | stamp ms (8B)
Checksum: CRC32 of the preceding 92 bytes
```

Quantization: `float [0, 1] ↔ uint8 [0, 255]` — precision ±0.004.
Compression vs JSON: ~4-5:1.
