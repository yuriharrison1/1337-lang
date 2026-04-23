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
cargo test --workspace                    # 173 Rust tests
bash test_all.sh                          # full audit (clippy + tests + PT names + CLI + Python)
```

## 32 Canonical Axes

4 blocks × 8 axes each:

| Block | Codes | Axes |
|---|---|---|
| **S** Semantic | S1–S8 | ESSENCE · CORRESPONDENCE · VIBRATION · POLARITY · RHYTHM · CAUSE_EFFECT · GENERATIVITY · SYSTEM |
| **D** Dynamic | D1–D8 | STATE · PROCESS · RELATION · SIGNAL · STABILITY · ONTOLOGICAL_VALENCE★ · CAUSALITY · VERIFIABILITY |
| **G** Gravity | G1–G8 | TEMPORALITY · TEMPORAL_ANCHOR★ · COMPLETENESS · REVERSIBILITY · COGNITIVE_LOAD · ORIGIN · EPISTEMIC_VALENCE★ · URGENCY |
| **P** Precision | P1–P8 | IMPACT · VALUE · ANOMALY · AFFECT★ · DEPENDENCY · TEMPORAL_VECTOR · ACTION · ACTION_VALENCE★ |

★ Valence axes: 0 = negative/past/contradictory · 0.5 = neutral · 1 = positive/future/confirmatory

Compact inline notation: `⟨G8=0.95 P3=0.90 D1=0.85⟩`

## MCP Tools (leet server — active when Claude Code loads this project)

| Tool | Description |
|---|---|
| `encode(text)` | Project text → active axes + values |
| `dist(a, b)` | Cosine distance; skip re-send if < 0.05 |
| `blend(a, b, α)` | Interpolate two COGONs |
| `axes()` | Full 32-axis reference |
| `inspect(json)` | Decode a COGON JSON payload |

## Leet Mode

Run `/leet` (or `/leet <task>`) to activate token-efficient COGON communication for the session.
See `.claude/commands/leet.md` for the full protocol.

## Key Invariants

- All axis values strictly in `[0.0, 1.0]`
- Timestamps in milliseconds (not nanoseconds)
- Delta magnitude normalised by `√32` → range `[0, 1]`
- Zero PT-language identifiers in `.rs` source (enforced by `test_all.sh` step 4)
- `leet-service` projects via `leet_bridge::nl_to_cogon()` — no duplicate heuristics
