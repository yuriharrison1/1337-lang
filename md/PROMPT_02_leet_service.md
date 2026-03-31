# PROMPT 02 — leet-service

Build a standalone Rust gRPC service called `leet-service` inside the existing workspace.
This is the semantic compilation service for the 1337 protocol — it receives text and returns
COGON vectors (sem[32] + unc[32]), supporting batching, SIMD acceleration, and horizontal scaling.

## Workspace context

The existing workspace at the current directory has:
- `leet-core/` — Rust library with Cogon, DAG, ops (FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE),
  validation rules R1–R21, C ABI FFI, PyO3 bindings.
  Key public types: `Cogon { id: Uuid, sem: [f32;32], unc: [f32;32], stamp: i64, raw: Option<RawField> }`

Add `leet-service` as a new workspace member.

## What to build

### Cargo.toml (workspace root — add member)
Add `"leet-service"` to `members`.

### leet-service/Cargo.toml
```toml
[package]
name = "leet-service"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "leet-service"
path = "src/main.rs"

[dependencies]
leet-core = { path = "../leet-core" }
tonic = { version = "0.11", features = ["transport"] }
tonic-build = "0.11"
prost = "0.12"
tokio = { version = "1", features = ["full"] }
tokio-stream = "0.1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4"] }
ndarray = { version = "0.15", features = ["blas"] }
blas-src = { version = "0.8", features = ["openblas"] }
openblas-src = { version = "0.10", features = ["cblas", "system"] }
redis = { version = "0.24", features = ["tokio-comp"] }
sqlx = { version = "0.7", features = ["sqlite", "runtime-tokio"] }
tracing = "0.1"
tracing-subscriber = "0.3"
dotenvy = "0.15"
anyhow = "1"
bytes = "1"

[build-dependencies]
tonic-build = "0.11"
```

### proto/leet.proto
Create at `leet-service/proto/leet.proto`:

```protobuf
syntax = "proto3";
package leet;

service LeetService {
  rpc Encode      (EncodeRequest)        returns (EncodeResponse);
  rpc Decode      (DecodeRequest)        returns (DecodeResponse);
  rpc EncodeBatch (stream EncodeRequest) returns (stream EncodeResponse);
  rpc Delta       (DeltaRequest)         returns (DeltaResponse);
  rpc Recall      (RecallRequest)        returns (RecallResponse);
  rpc Health      (HealthRequest)        returns (HealthResponse);
}

message EncodeRequest {
  string text       = 1;
  string agent_id   = 2;
  string session_id = 3;
}

message EncodeResponse {
  string cogon_id       = 1;
  repeated float sem    = 2;
  repeated float unc    = 3;
  int64  stamp          = 4;
  int64  tokens_saved   = 5;
}

message DecodeRequest {
  repeated float sem = 1;
  repeated float unc = 2;
  string lang        = 3;
}

message DecodeResponse {
  string text = 1;
}

message DeltaRequest {
  repeated float sem_prev = 1;
  repeated float sem_curr = 2;
}

message DeltaResponse {
  repeated float patch   = 1;
  float          magnitude = 2;
}

message RecallRequest {
  repeated float sem     = 1;
  repeated float unc     = 2;
  string         agent_id = 3;
  int32          k        = 4;
}

message RecallResponse {
  repeated CogonRecord results = 1;
}

message CogonRecord {
  string cogon_id    = 1;
  repeated float sem = 2;
  repeated float unc = 3;
  float  dist        = 4;
  int64  stamp       = 5;
}

message HealthRequest {}
message HealthResponse {
  string status  = 1;
  string backend = 2;
  int64  uptime  = 3;
}
```

### build.rs
```rust
fn main() {
    tonic_build::configure()
        .build_server(true)
        .compile(&["proto/leet.proto"], &["proto"])
        .unwrap();
}
```

### src/main.rs

```rust
mod config;
mod projection;
mod store;
mod server;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cfg = config::Config::from_env();
    tracing::info!("leet-service starting | backend={} port={}", cfg.backend, cfg.port);

    let store = store::build(&cfg).await?;
    let proj  = projection::Engine::new(&cfg).await?;

    server::run(cfg, proj, store).await
}
```

### src/config.rs

```rust
#[derive(Clone, Debug)]
pub struct Config {
    pub port:         u16,
    pub backend:      String,   // "cpu" | "simd" | "cuda" | "metal"
    pub store_url:    String,   // "redis://..." | "sqlite://..." | "memory"
    pub w_path:       Option<String>,
    pub batch_window_ms: u64,
    pub batch_max:    usize,
    pub embed_model:  String,   // "mock" | "openai" | path to local model
    pub embed_url:    Option<String>,
    pub embed_key:    Option<String>,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            port:            env_u16("LEET_PORT", 50051),
            backend:         env_str("LEET_BACKEND", "simd"),
            store_url:       env_str("LEET_STORE", "memory"),
            w_path:          std::env::var("LEET_W_PATH").ok(),
            batch_window_ms: env_u64("LEET_BATCH_WINDOW", 10),
            batch_max:       env_usize("LEET_BATCH_MAX", 64),
            embed_model:     env_str("LEET_EMBED_MODEL", "mock"),
            embed_url:       std::env::var("LEET_EMBED_URL").ok(),
            embed_key:       std::env::var("LEET_EMBED_KEY").ok(),
        }
    }
}

fn env_str(k: &str, default: &str) -> String {
    std::env::var(k).unwrap_or_else(|_| default.to_string())
}
fn env_u16(k: &str, d: u16) -> u16 {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
fn env_u64(k: &str, d: u64) -> u64 {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
fn env_usize(k: &str, d: usize) -> usize {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
```

### src/projection/mod.rs

The projection engine maps text → sem[32] + unc[32].

Pipeline:
1. Embed text → embedding vector (mock: deterministic hash-based; openai: API call)
2. Multiply embedding × W matrix (shape: [embed_dim × 32]) → raw[32]
3. Clamp to [0,1] → sem[32]
4. Estimate unc[32] from embedding variance proxy

If W matrix file not found: initialize W with identity-like values scaled to 32 dims.

```rust
pub mod engine;
pub mod embed;
pub mod matrix;
pub mod batch;
pub use engine::Engine;
```

**src/projection/embed.rs** — two implementations:

`MockEmbedder`: deterministic, no network. For each text, compute SHA256, expand to 128 floats
by cycling through hash bytes normalized to [0,1]. Fast, reproducible, good for testing.

`OpenAIEmbedder`: POST to `embed_url` (default: `https://api.openai.com/v1/embeddings`)
with model `text-embedding-3-small`, returns 1536-dim vector.

Trait:
```rust
#[async_trait::async_trait]
pub trait Embedder: Send + Sync {
    async fn embed(&self, text: &str) -> anyhow::Result<Vec<f32>>;
    fn dim(&self) -> usize;
}
```

**src/projection/matrix.rs** — W matrix operations:

```rust
pub struct WMatrix {
    data: ndarray::Array2<f32>,  // shape [embed_dim, 32]
}

impl WMatrix {
    pub fn load(path: &str) -> anyhow::Result<Self>;
    pub fn identity_init(embed_dim: usize) -> Self;
    // GEMM: embedding[1 × embed_dim] × W[embed_dim × 32] → out[1 × 32]
    pub fn project(&self, embedding: &[f32]) -> [f32; 32];
    pub fn save(&self, path: &str) -> anyhow::Result<()>;
}
```

For `identity_init`: create W where W[i, i % 32] = 1.0, rest = 0.0. Then add small noise (0.01).
This gives a reasonable starting point before calibration.

`project()` uses ndarray matrix multiplication (BLAS under the hood when openblas feature enabled).
After multiply, apply sigmoid to each element to ensure [0,1] range.

**src/projection/engine.rs**:

```rust
pub struct Engine {
    embedder: Box<dyn Embedder>,
    w:        WMatrix,
}

impl Engine {
    pub async fn new(cfg: &Config) -> anyhow::Result<Self>;
    
    pub async fn encode(&self, text: &str) -> anyhow::Result<([f32;32], [f32;32])> {
        // returns (sem, unc)
        let emb = self.embedder.embed(text).await?;
        let sem = self.w.project(&emb);
        let unc = estimate_unc(&emb, &sem);
        Ok((sem, unc))
    }
}

// unc estimation: for each dim i, unc[i] = 1.0 - confidence
// confidence proxy: how far sem[i] is from 0.5 (more extreme = more confident)
fn estimate_unc(emb: &[f32], sem: &[f32; 32]) -> [f32; 32] {
    let mut unc = [0f32; 32];
    for i in 0..32 {
        let distance_from_center = (sem[i] - 0.5).abs() * 2.0; // 0..1
        unc[i] = 1.0 - distance_from_center;
        unc[i] = unc[i].clamp(0.0, 1.0);
    }
    unc
}
```

**src/projection/batch.rs** — batch queue:

```rust
pub struct BatchQueue {
    tx: tokio::sync::mpsc::Sender<BatchItem>,
}

struct BatchItem {
    text:    String,
    resp_tx: tokio::sync::oneshot::Sender<anyhow::Result<([f32;32],[f32;32])>>,
}

impl BatchQueue {
    pub fn new(engine: Arc<Engine>, window_ms: u64, max_size: usize) -> Self;
    pub async fn encode(&self, text: String) -> anyhow::Result<([f32;32],[f32;32])>;
}
```

The worker loop:
- Collects items for `window_ms` milliseconds OR until `max_size` items
- Processes all in one batch (calls engine.encode for each — BLAS parallelizes internally)
- Sends results back via oneshot channels

### src/store/mod.rs

Trait + two implementations (memory and redis):

```rust
#[async_trait::async_trait]
pub trait Store: Send + Sync {
    async fn add(&self, agent_id: &str, record: CogonRecord) -> anyhow::Result<()>;
    async fn recall(&self, agent_id: &str, query: &[f32;32], query_unc: &[f32;32], k: usize)
        -> anyhow::Result<Vec<(CogonRecord, f32)>>;
    async fn get_session_delta(&self, session_id: &str, since: i64)
        -> anyhow::Result<Vec<CogonRecord>>;
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct CogonRecord {
    pub cogon_id: String,
    pub sem:      [f32; 32],
    pub unc:      [f32; 32],
    pub stamp:    i64,
    pub text_raw: Option<String>,
}
```

`MemoryStore`: uses `Arc<tokio::sync::RwLock<HashMap<String, Vec<CogonRecord>>>>`.
`recall()` computes DIST for all records and returns top-K.

DIST formula (from spec):
```
dist(c1, c2) = cosine_distance weighted by (1 - unc)
weight[i] = (1 - c1.unc[i]) * (1 - c2.unc[i])
weighted_dot = sum(c1.sem[i] * c2.sem[i] * weight[i])
weighted_norm1 = sqrt(sum(c1.sem[i]^2 * weight[i]))
weighted_norm2 = sqrt(sum(c2.sem[i]^2 * weight[i]))
similarity = weighted_dot / (weighted_norm1 * weighted_norm2 + 1e-8)
dist = 1.0 - similarity
```

`RedisStore`: stores CogonRecords as JSON under key `leet:store:{agent_id}` as a Redis list.
`recall()` loads all records, computes DIST in memory, returns top-K.

`build(cfg)` returns `Box<dyn Store>`:
- "memory" → MemoryStore
- starts with "redis://" → RedisStore
- starts with "sqlite://" → MemoryStore (sqlite planned, fallback for now with log warning)

### src/server/mod.rs

```rust
use tonic::{transport::Server, Request, Response, Status};
use crate::proto::leet_service_server::{LeetService, LeetServiceServer};

pub async fn run(cfg: Config, proj: Engine, store: Box<dyn Store>) -> anyhow::Result<()> {
    let addr = format!("0.0.0.0:{}", cfg.port).parse()?;
    let svc  = LeetServiceImpl::new(cfg, Arc::new(proj), store);
    
    tracing::info!("listening on {}", addr);
    Server::builder()
        .add_service(LeetServiceServer::new(svc))
        .serve(addr)
        .await?;
    Ok(())
}
```

`LeetServiceImpl` implements all 6 RPC methods:

**Encode**: call batch_queue.encode(text), build EncodeResponse with cogon_id (new UUID),
sem, unc, stamp (now nanoseconds), tokens_saved estimate (text.len() * 4 / 5 as rough proxy).
Also call store.add(agent_id, record) if agent_id non-empty.

**Decode**: reconstruct text from sem[32] by mapping each axis back to a human label.
Simple implementation: build a description string like
"[sys:0.8 state:0.3 process:0.7 ...]" using the 32 axis names.
Axis names in order (0–31):
via, correspondencia, vibracao, polaridade, ritmo, causa_efeito, genero,
sistema, estado, processo, relacao, sinal, estabilidade, valencia_ontologica,
verificabilidade, temporalidade, completude, causalidade, reversibilidade,
carga, origem, valencia_epistemica,
urgencia, impacto, acao, valor, anomalia, afeto, dependencia,
vetor_temporal, natureza, valencia_acao

**EncodeBatch**: streaming — for each incoming EncodeRequest, encode and stream back EncodeResponse.

**Delta**: compute element-wise difference sem_curr[i] - sem_prev[i] for each of 32 dims.
magnitude = euclidean norm of patch.

**Recall**: call store.recall(agent_id, sem, unc, k), return CogonRecord list with dist scores.

**Health**: return status="ok", backend from config, uptime in seconds.

### Token savings estimation

In Encode, compute `tokens_saved` as:
- text token estimate = text.len() / 4 (rough GPT tokenization proxy)
- cogon token estimate = 32 * 2 / 100  (32 floats, ~2 decimal digits each, packed)
- tokens_saved = max(0, text_tokens - cogon_tokens) as i64

### Dockerfile

```dockerfile
FROM rust:1.75-alpine AS builder
RUN apk add --no-cache musl-dev openblas-dev protobuf-dev
WORKDIR /app
COPY . .
RUN cargo build --release -p leet-service

FROM alpine:latest
RUN apk add --no-cache openblas libgcc
COPY --from=builder /app/target/release/leet-service /usr/local/bin/
EXPOSE 50051
CMD ["leet-service"]
```

### tests/integration_test.rs

Write integration tests that:
1. Start the service in a test tokio runtime
2. Create a gRPC client
3. Test Encode with a sample text, verify sem has 32 elements all in [0,1]
4. Test EncodeBatch with 5 messages
5. Test Delta between two different Encode results
6. Test Health returns "ok"
7. Test Recall after adding 3 cogons, verify returns ≤ k results

## Build and verify

After generating all files:

```bash
cargo build -p leet-service
cargo test -p leet-service
```

Fix any compilation errors. The service must compile clean and all tests must pass.

Then run a smoke test:
```bash
cargo run -p leet-service &
sleep 2
# if grpcurl available:
# grpcurl -plaintext localhost:50051 leet.LeetService/Health
echo "leet-service smoke test: check port 50051 is listening"
lsof -i :50051 | head -5
kill %1
```
