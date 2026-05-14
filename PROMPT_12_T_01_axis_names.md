# PROMPT 12-T-01 — CORRIGIR OS 32 NOMES DE EIXO PARA v0.5.1 REAL

Substituir os 32 nomes de eixo no código de **v0.4 traduzida para inglês** (ESSENCE, CORRESPONDENCE, VIBRATION, POLARITY, RHYTHM, CAUSE_EFFECT, GENERATIVITY, etc) pelos **nomes canônicos v0.5.1** que a especificação define (INTENTION, AMBIGUITY, LOCAL_CONTEXT, GLOBAL_CONTEXT, ENTROPY, DENSITY, COHERENCE, ALIGNMENT, etc).

**PRÉ-REQUISITOS**: workspace compila e 247 testes passam (verificado na auditoria pré-Fase 12).

**ESCOPO**: 8 arquivos. Mudança puramente sintática (renaming + comentários + docstrings). Não toca em valores numéricos do COGON_ZERO_SEM, na codec frame, na lógica de operadores, nem na arquitetura. **Não muda comportamento observável** — apenas labels semânticos pra coincidir com a spec.

**Taskwarrior**: `+prompt12_T_01`.

---

## CONTEXTO DA DIVERGÊNCIA

A migração v0.4 → v0.5.1 aterrissou parcialmente:

- **Aterrissou**: estrutura S/D/G/P (4 blocos × 8 eixos), valores numéricos do COGON_ZERO_SEM nas posições corretas, codec 96-byte frame, álgebra de operadores, regras R22/R23.
- **NÃO aterrissou**: os nomes/conceitos. PROMPT_07 manteve os 7 princípios herméticos da v0.4 + 5 valências, só rearranjados. PROMPT_08 (rename PT→EN) traduziu esses nomes literalmente em vez de substituí-los pelos nomes v0.5.1.

Resultado prático: a CLI imprime `S1 ESSENCE` quando devia imprimir `S1 INTENTION`, e o system prompt do MCP descreve eixos com semântica hermética em vez da semântica v0.5.1 que o spec docx em inglês documenta.

**Este prompt corrige isso de uma vez, em commit atômico.** Nada de divergência parcial.

---

## TABELA-MESTRA — RENAME DOS 32 EIXOS

| # | Código | Nome ATUAL (errado, v0.4 EN) | Nome NOVO (v0.5.1) | Descrição NOVA |
|---|---|---|---|---|
| 0  | S1 | ESSENCE              | INTENTION         | Directional purpose carried by the concept |
| 1  | S2 | CORRESPONDENCE       | AMBIGUITY         | Multiplicity of possible interpretations |
| 2  | S3 | VIBRATION            | LOCAL_CONTEXT     | Dependency on immediate surroundings |
| 3  | S4 | POLARITY             | GLOBAL_CONTEXT    | Anchoring in accumulated system history |
| 4  | S5 | RHYTHM               | ENTROPY           | Intrinsic informational uncertainty |
| 5  | S6 | CAUSE_EFFECT         | DENSITY           | Meaning compressed per unit |
| 6  | S7 | GENERATIVITY         | COHERENCE         | Internal logical consistency |
| 7  | S8 | SYSTEM               | ALIGNMENT         | Shared understanding between agents |
| 8  | D1 | STATE                | CONNECTION_WEIGHT | Strength of the bond with other COGONs |
| 9  | D2 | PROCESS              | LEARNING_RATE     | Plasticity — speed of absorbing new data |
| 10 | D3 | RELATION             | DECAY             | Loss of relevance without reinforcement |
| 11 | D4 | SIGNAL               | STABILITY         | Tendency toward equilibrium |
| 12 | D5 | STABILITY            | HYSTERESIS        | Dependency on prior state |
| 13 | D6 | ONTOLOGICAL_VALENCE  | PROPAGATION       | Influence over neighboring COGONs |
| 14 | D7 | CAUSALITY            | CAUSALITY         | Identifiability of concept's origin |
| 15 | D8 | VERIFIABILITY        | INERTIA           | Resistance to state change |
| 16 | G1 | TEMPORALITY          | MASS              | Relevance and accumulated confidence |
| 17 | G2 | TEMPORAL_ANCHOR      | TEMPORAL_ANCHOR   | Degree of temporal anchoring |
| 18 | G3 | COMPLETENESS         | AFFINITY          | Bipolar association with surroundings |
| 19 | G4 | REVERSIBILITY        | TEMPORALITY       | Bipolar temporal orientation (0=past · 0.5=present · 1=future) |
| 20 | G5 | COGNITIVE_LOAD       | LOCAL_FIELD       | Dominance within the semantic cluster |
| 21 | G6 | ORIGIN               | GLOBAL_FIELD      | Centrality in the global network |
| 22 | G7 | EPISTEMIC_VALENCE    | K_INTERACTION     | Adaptive local gain — field sensitivity |
| 23 | G8 | URGENCY              | GRADIENT          | Bipolar change direction/intensity |
| 24 | P1 | IMPACT               | QUANTIZATION      | Rounding level controlled by Pillars 6 & 7 |
| 25 | P2 | VALUE                | GRANULARITY       | Decomposable resolution |
| 26 | P3 | ANOMALY              | COMPRESSION       | Compression of representation |
| 27 | P4 | AFFECT               | NOISE             | Noise vs signal ratio |
| 28 | P5 | DEPENDENCY           | RESOLUTION        | Adaptive fineness |
| 29 | P6 | TEMPORAL_VECTOR      | CONFIDENCE        | Global fidelity (replaces v0.4 unc[32]) |
| 30 | P7 | ACTION               | ACTION            | Demand for active response |
| 31 | P8 | ACTION_VALENCE       | LATENCY           | Representation update delay |

**Importante**: códigos S1-P8 não mudam. Posições não mudam. Valores numéricos do COGON_ZERO_SEM **não mudam** (já estão nas posições corretas conforme v0.5.1).

**Mudança no conceito de "valência"**: v0.4 tinha 5 axes "valence" com baseline neutra 0.5 — `is_valence: bool`. Em v0.5.1 a noção é "bipolar": **3 axes** com baseline 0.5 (G3 AFFINITY, G4 TEMPORALITY, G8 GRADIENT). Os outros dois ex-valência viram axes regulares com baseline diferente (D6 PROPAGATION = baseline 1.0 conforme COGON_ZERO; P4 NOISE = baseline 0.0 conforme COGON_ZERO; P8 LATENCY = baseline 0.0).

A struct field renomeia de `is_valence: bool` → `bipolar: bool`. **Tests que iteravam sobre valence_axes() em busca de 5 elementos vão precisar ajuste pra esperar 3.**

---

## VERIFICAÇÃO DE INVARIANTES (não-mudança)

Antes de qualquer edit, confirme mentalmente:

- COGON_ZERO_SEM permanece **exatamente** o mesmo array. Os comentários acima dele (`// Block S: ESSENCE, CORRESPONDENCE...`) trocam pra usar nomes v0.5.1, mas os 32 floats não mudam.
- Codec wire format (96 bytes) não muda.
- Operadores (`blend`, `dist`, `anomaly_score`, `focus`, `delta`) não mudam — eles operam sobre posições, não sobre nomes.
- Regras R22 (clamp), R23 (G7 normalizado [0,1]) continuam aplicando pelos índices 0..31.
- Validação não muda.

Em resumo: lógica idêntica, comportamento idêntico, **só strings/identificadores trocam**.

---

## ARQUIVO 1 — `leet-core/src/axes.rs`

### Substituir o array CANONICAL_AXES inteiro

Edita o array começando em `pub const CANONICAL_AXES: [AxisInfo; 32]`. Substitui as 32 entradas pelas seguintes (mantém a estrutura/sintaxe; só troca os 3 campos `name`, `is_valence` → `bipolar`, `description`):

```rust
pub const CANONICAL_AXES: [AxisInfo; 32] = [
    // ── Block S — Semantics (0–7) ──────────────────────────────────────────
    AxisInfo { index: 0,  code: "S1", name: "INTENTION",         group: AxisGroup::S, bipolar: false, description: "Directional purpose carried by the concept" },
    AxisInfo { index: 1,  code: "S2", name: "AMBIGUITY",         group: AxisGroup::S, bipolar: false, description: "Multiplicity of possible interpretations" },
    AxisInfo { index: 2,  code: "S3", name: "LOCAL_CONTEXT",     group: AxisGroup::S, bipolar: false, description: "Dependency on immediate surroundings" },
    AxisInfo { index: 3,  code: "S4", name: "GLOBAL_CONTEXT",    group: AxisGroup::S, bipolar: false, description: "Anchoring in accumulated system history" },
    AxisInfo { index: 4,  code: "S5", name: "ENTROPY",           group: AxisGroup::S, bipolar: false, description: "Intrinsic informational uncertainty" },
    AxisInfo { index: 5,  code: "S6", name: "DENSITY",           group: AxisGroup::S, bipolar: false, description: "Meaning compressed per unit" },
    AxisInfo { index: 6,  code: "S7", name: "COHERENCE",         group: AxisGroup::S, bipolar: false, description: "Internal logical consistency" },
    AxisInfo { index: 7,  code: "S8", name: "ALIGNMENT",         group: AxisGroup::S, bipolar: false, description: "Shared understanding between agents" },
    // ── Block D — Dynamics (8–15) ──────────────────────────────────────────
    AxisInfo { index: 8,  code: "D1", name: "CONNECTION_WEIGHT", group: AxisGroup::D, bipolar: false, description: "Strength of the bond with other COGONs" },
    AxisInfo { index: 9,  code: "D2", name: "LEARNING_RATE",     group: AxisGroup::D, bipolar: false, description: "Plasticity — speed of absorbing new data" },
    AxisInfo { index: 10, code: "D3", name: "DECAY",             group: AxisGroup::D, bipolar: false, description: "Loss of relevance without reinforcement" },
    AxisInfo { index: 11, code: "D4", name: "STABILITY",         group: AxisGroup::D, bipolar: false, description: "Tendency toward equilibrium" },
    AxisInfo { index: 12, code: "D5", name: "HYSTERESIS",        group: AxisGroup::D, bipolar: false, description: "Dependency on prior state" },
    AxisInfo { index: 13, code: "D6", name: "PROPAGATION",       group: AxisGroup::D, bipolar: false, description: "Influence over neighboring COGONs" },
    AxisInfo { index: 14, code: "D7", name: "CAUSALITY",         group: AxisGroup::D, bipolar: false, description: "Identifiability of concept's origin (v0.5.1: replaces SATURATION)" },
    AxisInfo { index: 15, code: "D8", name: "INERTIA",           group: AxisGroup::D, bipolar: false, description: "Resistance to state change" },
    // ── Block G — Gravity (16–23) ─────────────────────────────────────────
    AxisInfo { index: 16, code: "G1", name: "MASS",              group: AxisGroup::G, bipolar: false, description: "Relevance and accumulated confidence" },
    AxisInfo { index: 17, code: "G2", name: "TEMPORAL_ANCHOR",   group: AxisGroup::G, bipolar: false, description: "Degree of temporal anchoring (v0.5.1: replaces DISTANCE)" },
    AxisInfo { index: 18, code: "G3", name: "AFFINITY",          group: AxisGroup::G, bipolar: true,  description: "Bipolar association with surroundings (0=repulsion · 0.5=neutral · 1=attraction)" },
    AxisInfo { index: 19, code: "G4", name: "TEMPORALITY",       group: AxisGroup::G, bipolar: true,  description: "Bipolar temporal orientation (0=past · 0.5=present · 1=future)" },
    AxisInfo { index: 20, code: "G5", name: "LOCAL_FIELD",       group: AxisGroup::G, bipolar: false, description: "Dominance within the semantic cluster" },
    AxisInfo { index: 21, code: "G6", name: "GLOBAL_FIELD",      group: AxisGroup::G, bipolar: false, description: "Centrality in the global network" },
    AxisInfo { index: 22, code: "G7", name: "K_INTERACTION",     group: AxisGroup::G, bipolar: false, description: "Adaptive local gain — field sensitivity" },
    AxisInfo { index: 23, code: "G8", name: "GRADIENT",          group: AxisGroup::G, bipolar: true,  description: "Bipolar change direction/intensity (0=decelerating · 0.5=stable · 1=accelerating)" },
    // ── Block P — Precision (24–31) ───────────────────────────────────────
    AxisInfo { index: 24, code: "P1", name: "QUANTIZATION",      group: AxisGroup::P, bipolar: false, description: "Rounding level controlled by Pillars 6 and 7" },
    AxisInfo { index: 25, code: "P2", name: "GRANULARITY",       group: AxisGroup::P, bipolar: false, description: "Decomposable resolution" },
    AxisInfo { index: 26, code: "P3", name: "COMPRESSION",       group: AxisGroup::P, bipolar: false, description: "Compression of representation" },
    AxisInfo { index: 27, code: "P4", name: "NOISE",             group: AxisGroup::P, bipolar: false, description: "Noise vs signal ratio" },
    AxisInfo { index: 28, code: "P5", name: "RESOLUTION",        group: AxisGroup::P, bipolar: false, description: "Adaptive fineness" },
    AxisInfo { index: 29, code: "P6", name: "CONFIDENCE",        group: AxisGroup::P, bipolar: false, description: "Global fidelity (v0.5.1: replaces unc[32])" },
    AxisInfo { index: 30, code: "P7", name: "ACTION",            group: AxisGroup::P, bipolar: false, description: "Demand for active response (v0.5.1: replaces COST)" },
    AxisInfo { index: 31, code: "P8", name: "LATENCY",           group: AxisGroup::P, bipolar: false, description: "Representation update delay" },
];
```

### Renomear o field `is_valence` → `bipolar` na struct `AxisInfo`

Edita a definição da struct (linha ~17):

```rust
pub struct AxisInfo {
    pub index: usize,
    pub code: &'static str,
    pub name: &'static str,
    pub group: AxisGroup,
    pub description: &'static str,
    /// True for the 3 bipolar axes whose neutral baseline is 0.5
    /// (G3 AFFINITY, G4 TEMPORALITY, G8 GRADIENT).
    pub bipolar: bool,
}
```

### Renomear `valence_axes()` → `bipolar_axes()`

Substitui a função:

```rust
/// Return the 3 bipolar axes (neutral baseline 0.5: G3, G4, G8).
pub fn bipolar_axes() -> Vec<&'static AxisInfo> {
    CANONICAL_AXES.iter().filter(|ax| ax.bipolar).collect()
}
```

### Atualizar testes inline em `leet-core/src/axes.rs`

Encontra o test `five_valence_axes` e substitui por:

```rust
#[test]
fn three_bipolar_axes() {
    let v = bipolar_axes();
    assert_eq!(v.len(), 3, "v0.5.1 has 3 bipolar axes");
    let indices: Vec<usize> = v.iter().map(|a| a.index).collect();
    assert!(indices.contains(&18), "G3 AFFINITY should be bipolar");   // was D6 ONTOLOGICAL_VALENCE
    assert!(indices.contains(&19), "G4 TEMPORALITY should be bipolar"); // was G2 TEMPORAL_ANCHOR
    assert!(indices.contains(&23), "G8 GRADIENT should be bipolar");    // was G7 EPISTEMIC_VALENCE
}
```

E adiciona um teste novo de sanity:

```rust
#[test]
fn s1_is_intention_not_essence() {
    let s1 = axis_by_code("S1").unwrap();
    assert_eq!(s1.name, "INTENTION", "v0.5.1: S1 must be INTENTION, not ESSENCE");
}

#[test]
fn p6_is_confidence_not_temporal_vector() {
    let p6 = axis_by_code("P6").unwrap();
    assert_eq!(p6.name, "CONFIDENCE", "v0.5.1: P6 must be CONFIDENCE");
}
```

---

## ARQUIVO 2 — `leet-core/src/types.rs`

### Atualizar comentário acima de `COGON_ZERO_SEM`

Localiza o bloco `pub const COGON_ZERO_SEM: SemVec = [` (linha ~56). Substitui apenas os comentários de cabeçalho dos 4 blocos pelos nomes corretos v0.5.1. **Os 32 valores numéricos não mudam.** Resultado:

```rust
pub const COGON_ZERO_SEM: SemVec = [
    // Block S: INTENTION, AMBIGUITY, LOCAL_CONTEXT, GLOBAL_CONTEXT, ENTROPY, DENSITY, COHERENCE, ALIGNMENT
    1.0, 0.0, 0.0, 0.0,   0.0, 1.0, 1.0, 1.0,
    // Block D: CONNECTION_WEIGHT, LEARNING_RATE, DECAY, STABILITY, HYSTERESIS, PROPAGATION, CAUSALITY, INERTIA
    0.5, 0.0, 0.0, 1.0,   0.0, 1.0, 1.0, 0.0,
    // Block G: MASS, TEMPORAL_ANCHOR, AFFINITY, TEMPORALITY, LOCAL_FIELD, GLOBAL_FIELD, K_INTERACTION, GRADIENT
    1.0, 0.5, 1.0, 0.5,   0.5, 1.0, 0.1, 0.0,
    // Block P: QUANTIZATION, GRANULARITY, COMPRESSION, NOISE, RESOLUTION, CONFIDENCE, ACTION, LATENCY
    0.8, 0.0, 1.0, 0.0,   0.5, 1.0, 0.0, 0.0,
];
```

Também elimina o warning `unused_imports` em `leet-core/src/types.rs:175`. A linha relevante é dentro do `mod tests` — apaga o `use std::collections::HashMap;` redundante (o import já existe no topo do módulo, linha ~2).

---

## ARQUIVO 3 — `leet-bridge/src/nl_translator.rs`

Substitui as 32 constantes pub no topo (linhas ~21-58):

```rust
// ── Block S — Semantics (0–7) ─────────────────────────────────────────────
pub const S1_INTENTION:        usize = 0;
pub const S2_AMBIGUITY:        usize = 1;
pub const S3_LOCAL_CONTEXT:    usize = 2;
pub const S4_GLOBAL_CONTEXT:   usize = 3;
pub const S5_ENTROPY:          usize = 4;
pub const S6_DENSITY:          usize = 5;
pub const S7_COHERENCE:        usize = 6;
pub const S8_ALIGNMENT:        usize = 7;

// ── Block D — Dynamics (8–15) ─────────────────────────────────────────────
pub const D1_CONNECTION_WEIGHT: usize = 8;
pub const D2_LEARNING_RATE:     usize = 9;
pub const D3_DECAY:             usize = 10;
pub const D4_STABILITY:         usize = 11;
pub const D5_HYSTERESIS:        usize = 12;
pub const D6_PROPAGATION:       usize = 13;
pub const D7_CAUSALITY:         usize = 14;
pub const D8_INERTIA:           usize = 15;

// ── Block G — Gravity (16–23) ─────────────────────────────────────────────
pub const G1_MASS:              usize = 16;
pub const G2_TEMPORAL_ANCHOR:   usize = 17;
pub const G3_AFFINITY:          usize = 18; // bipolar: 0=repulsion · 0.5=neutral · 1=attraction
pub const G4_TEMPORALITY:       usize = 19; // bipolar: 0=past · 0.5=present · 1=future
pub const G5_LOCAL_FIELD:       usize = 20;
pub const G6_GLOBAL_FIELD:      usize = 21;
pub const G7_K_INTERACTION:     usize = 22;
pub const G8_GRADIENT:          usize = 23; // bipolar: 0=decelerating · 0.5=stable · 1=accelerating

// ── Block P — Precision (24–31) ───────────────────────────────────────────
pub const P1_QUANTIZATION:      usize = 24;
pub const P2_GRANULARITY:       usize = 25;
pub const P3_COMPRESSION:       usize = 26;
pub const P4_NOISE:             usize = 27;
pub const P5_RESOLUTION:        usize = 28;
pub const P6_CONFIDENCE:        usize = 29; // replaces v0.4 unc[32]
pub const P7_ACTION:            usize = 30;
pub const P8_LATENCY:           usize = 31;
```

**Em seguida**, qualquer call-site dentro do mesmo arquivo que usa nomes antigos (ex: `S1_ESSENCE`, `G2_TEMPORAL_ANCHOR` que aliás continua igual, `D7_CAUSALITY` continua igual, `G4_REVERSIBILITY` → `G4_TEMPORALITY`, etc) precisa ser atualizado em cascata. `cargo check -p leet-bridge` vai apontar todas. Aplica conforme a tabela acima.

---

## ARQUIVO 4 — `leet-bridge/src/heuristics.rs`

Atualiza o módulo `axes` interno (linhas ~7-15):

```rust
mod axes {
    pub const D1_CONNECTION_WEIGHT: usize = 8;   // was D1_STATE
    pub const D2_LEARNING_RATE:     usize = 9;   // was D2_PROCESS
    pub const D6_PROPAGATION:       usize = 13;  // was D6_ONTOLOGICAL_VALENCE
    pub const G4_TEMPORALITY:       usize = 19;  // was G4_REVERSIBILITY
    pub const G8_GRADIENT:          usize = 23;  // was G8_URGENCY
    pub const P3_COMPRESSION:       usize = 26;  // was P3_ANOMALY
    pub const P7_ACTION:            usize = 30;
}
```

Em `RULES` (linhas ~25 em diante), substitui referências:
- `axes::D1_STATE` → `axes::D1_CONNECTION_WEIGHT`
- `axes::D2_PROCESS` → `axes::D2_LEARNING_RATE`
- `axes::D6_ONTOLOGICAL_VALENCE` → `axes::D6_PROPAGATION`
- `axes::G4_REVERSIBILITY` → `axes::G4_TEMPORALITY`
- `axes::G8_URGENCY` → `axes::G8_GRADIENT`
- `axes::P3_ANOMALY` → `axes::P3_COMPRESSION`
- `axes::P7_ACTION` → permanece `axes::P7_ACTION`

**Atenção semântica**: as keywords das regras (`["reverter", "rollback"]` apontava pra G4_REVERSIBILITY) continuam fazendo sentido pragmaticamente, mas agora populam G4_TEMPORALITY. **Isso é uma regressão de sinal**: se o usuário escreve "rollback", a heurística agora vai marcar TEMPORALITY (passado/presente/futuro) em vez de REVERSIBILITY. As regras heurísticas ficam num estado meio incoerente.

**Decisão consciente neste prompt**: aceitar a regressão. O calibrador W (PROMPT_06, futuro) vai substituir essas heurísticas por embedding aprendido. Mantemos as keywords e regras como **placeholders ativos** mas com o entendimento de que sua precisão semântica caiu até o W estar plugado. Adicione um comentário no topo do arquivo:

```rust
//! Keyword heuristics — fallback path for projection.
//!
//! NOTE (v0.5.1): the rules below were originally calibrated for v0.4 axis
//! semantics (e.g. "rollback" → G4_REVERSIBILITY made sense). After the
//! v0.5.1 axis substitution, some rules now point at axes whose semantics
//! shifted (G4 became TEMPORALITY). The wire format and indices are correct;
//! only the semantic crispness of these heuristics is reduced. Calibrated W
//! (PROMPT_06) is the long-term replacement. Do NOT delete these rules
//! before W is in place — they remain the active fallback.
```

---

## ARQUIVO 5 — `leet-bridge/src/projector.rs`

Atualiza os comentários nas linhas ~50-65 conforme o cascade:

- `// D2_PROCESS / P7_ACTION — process keywords` → `// D2_LEARNING_RATE / P7_ACTION — process keywords (legacy v0.4 mapping)`
- `// G4_REVERSIBILITY / P7_ACTION — rollback keywords` → `// G4_TEMPORALITY / P7_ACTION — rollback keywords (legacy v0.4 mapping)`
- O comentário inline `// G4_REVERSIBILITY` na linha 64 → `// G4_TEMPORALITY (legacy keyword path)`

Mantém os índices `sem[19] = 0.9;` e `sem[30] = 0.85;` etc. Não muda comportamento.

---

## ARQUIVO 6 — `leet-bridge/tests/translator_tests.rs`

Substitui referências às constantes em ~6 linhas:

```rust
// linha 84: comentário
// v0.5.1: S1_INTENTION = 1.0, not all-ones

// linha 85
assert_eq!(z.sem[0], 1.0, "S1_INTENTION must be 1.0");

// linha 137: comentário
/// Rollback keyword → G4_TEMPORALITY activated, P7_ACTION activated.

// linha 141
assert!(cogon.sem[leet_bridge::nl_translator::G4_TEMPORALITY] > 0.7);

// linha 145: comentário
/// Past tense → G2_TEMPORAL_ANCHOR near 0 (past).

// linha 150 (não muda — G2_TEMPORAL_ANCHOR mantém o nome)
// linha 152 (idem)
// linha 156 (idem — G2_TEMPORAL_ANCHOR)
// linha 161, 163 (idem)
```

`cargo test -p leet-bridge` deve continuar verde após esses asserts.

**Observação semântica**: o teste "Rollback keyword → G4_TEMPORALITY > 0.7" agora é semanticamente esquisito (rollback é mais sobre reversibilidade que sobre temporalidade). **Aceita a esquisitice por ora** — o teste verifica que a regra **dispara** o índice 19, o que é mecanicamente correto. A semântica volta ao trilho quando W substituir as heurísticas.

---

## ARQUIVO 7 — `leet-bridge/src/claude_1337_prompt.rs`

Reescreve a string `CLAUDE_1337_SYSTEM` substituindo as 17 linhas que mencionam nomes v0.4. Foco nas seções:

### 7.1 — Sub-seção sobre uncertainty (linhas ~30-32)

```rust
// ANTES:
- S5 RHYTHM     (sem[4])  — cyclic/pattern regularity (low = chaotic/uncertain)
- P4 AFFECT     (sem[27]) — affect valence (0=negative, 0.5=neutral, 1=positive)
- P6 TEMPORAL_VECTOR (sem[29]) — temporal direction (0=past-oriented, 1=future-oriented)

// DEPOIS:
- S5 ENTROPY    (sem[4])  — informational entropy (high = uncertain)
- P4 NOISE      (sem[27]) — signal-to-noise ratio (high = noisy/uncertain)
- P6 CONFIDENCE (sem[29]) — global representation fidelity (low = uncertain)
```

### 7.2 — Lista dos 32 axes (linhas ~43-86)

Substitui **todas as 32 linhas** pelos nomes v0.5.1:

```
**Block S — Semantics — indices 0..8**
Intrinsic meaning and representational quality.

- [0]  S1 INTENTION         — directional purpose (0=no purpose · 1=maximum purpose)
- [1]  S2 AMBIGUITY         — interpretation multiplicity (0=single meaning · 1=fully ambiguous)
- [2]  S3 LOCAL_CONTEXT     — local context dependence (0=autonomous · 1=fully dependent)
- [3]  S4 GLOBAL_CONTEXT    — global history anchoring (0=no history · 1=deeply anchored)
- [4]  S5 ENTROPY           — informational entropy (0=deterministic · 1=maximum uncertainty)
- [5]  S6 DENSITY           — meaning density (0=empty · 1=maximally compressed)
- [6]  S7 COHERENCE         — internal consistency (0=contradictory · 1=fully consistent)
- [7]  S8 ALIGNMENT         — inter-agent consensus (0=total divergence · 1=full consensus)

**Block D — Dynamics — indices 8..16**
How the concept evolves, learns, and resists change.

- [8]  D1 CONNECTION_WEIGHT — bond strength with other COGONs (0=weak · 1=strong)
- [9]  D2 LEARNING_RATE     — plasticity (0=frozen · 1=maximum plasticity)
- [10] D3 DECAY             — relevance loss without reinforcement (0=permanent · 1=fast decay)
- [11] D4 STABILITY         — equilibrium tendency (0=chaotic · 1=fully stable)
- [12] D5 HYSTERESIS        — historical-dependence (0=no memory · 1=high path-dependence)
- [13] D6 PROPAGATION       — influence over neighbors (0=isolated · 1=maximum influence)
- [14] D7 CAUSALITY         — origin identifiability (0=opaque · 1=clearly identifiable) [v0.5.1 replaces SATURATION]
- [15] D8 INERTIA           — resistance to state change (0=instant · 1=maximum resistance)

**Block G — Gravity — indices 16..24**
How COGONs attract, repel, organize themselves.

- [16] G1 MASS              — accumulated relevance (0=irrelevant · 1=high relevance)
- [17] G2 TEMPORAL_ANCHOR   — degree of temporal anchoring (0=timeless · 1=precise) [v0.5.1 replaces DISTANCE]
- [18] G3 AFFINITY ★        — bipolar association (0=repulsion · 0.5=neutral · 1=attraction)
- [19] G4 TEMPORALITY ★     — bipolar temporal orientation (0=past · 0.5=present · 1=future)
- [20] G5 LOCAL_FIELD       — cluster dominance (0=peripheral · 1=dominant)
- [21] G6 GLOBAL_FIELD      — network centrality (0=peripheral · 1=global hub)
- [22] G7 K_INTERACTION     — adaptive local gain (0=K_min · 1=K_max, normalized)
- [23] G8 GRADIENT ★        — bipolar change rate (0=decelerating · 0.5=stable · 1=accelerating)

**Block P — Precision — indices 24..32**
Representation quality and fidelity.

- [24] P1 QUANTIZATION      — rounding level (0=max precision · 1=max rounding)
- [25] P2 GRANULARITY       — decomposable resolution (0=atomic · 1=highly decomposable)
- [26] P3 COMPRESSION       — representation compression (0=expanded · 1=max compression)
- [27] P4 NOISE             — signal-to-noise ratio (0=pure signal · 1=noise-dominated)
- [28] P5 RESOLUTION        — adaptive fineness (0=coarse · 1=high resolution)
- [29] P6 CONFIDENCE        — global fidelity (0=no confidence · 1=full certainty) [v0.5.1 replaces unc[32]]
- [30] P7 ACTION            — active response demand (0=informative · 1=immediate execution) [v0.5.1 replaces COST]
- [31] P8 LATENCY           — update delay (0=real-time · 1=maximally delayed)
```

★ marca os 3 axes bipolares (G3, G4, G8).

### 7.3 — Boot defaults section

Se houver uma seção mencionando boot defaults Pillar 4, atualiza:

```
- S7 COHERENCE → 1.0     (assume consistent until proven otherwise)   [was S7 GENERATIVITY]
- G7 K_INTERACTION → 0.1 (low gain — avoid oscillation at boot)
- P1 QUANTIZATION → 0.8  (conservative rounding at boot)               [was P1 IMPACT]
- P7 ACTION → 0.0        (default: no action required)
```

(A função do prompt geralmente é descritiva. Localiza onde a string mencionar boot/Pillar 4 e ajusta os nomes.)

---

## ARQUIVO 8 — `leet-cli/src/cmd/zero.rs`

Substitui as 3 linhas que imprimem nomes:

```rust
println!("  sem[0] S1:       {} (INTENTION — directional purpose)", zero.sem[0]);
println!("  sem[13] D6:      {} (PROPAGATION — maximum influence)", zero.sem[13]);
println!("  sem[29] P6:      {} (CONFIDENCE — full certainty)", zero.sem[29]);
```

Renomeia os testes inline:

```rust
#[test]
fn test_cogon_zero_s1_intention() {
    use leet_core::types::Cogon;
    let z = Cogon::zero();
    assert_eq!(z.sem[0], 1.0, "S1_INTENTION should be 1.0 in COGON_ZERO");
}

#[test]
fn test_cogon_zero_p6_confidence() {
    use leet_core::types::Cogon;
    let z = Cogon::zero();
    assert_eq!(z.sem[29], 1.0, "P6_CONFIDENCE should be 1.0 in COGON_ZERO");
}
```

---

## ARQUIVO 9 — `leet-cli/tests/cli_test.rs`

Localiza os asserts:

```rust
// linha ~62-64 — função test_axes_first_is_s1_essence
#[test]
fn test_axes_first_is_s1_intention() {
    use leet_core::axes::CANONICAL_AXES;
    assert_eq!(CANONICAL_AXES[0].name, "INTENTION");
}

// linha ~114 — assert dentro de outro teste
assert_eq!(z.sem[0], 1.0, "COGON_ZERO: S1_INTENTION should be 1.0");
```

---

## VERIFICATION

```bash
# Compilação
cargo build --workspace
# Esperado: 0 errors, 0 warnings (warning de unused_imports em types.rs também some)

# Testes
cargo test --workspace
# Esperado: ainda 247 (ou mais, se novos sanity tests foram adicionados); 0 falhas.

# Sanity humano
./target/debug/leet axes | head -10
# Esperado: "[0]  S1     INTENTION  ..." e não "ESSENCE"

./target/debug/leet zero | head -8
# Esperado: "sem[0] S1: 1 (INTENTION — directional purpose)"

# Confirmação que nomes v0.4 sumiram do código (não dos PROMPTs antigos, esses são histórico)
grep -rn "ESSENCE\|CORRESPONDENCE\|VIBRATION\|POLARITY\|RHYTHM\|CAUSE_EFFECT\|GENERATIVITY\|VERIFIABILITY\|COMPLETENESS\|REVERSIBILITY\|COGNITIVE_LOAD\|ONTOLOGICAL_VALENCE\|EPISTEMIC_VALENCE\|ACTION_VALENCE\|TEMPORAL_VECTOR" --include="*.rs" leet-* 2>/dev/null | grep -v "^Binary" | head -10
# Esperado: ZERO matches em código .rs ativo. (PROMPT_*.md continuam com texto histórico — aceitável.)

# E o teste end-to-end MCP
rm -rf /tmp/leet-12t01 && mkdir /tmp/leet-12t01
cat <<'EOF' | LEET_PROJECT_ROOT=/tmp/leet-12t01 ./target/debug/leet-mcp 2>/dev/null | tail -3
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"test"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leet_recall","arguments":{}}}
EOF
# Esperado: response com record persistido. .leet/store.bin de 16+360=376 bytes.
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt12_T_01 "v0.5.1 axis names: substitute v0.4-translated-EN with real v0.5.1 names across 9 files"
task project:1337 +prompt12_T_01 start
# work
task project:1337 +prompt12_T_01 done

git add leet-core/src/axes.rs leet-core/src/types.rs \
        leet-bridge/src/nl_translator.rs leet-bridge/src/heuristics.rs \
        leet-bridge/src/projector.rs leet-bridge/src/claude_1337_prompt.rs \
        leet-bridge/tests/translator_tests.rs \
        leet-cli/src/cmd/zero.rs leet-cli/tests/cli_test.rs

git commit -m "refactor(axes): apply real v0.5.1 axis names (replace v0.4-EN holdover)

Discovered post-Phase-11 audit: PROMPT_07 landed the S/D/G/P 4-block
structure but kept the v0.4 hermetic-principles concepts (ESSENCE,
CORRESPONDENCE, VIBRATION, POLARITY, RHYTHM, CAUSE_EFFECT, GENERATIVITY,
five valence axes). PROMPT_08 then translated those v0.4 names to
English literally instead of substituting with the v0.5.1 names defined
in the spec.

This commit applies the actual v0.5.1 names across the workspace.

Mapping (excerpt, full table in commit message):
  ESSENCE → INTENTION              [S1]
  CORRESPONDENCE → AMBIGUITY       [S2]
  VIBRATION → LOCAL_CONTEXT        [S3]
  POLARITY → GLOBAL_CONTEXT        [S4]
  RHYTHM → ENTROPY                 [S5]
  CAUSE_EFFECT → DENSITY           [S6]
  GENERATIVITY → COHERENCE         [S7]
  STATE → CONNECTION_WEIGHT        [D1]
  ...
  ACTION_VALENCE → LATENCY         [P8]

Three v0.5.1 substitutions confirmed in place:
  D7 SATURATION → CAUSALITY (already correct from v0.4)
  G2 DISTANCE → TEMPORAL_ANCHOR (already correct from v0.4)
  P7 COST → ACTION (already correct from v0.4)

Struct field renamed: AxisInfo.is_valence → AxisInfo.bipolar.
Helper renamed: valence_axes() → bipolar_axes().
v0.4 had 5 valence axes; v0.5.1 has 3 bipolar axes (G3, G4, G8).

Invariants preserved (NOT changed by this commit):
  - COGON_ZERO_SEM 32-float values (positions/values are correct)
  - 96-byte codec wire format
  - All operators (BLEND, DIST, FOCUS, DELTA, ANOMALY_SCORE)
  - All structural rules R1–R23
  - Validate logic
  - PersonalStore binary format
  - MCP server protocol shape

Behavior is identical pre/post commit; only labels change.

Files touched (9):
  leet-core/src/axes.rs (32 entries + helper rename + tests)
  leet-core/src/types.rs (block comments only; values unchanged;
    also removes unused HashMap import warning)
  leet-bridge/src/nl_translator.rs (32 pub const renames)
  leet-bridge/src/heuristics.rs (axes module + RULES references;
    semantic crispness regression noted in module docstring;
    keywords retained as active fallback until W is calibrated)
  leet-bridge/src/projector.rs (comment updates only)
  leet-bridge/src/claude_1337_prompt.rs (32-axis system prompt rewrite)
  leet-bridge/tests/translator_tests.rs (cascade rename in asserts)
  leet-cli/src/cmd/zero.rs (display strings + test names)
  leet-cli/tests/cli_test.rs (assert string)

Part of Phase 12-T (técnico): canonical-state cleanup.
Resolves the divergence discovered during pre-Phase-12 audit."

git push origin main
```

---

**END OF PROMPT_12-T-01**
