# SKILL — 1337 Project Context for Claude Code

## Overview

**1337** is an inter-agent communication language built around semantic vectors.
Every concept is encoded as a COGON — a 32-dimensional semantic vector with an
uncertainty companion. Agents exchange typed envelopes (MSG_1337) over a shared
bus, enabling lossless, compressed communication without natural language overhead.

**Spec version**: v0.4
**Repo**: `git@github.com:yuriharrison1/1337-lang.git`
**Git root**: `/home/yuri/Projetos/1337/`

---

## Repo Structure

```
1337/
├── SKILL.md                  ← this file
├── CONTRACT.md               ← implementation contract + task tracking
├── Cargo.toml                ← Rust workspace root
├── leet-core/                ← Rust library: types, operators, validation, FFI
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs            ← re-exports all modules
│       ├── types.rs          ← Cogon, Edge, Dag, Msg1337, Intent, COGON_ZERO
│       ├── axes.rs           ← 32 canonical axes with metadata
│       ├── operators.rs      ← FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE
│       ├── validate.rs       ← R1–R21 validation
│       ├── error.rs          ← LeetError enum
│       ├── ffi.rs            ← C ABI exports
│       └── python.rs         ← PyO3 bindings (feature = "python")
├── leet-bridge/              ← Rust library: SemanticProjector + HumanBridge
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs
│       ├── projector.rs      ← SemanticProjector trait + MockProjector
│       └── human_bridge.rs   ← text_to_cogon, text_to_msg, cogon_to_text
├── python/                   ← Python package leet1337
│   ├── pyproject.toml
│   ├── leet/
│   │   ├── __init__.py
│   │   ├── types.py          ← Cogon, Edge, Dag, Msg1337, COGON_ZERO
│   │   ├── axes.py           ← CANONICAL_AXES (32 dicts)
│   │   ├── operators.py      ← blend, focus, delta, dist, anomaly_score
│   │   ├── validate.py       ← validate_cogon, validate_dag, validate_msg
│   │   ├── bridge.py         ← MockProjector, text_to_cogon, cogon_to_text
│   │   └── cli.py            ← Click CLI: encode|decode|zero|blend|dist|axes|validate
│   └── tests/
└── examples/
    └── net1337.py            ← Interactive IRC-style multi-agent simulator
```

---

## Spec Primitives

```
SCALAR  := float ∈ [0,1]
VECTOR  := SCALAR[]           (always 32 dims in fixed zone)
HASH    := SHA256
ID      := UUID v4
RAW     := any                (lives inside COGON only)
```

## Core Types

### COGON (the word)
```
Cogon { id: UUID, sem: [f32;32], unc: [f32;32], stamp: i64, raw: Option<RawField> }
```

### COGON_ZERO (bootstrap sentinel)
```
id:    "00000000-0000-0000-0000-000000000000"
sem:   [1.0; 32]
unc:   [0.0; 32]
stamp: 0
raw:   None
```
Every agent MUST transmit COGON_ZERO before any other message (R20).

### EDGE
```
Edge { from: UUID, to: UUID, edge_type: EdgeType, weight: f32 }
EdgeType: CAUSA | CONDICIONA | CONTRADIZ | REFINA | EMERGE
```

### DAG (the sentence)
```
Dag { root: UUID, nodes: Vec<Cogon>, edges: Vec<Edge> }
```
Must be acyclic (R4). All referenced nodes must exist (R3).

### MSG_1337 (the envelope)
```
Msg1337 {
  id, sender, receiver,
  intent: ASSERT|QUERY|DELTA|SYNC|ANOMALY|ACK,
  ref_hash: Option<[u8;32]>,
  patch: Option<[f32;32]>,
  payload: Cogon|Dag,
  c5: C5Block { zone_fixed, zone_emergent, schema_ver, align_hash },
  surface: SurfaceBlock { human_required, urgency, reconstruct_depth, lang }
}
```

---

## 32 Canonical Axes

| Idx | Code | Name | Group |
|-----|------|------|-------|
| 0 | A0 | VIA | Ontological |
| 1 | A1 | CORRESPONDÊNCIA | Ontological |
| 2 | A2 | VIBRAÇÃO | Ontological |
| 3 | A3 | POLARIDADE | Ontological |
| 4 | A4 | RITMO | Ontological |
| 5 | A5 | CAUSA E EFEITO | Ontological |
| 6 | A6 | GÊNERO | Ontological |
| 7 | A7 | SISTEMA | Ontological |
| 8 | A8 | ESTADO | Ontological |
| 9 | A9 | PROCESSO | Ontological |
| 10 | A10 | RELAÇÃO | Ontological |
| 11 | A11 | SINAL | Ontological |
| 12 | A12 | ESTABILIDADE | Ontological |
| 13 | A13 | VALÊNCIA ONTOLÓGICA | Ontological |
| 14 | B1 | VERIFICABILIDADE | Epistemic |
| 15 | B2 | TEMPORALIDADE | Epistemic |
| 16 | B3 | COMPLETUDE | Epistemic |
| 17 | B4 | CAUSALIDADE | Epistemic |
| 18 | B5 | REVERSIBILIDADE | Epistemic |
| 19 | B6 | CARGA | Epistemic |
| 20 | B7 | ORIGEM | Epistemic |
| 21 | B8 | VALÊNCIA EPISTÊMICA | Epistemic |
| 22 | C1 | URGÊNCIA | Pragmatic |
| 23 | C2 | IMPACTO | Pragmatic |
| 24 | C3 | AÇÃO | Pragmatic |
| 25 | C4 | VALOR | Pragmatic |
| 26 | C5 | ANOMALIA | Pragmatic |
| 27 | C6 | AFETO | Pragmatic |
| 28 | C7 | DEPENDÊNCIA | Pragmatic |
| 29 | C8 | VETOR TEMPORAL | Pragmatic |
| 30 | C9 | NATUREZA | Pragmatic |
| 31 | C10 | VALÊNCIA DE AÇÃO | Pragmatic |

Emergent zone starts at index 32 (append-only, R11).

---

## Operators

```
FOCUS(c, dims[]) → Cogon           — project onto dimensional subset
DELTA(c_prev, c) → [f32;32]        — difference between two states
BLEND(c1, c2, α) → Cogon           — sem = α·c1.sem + (1-α)·c2.sem; unc = max(c1,c2)
DIST(c1, c2) → f32                 — cosine distance weighted by (1-unc)
ANOMALY_SCORE(c, hist[]) → f32     — mean distance to historical centroid
```

Operator precedence: FOCUS > BLEND > others. Same-precedence: left-to-right (R15, R16).

---

## Rules R1–R21

| Rule | Constraint |
|------|-----------|
| R1 | Every MSG_1337 has exactly one intent |
| R2 | intent=DELTA requires ref+patch; non-DELTA prohibits patch |
| R3 | Every COGON referenced in DAG must be in nodes[] |
| R4 | DAG cannot have cycles |
| R5 | unc[i] > 0.9 triggers low-confidence flag |
| R6 | surface.human_required=true requires urgency declared |
| R7 | zone_emergent only references IDs registered in C5 handshake |
| R8 | BROADCAST only for ANOMALY or SYNC |
| R9 | RAW role=EVIDENCE must have coherent sem/unc |
| R10 | VECTOR[32] indexed by position, never by name at runtime |
| R11 | Emergent zone is append-only from index 32 |
| R12 | Deprecation keeps index with deprecated=true flag |
| R13 | Two agents share emergent shortcut only if both have same index in align_hash |
| R14 | No DAG node processed before all parents absorbed |
| R15 | Same-precedence operators: left to right |
| R16 | FOCUS always before BLEND |
| R17 | Envelope serialization in canonical order |
| R18 | OO inheritance conflict: specific wins |
| R19 | Max inheritance chain: 4 levels |
| R20 | Every agent transmits COGON_ZERO before any other message |
| R21 | BRIDGE agent never exposes 1337 internals to external system |

---

## Coding Conventions

### Rust (leet-core, leet-bridge)
- Edition 2021, resolver 2
- `[f32; 32]` for all semantic/uncertainty vectors (never Vec)
- `Scalar` is a newtype `f32` clamped to [0,1]
- `LeetError` enum with one variant per rule violation
- No `unwrap()` in library code — always propagate with `?`
- C ABI exports in `ffi.rs` with `#[no_mangle] extern "C"`
- PyO3 bindings gated behind `#[cfg(feature = "python")]`
- All structs derive `Serialize, Deserialize, Clone, Debug`

### Python (python/leet/)
- Python 3.10+, pure stdlib + click
- All vectors as `list[float]` with length assertion
- `COGON_ZERO` constant at module level
- `validate_*` functions return `list[str]` of errors (empty = valid)
- CLI uses Click, entry point `leet`

### Tests
- Rust: minimum 40 tests covering all rules and operators
- Python: minimum 25 tests (currently 146)
- Test data uses deterministic values, no randomness

---

## C5 Handshake (4 phases)

```
PROBE → ECHO → ALIGN → VERIFY
```
5 anchor concepts: presence, absence, change, agency, uncertainty.
Used to negotiate emergent zone IDs before communication starts.

---

## Message Lifecycle (7 steps)

1. Structural validation
2. Alignment check
3. Reference resolution
4. DAG expansion
5. Semantic absorption
6. Anomaly evaluation
7. Surface

---

## Key Dependencies

### Rust
- `serde` + `serde_json` — serialization
- `uuid` (v4 + serde features) — UUIDs
- `sha2` — SHA256 hashing
- `thiserror` — error derivation
- `pyo3` (optional, feature="python") — PyO3 bindings

### Python
- `click>=8.0` — CLI
- `pytest>=8` (dev) — testing

---

## Quick Start

```bash
# Build Rust
cargo build --workspace
cargo test --workspace

# Python
cd python && pip install -e ".[dev]"
pytest tests/ -v

# CLI
leet zero
leet encode "controle preditivo urgente"
leet dist "hello" "world"
leet axes

# Simulator
python examples/net1337.py
```
