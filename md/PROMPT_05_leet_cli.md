# PROMPT 05 — leet-cli

Build a Rust CLI tool called `leet-cli` inside the existing workspace.
The CLI provides developer tools for inspecting COGONs, encoding text,
benchmarking the service, and debugging the semantic space.

## Add to workspace

Add `"leet-cli"` to the root `Cargo.toml` members array.

## leet-cli/Cargo.toml

```toml
[package]
name = "leet-cli"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "leet"
path = "src/main.rs"

[dependencies]
leet-core     = { path = "../leet-core" }
clap          = { version = "4", features = ["derive"] }
tonic         = { version = "0.11", features = ["transport"] }
prost         = "0.12"
tokio         = { version = "1", features = ["full"] }
serde         = { version = "1", features = ["derive"] }
serde_json    = "1"
colored       = "2"
indicatif     = "0.17"
uuid          = { version = "1", features = ["v4"] }
sha2          = "0.10"
anyhow        = "1"
```

## Commands to implement

```
leet encode <TEXT>         → project text to COGON, print sem[32] + unc[32]
leet decode <SEM_JSON>     → COGON vector → human-readable summary
leet inspect <COGON_JSON>  → full COGON inspection with axis labels
leet dist <TEXT1> <TEXT2>  → compute DIST between two texts
leet bench [--n N]         → benchmark encode throughput (default N=1000)
leet health                → check leet-service health
leet axes                  → print all 32 canonical axis names with indices
leet version               → print version + spec version
```

## src/main.rs

```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "leet", about = "1337 protocol developer tools", version = "0.1.0")]
struct Cli {
    #[arg(long, default_value = "localhost:50051", global = true)]
    service: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Project text to COGON vector
    Encode {
        text: String,
        #[arg(long, default_value = "false")]
        json: bool,
    },
    /// Decode COGON vector to human-readable summary
    Decode {
        /// JSON array of 32 floats, e.g. '[0.1, 0.9, ...]'
        sem: String,
    },
    /// Inspect a full COGON JSON with axis labels
    Inspect {
        /// COGON as JSON string or file path
        cogon: String,
    },
    /// Compute semantic distance between two texts
    Dist {
        text1: String,
        text2: String,
    },
    /// Benchmark encode throughput
    Bench {
        #[arg(long, default_value = "1000")]
        n: usize,
        #[arg(long, default_value = "false")]
        parallel: bool,
    },
    /// Check leet-service health
    Health,
    /// Print all 32 canonical axis names
    Axes,
    /// Print version info
    Version,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Encode { text, json }      => cmd_encode(&text, json, &cli.service).await,
        Commands::Decode { sem }             => cmd_decode(&sem),
        Commands::Inspect { cogon }          => cmd_inspect(&cogon),
        Commands::Dist { text1, text2 }      => cmd_dist(&text1, &text2, &cli.service).await,
        Commands::Bench { n, parallel }      => cmd_bench(n, parallel, &cli.service).await,
        Commands::Health                     => cmd_health(&cli.service).await,
        Commands::Axes                       => cmd_axes(),
        Commands::Version                    => cmd_version(),
    }
}
```

## src/commands/encode.rs

`cmd_encode(text, json, service_url)`:

Try to connect to leet-service via gRPC. If unavailable, fall back to local mock projection
(SHA256-based, same algorithm as LocalProjector in leet-vm).

**Normal output** (not --json):
```
COGON encode: "explica controle preditivo MPC"

Group A — Ontological
  [0]  via              : 0.743  unc: 0.186  ████████░░
  [1]  correspondencia  : 0.312  unc: 0.523  ███░░░░░░░
  ...  (all 14 axes)

Group B — Epistemic
  [14] verificabilidade : 0.891  unc: 0.089  █████████░
  ...  (all 8 axes)

Group C — Pragmatic
  [22] urgencia         : 0.234  unc: 0.441  ██░░░░░░░░
  ...  (all 10 axes)

COGON ID : 550e8400-e29b-41d4-a716-446655440000
Stamp    : 1711670400000000000
Est. tokens saved: 47
```

Bar visualization: 10 chars, filled = round(val * 10), use █ for filled, ░ for empty.

**JSON output** (--json flag):
```json
{
  "id": "...",
  "sem": [0.743, 0.312, ...],
  "unc": [0.186, 0.523, ...],
  "stamp": 1711670400000000000
}
```

## src/commands/decode.rs

`cmd_decode(sem_json)`:

Parse the JSON array of 32 floats.
Print a human-readable summary using axis names + values.

Output format:
```
COGON decode summary:

High confidence signals (unc < 0.4):
  via              = 0.743  [alto — princípio ativo]
  verificabilidade = 0.891  [muito alto — verificável]
  urgencia         = 0.234  [baixo — sem pressão]

Axis positions:
  NATUREZA: 0.234 (→ substantivo)
  VETOR_TEMPORAL: 0.678 (→ futuro)
  VALENCIA_ACAO: 0.812 (→ positivo/confirmação)
```

## src/commands/inspect.rs

`cmd_inspect(cogon_json_or_path)`:

If argument is a file path, read the file. Otherwise parse as JSON string.
Parse as Cogon struct.

Print full inspection:
```
─────────────────────────────────────────
COGON INSPECTION
─────────────────────────────────────────
ID    : 550e8400-e29b-41d4-a716-446655440000
Stamp : 2026-01-01 00:00:00 UTC
RAW   : type=text/plain role=ARTIFACT

Validation (R1–R21):
  ✓ sem has 32 dims
  ✓ unc has 32 dims
  ✓ all sem values in [0,1]
  ✓ all unc values in [0,1]
  ⚠ unc[14]=0.92 > 0.9 — low confidence flag (R5)

Semantic profile:
  Group A  avg sem: 0.534  avg unc: 0.312
  Group B  avg sem: 0.672  avg unc: 0.198
  Group C  avg sem: 0.445  avg unc: 0.521

Dominant axes (sem > 0.7, unc < 0.4):
  [7]  sistema          = 0.832  unc=0.124
  [14] verificabilidade = 0.891  unc=0.089
  [22] urgencia         = 0.765  unc=0.201
─────────────────────────────────────────
```

Validation checks: len(sem)==32, len(unc)==32, all in [0,1], check R5 (any unc>0.9).

## src/commands/dist.rs

`cmd_dist(text1, text2, service_url)`:

Encode both texts (local or service), then compute DIST using the weighted cosine formula:

```
weight[i] = (1 - unc1[i]) * (1 - unc2[i])
dot  = sum(sem1[i] * sem2[i] * weight[i])
n1   = sqrt(sum(sem1[i]^2 * weight[i]))
n2   = sqrt(sum(sem2[i]^2 * weight[i]))
sim  = dot / (n1 * n2 + 1e-8)
dist = 1.0 - sim
```

Output:
```
Semantic distance between:
  A: "explica controle preditivo"
  B: "explain model predictive control"

DIST    : 0.127  (very similar)
SIM     : 0.873

Top contributing axes (highest weight * |sem_diff|):
  [16] completude      : A=0.72  B=0.68  diff=0.04
  [7]  sistema         : A=0.83  B=0.81  diff=0.02
  [14] verificabilidade: A=0.89  B=0.91  diff=0.02

Interpretation:
  0.0–0.2  Very similar
  0.2–0.4  Related
  0.4–0.6  Loosely related
  0.6–0.8  Different
  0.8–1.0  Unrelated
```

## src/commands/bench.rs

`cmd_bench(n, parallel, service_url)`:

Generate N sample texts (use a fixed list of 20 sample phrases, cycle through them).
Sample phrases: "hello world", "controle preditivo MPC", "sistema de automação",
"machine learning pipeline", "semantic vector encoding", ... (20 total, varied topics).

Non-parallel: encode sequentially, measure wall time.
Parallel: use tokio::spawn to fire all N concurrently, measure wall time.

Output:
```
leet-service benchmark (N=1000, parallel=false)
Service: localhost:50051
Mode: local (service unavailable)

████████████████████████████████████ 1000/1000

Results:
  Total time : 1.234s
  Throughput : 810.4 encode/sec
  Avg latency: 1.23ms
  p50 latency: 1.18ms
  p95 latency: 2.41ms
  p99 latency: 4.12ms

Estimated savings (vs raw text):
  Avg text tokens  : 6.2
  Avg COGON tokens : 0.6
  Avg savings      : 90.3%
```

Use `indicatif` for the progress bar.
Collect all latencies in a Vec, sort to compute percentiles.

## src/commands/health.rs

`cmd_health(service_url)`:

Try gRPC Health RPC. If service available, print response.
If unavailable, print error message with suggestion.

Output (success):
```
leet-service health check
Service : localhost:50051
Status  : ok
Backend : simd
Uptime  : 3h 24m 11s
```

Output (failure):
```
leet-service unreachable at localhost:50051

Start the service:
  cargo run -p leet-service
  # or
  docker run -p 50051:50051 leet/service:latest

Environment:
  LEET_BACKEND=simd   (cpu | simd | cuda | metal)
  LEET_STORE=memory   (memory | redis://... | sqlite://...)
  LEET_PORT=50051
```

## src/commands/axes.rs

`cmd_axes()`:

Print the 32 canonical axes with their index, group, code and description.
Use colored output: Group A in blue, Group B in cyan, Group C in green.

```
1337 Canonical Space — v0.4 — 32 axes

GROUP A — Ontological (0–13)
  [0]  A0  via               Existência por si mesmo. Alta = essência pura.
  [1]  A1  correspondência   Espelha padrões em outros níveis de abstração.
  [2]  A2  vibração          Movimento/transformação contínua.
  [3]  A3  polaridade        Posição num espectro entre extremos.
  [4]  A4  ritmo             Padrão cíclico ou periódico.
  [5]  A5  causa e efeito    Agente causal vs efeito.
  [6]  A6  gênero            Gerador/ativo vs receptivo/passivo.
  [7]  A7  sistema           Conjunto com comportamento emergente.
  [8]  A8  estado            Configuração num dado momento.
  [9]  A9  processo          Transformação no tempo.
  [10] A10 relação           Conexão entre entidades.
  [11] A11 sinal             Informação carregando variação.
  [12] A12 estabilidade      Tende ao equilíbrio ou divergência.
  [13] A13 valência ont.     Sinal intrínseco. 0=negativo → 1=positivo.

GROUP B — Epistemic (14–21)
  [14] B1  verificabilidade  Pode ser confirmado externamente.
  [15] B2  temporalidade     Tem âncora temporal definida.
  [16] B3  completude        Está resolvido ou em aberto.
  [17] B4  causalidade       A origem é identificável.
  [18] B5  reversibilidade   Pode ser desfeito.
  [19] B6  carga             Recurso cognitivo consumido.
  [20] B7  origem            Observado vs inferido vs assumido.
  [21] B8  valência epist.   0=contraditório → 0.5=inconclusivo → 1=confirmatório.

GROUP C — Pragmatic (22–31)
  [22] C1  urgência          Exige resposta imediata.
  [23] C2  impacto           Gera consequências no sistema.
  [24] C3  ação              Demanda execução vs alinhamento.
  [25] C4  valor             Ativa valores, não só lógica.
  [26] C5  anomalia          Desvio do padrão esperado.
  [27] C6  afeto             Valência emocional relevante.
  [28] C7  dependência       Precisa de outro para existir.
  [29] C8  vetor temporal    0=passado → 0.5=presente → 1=futuro.
  [30] C9  natureza          0=substantivo → 1=verbo.
  [31] C10 valência ação     0=alerta → 0.5=consulta → 1=confirmação.

Emergent zone: indices 32+ (append-only, learned from usage)
```

## src/commands/version.rs

```
leet-cli  v0.1.0
leet-core v0.1.0
spec      v0.4 (32 canonical axes)
author    Yuri Harrison — Fortaleza, Ceará — Brasil — 2026
```

## Build and verify

```bash
cargo build -p leet-cli
cargo test  -p leet-cli

# smoke tests
./target/debug/leet version
./target/debug/leet axes
./target/debug/leet encode "controle preditivo MPC"
./target/debug/leet dist "hello world" "olá mundo"
./target/debug/leet bench --n 100
./target/debug/leet health
```

All commands must run without panics. Health will fail gracefully if service not running.
