# 1337 Axes Reference — 32 Canonical Axes

> **Note:** this reference is corrected to match `leet-core/src/axes.rs` (the
> `CANONICAL_AXES` array), the current ground truth as of v0.5.1. The previous version of
> this document used a deprecated Group A/B/C (Ontological/Epistemic/Pragmatic, 14+8+10
> axes) scheme built around the 7 Hermetic Principles, which no longer matches the
> codebase. It has been fully rebuilt below with the current 4-block S/D/G/P scheme
> (8 axes per block). All values are `float ∈ [0,1]`. VECTOR[32] is **always indexed by
> position** — never by name (R10).

---

## Block S — Semantic (indices 0–7): What IS the concept?

This block captures the concept's intrinsic linguistic/semantic character — its purpose,
clarity, context-dependence, and internal coherence.

### [0] S1 INTENTION
**Directional purpose carried by the concept.**
- High (→1.0) = strong directional purpose, deliberate aim, clear intent
- Low (→0.0) = no clear purpose, aimless, incidental
- Examples: "mission statement" → 0.9 | "casual remark" → 0.3 | "random noise" → 0.05

### [1] S2 AMBIGUITY
**Multiplicity of possible interpretations.**
- High (→1.0) = highly ambiguous, many valid readings
- Low (→0.0) = single, unambiguous interpretation
- Examples: "bank (river or finance?)" → 0.9 | "it depends" → 0.85 | "2 + 2 = 4" → 0.02

### [2] S3 LOCAL_CONTEXT
**Dependency on immediate surroundings.**
- High (→1.0) = strongly context-dependent, meaningless in isolation
- Low (→0.0) = context-independent, self-contained
- Examples: "that one" (pronoun) → 0.9 | "water boils at 100°C" → 0.1

### [3] S4 GLOBAL_CONTEXT
**Anchoring in accumulated system history.**
- High (→1.0) = strongly anchored in long-running session/system history
- Low (→0.0) = unanchored, a freestanding fact
- Examples: "as we discussed earlier" → 0.9 | "1 + 1 = 2" → 0.05

### [4] S5 ENTROPY
**Intrinsic informational uncertainty.**
- High (→1.0) = high uncertainty, unpredictable
- Low (→0.0) = low uncertainty, predictable
- Examples: "coin flip outcome" → 0.9 | "the sun rises tomorrow" → 0.05

### [5] S6 DENSITY
**Meaning compressed per unit.**
- High (→1.0) = dense, meaning-packed
- Low (→0.0) = sparse, verbose, thin content
- Examples: "E=mc²" → 0.95 | "um, well, you know..." → 0.1

### [6] S7 COHERENCE
**Internal logical consistency.**
- High (→1.0) = fully coherent, no contradictions
- Low (→0.0) = incoherent, self-contradictory
- Examples: "well-formed proof" → 0.95 | "contradictory statement" → 0.1

### [7] S8 ALIGNMENT
**Shared understanding between agents.**
- High (→1.0) = fully aligned, mutually understood
- Low (→0.0) = misaligned, divergent understanding
- Examples: "confirmed shared understanding" → 0.9 | "miscommunication" → 0.1

---

## Block D — Dynamic (indices 8–15): How does it CHANGE?

This block captures how the concept behaves over time and through interaction: its
bonds, plasticity, decay, and resistance to change.

### [8] D1 CONNECTION_WEIGHT
**Strength of the bond with other COGONs.**
- High (→1.0) = strongly bonded/coupled
- Low (→0.0) = weakly bonded, isolated
- Examples: "tightly coupled service" → 0.9 | "standalone utility" → 0.1

### [9] D2 LEARNING_RATE
**Plasticity — speed of absorbing new data.**
- High (→1.0) = highly plastic, adapts fast
- Low (→0.0) = rigid, resists updates
- Examples: "online learning model" → 0.9 | "hardcoded constant" → 0.05

### [10] D3 DECAY
**Loss of relevance without reinforcement.**
- High (→1.0) = decays fast without reinforcement
- Low (→0.0) = persists, no decay
- Examples: "breaking news" → 0.9 | "mathematical constant" → 0.02

### [11] D4 STABILITY
**Tendency toward equilibrium.**
- High (→1.0) = stable, converges to equilibrium
- Low (→0.0) = unstable, diverges
- Examples: "physical law" → 0.95 | "market crash" → 0.1

### [12] D5 HYSTERESIS
**Dependency on prior state.**
- High (→1.0) = strong path-dependency, remembers prior state
- Low (→0.0) = no memory of prior state
- Examples: "thermostat with hysteresis band" → 0.9 | "stateless function" → 0.05

### [13] D6 PROPAGATION
**Influence over neighboring COGONs.**
- High (→1.0) = highly propagating, contagious influence
- Low (→0.0) = isolated, no spread
- Examples: "viral trend" → 0.9 | "private note" → 0.1

### [14] D7 CAUSALITY
**Identifiability of the concept's origin** (v0.5.1: replaces SATURATION).
- High (→1.0) = clear, traceable origin
- Low (→0.0) = opaque, untraceable origin
- Examples: "root cause identified" → 0.9 | "mysterious bug" → 0.1

### [15] D8 INERTIA
**Resistance to state change.**
- High (→1.0) = high resistance to change
- Low (→0.0) = low resistance, easily changed
- Examples: "legacy system" → 0.85 | "draft in progress" → 0.15

---

## Block G — Gravity (indices 16–23): How does it RELATE across the field?

This block captures the concept's position and pull within the semantic field: its
relevance, temporal anchoring, association, and rate of change. It contains 3 of the
protocol's 3 bipolar axes (marked ★), whose neutral baseline is 0.5, not 0.

### [16] G1 MASS
**Relevance and accumulated confidence.**
- High (→1.0) = highly relevant, high accumulated confidence
- Low (→0.0) = low relevance, low confidence
- Examples: "core architectural decision" → 0.9 | "throwaway comment" → 0.1

### [17] G2 TEMPORAL_ANCHOR
**Degree of temporal anchoring** (v0.5.1: replaces DISTANCE).
- High (→1.0) = precisely anchored in time
- Low (→0.0) = untethered in time
- Examples: "timestamped log entry" → 0.9 | "timeless proverb" → 0.05

### [18] G3★ AFFINITY
**Bipolar association with surroundings** (0=repulsion · 0.5=neutral · 1=attraction).
- Examples: "strong rejection" → 0.1 | "neutral mention" → 0.5 | "strong endorsement" → 0.9

### [19] G4★ TEMPORALITY
**Bipolar temporal orientation** (0=past · 0.5=present · 1=future).
- Examples: "post-mortem" → 0.1 | "current status" → 0.5 | "roadmap" → 0.9

### [20] G5 LOCAL_FIELD
**Dominance within the semantic cluster.**
- High (→1.0) = locally dominant within its cluster
- Low (→0.0) = peripheral within its cluster
- Examples: "primary key concept in the doc" → 0.9 | "footnote" → 0.1

### [21] G6 GLOBAL_FIELD
**Centrality in the global network.**
- High (→1.0) = globally central
- Low (→0.0) = peripheral overall
- Examples: "foundational protocol rule" → 0.9 | "obscure edge case" → 0.1

### [22] G7 K_INTERACTION
**Adaptive local gain — field sensitivity.**
- High (→1.0) = highly sensitive to local field changes
- Low (→0.0) = low sensitivity, inert
- Examples: "reactive trigger" → 0.85 | "inert constant" → 0.1

### [23] G8★ GRADIENT
**Bipolar change direction/intensity** (0=decelerating · 0.5=stable · 1=accelerating).
- Examples: "slowing down" → 0.1 | "steady state" → 0.5 | "rapidly accelerating" → 0.9

---

## Block P — Precision (indices 24–31): How CONFIDENT/actionable is it?

This block captures the fidelity, granularity, and actionability of the representation
itself — how the concept should be handled once received.

### [24] P1 QUANTIZATION
**Rounding level controlled by Pillars 6 and 7.**
- High (→1.0) = coarsely rounded
- Low (→0.0) = fine-grained
- Examples: "rough estimate" → 0.8 | "exact measurement" → 0.1

### [25] P2 GRANULARITY
**Decomposable resolution.**
- High (→1.0) = finely decomposable
- Low (→0.0) = monolithic
- Examples: "detailed breakdown" → 0.9 | "black box" → 0.1

### [26] P3 COMPRESSION
**Compression of representation.**
- High (→1.0) = highly compressed
- Low (→0.0) = uncompressed, verbose
- Examples: "COGON vector" → 0.9 | "verbose transcript" → 0.1

### [27] P4 NOISE
**Noise vs. signal ratio.**
- High (→1.0) = high noise
- Low (→0.0) = clean signal
- Examples: "garbled transmission" → 0.9 | "clean measurement" → 0.05

### [28] P5 RESOLUTION
**Adaptive fineness.**
- High (→1.0) = fine resolution
- Low (→0.0) = coarse resolution
- Examples: "high-res sensor reading" → 0.9 | "ballpark figure" → 0.1

### [29] P6 CONFIDENCE
**Global fidelity** (v0.5.1: replaces unc[32]).
- High (→1.0) = high fidelity/confidence
- Low (→0.0) = low fidelity/confidence
- Examples: "verified fact" → 0.95 | "unconfirmed rumor" → 0.1

### [30] P7 ACTION
**Demand for active response** (v0.5.1: replaces COST).
- High (→1.0) = demands action
- Low (→0.0) = informational only
- Examples: "rollback now" → 0.95 | "FYI, no action needed" → 0.05

### [31] P8 LATENCY
**Representation update delay.**
- High (→1.0) = high delay
- Low (→0.0) = immediate
- Examples: "nightly batch job" → 0.9 | "real-time stream" → 0.05

---

## Projection Guide

When projecting a concept, ask for each axis: "How much does this concept express this
quality?" The three examples below re-project the same source sentences used in the
previous (deprecated) version of this document, now scored against the current 32-axis
S/D/G/P scheme.

### Example 1: "The server crashed"

```
[0]  S1 INTENTION           0.30  # no deliberate purpose, it's a failure event
[1]  S2 AMBIGUITY           0.20  # meaning is clear
[2]  S3 LOCAL_CONTEXT       0.60  # "the server" needs context to resolve which one
[3]  S4 GLOBAL_CONTEXT      0.50
[4]  S5 ENTROPY             0.40
[5]  S6 DENSITY             0.50
[6]  S7 COHERENCE           0.80
[7]  S8 ALIGNMENT           0.60
[8]  D1 CONNECTION_WEIGHT   0.60  # affects dependent services
[9]  D2 LEARNING_RATE       0.20
[10] D3 DECAY               0.70  # urgency fades once resolved
[11] D4 STABILITY           0.10  # unstable state
[12] D5 HYSTERESIS          0.40
[13] D6 PROPAGATION         0.80  # impacts other systems
[14] D7 CAUSALITY           0.40  # root cause not yet known
[15] D8 INERTIA             0.30
[16] G1 MASS                0.90  # highly relevant, urgent
[17] G2 TEMPORAL_ANCHOR     0.90  # precise timestamp (health check)
[18] G3 AFFINITY            0.15  # repulsion — negative event
[19] G4 TEMPORALITY         0.55  # just happened, near-present
[20] G5 LOCAL_FIELD         0.80
[21] G6 GLOBAL_FIELD        0.60
[22] G7 K_INTERACTION       0.70
[23] G8 GRADIENT            0.15  # degrading, decelerating
[24] P1 QUANTIZATION        0.30
[25] P2 GRANULARITY         0.50
[26] P3 COMPRESSION         0.40
[27] P4 NOISE               0.30
[28] P5 RESOLUTION          0.60
[29] P6 CONFIDENCE          0.85  # high certainty this happened
[30] P7 ACTION              0.90  # demands response
[31] P8 LATENCY             0.10  # needs immediate handling
```

### Example 2: "I need urgent help"

```
[0]  S1 INTENTION           0.85  # clear directional purpose — asking for help
[1]  S2 AMBIGUITY           0.30
[2]  S3 LOCAL_CONTEXT       0.60
[3]  S4 GLOBAL_CONTEXT      0.30
[4]  S5 ENTROPY             0.50
[5]  S6 DENSITY             0.60
[6]  S7 COHERENCE           0.80
[7]  S8 ALIGNMENT           0.40  # not yet aligned, seeking alignment
[8]  D1 CONNECTION_WEIGHT   0.80  # depends on another agent
[9]  D2 LEARNING_RATE       0.30
[10] D3 DECAY               0.60
[11] D4 STABILITY           0.20
[12] D5 HYSTERESIS          0.30
[13] D6 PROPAGATION         0.50
[14] D7 CAUSALITY           0.30
[15] D8 INERTIA             0.20
[16] G1 MASS                0.80
[17] G2 TEMPORAL_ANCHOR     0.70
[18] G3 AFFINITY            0.60  # seeking connection — mild attraction
[19] G4 TEMPORALITY         0.55
[20] G5 LOCAL_FIELD         0.60
[21] G6 GLOBAL_FIELD        0.40
[22] G7 K_INTERACTION       0.70
[23] G8 GRADIENT            0.75  # urgency — accelerating
[24] P1 QUANTIZATION        0.40
[25] P2 GRANULARITY         0.30
[26] P3 COMPRESSION         0.30
[27] P4 NOISE               0.30
[28] P5 RESOLUTION          0.50
[29] P6 CONFIDENCE          0.60
[30] P7 ACTION              0.90  # demands active response
[31] P8 LATENCY             0.05  # immediate
```

### Example 3: "Gravity is a fundamental force"

```
[0]  S1 INTENTION           0.20  # purely informational statement
[1]  S2 AMBIGUITY           0.10
[2]  S3 LOCAL_CONTEXT       0.10
[3]  S4 GLOBAL_CONTEXT      0.70  # well-established scientific fact
[4]  S5 ENTROPY             0.05
[5]  S6 DENSITY             0.70
[6]  S7 COHERENCE           0.95
[7]  S8 ALIGNMENT           0.90
[8]  D1 CONNECTION_WEIGHT   0.30
[9]  D2 LEARNING_RATE       0.05
[10] D3 DECAY               0.02
[11] D4 STABILITY           0.95
[12] D5 HYSTERESIS          0.10
[13] D6 PROPAGATION         0.30
[14] D7 CAUSALITY           0.70
[15] D8 INERTIA             0.90
[16] G1 MASS                0.85
[17] G2 TEMPORAL_ANCHOR     0.05  # timeless
[18] G3 AFFINITY            0.50  # neutral
[19] G4 TEMPORALITY         0.50  # atemporal / eternal present
[20] G5 LOCAL_FIELD         0.60
[21] G6 GLOBAL_FIELD        0.90
[22] G7 K_INTERACTION       0.20
[23] G8 GRADIENT            0.50  # stable
[24] P1 QUANTIZATION        0.20
[25] P2 GRANULARITY         0.40
[26] P3 COMPRESSION         0.50
[27] P4 NOISE               0.05
[28] P5 RESOLUTION          0.60
[29] P6 CONFIDENCE          0.95
[30] P7 ACTION              0.10  # informative, no action demanded
[31] P8 LATENCY             0.50
```

---

## Quick Index

```
S1=0  S2=1  S3=2  S4=3  S5=4  S6=5  S7=6  S8=7
D1=8  D2=9  D3=10 D4=11 D5=12 D6=13 D7=14 D8=15
G1=16 G2=17 G3=18 G4=19 G5=20 G6=21 G7=22 G8=23
P1=24 P2=25 P3=26 P4=27 P5=28 P6=29 P7=30 P8=31
```
