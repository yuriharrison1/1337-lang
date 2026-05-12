# 1337 — Inter-Agent Communication Language

Rust workspace v0.5.1 + Python packages. COGON: `[f32; 32]` semantic vector, one float per canonical axis, all in [0, 1].

## Workspace

| Crate | Role |
|---|---|
| `leet-core` | COGON types, 32-axis definitions, protocol, validation |
| `leet-bridge` | NL → COGON projection (heuristics + calibrated W matrix) |
| `leet-service` | gRPC + TCP service, batch, agent engine |
| `leet-cli` | `leet encode / decode / dist / blend / axes / inspect / chat` |

Python: `python/` (leet1337 SDK · `leet_vm` namespace) · `leet-vm/` (VM runtime) · `leet-py/` (LeetClient public SDK)

## Build & Test

```bash
cargo build --workspace                   # debug
cargo build --workspace --release         # release
cargo test --workspace                    # 249 Rust tests
bash test_all.sh                          # full audit (clippy + tests + PT names + CLI + Python)
```

## 32 Canonical Axes

4 blocks × 8 axes each:

| Block | Codes | Axes |
|---|---|---|
| **S** Semantic | S1–S8 | INTENTION · AMBIGUITY · LOCAL_CONTEXT · GLOBAL_CONTEXT · ENTROPY · DENSITY · COHERENCE · ALIGNMENT |
| **D** Dynamic | D1–D8 | CONNECTION_WEIGHT · LEARNING_RATE · DECAY · STABILITY · HYSTERESIS · PROPAGATION · CAUSALITY · INERTIA |
| **G** Gravity | G1–G8 | MASS · TEMPORAL_ANCHOR · AFFINITY★ · TEMPORALITY★ · LOCAL_FIELD · GLOBAL_FIELD · K_INTERACTION · GRADIENT★ |
| **P** Precision | P1–P8 | QUANTIZATION · GRANULARITY · COMPRESSION · NOISE · RESOLUTION · CONFIDENCE · ACTION · LATENCY |

★ Bipolar axes: G3 AFFINITY (0=repulsion · 0.5=neutral · 1=attraction) · G4 TEMPORALITY (0=past · 0.5=present · 1=future) · G8 GRADIENT (0=decelerating · 0.5=stable · 1=accelerating)

Compact inline notation: `⟨G8=0.95 P3=0.90 D1=0.85⟩`

## MCP Tools (leet server — active when Claude Code loads this project)

| Tool | Description |
|---|---|
| `leet_recall(query?, limit?)` | Tiered recall from store (foundation + mid + raw) |
| `leet_remember(text)` | Compress text → COGON, append to store |
| `leet_encode(text)` | Text → sem[32] vector (no persist) |
| `leet_decode(sem)` | sem[32] → dominant-axis description |
| `leet_dist(a, b)` | Cosine distance weighted by P6_CONFIDENCE |
| `leet_recall_delta(since_unix_ns?)` | Patch vector since last recall cursor |

## Leet Mode

Run `/leet` (or `/leet <task>`) to activate token-efficient COGON communication for the session.
See `.claude/commands/leet.md` for the full protocol.

## Key Invariants

- All axis values strictly in `[0.0, 1.0]`
- Timestamps in milliseconds (not nanoseconds)
- Delta magnitude normalised by `√32` → range `[0, 1]`
- Zero PT-language identifiers in `.rs` source (enforced by `test_all.sh` step 4)
- `leet-service` projects via `leet_bridge::nl_to_cogon()` — no duplicate heuristics
