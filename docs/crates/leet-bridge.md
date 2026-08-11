# leet-bridge

Rust crate for NL↔COGON translation. Implements R21: no protocol internals are exposed to external systems.

## Responsibility

```
External System
     │ (plain text)
     ▼
┌─────────────┐
│  BridgeIn   │  encode(text) → Cogon
│  BridgeOut  │  decode(Cogon) → text
└─────────────┘
     │ (COGON / DAG — internal)
     ▼
 leet-core network
```

## Public API

```rust
use leet_bridge::{encode, decode, BridgeProjector, MockProjector};

// Encode: text → COGON
let cogon = encode("deploy urgente falhou", &projector)?;

// Decode: COGON → text
let text = decode(&cogon, &projector)?;
```

## BridgeProjector

Trait for different projection backends:

```rust
pub trait BridgeProjector: Send + Sync {
    fn project(&self, text: &str) -> Result<Cogon, LeetError>;
    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError>;
}
```

### MockProjector

Deterministic implementation for tests — no network, no API.

Uses keyword heuristics to activate semantic axes:

```rust
let proj = MockProjector;
let cogon = proj.project("o servidor caiu")?;
// cogon.sem[8]  = 0.9  (D1_CONNECTION_WEIGHT)
// cogon.sem[26] = 0.9  (P3_COMPRESSION)
// cogon.sem[13] = 0.15 (D6_PROPAGATION — low influence)
```

## W Matrix (Primary Path)

The main projection uses a calibrated `W` matrix of dimensions `[32 × D]`, where D is the embedding dimension (e.g. 768 or 1536).

```
text → embedding → W @ embedding → clamp(0, 1) → sem[32]
```

### Loading

The W matrix is loaded once per process (`OnceLock`). Search order:

1. `LEET_W_PATH` (environment variable)
2. `./calibration/data/W.bin` (local workspace)
3. `/usr/share/leetlang/W.bin` (system installation)

```rust
use leet_bridge::projector::w_matrix;

if let Some(w) = w_matrix() {
    println!("W loaded: {}x{}", w.rows, w.cols);
}
```

### W.bin File Format

```
Offset  Size  Field
0       4        u32 rows (always 32)
4       4        u32 cols (embedding dimension)
8       rows*cols*4  f32 little-endian, row-major
```

### Projection via W

```rust
use leet_bridge::projector::{project_embedding, project_text, EmbeddingProvider};

// From a precomputed embedding
let sem = project_embedding(&embedding_vec)?;

// From text + provider
let cogon = project_text("texto aqui", &provider)?;
```

### EmbeddingProvider

Trait for different embedding backends:

```rust
pub trait EmbeddingProvider: Send + Sync {
    fn embed(&self, text: &str) -> Result<Vec<f32>, BridgeError>;
    fn dim(&self) -> usize;
}
```

### Fallback

With the `keyword-fallback` feature enabled, if `W.bin` is unavailable the system falls back to keyword heuristics. Without the feature, the absence of `W.bin` is a hard error.

## Heuristics (RULES)

Table of rules applied by the MockProjector and the fallback:

| Keywords | Axis | Value |
|----------|------|-------|
| caiu, falhou, erro, down, crash | D1_CONNECTION_WEIGHT (8) | 0.9 |
| caiu, falhou, erro, down, crash | P3_COMPRESSION (26) | 0.9 |
| deploy, processo, pipeline, rodando | D2_LEARNING_RATE (9) | 0.85 |
| deploy, processo, pipeline, rodando | P7_ACTION (30) | 0.8 |
| reverter, desfazer, rollback, undo | G4_TEMPORALITY (19) | 0.9 |
| reverter, desfazer, rollback, undo | P7_ACTION (30) | 0.85 |
| urgente, crítico, agora, imediato | G8_GRADIENT (23) | 0.95 |

## nl_translator

Helper functions for NL↔COGON translation and intent inference:

```rust
use leet_bridge::{nl_to_cogon, cogon_to_nl, infer_intent};

let cogon = nl_to_cogon("deploy falhou", &projector)?;
let text  = cogon_to_nl(&cogon, &projector)?;
let intent = infer_intent("me diga o status");  // Intent::Query
```

## Anthropic Client

`leet_bridge::anthropic_client` — HTTP client for the Anthropic API, used by the CLI's `chat` mode.

Uses `LEET_API_KEY` as the environment variable.

## Claude 1337 Prompt

`leet_bridge::claude_1337_prompt` — system prompt configured so that Claude Code operates in 1337 mode (COGON-first communication, compact `⟨…⟩` notation).

## Tests

```bash
cargo test -p leet-bridge   # 12 tests
```

All tests use `MockProjector` — no network calls.
