# PROMPT 01 — LEET-CORE + BRIDGE/TRANSLATOR + PYTHON + NET1337 + SKILL

Build the complete foundation of the 1337 project. Everything below is self-contained —
the full v0.4 spec is embedded. Do NOT read external files. Do NOT ask questions. Build everything.

**PARTIAL EXECUTION**: This prompt may have been partially run before. If files already exist,
review them, fix any issues, and complete what's missing. Do NOT skip files that already exist
— verify they match this spec and fix if needed. The goal is a COMPLETE, WORKING foundation.

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## SPEC v0.4 — SOLE SOURCE OF TRUTH

### Primitives
```
SCALAR := float ∈ [0,1]
VECTOR := SCALAR[]
HASH   := SHA256
ID     := UUID v4
RAW    := any
```

RAW lives inside COGON only. Declared with:
```
raw: { type: MIME|ENUM, content: any, role: ENUM{EVIDENCE, ARTIFACT, TRACE, BRIDGE} }
```

### COGON (the word)
```
COGON := { id: ID, sem: VECTOR[32], unc: VECTOR[32], stamp: int64, raw: RAW? }
```

### COGON_ZERO
```
COGON_ZERO := {
  id:    "00000000-0000-0000-0000-000000000000",
  sem:   [1]*32,
  unc:   [0]*32,
  stamp: 0,
  raw:   null
}
```

### EDGE
```
EDGE := { from: ID, to: ID, type: ENUM<CAUSA|CONDICIONA|CONTRADIZ|REFINA|EMERGE>, weight: SCALAR }
```

### DAG (the sentence)
```
DAG := { root: ID, nodes: COGON[], edges: EDGE[] }
```

### Intent
```
INT := ENUM { ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK }
```

### MSG_1337 (the envelope)
```
MSG_1337 := {
  id: ID, sender: ID, receiver: ID|BROADCAST,
  intent: ENUM<ASSERT|QUERY|DELTA|SYNC|ANOMALY|ACK>,
  ref: HASH?, patch: VECTOR[32]?,
  payload: COGON|DAG,
  c5: { zone_fixed: VECTOR[32], zone_emergent: MAP<ID,SCALAR>, schema_ver: semver, align_hash: HASH },
  surface: { human_required: bool, urgency: SCALAR, reconstruct_depth: int, lang: ISO_639 }
}
```

### 32 Canonical Axes

**Group A — Ontological (0–13)**

| Idx | Code | Name | Description |
|-----|------|------|-------------|
| 0 | A0 | VIA | Degree concept exists by itself, independent of external relations |
| 1 | A1 | CORRESPONDÊNCIA | Degree concept mirrors patterns at other abstraction levels |
| 2 | A2 | VIBRAÇÃO | Degree concept is in continuous motion/transformation |
| 3 | A3 | POLARIDADE | Degree concept is positioned on a spectrum between extremes |
| 4 | A4 | RITMO | Degree concept exhibits cyclic or periodic pattern |
| 5 | A5 | CAUSA E EFEITO | Degree concept is causal agent vs effect |
| 6 | A6 | GÊNERO | Degree concept is generative/active vs receptive/passive |
| 7 | A7 | SISTEMA | Degree concept is a set with emergent behavior |
| 8 | A8 | ESTADO | Degree concept is a configuration at a given moment |
| 9 | A9 | PROCESSO | Degree concept is transformation over time |
| 10 | A10 | RELAÇÃO | Degree concept is connection between entities |
| 11 | A11 | SINAL | Degree concept is information carrying variation |
| 12 | A12 | ESTABILIDADE | Degree concept tends toward equilibrium or divergence |
| 13 | A13 | VALÊNCIA ONTOLÓGICA | Intrinsic sign: 0=negative → 0.5=neutral → 1=positive |

**Group B — Epistemic (14–21)**

| Idx | Code | Name | Description |
|-----|------|------|-------------|
| 14 | B1 | VERIFICABILIDADE | Can be externally confirmed? |
| 15 | B2 | TEMPORALIDADE | Has defined temporal anchor? |
| 16 | B3 | COMPLETUDE | Resolved or open? |
| 17 | B4 | CAUSALIDADE | Origin identifiable? |
| 18 | B5 | REVERSIBILIDADE | Can be undone? |
| 19 | B6 | CARGA | Cognitive resource consumption |
| 20 | B7 | ORIGEM | Observed vs inferred vs assumed |
| 21 | B8 | VALÊNCIA EPISTÊMICA | 0=contradictory → 0.5=inconclusive → 1=confirmatory |

**Group C — Pragmatic (22–31)**

| Idx | Code | Name | Description |
|-----|------|------|-------------|
| 22 | C1 | URGÊNCIA | Requires immediate response? |
| 23 | C2 | IMPACTO | Expected consequences? |
| 24 | C3 | AÇÃO | Requires active response vs alignment only? |
| 25 | C4 | VALOR | Connects with something that truly matters? |
| 26 | C5 | ANOMALIA | Deviation from expected pattern? |
| 27 | C6 | AFETO | Relevant emotional valence? |
| 28 | C7 | DEPENDÊNCIA | Needs another to exist? |
| 29 | C8 | VETOR TEMPORAL | 0=past → 0.5=present → 1=future |
| 30 | C9 | NATUREZA | 0=noun → 1=verb |
| 31 | C10 | VALÊNCIA DE AÇÃO | 0=alert/contractive → 0.5=neutral → 1=confirmation/expansive |

**Emergent Zone**: index 32+ — append-only, learned dimensions.

### Operators (with precedence)
```
1. FOCUS(c, dims[]) → COGON           — project onto dimensional subset
2. DELTA(c_prev, c) → VECTOR[32]      — difference between two states
3. BLEND(c1, c2, α) → COGON           — sem = α·c1.sem + (1-α)·c2.sem; unc = max(c1.unc, c2.unc)
4. DIST(c1, c2) → SCALAR              — cosine distance weighted by (1-unc)
5. ANOMALY_SCORE(c, hist[]) → SCALAR  — mean distance to historical centroid
```

### Rules R1–R21
```
R1:  Every MSG_1337 has exactly one intent.
R2:  intent=DELTA requires ref+patch. Non-DELTA prohibits patch.
R3:  Every COGON referenced in DAG must be declared in nodes.
R4:  DAG cannot have cycles.
R5:  unc[i] > 0.9 triggers low-confidence flag.
R6:  surface.human_required=true requires urgency declared.
R7:  zone_emergent only references IDs registered in C5 handshake.
R8:  BROADCAST only for ANOMALY or SYNC.
R9:  RAW role=EVIDENCE must have coherent sem/unc.
R10: VECTOR[32] indexed by position, never by name at runtime.
R11: Emergent zone is append-only from index 32.
R12: Deprecation keeps index occupied with deprecated=true flag.
R13: Two agents share emergent shortcut only if both have same index in align_hash.
R14: No DAG node processed before all parents absorbed.
R15: Same-precedence operators: left to right.
R16: FOCUS always before BLEND.
R17: Envelope serialization in canonical order.
R18: OO inheritance conflict: specific wins.
R19: Max inheritance chain: 4 levels.
R20: Every agent transmits COGON_ZERO before any other message.
R21: BRIDGE agent never exposes 1337 internals to external system.
```

### C5 Handshake
4 phases: PROBE → ECHO → ALIGN → VERIFY.
5 anchor concepts: presence, absence, change, agency, uncertainty.

### Message Lifecycle
7 steps: structural validation → alignment check → reference resolution → DAG expansion → semantic absorption → anomaly evaluation → surface.

---

## WHAT TO BUILD

### 1. SKILL.md + references/
Create a Claude Code skill at repo root:
```
SKILL.md                           — Main skill file: project overview, how to build, key concepts
references/
├── spec-v0.4-compact.md           — Compact spec reference (all types, rules, operators)
├── axes-reference.md              — All 32 axes with full descriptions and keyword mappings
└── rust-implementation-guide.md   — Coding conventions, module structure, test patterns
```
SKILL.md must include: project purpose (inter-agent communication), spec version (v0.4),
repo structure, how to run tests, key types (Cogon, DAG, MSG_1337), and link to references.
The references/ files give Claude Code full context without needing to read source files.

### 2. Cargo Workspace
```
Cargo.toml (workspace root)
├── leet-core/     (lib)
├── leet-bridge/   (lib)
├── python/        (Python package)
└── examples/      (net1337.py, etc.)
```

Root Cargo.toml:
```toml
[workspace]
members = ["leet-core", "leet-bridge"]
resolver = "2"
```

---

### 3. leet-core (Rust library)

**Cargo.toml:**
```toml
[package]
name = "leet-core"
version = "0.4.0"
edition = "2021"

[lib]
name = "leet_core"
crate-type = ["rlib", "cdylib"]

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4", "serde"] }
sha2 = "0.10"
thiserror = "1"

[features]
default = []
python = ["pyo3"]

[dependencies.pyo3]
version = "0.20"
optional = true
features = ["extension-module"]
```

**Files to create:**

`src/lib.rs` — re-exports all modules. Include constants:
```rust
pub const FIXED_DIMS: usize = 32;
pub const MAX_INHERITANCE_DEPTH: u8 = 4;
pub const LOW_CONFIDENCE_THRESHOLD: f32 = 0.9;
```
Conditionally compile python module: `#[cfg(feature = "python")] pub mod python;`

`src/types.rs` — ALL types: Scalar(f32 clamped 0..1), Cogon, Edge, EdgeType, Dag, RawField, RawRole, Intent, Receiver, C5Block, SurfaceBlock, Msg1337, EmergentRecord, CogonZero constant. VECTOR[32] = `[f32; 32]`. Cogon::zero() returns COGON_ZERO.

`src/axes.rs` — AxisInfo struct { index, code, name, group, description }. CANONICAL_AXES: [AxisInfo; 32] with ALL 32 axes from spec above. AxisGroup enum {Ontological, Epistemic, Pragmatic}. Functions: axes_by_group(), axis_by_index(), axis_by_code().

`src/operators.rs` — focus(), delta(), blend(), dist(), anomaly_score(). All operate on [f32;32]. blend: sem=α*c1+(1-α)*c2, unc=element-wise max. dist: cosine weighted by (1-unc). anomaly_score: mean dist to centroid.

`src/validate.rs` — validate_cogon(), validate_dag(), validate_msg(). Returns Vec<LeetError>. Covers R1–R21 exhaustively. has_cycle() via DFS. validate_msg checks intent/ref/patch consistency, broadcast rules, surface rules.

`src/error.rs` — LeetError enum with variant per rule (R1MissingIntent, R2DeltaRefMismatch, R3MissingNode(Uuid), R4Cycle, R5LowConfidence{dim,value}, R6MissingUrgency, R7UnregisteredEmergent, R8InvalidBroadcast, R9IncoherentEvidence, R14ParentNotAbsorbed, R16FocusAfterBlend, R19InheritanceTooDeep, R20MissingCogonZero, R21BridgeExposure, DimensionMismatch, ScalarOutOfRange, AlignmentMismatch).

`src/ffi.rs` — C ABI exports with #[no_mangle] extern "C":
- `leet_cogon_zero() → CogonPtr` — allocates COGON_ZERO on heap
- `leet_cogon_free(ptr: CogonPtr)` — frees a Cogon (essential for C callers)
- `leet_blend(c1: CogonPtr, c2: CogonPtr, alpha: f32) → CogonPtr`
- `leet_dist(c1: CogonPtr, c2: CogonPtr) → f32`
- `leet_get_sem(ptr: CogonPtr, out: *mut f32, n: i32)` — copies sem values to caller buffer
- `leet_get_unc(ptr: CogonPtr, out: *mut f32, n: i32)` — copies unc values to caller buffer
- `leet_anomaly_score(c: CogonPtr, hist: *const CogonPtr, hist_len: i32) → f32`
- `leet_validate_cogon(ptr: CogonPtr) → i32` — returns 0 if valid, error count otherwise
- Use `type CogonPtr = *mut Cogon;` as opaque pointer for C callers.

`src/python.rs` — #[cfg(feature = "python")] PyO3 module: PyCogon, PyDag, py_blend(), py_dist(), py_focus(), py_delta(), py_anomaly_score(), py_validate(), py_cogon_zero(), py_axes().

**Tests (in each module + tests/ directory):**
Minimum 40 tests covering:
- Cogon creation and validation
- CogonZero properties (all sem=1, all unc=0)
- All 5 operators with known inputs/outputs
- BLEND conservatism (unc = max)
- DIST symmetry
- DAG cycle detection
- Each rule R1–R21 (positive and negative cases)
- Edge type creation
- Serialization roundtrip (serde_json)

---

### 4. leet-bridge (Rust library) — THE TRANSLATOR

This is the human ↔ 1337 translation layer. It converts human text to COGONs/DAGs/MSG_1337s
and back. Two projector backends: MockProjector (heuristics, no LLM) and prompt templates
for real LLM projectors.

**Cargo.toml:**
```toml
[package]
name = "leet-bridge"
version = "0.4.0"
edition = "2021"

[dependencies]
leet-core = { path = "../leet-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "1"
uuid = { version = "1", features = ["v4"] }
sha2 = "0.10"
hex = "0.4"
async-trait = "0.1"
tokio = { version = "1", features = ["full"], optional = true }

[features]
default = []
async = ["dep:tokio"]
```

**Files:**

#### src/lib.rs
Re-exports: projector, human_to_1337, leet_to_human, prompts, error.

#### src/error.rs
```rust
#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("Empty input text")]
    EmptyInput,
    #[error("Projection failed: {0}")]
    ProjectionFailed(String),
    #[error("Reconstruction failed: {0}")]
    ReconstructionFailed(String),
    #[error("Validation failed: {0:?}")]
    ValidationFailed(Vec<leet_core::error::LeetError>),
    #[error("JSON parse error: {0}")]
    JsonParse(String),
}
```

#### src/projector.rs — SemanticProjector trait + MockProjector

```rust
use async_trait::async_trait;
use leet_core::types::Cogon;
use crate::error::BridgeError;

/// Any backend that can project text into 1337's 32-dimensional space.
/// Anthropic Claude, OpenAI, local model, Ollama, whatever.
#[async_trait]
pub trait SemanticProjector: Send + Sync {
    /// Project human text onto 32 canonical axes.
    /// Returns (sem[32], unc[32]).
    async fn project(&self, text: &str) -> Result<([f32; 32], [f32; 32]), BridgeError>;

    /// Batch projection. Default: iterate. Override for batched LLM calls.
    async fn project_batch(&self, texts: &[&str]) -> Result<Vec<([f32; 32], [f32; 32])>, BridgeError> {
        let mut results = Vec::with_capacity(texts.len());
        for t in texts { results.push(self.project(t).await?); }
        Ok(results)
    }

    /// Reconstruct human text from a COGON.
    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError>;

    /// Reconstruct text from a DAG. depth = levels to reconstruct (leaf → root).
    async fn reconstruct_dag(&self, dag: &leet_core::types::Dag, depth: usize) -> Result<String, BridgeError>;

    /// Projector name for logging.
    fn name(&self) -> &str;
}
```

**MockProjector** — deterministic, no LLM, no network. Keyword-based heuristics per axis.

Implementation rules for EACH axis:

```
URGÊNCIA [22]:
  keywords: ["urgent","emergency","critical","crash","down","fail","agora","urgente","crítico","imediato"]
  unc when matched: 0.25

ANOMALIA [26]:
  keywords: ["error","bug","unexpected","strange","weird","anomaly","erro","estranho"]
  unc when matched: 0.25

AÇÃO [24]:
  keywords: ["run","execute","deploy","fix","update","implement","fazer","executar","corrigir"]
  unc when matched: 0.3

PROCESSO [9]:
  keywords: ["process","transform","convert","pipeline","flow","processar","transformar"]
  unc when matched: 0.3

SISTEMA [7]:
  keywords: ["system","network","cluster","service","agent","sistema","rede","serviço"]
  unc when matched: 0.3

ESTADO [8]:
  keywords: ["state","status","config","snapshot","crashed","running","estado","rodando","caiu"]
  unc when matched: 0.3

IMPACTO [23]:
  keywords: ["impact","critical","important","breaking","major","importante","grave"]
  unc when matched: 0.3

AFETO [27]:
  keywords: ["love","hate","happy","sad","angry","fear","joy","amor","ódio","feliz","triste","medo"]
  unc when matched: 0.25

VALOR [25]:
  keywords: ["value","important","meaningful","matters","purpose","valor","significado","propósito"]
  unc when matched: 0.3

COMPLETUDE [16]:
  keywords_high: ["done","finished","complete","resolved","concluído","pronto"]
  keywords_low:  ["todo","pending","working","wip","em andamento"]
  unc when matched: 0.3

REVERSIBILIDADE [18]:
  keywords_low:  ["delete","remove","destroy","irreversible","permanente","apagar"]
  keywords_high: ["draft","temp","test","reversível","rascunho"]
  unc when matched: 0.3

CARGA [19]:
  heuristic: text.len() > 200 chars → high. Contains nested technical terms → high.
  unc: 0.4

VETOR TEMPORAL [29]:
  past_keywords:   ["last","ago","yesterday","ontem","antes","previous","passado"]
  future_keywords: ["will","future","tomorrow","amanhã","próximo","next","futuro"]
  if past > future: sem = 0.2 * past_score
  if future > past: sem = 0.7 + 0.3 * future_score
  else: sem = 0.5
  unc when matched: 0.3

NATUREZA [30]:
  verb_keywords: ["run","do","make","create","update","process","send","get","fix","build"]
  sem = 0.3 + verb_score * 0.7
  unc: 0.4

VALÊNCIA DE AÇÃO [31]:
  alert_keywords:  ["warning","alert","danger","cuidado","perigo","atenção"]  → sem=0.1
  confirm_keywords: ["ok","confirmed","approved","done","aprovado","confirmado"] → sem=0.9
  unc when matched: 0.3
```

**Default values:** sem = 0.5, unc = 0.7 (high uncertainty).
**Hash-based fallback** for axes not matched by heuristics:
```rust
// SHA256(text + axis_index) → normalize to [0,1]
use sha2::Digest;
let mut h = sha2::Sha256::new();
h.update(text.as_bytes());
h.update(&(axis_index as u64).to_le_bytes());
let result = h.finalize();
let val = u16::from_le_bytes([result[0], result[1]]) as f32 / 65535.0;
sem[i] = val;
// unc stays at 0.7 for hash-based
```

**reconstruct(cogon):** Find top-3 axes by sem value, construct descriptive sentence.
Example: sem[22]=0.9, sem[7]=0.8, sem[26]=0.7 → "Situação urgente no sistema com anomalia detectada"

**reconstruct_dag(dag, depth):** Walk from leaves to root up to depth levels. For each node,
reconstruct text. Connect with edge-type words: CAUSA→"causou", CONDICIONA→"depende de",
CONTRADIZ→"contradiz", REFINA→"refina", EMERGE→"emergiu de".

#### src/prompts.rs — LLM Prompt Templates

These are the prompts sent to real LLMs (Anthropic, OpenAI, etc.) for projection.

```rust
/// Generate the projection prompt that asks an LLM to score text on 32 axes.
/// The prompt lists ALL 32 axes with index, code, name, and description.
/// Asks for JSON response: {"sem": [32 floats], "unc": [32 floats]}
pub fn projection_prompt(text: &str) -> String {
    format!(r#"You are a semantic analysis engine for the 1337 inter-agent protocol.
Score the following text on exactly 32 semantic axes.
Each score is a float in [0.0, 1.0].
unc = your uncertainty about each score (0=certain, 1=no idea).

## Axes

[0]  A0  VIA:                Degree concept exists by itself (0=dependent, 1=pure essence)
[1]  A1  CORRESPONDÊNCIA:    Degree concept mirrors patterns at other scales (0=unique, 1=fractal)
[2]  A2  VIBRAÇÃO:           Degree concept is in continuous motion (0=static, 1=constant flux)
[3]  A3  POLARIDADE:         Degree on spectrum between extremes (0=neutral, 1=strongly polar)
[4]  A4  RITMO:              Degree of cyclic/periodic pattern (0=irregular, 1=clear rhythm)
[5]  A5  CAUSA E EFEITO:     Causal agent vs effect (0=pure consequence, 1=primary cause)
[6]  A6  GÊNERO:             Generative/active vs receptive (0=receptive, 1=active principle)
[7]  A7  SISTEMA:            Set with emergent behavior (0=isolated, 1=complex system)
[8]  A8  ESTADO:             Configuration at a given moment (0=process, 1=pure snapshot)
[9]  A9  PROCESSO:           Transformation over time (0=static, 1=transformation)
[10] A10 RELAÇÃO:            Connection between entities (0=isolated, 1=purely relational)
[11] A11 SINAL:              Information carrying variation (0=noise, 1=pure signal)
[12] A12 ESTABILIDADE:       Tends toward equilibrium (0=chaotic, 1=convergent)
[13] A13 VALÊNCIA ONTOLÓGICA: Intrinsic sign (0=negative/contractive, 0.5=neutral, 1=positive/expansive)
[14] B1  VERIFICABILIDADE:   Externally confirmable (0=unfalsifiable, 1=verifiable)
[15] B2  TEMPORALIDADE:      Has temporal anchor (0=timeless, 1=precise moment)
[16] B3  COMPLETUDE:         Resolved (0=open/in-progress, 1=closed/conclusive)
[17] B4  CAUSALIDADE:        Origin identifiable (0=opaque, 1=clear cause)
[18] B5  REVERSIBILIDADE:    Can be undone (0=irreversible, 1=fully reversible)
[19] B6  CARGA:              Cognitive load (0=automatic, 1=heavy attention)
[20] B7  ORIGEM:             Observed vs inferred (0=pure assumption, 1=direct observation)
[21] B8  VALÊNCIA EPISTÊMICA: Knowledge sign (0=contradictory, 0.5=inconclusive, 1=confirmatory)
[22] C1  URGÊNCIA:           Requires immediate response (0=no rush, 1=critical pressure)
[23] C2  IMPACTO:            Consequences (0=innocuous, 1=changes system state)
[24] C3  AÇÃO:               Requires active response (0=informational, 1=demands execution)
[25] C4  VALOR:              Activates values, not just logic (0=neutral, 1=meaning-loaded)
[26] C5  ANOMALIA:           Deviation from expected (0=normal, 1=strong rupture)
[27] C6  AFETO:              Emotional valence (0=neutral, 1=strong affect)
[28] C7  DEPENDÊNCIA:        Needs another to exist (0=autonomous, 1=fully coupled)
[29] C8  VETOR TEMPORAL:     Time orientation (0=past, 0.5=present, 1=future)
[30] C9  NATUREZA:           Semantic category (0=noun/thing, 1=verb/process)
[31] C10 VALÊNCIA DE AÇÃO:   Transmission intent (0=alert, 0.5=neutral, 1=confirmation)

## Text to score:
"{text}"

Respond with ONLY the JSON, no explanation:
{{"sem": [f0, f1, ..., f31], "unc": [u0, u1, ..., u31]}}"#, text = text)
}

/// Generate reconstruction prompt: given sem[32]+unc[32] with axis names,
/// ask LLM to produce natural language text.
pub fn reconstruction_prompt(sem: &[f32; 32], unc: &[f32; 32]) -> String {
    // Build axis value list with names, like:
    // "[0]  A0  VIA=0.82 (unc=0.10)"
    // "[1]  A1  CORRESPONDÊNCIA=0.21 (unc=0.30)"
    // ... all 32 ...
    // Then append:
    // "Given these semantic axis scores for a concept in the 1337 protocol,
    //  reconstruct the most likely natural language text (in Portuguese) that
    //  would produce these values. Focus on axes with high sem and low unc.
    //  Respond with ONLY the text, nothing else."
    // MUST be fully implemented — not a stub/todo.
}
```

Both prompts must be complete and ready to send to any LLM API.

#### src/human_to_1337.rs — HumanBridge (text → 1337)

```rust
pub struct HumanBridge<P: SemanticProjector> {
    pub projector: P,
    pub human_agent_id: uuid::Uuid,
}

impl<P: SemanticProjector> HumanBridge<P> {
    pub fn new(projector: P) -> Self;

    /// Text → COGON. Projects, validates R5 (low confidence flags).
    pub async fn text_to_cogon(&self, text: &str) -> Result<Cogon, BridgeError>;

    /// Complex text → DAG with multiple COGONs.
    /// Strategy: split by sentence boundaries (['.', '!', '?']).
    /// Single sentence → DAG with 1 node (root).
    /// Multiple sentences → each sentence becomes a COGON,
    /// connected with CONDICIONA edges in sequence.
    /// "O servidor caiu. Precisamos agir." → 2 nodes + 1 CONDICIONA edge.
    pub async fn text_to_dag(&self, text: &str) -> Result<Dag, BridgeError>;

    /// Text → full MSG_1337 envelope.
    /// Fills c5 with: zone_fixed from COGON/DAG sem, zone_emergent empty,
    /// schema_ver="0.4.0", align_hash from SHA256 of zone_fixed.
    /// Surface: human_required=false by default, urgency from sem[22] (C1),
    /// reconstruct_depth=3, lang="pt".
    /// Validates with validate_msg() before returning.
    pub async fn text_to_msg(
        &self,
        text: &str,
        sender: uuid::Uuid,
        receiver: leet_core::types::Receiver,
        intent: leet_core::types::Intent,
    ) -> Result<leet_core::types::Msg1337, BridgeError>;
}
```

#### src/leet_to_human.rs — Reverse translation (1337 → text)

```rust
use leet_core::types::*;
use crate::projector::SemanticProjector;
use crate::error::BridgeError;

/// COGON → human text.
/// Uses projector.reconstruct() if available.
/// Fallback: describe top-N axes by sem value with their names.
pub async fn cogon_to_text<P: SemanticProjector>(
    cogon: &Cogon,
    projector: &P,
) -> Result<String, BridgeError>;

/// DAG → human text.
/// Walks from leaves to root up to `depth` levels.
/// Reconstructs each node, connects with edge-type connectors:
///   CAUSA → "causou" / "caused"
///   CONDICIONA → "depende de" / "depends on"
///   CONTRADIZ → "contradiz" / "contradicts"
///   REFINA → "refina" / "refines"
///   EMERGE → "emergiu de" / "emerged from"
/// Respects depth parameter — stops at depth levels from leaves.
pub async fn dag_to_text<P: SemanticProjector>(
    dag: &Dag,
    projector: &P,
    depth: usize,
) -> Result<String, BridgeError>;

/// MSG_1337 → human text.
/// Uses surface.reconstruct_depth for DAG depth.
/// Prepends header with intent and urgency if relevant.
/// Example: "[ANOMALY | urgência=0.92] Servidor caiu. Precisa de ação."
pub async fn msg_to_text<P: SemanticProjector>(
    msg: &Msg1337,
    projector: &P,
) -> Result<String, BridgeError>;
```

#### Bridge Tests (minimum 15 tests)

```
test_text_to_cogon_basic           — "olá" → COGON with 32 dims, sem in [0,1]
test_text_to_cogon_urgent          — "urgente" → sem[22] (URGÊNCIA) > 0.8
test_text_to_cogon_system_failure  — "o servidor caiu" → sem[8] (ESTADO) > 0.7, sem[26] (ANOMALIA) > 0.7
test_text_to_cogon_action          — "execute deploy" → sem[24] (AÇÃO) > 0.7
test_text_to_cogon_emotional       — "eu te amo" → sem[27] (AFETO) > 0.7
test_text_to_cogon_generic         — "bom dia" → average sem ∈ [0.3, 0.7] (moderate)
test_text_to_dag_single_sentence   — "o sol brilha" → DAG with 1 node
test_text_to_dag_multi_sentence    — "O servidor caiu. Precisamos agir." → 2 nodes + 1 CONDICIONA edge
test_text_to_msg_envelope          — text_to_msg → validates envelope is complete, all fields present
test_text_to_msg_urgency_surface   — urgent text → surface.urgency matches sem[22]
test_cogon_to_text_roundtrip       — text → cogon → text → verify dominant axes preserved
test_dag_to_text_basic             — DAG → readable string containing edge connectors
test_msg_to_text_with_header       — MSG with ANOMALY intent → text starts with "[ANOMALY |"
test_mock_projector_deterministic  — same input → same output (deterministic)
test_projection_prompt_complete    — projection_prompt() contains all 32 axis names
```

---

### 5. Python package

```
python/
├── pyproject.toml
├── leet/
│   ├── __init__.py
│   ├── types.py      — @dataclass Cogon, Edge, Dag, Msg1337, COGON_ZERO
│   ├── axes.py       — CANONICAL_AXES list of 32 dicts, axes_by_group(), axis_by_index()
│   ├── operators.py  — blend(), focus(), delta(), dist(), anomaly_score() pure Python
│   ├── validate.py   — validate_cogon(), validate_dag(), validate_msg()
│   ├── bridge.py     — MockProjector + AnthropicProjector + encode() + decode()
│   └── cli.py        — Click CLI: leet encode|decode|zero|blend|dist|axes|validate
└── tests/
    ├── test_types.py
    ├── test_operators.py
    ├── test_validate.py
    ├── test_bridge.py
    └── test_cli.py
```

**pyproject.toml:**
```toml
[project]
name = "leet1337"
version = "0.4.0"
requires-python = ">=3.10"
dependencies = ["click>=8.0"]

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
dev = ["pytest>=8", "pytest-asyncio"]

[project.scripts]
leet = "leet.cli:main"
```

#### Python bridge.py — MUST be complete (not stubs)

**MockProjector** — same heuristics as Rust version:
```python
class MockProjector:
    """Deterministic projector using keyword heuristics. No LLM, no network."""
    name = "mock"

    def project(self, text: str) -> tuple[list[float], list[float]]:
        t = text.lower()
        sem = [0.5] * 32
        unc = [0.7] * 32

        def kw(keywords):
            hits = sum(1 for k in keywords if k in t)
            return min(hits / max(len(keywords), 1), 1.0)

        # Same keyword mappings as Rust MockProjector (see above)
        sem[22] = kw(["urgent","emergency","critical","crash","down","fail","agora","urgente","crítico","imediato"])
        sem[26] = kw(["error","bug","unexpected","anomaly","erro","strange"])
        sem[24] = kw(["run","execute","deploy","fix","update","fazer","executar"])
        sem[9]  = kw(["process","transform","convert","pipeline","processar"])
        sem[7]  = kw(["system","network","service","agent","sistema","rede"])
        sem[8]  = kw(["state","status","config","crashed","running","estado","caiu"])
        sem[16] = kw(["done","finished","complete","resolved","concluído"])
        sem[27] = kw(["love","hate","happy","sad","angry","amor","ódio","feliz","triste"])
        # ... all other axes from Rust spec ...

        # mark heuristic dims as more confident
        for i in [7, 8, 9, 16, 22, 24, 26, 27, 29, 30]:
            if sem[i] != 0.5: unc[i] = 0.3

        # hash-based fallback for remaining axes
        import hashlib
        for i in range(32):
            if unc[i] > 0.5:
                h = hashlib.sha256(f"{text}:{i}".encode()).digest()
                sem[i] = int.from_bytes(h[:2], "little") / 65535.0

        return sem, unc
```

**AnthropicProjector** — uses `anthropic` lib with projection prompt listing all 32 axes.
The PROMPT_TEMPLATE MUST list all 32 axes inline (copy from the Rust projection_prompt above).
Do NOT use "..." or placeholders — list every single axis from [0] to [31] with descriptions.
```python
class AnthropicProjector:
    """Uses Claude to project text onto 32 axes. Requires ANTHROPIC_API_KEY."""
    name = "anthropic"

    # PROMPT_TEMPLATE must contain ALL 32 axes with full descriptions,
    # identical to the Rust projection_prompt() output.
    # [0]  A0  VIA: ...
    # [1]  A1  CORRESPONDÊNCIA: ...
    # ... every single axis through ...
    # [31] C10 VALÊNCIA DE AÇÃO: ...

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        """Call anthropic API with self.PROMPT_TEMPLATE.format(text=text).
        Parse JSON response, validate 32 dims, clamp to [0,1].
        Retry up to 3 times on parse failure.
        Return (sem, unc)."""

    async def reconstruct(self, cogon) -> str:
        """Build reconstruction prompt with all 32 axis values + names.
        Ask Claude to produce natural language. Return text."""
```

**Helper functions:**
```python
async def encode(text: str, projector=None) -> Cogon:
    """Text → COGON. Uses MockProjector if none given."""

async def decode(cogon: Cogon, projector=None) -> str:
    """COGON → text. Reconstructs from top axes."""
```

#### CLI commands — ALL fully implemented (not stubs)

- `leet zero` — prints COGON_ZERO formatted with all 32 dims at 1.0
- `leet encode "texto"` — projects text → sem[32] with colored bars per axis grouped by A/B/C
- `leet decode '{"sem":[...]}'` — reconstructs text from vector
- `leet dist "a" "b"` — computes DIST with per-axis contribution
- `leet blend "a" "b" --alpha 0.6` — blends two concepts, shows result
- `leet axes [--group A|B|C]` — prints all 32 axes colored by group (A=blue, B=green, C=yellow)
- `leet validate msg.json` — validates against R1-R21, shows ✓/✗ per rule
- `leet version` — prints leet1337 version + spec version (0.4.0)

**Tests:** Minimum 25 tests covering types, operators, validate, bridge, CLI.
Include `tests/test_e2e.py` with end-to-end tests:
- COGON_ZERO roundtrip (create → serialize → deserialize → verify)
- text → COGON → text roundtrip preserving dominant axes
- DAG with cycle detection
- DELTA compression between two states
- BLEND conservatism (unc = max)
- Full MSG_1337 envelope validation
- MockProjector determinism (same input → same output)

---

### 6. net1337.py (simulator)

Interactive IRC-style multi-agent simulator. Place at `examples/net1337.py`.

Features:
- 3 default agents: Catalogador, Aprendiz, Orquestrador
- Each agent has personality (sem bias vector)
- Agents exchange MSG_1337 via shared bus
- Commands: /join <name>, /send <agent> <text>, /dag, /status, /quit
- Shows COGON vectors as colored bars
- All communication uses leet Python package (MockProjector)

---

## TASKWARRIOR + CONTRACT UPDATE

At the END of the build, after all tests pass:

```bash
# Mark tasks done
task project:1337 +prompt01 status:pending done

# Update CONTRACT.md
sed -i 's/| leet-core (Rust) | PROMPT_01 | `\[ \]` PENDENTE/| leet-core (Rust) | PROMPT_01 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

# Update test counts
RUST_TESTS=$(cargo test --workspace 2>&1 | grep "test result" | grep -oP '\d+ passed' | head -1)
PYTHON_TESTS=$(cd python && pytest tests/ --co -q 2>/dev/null | tail -1)
echo "Rust: $RUST_TESTS | Python: $PYTHON_TESTS"

# Commit
git add -A
git commit -m "feat(prompt-01): leet-core + bridge/translator + Python + net1337

- leet-core v0.4: types, 32 axes, operators, R1-R21 validation, C ABI, PyO3
- leet-bridge: SemanticProjector trait, MockProjector (full heuristics per axis),
  HumanBridge (text_to_cogon, text_to_dag, text_to_msg),
  leet_to_human (cogon_to_text, dag_to_text, msg_to_text),
  LLM prompt templates (projection + reconstruction)
- Python leet1337: MockProjector, AnthropicProjector, encode/decode, CLI
- net1337.py: multi-agent simulator
- SKILL.md: Claude Code context
- CONTRACT.md updated
- Taskwarrior tasks marked done"

git push origin main
```

---

## FINAL VERIFICATION

```bash
# Rust
cargo build --workspace
cargo test --workspace

# Python
cd python && pip install -e ".[dev]" && pytest tests/ -v

# CLI
leet zero
leet encode "controle preditivo urgente"
leet encode "o servidor caiu e precisa de ação imediata"
leet dist "amor" "ódio"
leet blend "ciência" "arte" --alpha 0.5
leet axes
leet axes --group C

# Simulator
python examples/net1337.py

# Taskwarrior
task project:1337 +prompt01 list
```

ALL tests must pass. ALL CLI commands must work. net1337.py must start without errors.
MockProjector must produce semantically coherent results for the test cases above.

**END OF PROMPT_01**
