# leet-core

[![crates.io](https://img.shields.io/crates/v/leet-core.svg)](https://crates.io/crates/leet-core)
[![docs.rs](https://docs.rs/leet-core/badge.svg)](https://docs.rs/leet-core)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](../LICENSE)

Core types and algebra for the **1337 semantic protocol** — the inter-agent
communication language for AI systems.

## What's here

- `Cogon` — the 32-axis semantic vector (`sem: [f32; 32]`, all values in `[0, 1]`)
- `SemVec` — type alias for `[f32; 32]`
- 32 canonical axes across 4 blocks: **S**emantics · **D**ynamics · **G**ravity · **P**recision
- Algebra: `blend()`, `dist()`, `cogon_zero()`
- Protocol validation: R1–R25 structural rules
- `UserFacingError` — typed, actionable errors for CLI/MCP boundaries
- Binary codec: 96-byte fixed COGON frames with CRC32

## Usage

```toml
[dependencies]
leet-core = "0.5"
```

```rust
use leet_core::{Cogon, blend, dist, cogon_zero};

// Blend two COGONs (BLEND operator)
let result = blend(&a, &b, 0.5);

// Cosine distance weighted by P6_CONFIDENCE
let d = dist(&a, &b);

// The canonical boot vector (R20: broadcast on network join)
let zero = cogon_zero();
```

## The 32 axes

| Block | Codes | Axes |
|---|---|---|
| **S** Semantic | S1–S8 | INTENTION · AMBIGUITY · LOCAL_CONTEXT · GLOBAL_CONTEXT · ENTROPY · DENSITY · COHERENCE · ALIGNMENT |
| **D** Dynamic | D1–D8 | CONNECTION_WEIGHT · LEARNING_RATE · DECAY · STABILITY · HYSTERESIS · PROPAGATION · CAUSALITY · INERTIA |
| **G** Gravity | G1–G8 | MASS · TEMPORAL_ANCHOR · AFFINITY★ · TEMPORALITY★ · LOCAL_FIELD · GLOBAL_FIELD · K_INTERACTION · GRADIENT★ |
| **P** Precision | P1–P8 | QUANTIZATION · GRANULARITY · COMPRESSION · NOISE · RESOLUTION · CONFIDENCE · ACTION · LATENCY |

★ Bipolar axes (0=negative pole · 0.5=neutral · 1=positive pole)

## License

Apache-2.0. Part of the [1337 project](https://github.com/leetlang/leet).
