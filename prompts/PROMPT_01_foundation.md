# PROMPT 01 — LEET-CORE + BRIDGE + PYTHON + NET1337 + SKILL

Build the complete foundation of the 1337 project. Everything below is self-contained —
the full v0.4 spec is embedded. Do NOT read external files. Do NOT ask questions. Build everything.

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

### 1. SKILL.md
Create `SKILL.md` at repo root with full project context for Claude Code.
Include: project overview, spec summary, repo structure, coding conventions, key types.

### 2. Cargo Workspace
```
Cargo.toml (workspace root)
├── leet-core/     (lib)
└── leet-bridge/   (lib)
```

Root Cargo.toml:
```toml
[workspace]
members = ["leet-core", "leet-bridge"]
resolver = "2"
```

### 3. leet-core (Rust library)

**Cargo.toml:**
```toml
[package]
name = "leet-core"
version = "0.4.0"
edition = "2021"

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4", "serde"] }
sha2 = "0.10"
thiserror = "2"

[features]
default = []
python = ["pyo3"]

[dependencies.pyo3]
version = "0.22"
optional = true
features = ["extension-module"]
```

**Files to create:**

`src/lib.rs` — re-exports all modules
`src/types.rs` — ALL types: Scalar(f32 clamped 0..1), Cogon, Edge, EdgeType, Dag, RawField, RawRole, Intent, Receiver, C5Block, SurfaceBlock, Msg1337, EmergentRecord, CogonZero constant. VECTOR[32] = `[f32; 32]`. Cogon::zero() returns COGON_ZERO.
`src/axes.rs` — AxisInfo struct { index, code, name, group, description }. CANONICAL_AXES: [AxisInfo; 32] with ALL 32 axes from spec above. AxisGroup enum {Ontological, Epistemic, Pragmatic}. Functions: axes_by_group(), axis_by_index(), axis_by_code().
`src/operators.rs` — focus(), delta(), blend(), dist(), anomaly_score(). All operate on [f32;32]. blend: sem=α*c1+(1-α)*c2, unc=element-wise max. dist: cosine weighted by (1-unc). anomaly_score: mean dist to centroid.
`src/validate.rs` — validate_cogon(), validate_dag(), validate_msg(). Returns Vec<LeetError>. Covers R1–R21 exhaustively. has_cycle() via DFS. validate_msg checks intent/ref/patch consistency, broadcast rules, surface rules.
`src/error.rs` — LeetError enum with variant per rule (R1MissingIntent, R2DeltaRefMismatch, R3MissingNode(Uuid), R4Cycle, R5LowConfidence{dim,value}, R6MissingUrgency, R7UnregisteredEmergent, R8InvalidBroadcast, R9IncoherentEvidence, R14ParentNotAbsorbed, R16FocusAfterBlend, R19InheritanceTooDeep, R20MissingCogonZero, R21BridgeExposure, DimensionMismatch, ScalarOutOfRange, AlignmentMismatch).
`src/ffi.rs` — C ABI exports: leet_cogon_zero(), leet_blend(), leet_dist(), leet_validate_cogon(). Use #[no_mangle] extern "C". Pointers + lengths for arrays.
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

### 4. leet-bridge (Rust library)

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
thiserror = "2"
uuid = { version = "1", features = ["v4"] }
```

**Files:**
`src/lib.rs` — re-exports
`src/projector.rs` — trait SemanticProjector { fn project(&self, text: &str) -> ([f32;32], [f32;32]); }. MockProjector: heuristic-based projection using keyword matching to axes. No LLM, no network.
`src/human_bridge.rs` — text_to_cogon(text, projector) → Cogon. text_to_msg(text, sender, receiver, projector) → Msg1337. cogon_to_text(cogon) → String (reconstruct from sem values + axis names).

**Tests:** Minimum 10 tests.

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
│   ├── bridge.py     — MockProjector + text_to_cogon() + cogon_to_text()
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
dev = ["pytest>=8", "pytest-asyncio"]

[project.scripts]
leet = "leet.cli:main"
```

CLI commands:
- `leet zero` — prints COGON_ZERO formatted
- `leet encode "texto"` — projects text → sem[32] with colored bars per axis
- `leet decode '{"sem":[...]}'` — reconstructs text from vector
- `leet dist "a" "b"` — computes DIST with per-axis contribution
- `leet blend "a" "b" --alpha 0.6` — blends two concepts
- `leet axes` — prints all 32 axes colored by group (A=blue, B=green, C=yellow)
- `leet validate msg.json` — validates against R1-R21

**Tests:** Minimum 25 tests.

### 6. net1337.py (simulator)

Interactive IRC-style multi-agent simulator. Place at `examples/net1337.py`.

Features:
- 3 default agents: Catalogador, Aprendiz, Orquestrador
- Each agent has personality (sem bias vector)
- Agents exchange MSG_1337 via shared bus
- Commands: /join <name>, /send <agent> <text>, /dag, /status, /quit
- Shows COGON vectors as colored bars
- All communication uses leet Python package

---

## TASKWARRIOR + CONTRACT UPDATE

At the END of the build, after all tests pass:

```bash
# Mark tasks done
for i in $(seq 1 20); do
  TASK_ID=$(task project:1337 +prompt01 "T01.$(printf '%02d' $i)" uuids 2>/dev/null | head -1)
  if [ -n "$TASK_ID" ]; then
    task "$TASK_ID" done 2>/dev/null || true
  fi
done

# Alternative: mark by description pattern
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
git commit -m "feat(prompt-01): leet-core + bridge + Python + net1337

- leet-core v0.4: types, 32 axes, operators, R1-R21 validation, C ABI, PyO3
- leet-bridge: SemanticProjector trait, MockProjector, HumanBridge
- Python leet1337: pure-python fallback, CLI, tests
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
leet dist "hello" "world"
leet axes

# Simulator
python examples/net1337.py

# Taskwarrior
task project:1337 +prompt01 list
```

ALL tests must pass. ALL CLI commands must work. net1337.py must start without errors.

**END OF PROMPT_01**
