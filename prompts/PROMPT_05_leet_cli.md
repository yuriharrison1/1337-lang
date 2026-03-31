# PROMPT 05 — LEET-CLI (Ferramentas de Debug · Rust · clap)

Build `leet-cli` — a Rust binary with debug and inspection tools for the 1337 protocol.
Rich colored output. Fast. Works standalone or connected to leet-service.

**PREREQUISITE**: PROMPT_01 completed (leet-core exists).

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## STRUCTURE

```
leet-cli/
├── Cargo.toml
└── src/
    ├── main.rs
    ├── output.rs         # Shared formatting: colored bars, tables
    └── cmd/
        ├── mod.rs
        ├── encode.rs
        ├── decode.rs
        ├── dist.rs
        ├── blend.rs
        ├── axes.rs
        ├── zero.rs
        ├── validate.rs
        ├── bench.rs
        ├── inspect.rs
        ├── health.rs
        └── version.rs
```

Add `"leet-cli"` to workspace members in root Cargo.toml.

**leet-cli/Cargo.toml:**
```toml
[package]
name = "leet-cli"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "leet"
path = "src/main.rs"

[dependencies]
leet-core = { path = "../leet-core" }
leet-bridge = { path = "../leet-bridge" }
clap = { version = "4", features = ["derive"] }
colored = "2"
serde_json = "1"
uuid = { version = "1", features = ["v4"] }
tonic = { version = "0.12", features = ["transport"], optional = true }
tokio = { version = "1", features = ["full"], optional = true }
indicatif = "0.17"

[features]
default = []
service = ["tonic", "tokio"]  # enables health + service-connected commands
```

---

## COMMANDS

### `leet encode "texto"`
- Project text through MockProjector → sem[32] + unc[32]
- Display as colored horizontal bars per axis
- Group by A (blue), B (green), C (yellow)
- Show axis code + name + bar + numeric value
- Example output:
```
  ═══ Ontológico ═══
  [A0] VIA             ████████░░  0.82
  [A1] CORRESPONDÊNCIA ██░░░░░░░░  0.21
  ...
  ═══ Epistêmico ═══
  [B1] VERIFICABILIDADE ██████░░░░  0.65
  ...
  ═══ Pragmático ═══
  [C1] URGÊNCIA        █████████░  0.91
  ...
```

### `leet decode '{"sem":[0.8,0.2,...],"unc":[0.1,0.1,...]}'`
- Parse JSON input
- Reconstruct natural language from top axes
- Show reconstruction + confidence

### `leet dist "conceito A" "conceito B"`
- Encode both, compute DIST
- Show overall distance
- Show per-axis contribution (which axes diverge most)
- Color-code by magnitude of difference

### `leet blend "conceito A" "conceito B" --alpha 0.6`
- Encode both, compute BLEND with given α
- Show resulting COGON with bars
- Show delta from each input

### `leet axes [--group A|B|C] [--verbose]`
- Print all 32 axes with group coloring
- --group filters to specific group
- --verbose adds full descriptions
- Default: compact table

### `leet zero`
- Print COGON_ZERO in formatted display
- All 32 dimensions at 1.0 with zero uncertainty
- Show "I AM" declaration

### `leet validate <file.json>`
- Read MSG_1337 or COGON from JSON file
- Run R1–R21 validation
- Print results: ✓ for pass, ✗ with explanation for fail
- Exit code 0 if valid, 1 if violations found

### `leet bench --n 1000 [--warmup 100]`
- Run N encode operations
- Report: min, p50, p95, p99, max latency
- Report: throughput (ops/sec)
- Use indicatif progress bar during run

### `leet inspect <cogon.json>`
- Load COGON from JSON
- Show semantic interpretation:
  - Top 5 axes by sem value
  - Bottom 5 axes
  - Overall uncertainty profile
  - Suggested intent based on pragmatic axes
  - Closest axis group (most active)

### `leet health [--host localhost:50051]`
- Requires `service` feature
- Connect to leet-service gRPC
- Report status, backend, uptime
- Exit code 0 if healthy

### `leet version`
- Print: leet-cli version, spec version (0.4.0), build date
- Print: features enabled (service, etc.)

---

## output.rs — Shared formatting

```rust
/// Draw a colored bar: ████████░░ 0.82
fn draw_bar(value: f32, width: usize, color: Color) -> String;

/// Color by group: A=blue, B=green, C=yellow
fn group_color(group: &str) -> Color;

/// Print axis table with alignment
fn print_axes_table(axes: &[AxisInfo], verbose: bool);

/// Print COGON as colored bars grouped by axis group
fn print_cogon_bars(sem: &[f32;32], unc: &[f32;32]);
```

---

## TESTS (minimum 15)

- `leet zero` output contains all 32 dims at 1.0
- `leet axes` lists exactly 32 axes
- `leet axes --group A` lists exactly 14 axes
- `leet axes --group B` lists exactly 8 axes
- `leet axes --group C` lists exactly 10 axes
- encode produces valid sem[32] values in [0,1]
- dist is symmetric: dist(a,b) == dist(b,a)
- blend with α=0 returns c2, α=1 returns c1
- validate accepts valid COGON
- validate rejects COGON with sem out of range
- validate rejects DAG with cycle
- inspect identifies top axes correctly
- bench runs without error
- version shows correct spec version
- decode produces non-empty string

---

## TASKWARRIOR + CONTRACT UPDATE

```bash
task project:1337 +prompt05 status:pending done

sed -i 's/| leet-cli (ferramentas) | PROMPT_05 | `\[ \]` PENDENTE/| leet-cli (ferramentas) | PROMPT_05 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

git add -A
git commit -m "feat(prompt-05): leet-cli — encode, dist, axes, bench, validate

- 12 subcommands with rich colored output
- Bar visualization per axis grouped by A/B/C
- Benchmarking with percentile latency reporting
- R1-R21 validation from CLI
- CONTRACT.md + Taskwarrior updated"

git push origin main
```

---

## VERIFICATION

```bash
cargo build -p leet-cli
cargo test -p leet-cli
cargo install --path leet-cli

leet version
leet zero
leet axes
leet axes --group B --verbose
leet encode "controle preditivo MPC urgente"
leet dist "amor" "ódio"
leet blend "ciência" "arte" --alpha 0.5
leet bench --n 500
```

**END OF PROMPT_05**
