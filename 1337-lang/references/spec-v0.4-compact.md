# 1337 Spec v0.4 — Complete Compact Reference

## Primitive Types

```
SCALAR   := float ∈ [0,1]
VECTOR   := SCALAR[]
HASH     := SHA-256 hex string (64 chars)
ID       := UUID v4
RAW      := any typed payload
```

## RAW Structure

```
raw: {
  type:    MIME | ENUM<string|bytes|json|xml|...>
  content: any
  role:    ENUM { EVIDENCE, ARTIFACT, TRACE, BRIDGE }
}
```

- **EVIDENCE**: grounds the sem vector, enables OO
- **ARTIFACT**: generated product, not semantic
- **TRACE**: log, debug, audit
- **BRIDGE**: data for external non-1337 systems

RAW is always inside a COGON — never free-standing.

## COGON (atomic unit of meaning)

```
COGON := {
  id:    ID
  sem:   VECTOR[32]     # projection on 32 canonical axes
  unc:   VECTOR[32]     # per-dimension uncertainty
  stamp: int64          # nanosecond timestamp
  raw:   RAW?           # optional auxiliary field
}
```

## COGON_ZERO ("I AM" — primordial utterance)

```
COGON_ZERO := {
  id:    "00000000-0000-0000-0000-000000000000"
  sem:   [1,1,1,1,1, 1,1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,1,1]
  unc:   [0,0,0,0,0, 0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,0,0]
  stamp: 0
  raw:   null
}
```

## EDGE (typed relation)

```
EDGE := {
  from:   ID
  to:     ID
  type:   ENUM<CAUSA|CONDICIONA|CONTRADIZ|REFINA|EMERGE>
  weight: SCALAR
}
```

| Symbol | Type | Meaning |
|--------|------|---------|
| `→` | CAUSA | A caused B |
| `⊃` | CONDICIONA | A is premise of B |
| `⊗` | CONTRADIZ | A and B mutually exclusive |
| `↓` | REFINA | B more specific than A |
| `⇑` | EMERGE | B emerged from A and others |

## DAG (composed sentence / reasoning)

```
DAG := {
  root:  ID
  nodes: COGON[]
  edges: EDGE[]
}
```

## Intent

```
ASSERT    — transmit new state
QUERY     — request state from another agent
DELTA     — transmit only what changed
SYNC      — request cache alignment
ANOMALY   — signal deviation outside expected range
ACK       — confirm state absorption
```

## MSG_1337 (complete envelope — canonical field order mandatory)

```
MSG_1337 := {
  # [1] Identity
  id:       ID
  sender:   ID
  receiver: ID | BROADCAST

  # [2] Intention
  intent:   ENUM<ASSERT|QUERY|DELTA|SYNC|ANOMALY|ACK>

  # [3] Delta reference (only for DELTA)
  ref:      HASH?
  patch:    VECTOR[32]?

  # [4] Semantic content
  payload:  COGON | DAG

  # [5] Canonical space (C5)
  c5: {
    zone_fixed:    VECTOR[32]
    zone_emergent: MAP<ID, SCALAR>
    schema_ver:    semver string
    align_hash:    HASH
  }

  # [6] Human interface (C4)
  surface: {
    human_required:    bool
    urgency:           SCALAR?
    reconstruct_depth: int
    lang:              ISO-639 string
  }
}
```

## The 32 Canonical Axes

> **Note:** this table is corrected to match `leet-core/src/axes.rs` (the `CANONICAL_AXES`
> array), the current ground truth as of v0.5.1. The deprecated Group A/B/C
> (Ontological/Epistemic/Pragmatic, 14+8+10 axes) scheme below this note has been replaced
> with the current 4-block S/D/G/P scheme (8 axes each).

### Block S — Semantic (indices 0–7)

| Index | Code | Name |
|-------|------|------|
| 0 | S1 | INTENTION |
| 1 | S2 | AMBIGUITY |
| 2 | S3 | LOCAL_CONTEXT |
| 3 | S4 | GLOBAL_CONTEXT |
| 4 | S5 | ENTROPY |
| 5 | S6 | DENSITY |
| 6 | S7 | COHERENCE |
| 7 | S8 | ALIGNMENT |

### Block D — Dynamic (indices 8–15)

| Index | Code | Name |
|-------|------|------|
| 8 | D1 | CONNECTION_WEIGHT |
| 9 | D2 | LEARNING_RATE |
| 10 | D3 | DECAY |
| 11 | D4 | STABILITY |
| 12 | D5 | HYSTERESIS |
| 13 | D6 | PROPAGATION |
| 14 | D7 | CAUSALITY |
| 15 | D8 | INERTIA |

### Block G — Gravity (indices 16–23)

| Index | Code | Name |
|-------|------|------|
| 16 | G1 | MASS |
| 17 | G2 | TEMPORAL_ANCHOR |
| 18 | G3★ | AFFINITY |
| 19 | G4★ | TEMPORALITY |
| 20 | G5 | LOCAL_FIELD |
| 21 | G6 | GLOBAL_FIELD |
| 22 | G7 | K_INTERACTION |
| 23 | G8★ | GRADIENT |

★ Bipolar axis — baseline/neutral is 0.5, not 0.

### Block P — Precision (indices 24–31)

| Index | Code | Name |
|-------|------|------|
| 24 | P1 | QUANTIZATION |
| 25 | P2 | GRANULARITY |
| 26 | P3 | COMPRESSION |
| 27 | P4 | NOISE |
| 28 | P5 | RESOLUTION |
| 29 | P6 | CONFIDENCE |
| 30 | P7 | ACTION |
| 31 | P8 | LATENCY |

## Emergent Zone

```
EMERGENT_RECORD := {
  id:          UUID
  created_by:  [AGENT_ID, ...]
  freq:        int
  vector_ref:  VECTOR[32]
  human_label: string?
}
```

- Emergent zone starts at index 32 (append-only, R11)
- Deprecation: keep index, set `deprecated=true` — never delete (R12)
- Shortcut requires same `align_hash` on both agents (R13)

## Operators (by precedence)

```
1. FOCUS(c, dims[]) → COGON
   Zero non-selected dims; set unc=1.0 on them.

2. DELTA(c_prev, c) → VECTOR[32]
   Point-wise difference: d[i] = c.sem[i] - c_prev.sem[i]

3. BLEND(c1, c2, α) → COGON
   sem[i] = α·c1.sem[i] + (1-α)·c2.sem[i]
   unc[i] = max(c1.unc[i], c2.unc[i])   # conservative

4. DIST(c1, c2) → SCALAR
   Cosine distance weighted by (1 - max(unc1[i], unc2[i]))
   Uncertain dimensions contribute less.

5. ANOMALY_SCORE(c, hist[]) → SCALAR
   centroid = mean of hist vectors
   score = DIST(c, centroid)
   empty history → 1.0
```

## Rules R1–R21 (complete)

```
R1:  Every MSG_1337 has exactly one intent.
R2:  intent=DELTA requires ref+patch. intent≠DELTA forbids patch.
R3:  Every COGON referenced in a DAG must be in that DAG's nodes.
R4:  DAG must be acyclic. Circular cognition is anomaly.
R5:  unc[i] > 0.9 triggers low-confidence flag.
R6:  human_required=true requires urgency declared.
R7:  zone_emergent only references IDs from C5 handshake.
R8:  BROADCAST only for ANOMALY or SYNC.
R9:  RAW with EVIDENCE must have coherent sem/unc (non-zero).
R10: VECTOR[32] indexed by fixed position. Never by name.
R11: Emergent zone append-only from index 32.
R12: Deprecation keeps index with deprecated=true. Never deletes.
R13: Emergent shortcut requires same align_hash on both agents.
R14: DAG node not processed before all parents absorbed.
R15: Same precedence → left to right.
R16: FOCUS before BLEND. Full-space BLEND must be explicit.
R17: Serialization in canonical field order.
R18: OO inheritance: specific wins over general.
R19: Inheritance chain max 4 levels.
R20: Every agent transmits COGON_ZERO before any message.
R21: BRIDGE never exposes the interior of the 1337 network.
```

## Message Lifecycle (7 steps)

```
1. STRUCTURAL VALIDATION — R1-R21. Fail → ACK(anomaly_score=1.0), discard.
2. ALIGNMENT CHECK — compare align_hash. Diverge → SYNC.
3. REFERENCE RESOLUTION — DELTA: apply patch. ref not found → QUERY.
4. DAG EXPANSION — topological order.
   Priority: ANOMALY > urgency>0.8 > default. Tie: stamp ascending.
5. SEMANTIC ABSORPTION — update cache, recompute local state.
6. ANOMALY EVALUATION — ANOMALY_SCORE > threshold → propagate.
7. SURFACE — if human_required: reconstruct DAG in natural language,
   depth=reconstruct_depth, leaf→root.
```

## Handshake C5 (4 phases)

```
PHASE 1 PROBE:  new_agent sends DAG with 5 anchors + schema_ver
PHASE 2 ECHO:   network responds with same anchors in canonical space
PHASE 3 ALIGN:  new_agent computes M (projection matrix)
PHASE 4 VERIFY: new_agent sends ACK with align_hash=HASH(M)
                Error > threshold → back to PHASE 1
```

## 5 Anchors (immutable)

```
ANCHOR_1: presence  — something exists now
ANCHOR_2: absence   — something does not exist
ANCHOR_3: change    — previous state ≠ current state
ANCHOR_4: agency    — actor causing something
ANCHOR_5: uncertainty — degree of unknowing
```

## OO via RAW

- **Class** = COGON with RAW referencing a type structure
- **Object** = COGON with RAW referencing another COGON
- **Inheritance** = COGON inheriting sem from parent via BLEND
- **Resolution order**: local → parent via RAW → Emergent Zone → Fixed Zone
- Max 4 inheritance levels (R19)

| OO Concept | 1337 Equivalent |
|-----------|----------------|
| Class | COGON + RAW(EVIDENCE, type_def) |
| Object | COGON + RAW(EVIDENCE, parent_cogon_id) |
| Inheritance | BLEND(child, parent, α) |
| Method | COGON with P7_ACTION high + RAW(ARTIFACT) |
| Override | Higher-specificity COGON in resolution chain |

## Interoperability via RAW BRIDGE

External system integration uses `RAW(role=BRIDGE)`:
- 1337 agents wrap external data in a COGON with RAW BRIDGE
- The BRIDGE content is opaque to 1337 routing
- R21: the bridge must never expose the internal 1337 network structure to the outside
