# 1337 Spec v0.4 — Compact Reference

## Primitives
```
SCALAR := float ∈ [0,1]
VECTOR := SCALAR[32]
HASH   := SHA256
ID     := UUID v4
```

## COGON
```
COGON := { id: ID, sem: VECTOR[32], unc: VECTOR[32], stamp: int64, raw: RAW? }
COGON_ZERO := { id: "00000000-0000-0000-0000-000000000000", sem: [1]*32, unc: [0]*32, stamp: 0 }
```

## RAW
```
RAW := { type: MIME|ENUM, content: any, role: ENUM{EVIDENCE, ARTIFACT, TRACE, BRIDGE} }
```

## EDGE
```
EDGE := { from: ID, to: ID, type: ENUM<CAUSA|CONDICIONA|CONTRADIZ|REFINA|EMERGE>, weight: SCALAR }
```

## DAG
```
DAG := { root: ID, nodes: COGON[], edges: EDGE[] }
```

## Intent
```
INT := ENUM { ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK }
```

## MSG_1337
```
MSG_1337 := {
  id: ID, sender: ID, receiver: ID|BROADCAST,
  intent: INT,
  ref: HASH?, patch: VECTOR[32]?,
  payload: COGON|DAG,
  c5: { zone_fixed: VECTOR[32], zone_emergent: MAP<ID,SCALAR>, schema_ver: semver, align_hash: HASH },
  surface: { human_required: bool, urgency: SCALAR, reconstruct_depth: int, lang: ISO_639 }
}
```

## Operators (precedence order)
```
1. FOCUS(c, dims[])     → COGON    — project onto subset; others: sem=0, unc=1
2. DELTA(c_prev, c)     → VEC[32]  — pointwise difference
3. BLEND(c1, c2, α)     → COGON    — sem = α·c1 + (1-α)·c2; unc = max(c1.unc, c2.unc)
4. DIST(c1, c2)         → SCALAR   — cosine distance weighted by (1-unc)
5. ANOMALY_SCORE(c, []) → SCALAR   — mean distance to historical centroid
```

## Rules R1–R21
```
R1:  Every MSG_1337 has exactly one intent.
R2:  DELTA requires ref+patch. Non-DELTA forbids patch.
R3:  Every COGON in DAG edges must be in DAG.nodes.
R4:  DAG must be acyclic.
R5:  unc[i] > 0.9 → low-confidence flag.
R6:  human_required=true requires urgency declared.
R7:  zone_emergent only references C5 handshake IDs.
R8:  BROADCAST only for ANOMALY or SYNC.
R9:  RAW EVIDENCE must have coherent sem/unc.
R10: VECTOR[32] indexed by position, never by name at runtime.
R11: Emergent zone is append-only from index 32.
R12: Deprecated index stays occupied with deprecated=true.
R13: Emergent shortcut shared only if both agents have same align_hash.
R14: No DAG node processed before all parents absorbed.
R15: Same-precedence operators: left to right.
R16: FOCUS always before BLEND.
R17: Envelope serialization in canonical order.
R18: OO inheritance: specific wins.
R19: Max inheritance chain: 4 levels.
R20: Every agent transmits COGON_ZERO before any other message.
R21: BRIDGE never exposes 1337 internals to external system.
```

## C5 Handshake
```
4 phases: PROBE → ECHO → ALIGN → VERIFY
5 anchors: presence, absence, change, agency, uncertainty
```

## Wire Format (v0.4 optimization)
```
WireCogon: id(16B) + sem[32×f32=128B] + stamp(8B) = 152B  [unc omitted — recomputed]
SparseDelta: ref_id(16B) + n(1B) + n×(idx:u8, val:f32) = 17+n×5 B
WireMsg header: SessionId(8B) + WireIntent(1B) + align_hash(4B) + tag(1B) = 14B
unc recompute: unc[i] = (1 - |sem[i] - 0.5| * 2).clamp(0,1)
```

## Constants
```
FIXED_DIMS              = 32
MAX_INHERITANCE_DEPTH   = 4
LOW_CONFIDENCE_THRESHOLD = 0.9
```
