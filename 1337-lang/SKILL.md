---
name: 1337-lang
description: >
  Native inter-agent communication language 1337 v0.4 (32 canonical axes).
  TRIGGER on any mention of: 1337, COGON, COGON_ZERO, DAG semântico, espaço canônico,
  inter-agent communication language, bridge protocol, MSG_1337, vetores semânticos,
  UNC/incerteza vetorial, BLEND, FOCUS, DELTA, DIST, ANOMALY_SCORE, RAW BRIDGE,
  semantic vectors, zona emergente, handshake C5, eixos canônicos 32,
  valência ontológica, valência epistêmica, valência de ação, SemanticProjector,
  leet_core, leet_bridge, leet1337.
  Also trigger when the user wants to implement, code, test or debug any part of
  1337 in Rust or Python.
---

# 1337 — Native Inter-Agent Communication Language v0.4

1337 is a compact, typed, semantic language for AI-to-AI communication.
Instead of natural language tokens, agents exchange **COGONs** — vectors of 32 scalar values
projecting meaning onto canonical axes (ontological, epistemic, pragmatic).
The protocol is self-describing, formally validated (R1-R21), and exposes a C ABI so any
language can participate.

> **Before writing any code:** read `references/spec-v0.4-compact.md`.
> **Before projecting concepts:** read `references/axes-reference.md`.
> **Before implementing in Rust/Python:** read `references/rust-implementation-guide.md`.

---

## Primitives

| Type | Definition |
|------|-----------|
| `SCALAR` | `float ∈ [0,1]` |
| `VECTOR` | `SCALAR[]` |
| `HASH` | SHA-256 hex string |
| `ID` | UUID v4 |
| `RAW` | any (typed payload) |

---

## Compound Types

| Type | Description |
|------|-------------|
| `COGON` | Atomic unit of meaning: `{id, sem[32], unc[32], stamp, raw?}` |
| `EDGE` | Typed relation: `{from, to, type, weight}` |
| `DAG` | Composed thought/sentence: `{root, nodes[], edges[]}` |

**COGON_ZERO** ("I AM" — primordial utterance):
```
id=00000000-0000-0000-0000-000000000000, sem=[1]*32, unc=[0]*32, stamp=0, raw=null
```

---

## MSG_1337 Envelope (canonical field order)

```
id        — message UUID
sender    — agent UUID
receiver  — agent UUID | BROADCAST
intent    — ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK
ref       — HASH? (only for DELTA)
patch     — VECTOR[32]? (only for DELTA)
payload   — COGON | DAG
c5        — { zone_fixed[32], zone_emergent{}, schema_ver, align_hash }
surface   — { human_required, urgency?, reconstruct_depth, lang }
```

---

## 6 Intents

| Intent | Meaning |
|--------|---------|
| `ASSERT` | Transmit new state |
| `QUERY` | Request state from another agent |
| `DELTA` | Transmit only what changed (requires `ref`+`patch`) |
| `SYNC` | Request cache alignment |
| `ANOMALY` | Signal deviation outside expected range |
| `ACK` | Confirm state absorption |

---

## 5 Operators (by precedence)

| # | Operator | Signature | Description |
|---|----------|-----------|-------------|
| 1 | `FOCUS` | `(c, dims[]) → COGON` | Project onto dimension subset; others zeroed, unc=1 |
| 2 | `DELTA` | `(c_prev, c) → VECTOR[32]` | Point-wise difference between states |
| 3 | `BLEND` | `(c1, c2, α) → COGON` | `sem=α·c1+(1-α)·c2`; `unc=max(c1.unc, c2.unc)` |
| 4 | `DIST` | `(c1, c2) → SCALAR` | Cosine distance weighted by `(1-unc)` |
| 5 | `ANOMALY_SCORE` | `(c, hist[]) → SCALAR` | Mean dist to history centroid; empty→1.0 |

---

## 4 RAW Roles

| Role | Use |
|------|-----|
| `EVIDENCE` | Grounds the semantic vector; enables OO |
| `ARTIFACT` | Generated product, not semantic |
| `TRACE` | Log, debug, audit trail |
| `BRIDGE` | Data for non-1337 external systems (never exposes 1337 interior) |

---

## 5 EDGE Types

| Symbol | Type | Meaning |
|--------|------|---------|
| `→` | `CAUSA` | A caused B |
| `⊃` | `CONDICIONA` | A is premise of B |
| `⊗` | `CONTRADIZ` | A and B mutually exclusive |
| `↓` | `REFINA` | B is more specific than A |
| `⇑` | `EMERGE` | B emerged from combination of A and others |

---

## 6 Layers (C0–C5)

| Layer | Name | Description |
|-------|------|-------------|
| C0 | **Primitive** | Scalars, Vectors, Hashes, IDs, RAW — immutable |
| C1 | **Semantic** | COGON — the atomic unit; id+sem+unc+stamp |
| C2 | **Relational** | EDGE + DAG — composed reasoning |
| C3 | **Intentional** | MSG_1337 intent field — what the message does |
| C4 | **Surface** | Human interface — reconstruction, urgency, lang |
| C5 | **Canonical Space** | Shared coordinate system; handshake + zone_emergent |

---

## Rules R1–R21

| # | Rule |
|---|------|
| R1 | Every MSG_1337 has exactly one intent |
| R2 | intent=DELTA requires ref+patch; intent≠DELTA forbids patch |
| R3 | Every COGON referenced in a DAG must appear in that DAG's nodes |
| R4 | DAG must be acyclic — circular cognition is anomaly |
| R5 | unc[i] > 0.9 triggers low-confidence flag |
| R6 | human_required=true requires urgency declared |
| R7 | zone_emergent only references IDs from C5 handshake |
| R8 | BROADCAST only for ANOMALY or SYNC |
| R9 | RAW with EVIDENCE role must have coherent sem/unc (non-zero) |
| R10 | VECTOR[32] indexed by fixed position — never by name |
| R11 | Emergent zone is append-only from index 32 |
| R12 | Deprecation keeps index with deprecated=true — never deletes |
| R13 | Emergent shortcut requires same align_hash on both agents |
| R14 | DAG node not processed before all parents are absorbed |
| R15 | Same precedence → left to right |
| R16 | FOCUS before BLEND; full-space BLEND must be explicit |
| R17 | Serialization in canonical field order |
| R18 | OO inheritance: specific wins over general |
| R19 | Inheritance chain max 4 levels |
| R20 | Every agent transmits COGON_ZERO before any message |
| R21 | BRIDGE never exposes the interior of the 1337 network |

---

## Implementation Architecture

The 1337 stack has three layers:

```
┌─────────────────────────────────────────┐
│  Python (leet1337 package)              │
│  types.py · operators.py · bridge.py   │
│  validate.py · axes.py · cli.py        │
├─────────────────────────────────────────┤
│  PyO3 bindings  │  C ABI/FFI           │
├─────────────────┴──────────────────────┤
│  Rust (leet-core crate)                 │
│  types · axes · operators · validate   │
│  error · ffi · python                  │
├─────────────────────────────────────────┤
│  Rust (leet-bridge crate)               │
│  SemanticProjector trait               │
│  MockProjector · HumanBridge           │
└─────────────────────────────────────────┘
```

**Access patterns:**
1. **Rust native** — `use leet_core::*;`
2. **C ABI/FFI** — `leet_cogon_zero()`, `leet_blend()`, … (any language)
3. **Python** — `from leet import Cogon, blend, encode, decode` + CLI `leet encode "text"`

**Read `references/rust-implementation-guide.md` before implementing in Rust.**
**Read `references/axes-reference.md` when projecting concepts to/from COGON.**
**Read `references/spec-v0.4-compact.md` for complete formal specification.**
