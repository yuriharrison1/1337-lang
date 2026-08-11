# 1337 — 32 Canonical Axes Reference

> Corrected to match `leet-core/src/axes.rs` (the `CANONICAL_AXES` array), the current ground truth as of v0.5.1. The previous version of this table used a deprecated Group A/B/C (Ontological/Epistemic/Pragmatic) scheme that no longer matches the codebase; it has been replaced below with the current S/D/G/P block scheme.

## Block S — Semantic (0–7): What IS the concept?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 0 | S1 | INTENTION | Directional purpose carried by the concept (0=no clear purpose, 1=strong directional purpose) | essência, núcleo / essence, identity, core |
| 1 | S2 | AMBIGUITY | Multiplicity of possible interpretations (0=single interpretation, 1=highly ambiguous) | análogo, parecido / similar, analogous, resembles |
| 2 | S3 | LOCAL_CONTEXT | Dependency on immediate surroundings (0=context-independent, 1=strongly context-dependent) | mudança, transformação / change, transition, migration |
| 3 | S4 | GLOBAL_CONTEXT | Anchoring in accumulated system history (0=unanchored, 1=strongly anchored) | oposto, extremo / opposite, spectrum, polarity |
| 4 | S5 | ENTROPY | Intrinsic informational uncertainty (0=low uncertainty, 1=high uncertainty) | ciclo, periódico / cycle, periodic, recurring |
| 5 | S6 | DENSITY | Meaning compressed per unit (0=sparse, 1=dense) | porque, causa / cause, result of, consequence |
| 6 | S7 | COHERENCE | Internal logical consistency (0=incoherent, 1=fully coherent) | gera, ativo / generates, active, proactive |
| 7 | S8 | ALIGNMENT | Shared understanding between agents (0=misaligned, 1=fully aligned) | sistema, rede / system, network, emergent |

## Block D — Dynamic (8–15): How does it CHANGE?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 8 | D1 | CONNECTION_WEIGHT | Strength of the bond with other COGONs (0=weak bond, 1=strong bond) | status, estado / status, state, condition |
| 9 | D2 | LEARNING_RATE | Plasticity — speed of absorbing new data (0=rigid, 1=highly plastic) | processo, pipeline / process, deploy, running |
| 10 | D3 | DECAY | Loss of relevance without reinforcement (0=no decay, 1=rapid decay) | relacionado, conectado / related, connected, dependency |
| 11 | D4 | STABILITY | Tendency toward equilibrium (0=unstable, 1=stable) | sinal, evento / signal, event, alert, trigger |
| 12 | D5 | HYSTERESIS | Dependency on prior state (0=no memory of prior state, 1=strong path-dependency) | estável, equilíbrio / stable, equilibrium, unstable |
| 13 | D6 | PROPAGATION | Influence over neighboring COGONs (0=isolated, 1=highly propagating) | bom, funciona / good, works, success — vs. ruim, falhou / bad, failed |
| 14 | D7 | CAUSALITY | Identifiability of concept's origin (0=opaque origin, 1=clear origin) | origem, causado por / source, root cause, reason |
| 15 | D8 | INERTIA | Resistance to state change (0=low resistance, 1=high resistance) | confirmado, verificado / confirmed, verified, tested |

## Block G — Gravity (16–23): How does it RELATE across the field?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 16 | G1 | MASS | Relevance and accumulated confidence (0=low relevance, 1=high relevance) | quando, agendado / when, schedule, timestamp |
| 17 | G2 | TEMPORAL_ANCHOR | Degree of temporal anchoring (0=untethered in time, 1=precisely anchored) | ontem, passado / yesterday, previously — vs. amanhã, futuro / tomorrow, future, planned |
| 18 | G3★ | AFFINITY | Bipolar association with surroundings (0=repulsion · 0.5=neutral · 1=attraction) | completo, resolvido / complete, done, resolved — vs. pendente, bloqueado / pending, blocked |
| 19 | G4★ | TEMPORALITY | Bipolar temporal orientation (0=past · 0.5=present · 1=future) | reverter, rollback / revert, undo — vs. irreversível, permanente / irreversible, permanent |
| 20 | G5 | LOCAL_FIELD | Dominance within the semantic cluster (0=peripheral, 1=locally dominant) | complexo, difícil / complex, difficult, heavy |
| 21 | G6 | GLOBAL_FIELD | Centrality in the global network (0=peripheral, 1=globally central) | observado, medido / observed, detected, measured |
| 22 | G7 | K_INTERACTION | Adaptive local gain — field sensitivity (0=low sensitivity, 1=high sensitivity) | certamente, confirmado / certainly, confirmed, correct |
| 23 | G8★ | GRADIENT | Bipolar change direction/intensity (0=decelerating · 0.5=stable · 1=accelerating) | urgente, crítico / urgent, critical, emergency |

★ Bipolar axis — baseline/neutral is 0.5, not 0.

## Block P — Precision (24–31): How CONFIDENT/actionable is it?

| Idx | Code | Name | Range | Keywords |
|-----|------|------|-------|----------|
| 24 | P1 | QUANTIZATION | Rounding level controlled by Pillars 6 and 7 (0=fine-grained, 1=coarsely rounded) | impacto, consequência / impact, consequence, effect |
| 25 | P2 | GRANULARITY | Decomposable resolution (0=monolithic, 1=finely decomposable) | valor, importa / value, matters, essential |
| 26 | P3 | COMPRESSION | Compression of representation (0=uncompressed, 1=highly compressed) | erro, falha / error, failure, crash, bug |
| 27 | P4 | NOISE | Noise vs. signal ratio (0=clean signal, 1=high noise) | excelente, feliz / excellent, happy — vs. preocupante, triste / concerning, worried |
| 28 | P5 | RESOLUTION | Adaptive fineness (0=coarse, 1=fine) | depende, precisa / depends, needs, requires |
| 29 | P6 | CONFIDENCE | Global fidelity (0=low fidelity, 1=high fidelity) | futuro, planejado / future, planned — vs. histórico, legado / historic, legacy, deprecated |
| 30 | P7 | ACTION | Demand for active response (0=informational only, 1=demands action) | fazer, executar, implementar / do, execute, implement |
| 31 | P8 | LATENCY | Representation update delay (0=immediate, 1=high delay) | confirmar, aprovado / confirm, approved — vs. alerta, aviso / alert, warning |

## Keyword Heuristic Rules (`leet-bridge`)

The `MockProjector` (`leet-bridge/src/projector.rs`, mirrored in Python by `python/leet/bridge.py`) is the deterministic, network-free fallback used in tests. Its rules — sourced from `leet-bridge/src/nl_translator.rs` — are bilingual: keywords in Portuguese and English trigger the same axis, since 1337 is designed to project natural language from either. The excerpt below keeps a handful of representative rules from the real rule table (not exhaustive — see the source file for the complete list across all 32 axes):

```rust
const RULES: &[Rule] = &[
    // ── Block S ──────────────────────────────────────────────────────────
    Rule { keywords: &["essência", "essencia", "identity", "core", "essence"], axis: S1_INTENTION, value: 0.9 },
    Rule { keywords: &["sistema", "system", "conjunto", "emergent", "network"], axis: S8_ALIGNMENT, value: 0.85 },

    // ── Block D ──────────────────────────────────────────────────────────
    Rule { keywords: &["status", "estado", "state", "condition"], axis: D1_CONNECTION_WEIGHT, value: 0.85 },
    Rule { keywords: &["confirmado", "confirmed", "verificado", "verified", "tested"], axis: D8_INERTIA, value: 0.9 },

    // ── Block G ──────────────────────────────────────────────────────────
    Rule { keywords: &["urgente", "urgent", "imediato", "immediate", "asap", "emergência"], axis: G8_GRADIENT, value: 0.95 },
    Rule { keywords: &["reverter", "revert", "desfazer", "undo", "rollback"], axis: G4_TEMPORALITY, value: 0.9 },

    // ── Block P ──────────────────────────────────────────────────────────
    Rule { keywords: &["erro", "error", "falha", "failure", "crash", "bug"], axis: P3_COMPRESSION, value: 0.9 },
    Rule { keywords: &["fazer", "do", "executar", "execute", "implementar", "implement"], axis: P7_ACTION, value: 0.9 },
];
```

## Axis Constants (`leet-bridge/src/nl_translator.rs`)

```rust
pub const S1_INTENTION:        usize = 0;
pub const S2_AMBIGUITY:        usize = 1;
// ... (S3–S8)
pub const D1_CONNECTION_WEIGHT: usize = 8;
// ... (D2–D8)
pub const G1_MASS:              usize = 16;
pub const G3_AFFINITY:          usize = 18;
pub const G4_TEMPORALITY:       usize = 19;
pub const G8_GRADIENT:          usize = 23;
// ... (G2, G5–G7)
pub const P1_QUANTIZATION:      usize = 24;
pub const P3_COMPRESSION:       usize = 26;
pub const P7_ACTION:            usize = 30;
// ... (P2, P4–P6, P8)
```
