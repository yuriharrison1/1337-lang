# PROMPT 08 — RENAME PT → EN (bloco 2 da Fase A)

Rename mecânico dos 32 nomes de eixo e da API pública relacionada, de português para inglês. Zero mudança semântica. Zero mudança de lógica. Apenas substituição de identificadores e strings visíveis em API pública.

**PRÉ-REQUISITOS**: toda a sequência 07a–07g executada e commitada. `cargo test --workspace` verde. `leet-core` inteiro em v0.5.1 PT.

**IMPORTANTE**: é um prompt único (não fragmentado como PROMPT_07) porque rename é low-risk e a consistência global precisa aterrissar em um commit atômico — não faz sentido o workspace ficar meio PT meio EN entre sub-passos.

**Taskwarrior**: `+prompt08`.

---

## TABELA DE RENAME — OS 32 EIXOS

Literal, sem reinterpretação. Códigos curtos (S1..P8) **não mudam** — são agnósticos de idioma.

| # | Código | PT (atual)         | EN (novo)          |
|---|--------|--------------------|--------------------|
| 0 | S1     | INTENCAO           | INTENTION          |
| 1 | S2     | AMBIGUIDADE        | AMBIGUITY          |
| 2 | S3     | CONTEXTO_LOCAL     | LOCAL_CONTEXT      |
| 3 | S4     | CONTEXTO_GLOBAL    | GLOBAL_CONTEXT     |
| 4 | S5     | ENTROPIA           | ENTROPY            |
| 5 | S6     | DENSIDADE          | DENSITY            |
| 6 | S7     | COERENCIA          | COHERENCE          |
| 7 | S8     | ALINHAMENTO        | ALIGNMENT          |
| 8 | D1     | PESO_CONEXAO       | CONNECTION_WEIGHT  |
| 9 | D2     | TAXA_APRENDIZADO   | LEARNING_RATE      |
| 10| D3     | DECAIMENTO         | DECAY              |
| 11| D4     | ESTABILIDADE       | STABILITY          |
| 12| D5     | HISTERESE          | HYSTERESIS         |
| 13| D6     | PROPAGACAO         | PROPAGATION        |
| 14| D7     | CAUSALIDADE        | CAUSALITY          |
| 15| D8     | INERCIA            | INERTIA            |
| 16| G1     | MASSA              | MASS               |
| 17| G2     | ANCORA_TEMPORAL    | TEMPORAL_ANCHOR    |
| 18| G3     | AFINIDADE          | AFFINITY           |
| 19| G4     | TEMPORALIDADE      | TEMPORALITY        |
| 20| G5     | CAMPO_LOCAL        | LOCAL_FIELD        |
| 21| G6     | CAMPO_GLOBAL       | GLOBAL_FIELD       |
| 22| G7     | K_INTERACAO        | K_INTERACTION      |
| 23| G8     | GRADIENTE          | GRADIENT           |
| 24| P1     | QUANTIZACAO        | QUANTIZATION       |
| 25| P2     | GRANULARIDADE      | GRANULARITY        |
| 26| P3     | COMPRESSAO         | COMPRESSION        |
| 27| P4     | RUIDO              | NOISE              |
| 28| P5     | RESOLUCAO          | RESOLUTION         |
| 29| P6     | CONFIANCA          | CONFIDENCE         |
| 30| P7     | ACAO               | ACTION             |
| 31| P8     | LATENCIA           | LATENCY            |

---

## ESCOPO — O QUE MUDA E O QUE FICA

### MUDA (rename mecânico)

1. `leet-core/src/axes.rs` — campo `name: &'static str` de cada `AxisInfo` (32 strings).
2. `leet-core/src/axes.rs` — `AxisBlock::title()` vira inglês:
   - `"Bloco 1 — SEMÂNTICA"` → `"Block 1 — SEMANTICS"`
   - `"Bloco 2 — DINÂMICA"` → `"Block 2 — DYNAMICS"`
   - `"Bloco 3 — GRAVIDADE"` → `"Block 3 — GRAVITY"`
   - `"Bloco 4 — PRECISÃO"` → `"Block 4 — PRECISION"`
3. `leet-core/src/axes.rs` — `description` de cada eixo: **SIM, traduzir**. Esses strings aparecem em `leet axes --json` e são API pública de facto.
4. `leet-core/src/axes.rs` — `normalization` de cada eixo: **SIM, traduzir**. Mesma razão.
5. `leet-core/src/axes.rs` — testes (`tests` module) que fazem `assert_eq!(axis.name, "INTENCAO")` etc.
6. `leet-bridge/src/claude_1337_prompt.rs` — lista dos 32 eixos. **Nomes no prompt passam de PT para EN** já que agora os nomes canônicos SÃO em EN. Remover as glosas "(english gloss)" redundantes.
7. `leet-bridge/src/nl_translator.rs` — constantes `pub const D7_CAUSALIDADE: usize = 14;` viram `pub const D7_CAUSALITY: usize = 14;`. Todas as usages subsequentes renomeiam em cascata.
8. `leet-cli/tests/cli_test.rs` — asserts que checam `assert_eq!(CANONICAL_AXES[0].name, "INTENCAO")` → `"INTENTION"`.
9. `python/leet/axes.py` (se existir pós-07) — constantes `S1_INTENCAO = 0` → `S1_INTENTION = 0`. Verificar.
10. `leet-py/` (SDK público Python) — classes e constantes exportadas que mencionam nomes PT. Expõe `Axis.MASS` não `Axis.MASSA`.

### NÃO MUDA (fora do escopo mínimo)

- Comentários internos em `.rs` (ex: `// sem[16] é G1 MASSA`). Ficam em PT. Só adaptar onde PT não faz mais sentido em contexto de código EN — mas não caçar.
- `leet-core/src/error.rs` — mensagens de erro `#[error(...)]`. Ficam em inglês já (já estão), só garantir que não mencionem nomes PT de eixo.
- `leet-cli/src/cmd/*.rs` help strings (`clap` `#[arg(help = "...")]`). Ficam como estão.
- `leet-bridge/src/heuristics.rs` — keyword lists (`&["ontem", "yesterday", ...]`) são conteúdo, não API. Ficam em PT.
- `net1337.py`, `plato_discussion.py`, scripts em `comparison_reports/`, `prompts/PROMPT_*.md`. Fora do escopo.
- `python/leet/` (SDK interno usado por experimentos). Fora do escopo mínimo; **exceção**: se `python/leet/axes.py` expõe constantes que são reexportadas por `leet-py`, então SIM, porque viraram API pública transitivamente.
- `.docx` specs. Bloco 3 da Fase A regera spec em EN.

### SIM, tocar em `claude_1337_prompt.rs` de novo

Em 07g esse arquivo foi reescrito em inglês mas mantendo os **nomes dos eixos em português** com glosa EN ao lado. Agora em PROMPT_08 os nomes passam a ser em inglês, então as glosas ficam redundantes e saem. Fica mais limpo.

---

## ARQUIVO 1 — `leet-core/src/axes.rs`

### 1a. Campo `name` e `description` em `CANONICAL_AXES`

Aplicar substituição literal. Exemplos-âncora da tradução:

```rust
// ANTES
AxisInfo {
    index: 0, code: "S1", name: "INTENCAO", block: AxisBlock::Semantic,
    description: "Grau em que o conceito carrega propósito direcional",
    normalization: "0=sem propósito · 1=propósito máximo",
    boot_default: 0.5, bipolar: false,
},

// DEPOIS
AxisInfo {
    index: 0, code: "S1", name: "INTENTION", block: AxisBlock::Semantic,
    description: "Degree to which the concept carries directional purpose",
    normalization: "0=no purpose · 1=maximum purpose",
    boot_default: 0.5, bipolar: false,
},
```

As traduções de `description` e `normalization` completas estão na tabela abaixo. Padrão: tradução neutra, técnica, sem ornamento.

| # | description (PT → EN) | normalization (PT → EN) |
|---|---|---|
| 0 | "Degree to which the concept carries directional purpose" | "0=no purpose · 1=maximum purpose" |
| 1 | "Multiplicity of possible interpretations" | "0=single meaning · 1=fully ambiguous" |
| 2 | "Dependency on immediate surroundings to be understood" | "0=autonomous · 1=fully dependent" |
| 3 | "Anchoring in the system's accumulated history" | "0=no history · 1=deeply anchored" |
| 4 | "Informational uncertainty intrinsic to the concept" | "0=deterministic · 1=maximum uncertainty" |
| 5 | "Amount of meaning compressed per unit" | "0=empty · 1=maximum compression" |
| 6 | "Internal logical consistency of the concept" | "0=contradictory · 1=fully consistent" |
| 7 | "Shared understanding between agents about this concept" | "0=total divergence · 1=full consensus" |
| 8 | "Strength of the bond with other COGONs in the network" | "0=weak link · 1=strong link" |
| 9 | "Plasticity — speed of absorbing new data" | "0=frozen · 1=maximum plasticity" |
| 10 | "Speed at which the concept loses relevance without reinforcement" | "0=permanent · 1=maximum decay" |
| 11 | "Tendency toward equilibrium vs chaotic instability" | "0=chaotic · 1=fully stable" |
| 12 | "Dependency on prior state — trajectory memory" | "0=no memory · 1=high historical dependence" |
| 13 | "Degree of influence over neighboring COGONs" | "0=isolated · 1=maximum influence" |
| 14 | "Degree to which the concept's origin is identifiable (v0.5.1: replaces SATURACAO)" | "0=opaque origin · 1=clearly identifiable cause" |
| 15 | "Resistance to state change" | "0=changes instantly · 1=maximum resistance" |
| 16 | "Relevance and accumulated confidence of the COGON in the system" | "0=irrelevant · 1=high relevance" |
| 17 | "Degree to which the concept has a defined temporal anchor (v0.5.1: replaces DISTANCIA)" | "0=timeless · 1=precise moment defined" |
| 18 | "Negative vs positive association with the surroundings (bipolar)" | "0=repulsion · 0.5=neutral · 1=attraction" |
| 19 | "Temporal orientation of interaction between COGONs (bipolar)" | "0=past · 0.5=present · 1=future" |
| 20 | "Dominance of the COGON within its semantic cluster" | "0=peripheral · 1=dominant" |
| 21 | "Centrality of the COGON in the global network" | "0=peripheral · 1=global hub" |
| 22 | "Adaptive local gain — field sensitivity in this region" | "0=K_min · 1=K_max (normalized)" |
| 23 | "Direction and intensity of change of the gravitational field (bipolar)" | "0=decelerating · 0.5=stable · 1=accelerating" |
| 24 | "Level of rounding applied (controlled by Pillars 6 and 7)" | "0=maximum precision · 1=maximum rounding" |
| 25 | "Decomposable resolution of the concept" | "0=atomic · 1=highly decomposable" |
| 26 | "Degree of compression of the representation" | "0=expanded · 1=maximum compression" |
| 27 | "Noise vs signal ratio in the representation" | "0=pure signal · 1=noise-dominated" |
| 28 | "Fineness of the adaptive representation" | "0=coarse · 1=high resolution" |
| 29 | "Confidence in the fidelity of the representation (replaces v0.4 unc[32])" | "0=no confidence · 1=full certainty" |
| 30 | "Degree to which the concept demands active response from the receiver (v0.5.1: replaces CUSTO)" | "0=purely informative · 1=demands immediate execution" |
| 31 | "Representation update delay" | "0=real-time · 1=maximally delayed" |

### 1b. Doc-comment do arquivo

Atualizar o cabeçalho do arquivo:

```rust
// ANTES
//! Canonical 32-axis space v0.5.1.
//! ...
//! Axis names preserved in Portuguese; English rename is PROMPT_08.

// DEPOIS
//! Canonical 32-axis space v0.5.1 (English).
//! ...
//! Axis names are canonical English identifiers. Historical substitutions
//! vs v0.5: D7 SATURATION → CAUSALITY, G2 DISTANCE → TEMPORAL_ANCHOR,
//! P7 COST → ACTION.
```

### 1c. `AxisBlock::title()`

```rust
pub fn title(&self) -> &'static str {
    match self {
        AxisBlock::Semantic  => "Block 1 — SEMANTICS",
        AxisBlock::Dynamic   => "Block 2 — DYNAMICS",
        AxisBlock::Gravity   => "Block 3 — GRAVITY",
        AxisBlock::Precision => "Block 4 — PRECISION",
    }
}
```

### 1d. Módulo `tests` — atualizar asserts de nome

```rust
#[test]
fn axis_by_code_s1_is_intention() {  // renomear também a função se existir como intencao
    let ax = axis_by_code("S1").unwrap();
    assert_eq!(ax.index, 0);
    assert_eq!(ax.name, "INTENTION");  // was "INTENCAO"
    assert_eq!(ax.block, AxisBlock::Semantic);
}

#[test]
fn axis_by_code_p8_is_latency() {
    let ax = axis_by_code("P8").unwrap();
    assert_eq!(ax.index, 31);
    assert_eq!(ax.name, "LATENCY");  // was "LATENCIA"
}

#[test]
fn v051_substitutions_in_place() {
    assert_eq!(axis_by_index(14).unwrap().name, "CAUSALITY");       // was CAUSALIDADE
    assert_eq!(axis_by_index(17).unwrap().name, "TEMPORAL_ANCHOR"); // was ANCORA_TEMPORAL
    assert_eq!(axis_by_index(30).unwrap().name, "ACTION");          // was ACAO
}
```

Se algum nome de função de teste continha o nome PT (ex: `intencao` em `axis_by_code_s1_is_intencao`), renomear a função também — mantém consistência.

### 1e. Boot exceptions test

```rust
#[test]
fn boot_exceptions_match_pilar_4() {
    let v = boot_vector();
    assert_eq!(v[6],  1.0, "S7_COHERENCE boot = 1.0");       // was COERENCIA
    assert_eq!(v[22], 0.1, "G7_K_INTERACTION boot = 0.1");   // was K_INTERACAO
    assert_eq!(v[24], 0.8, "P1_QUANTIZATION boot = 0.8");    // was QUANTIZACAO
    assert_eq!(v[30], 0.0, "P7_ACTION boot = 0.0");          // was ACAO
    // resto igual
}
```

---

## ARQUIVO 2 — `leet-bridge/src/nl_translator.rs`

Constantes de índice com nomes de eixo. Renomear **todas** sistematicamente:

```rust
// ANTES
pub const D7_CAUSALIDADE: usize = 14;
pub const G2_ANCORA_TEMPORAL: usize = 17;
// ... e assim por diante

// DEPOIS
pub const D7_CAUSALITY: usize = 14;
pub const G2_TEMPORAL_ANCHOR: usize = 17;
```

Verificar **todas** as constantes nomeadas `<CODIGO>_<NOME_PT>` neste arquivo e aplicar o rename uniforme conforme a tabela-mestra.

Os locais de uso dessas constantes dentro do mesmo arquivo também renomeiam em cascata (`cargo check` vai apontar todos).

Os comentários doc do arquivo (linhas `//! Block G [16-23]: TEMPORALIDADE, ANCORA_TEMPORAL, ...`) passam a `//! Block G [16-23]: MASS, TEMPORAL_ANCHOR, AFFINITY, TEMPORALITY, LOCAL_FIELD, GLOBAL_FIELD, K_INTERACTION, GRADIENT`.

**Keyword lists em regras** (`Rule { keywords: &["ontem", "yesterday", ...], axis: G2_TEMPORAL_ANCHOR, ... }`): **não mexer nas keywords**. As palavras-chave que disparam heurísticas continuam bilíngues — esse é o ponto delas. Só o nome da constante do campo `axis` renomeia.

---

## ARQUIVO 3 — `leet-bridge/tests/translator_tests.rs`

Onde houver `leet_bridge::nl_translator::G2_ANCORA_TEMPORAL`, renomear para `leet_bridge::nl_translator::G2_TEMPORAL_ANCHOR`. Mesmo com qualquer outra constante do translator que tenha sido usada nos testes. Comentários de teste (`/// Past tense → G2_ANCORA_TEMPORAL near 0`) também se atualizam pro nome novo.

---

## ARQUIVO 4 — `leet-bridge/src/claude_1337_prompt.rs`

Aqui é reescrita das 32 linhas de eixo. O prompt em 07g ficou em EN explicando nomes PT. Agora os nomes SÃO EN — remove as glosas que viraram redundantes.

```rust
// ANTES (bloco S no prompt)
- [0]  S1 INTENCAO        — directional purpose     (0=no purpose · 1=maximum purpose)
- [1]  S2 AMBIGUIDADE     — interpretation multiplicity (0=single meaning · 1=fully ambiguous)
// ...

// DEPOIS
- [0]  S1 INTENTION          — directional purpose (0=no purpose · 1=maximum purpose)
- [1]  S2 AMBIGUITY          — interpretation multiplicity (0=single meaning · 1=fully ambiguous)
- [2]  S3 LOCAL_CONTEXT      — local context dependence (0=autonomous · 1=fully dependent)
- [3]  S4 GLOBAL_CONTEXT     — global history anchoring (0=no history · 1=deeply anchored)
- [4]  S5 ENTROPY            — informational entropy (0=deterministic · 1=maximum uncertainty)
- [5]  S6 DENSITY            — meaning density (0=empty · 1=maximally compressed)
- [6]  S7 COHERENCE          — internal consistency (0=contradictory · 1=fully consistent)
- [7]  S8 ALIGNMENT          — inter-agent consensus (0=total divergence · 1=full consensus)
```

E análogo para blocos D, G, P. A lista do prompt fica perfeitamente idempotente: nomes canônicos em inglês, sem glosa paralela.

Mesmo tratamento para:
- Cabeçalho do bloco (`**Block S — SEMÂNTICA (Semantics) — indices 0..8**` → `**Block S — SEMANTICS — indices 0..8**`).
- Seção "v0.5.1 BOOT DEFAULTS (Pilar 4)": `S7 COERENCIA` → `S7 COHERENCE`, etc.
- Seção do COGON_ZERO: os comentários de bloco (`// Block S`, `// Block D`...) já estão em EN, nada a fazer lá.

---

## ARQUIVO 5 — `leet-core/src/lib.rs`

Se `lib.rs` reexporta constantes nomeadas, ajustar. Exemplo hipotético:

```rust
// ANTES
pub use axes::{CANONICAL_AXES, AxisInfo, AxisBlock, axis_by_code, axis_by_index, axes_by_block, boot_vector};

// DEPOIS — mesma coisa, nenhum nome de função mudou.
// Só verificar que não está reexportando algum símbolo com nome PT.
```

Se não há reexport de strings-de-nome, este arquivo não muda. Verificar com `grep -n "pub use" leet-core/src/lib.rs`.

---

## ARQUIVO 6 — `leet-cli/tests/cli_test.rs`

Asserts sobre nomes:

```rust
// ANTES
assert_eq!(CANONICAL_AXES[0].name, "INTENCAO");
assert_eq!(CANONICAL_AXES[31].name, "LATENCIA");
assert_eq!(CANONICAL_AXES[22].name, "K_INTERACAO");

// DEPOIS
assert_eq!(CANONICAL_AXES[0].name, "INTENTION");
assert_eq!(CANONICAL_AXES[31].name, "LATENCY");
assert_eq!(CANONICAL_AXES[22].name, "K_INTERACTION");
```

Qualquer outro assert de nome PT aplicar a tabela-mestra.

---

## ARQUIVO 7 (CONDICIONAL) — `python/leet/axes.py` e `leet-py/`

**Antes de tocar, verificar escopo**:

```bash
# O que existe hoje?
ls python/leet/axes.py 2>/dev/null && echo "exists" || echo "no python/leet"
ls leet-py/ 2>/dev/null && echo "exists" || echo "no leet-py"
grep -rn "INTENCAO\|MASSA\|CONFIANCA" python/ leet-py/ 2>/dev/null
```

**Se `python/leet/axes.py` existe pós-07 e está em v0.5.1 PT** (constantes como `S1_INTENCAO = 0`):
Renomear cada constante conforme a tabela-mestra. Ex: `S1_INTENCAO = 0` → `S1_INTENTION = 0`.

**Se `leet-py/` é o SDK público Python** (conforme memória) e expõe `Axis.INTENCAO`, `Axis.MASSA`, etc:
Renomear. Esses são API pública — o contrato é `Axis.MASS`, `Axis.CONFIDENCE`, `Axis.ACTION`.

**Se nenhum existe ou estão fora do escopo mínimo declarado**: pular, registrar em CONTRACT.md como "deferred to later phase".

Se o rename no Python quebra testes Python (`pytest`), ajustar os testes — estão testando a API pública que mudou de contrato.

---

## ORDEM DE EXECUÇÃO DENTRO DO PROMPT

Sugestão para Claude Code executar na seguinte sequência, com `cargo check --workspace` após cada passo:

1. Aplicar rename em `axes.rs` (nome + description + normalization + title + tests).
2. `cargo check --workspace` — vai quebrar em `nl_translator.rs` e `claude_1337_prompt.rs` via string refs, mas vai apontar exatamente onde.
3. Aplicar rename em `nl_translator.rs` (constantes + doc comments + comments de keyword).
4. Aplicar rename em `translator_tests.rs` (cascade do 3).
5. Aplicar rename em `claude_1337_prompt.rs` (reescrita das 32 linhas + cabeçalhos de bloco + seção boot defaults).
6. Aplicar rename em `cli_test.rs` (asserts).
7. Verificar `lib.rs` (provavelmente noop).
8. Condicional: Python (se aplicável ao escopo mínimo).
9. `cargo test --workspace` — tem que ficar verde.
10. `grep -rn "INTENCAO\|AMBIGUIDADE\|CONTEXTO_LOCAL\|CONTEXTO_GLOBAL\|ENTROPIA\|DENSIDADE\|COERENCIA\|ALINHAMENTO\|PESO_CONEXAO\|TAXA_APRENDIZADO\|DECAIMENTO\|ESTABILIDADE\|HISTERESE\|PROPAGACAO\|CAUSALIDADE\|INERCIA\|MASSA\|ANCORA_TEMPORAL\|AFINIDADE\|TEMPORALIDADE\|CAMPO_LOCAL\|CAMPO_GLOBAL\|K_INTERACAO\|GRADIENTE\|QUANTIZACAO\|GRANULARIDADE\|COMPRESSAO\|RUIDO\|RESOLUCAO\|CONFIANCA" --include="*.rs" leet-core leet-cli leet-bridge leet-service`

Resultado esperado do grep final: **zero matches em código ativo**. Pode haver matches em:
- Comentários de contexto histórico (ex: "v0.5.1: replaces CAUSALIDADE" — manter, é doc).
- `prompts/` e scripts de experimento (fora do escopo).
- `leet1337/` (pasta abandonada, será deletada em bloco 4 de suporte).

---

## VERIFICATION

```bash
# Gate principal
cargo test --workspace
cargo clippy --workspace -- -D warnings

# Sanity semântico
cargo run -p leet-cli --bin leet -- axes | head -20
# Esperado: "Block 1 — SEMANTICS" como cabeçalho, primeira linha "S1 INTENTION ..."

cargo run -p leet-cli --bin leet -- axes --json | jq '.[0].name, .[16].name, .[31].name'
# Esperado: "INTENTION", "MASS", "LATENCY"

# Confirma que códigos não mudaram
cargo run -p leet-cli --bin leet -- axes --json | jq '.[22].code'
# Esperado: "G7"

# Python (se tocou leet-py)
python -c "from leet_sdk import Axis; print(Axis.MASS, Axis.CONFIDENCE, Axis.ACTION)"
# Esperado: três valores válidos
```

Se `cargo test --workspace` passa e os três greps semânticos batem, PROMPT_08 está completo.

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt08 "Rename 32 axis names PT → EN across leet-core and public API"
task project:1337 +prompt08 start
# work
task project:1337 +prompt08 done

git add leet-core/src/axes.rs \
        leet-core/src/lib.rs \
        leet-bridge/src/nl_translator.rs \
        leet-bridge/src/claude_1337_prompt.rs \
        leet-bridge/tests/translator_tests.rs \
        leet-cli/tests/cli_test.rs
# Se tocou Python:
#   python/leet/axes.py
#   leet-py/...

git commit -m "refactor(axes): rename 32 axis names PT → EN (v0.5.1, no semantic change)

Mechanical rename of every axis identifier from Portuguese to English.
Short codes (S1..P8) are language-agnostic and unchanged.

Full mapping (32 axes):
  INTENCAO→INTENTION          AMBIGUIDADE→AMBIGUITY
  CONTEXTO_LOCAL→LOCAL_CONTEXT  CONTEXTO_GLOBAL→GLOBAL_CONTEXT
  ENTROPIA→ENTROPY            DENSIDADE→DENSITY
  COERENCIA→COHERENCE         ALINHAMENTO→ALIGNMENT
  PESO_CONEXAO→CONNECTION_WEIGHT  TAXA_APRENDIZADO→LEARNING_RATE
  DECAIMENTO→DECAY            ESTABILIDADE→STABILITY
  HISTERESE→HYSTERESIS        PROPAGACAO→PROPAGATION
  CAUSALIDADE→CAUSALITY       INERCIA→INERTIA
  MASSA→MASS                  ANCORA_TEMPORAL→TEMPORAL_ANCHOR
  AFINIDADE→AFFINITY          TEMPORALIDADE→TEMPORALITY
  CAMPO_LOCAL→LOCAL_FIELD     CAMPO_GLOBAL→GLOBAL_FIELD
  K_INTERACAO→K_INTERACTION   GRADIENTE→GRADIENT
  QUANTIZACAO→QUANTIZATION    GRANULARIDADE→GRANULARITY
  COMPRESSAO→COMPRESSION      RUIDO→NOISE
  RESOLUCAO→RESOLUTION        CONFIANCA→CONFIDENCE
  ACAO→ACTION                 LATENCIA→LATENCY

Scope (minimal, per user decision):
- leet-core/src/axes.rs: name, description, normalization, block titles, tests.
- leet-bridge/src/nl_translator.rs: 32 index constants (D7_CAUSALITY, ...).
- leet-bridge/src/claude_1337_prompt.rs: 32 axis lines, block headers, boot defaults section.
- leet-bridge/tests/translator_tests.rs: constant references (cascade).
- leet-cli/tests/cli_test.rs: name asserts.
- Public Python API (leet-py): class attrs and exported constants (if applicable).

Out of scope (unchanged):
- Internal comments in .rs files
- Error messages (#[error(...)])
- CLI help strings
- Heuristic keyword lists (bilingual by design)
- Scripts in prompts/, net1337.py, plato_discussion.py, comparison_reports/
- Docx specs (block 3 of Fase A regenerates them in EN)

Concludes block 2 of Fase A. Block 3 (regenerate .docx spec in EN) next.

Part of Fase A, sub-prompt 08."

git push origin main
```

---

## ATUALIZAR CONTRACT.md

```markdown
### Fase A, Block 2 — PROMPT_08 (COMPLETED)
- 32 axis names renamed PT → EN across leet-core + public API
- Axis codes (S1..P8) unchanged
- leet-core inteiro em EN; SDK Python público idem
- Gate: cargo test --workspace + cargo clippy -- -D warnings verdes
- Pendente: spec .docx v0.5.1 regenerada em EN (Fase A, Block 3)
- Pendente: bloco 4 de suporte (workspace.package, W opt-in, limpeza leet1337/, governança)
```

---

**END OF PROMPT_08 — BLOCK 2 OF FASE A COMPLETE**
