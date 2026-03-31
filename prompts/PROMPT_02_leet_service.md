# PROMPT 02 — LEET-SERVICE (gRPC · Rust · Tokio · Batch · SIMD)

Build `leet-service` — the semantic compilation service for 1337.
It receives text, returns COGON vectors (sem[32] + unc[32]).
Stateless. Horizontally scalable. SIMD-accelerated.

**PREREQUISITE**: PROMPT_01 completed. `leet-core` and `leet-bridge` exist in workspace.

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## CONTEXT

The existing workspace has:
- `leet-core/` — Cogon{id,sem:[f32;32],unc:[f32;32],stamp,raw}, operators (FOCUS,DELTA,BLEND,DIST,ANOMALY_SCORE), validate R1-R21
- `leet-bridge/` — SemanticProjector trait, MockProjector

Add `leet-service` as new workspace member. Also create shared `proto/` directory.

---

## WHAT TO BUILD

### proto/leet.proto

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

message EncodeRequest  { string text=1; string agent_id=2; string session_id=3; }
message EncodeResponse { string cogon_id=1; repeated float sem=2; repeated float unc=3; int64 stamp=4; int64 tokens_saved=5; }
message DecodeRequest  { repeated float sem=1; repeated float unc=2; string lang=3; }
message DecodeResponse { string text=1; }
message DeltaRequest   { repeated float sem_prev=1; repeated float sem_curr=2; }
message DeltaResponse  { repeated float patch=1; float magnitude=2; }
message RecallRequest  { repeated float sem=1; repeated float unc=2; string agent_id=3; int32 k=4; }
message RecallResponse { repeated CogonRecord results=1; }
message CogonRecord    { string cogon_id=1; repeated float sem=2; repeated float unc=3; float dist=4; int64 stamp=5; }
message HealthRequest  {}
message HealthResponse { string status=1; string backend=2; int64 uptime=3; }
```

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
tonic = { version = "0.12", features = ["transport"] }
prost = "0.13"
tokio = { version = "1", features = ["full"] }
tokio-stream = "0.1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
uuid = { version = "1", features = ["v4"] }
ndarray = "0.16"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
dotenvy = "0.15"
anyhow = "1"
bytes = "1"

[build-dependencies]
tonic-build = "0.12"
```

### Files to create:

**build.rs** — tonic_build::compile_protos("../proto/leet.proto")

**src/config.rs** — Config struct loaded from env vars:
- LEET_PORT (default 50051)
- LEET_BACKEND (mock|w_matrix, default mock)
- LEET_STORE (memory|sqlite, default memory)
- LEET_W_MATRIX_PATH (path to W.bin, optional)
- LEET_BATCH_WINDOW_MS (default 10)
- LEET_BATCH_MAX_SIZE (default 32)

**src/projection.rs** — Engine struct:
- `Engine::new(config)` — loads W matrix if path given, else uses MockProjector
- `engine.encode(text) → (sem[32], unc[32])` — if W loaded: embedding * W → sem, heuristic → unc. If mock: keyword heuristics.
- `engine.decode(sem, unc, lang) → String` — reconstruct from top axes
- W matrix: `[f32; EMB_DIM * 32]` loaded from binary file. Projection: `sem = normalize(W @ embedding)`.

**src/store.rs** — PersonalStore trait + implementations:
- `MemoryStore` — HashMap<agent_id, Vec<(Cogon, i64)>>
- `SqliteStore` — SQLite with table: cogons(id, agent_id, sem BLOB, unc BLOB, stamp)
- `store.add(agent_id, cogon)`
- `store.recall(agent_id, query_sem, query_unc, k) → Vec<(Cogon, f32)>` — top-k by DIST
- Build function: `build_store(config) → Box<dyn Store>`

**src/batch.rs** — BatchQueue:
- Collects encode requests for up to `window_ms` milliseconds or `max_size` items
- Flushes as a batch to Engine
- Uses tokio::select! with timer
- Returns results to individual callers via oneshot channels

**src/accel.rs** — SIMD acceleration helpers:
- `simd_cosine_dist(a: &[f32;32], b: &[f32;32], weights: &[f32;32]) → f32`
- `simd_blend(a: &[f32;32], b: &[f32;32], alpha: f32) → [f32;32]`
- Use ndarray for matrix operations
- Feature-gate SIMD intrinsics behind cfg

**src/server.rs** — impl LeetService for LeetServer:
- Each RPC method validates input, calls Engine/Store, returns response
- EncodeBatch uses streaming
- Health returns uptime + backend type
- Logging via tracing

**src/main.rs** — Entry point:
- Load config from env
- Init tracing
- Build store + engine + batch queue
- Start tonic server
- Graceful shutdown on SIGTERM/SIGINT

**Dockerfile** — Multi-stage:
- Stage 1: rust:1.82 builder
- Stage 2: debian:bookworm-slim runtime
- Expose 50051
- ENTRYPOINT ["leet-service"]

### Tests (minimum 20):
- Config loading from env
- MockProjector encode/decode roundtrip
- MemoryStore add/recall
- BatchQueue flush behavior
- Server health endpoint
- Encode request validation
- Delta computation
- SIMD cosine dist matches naive impl
- SIMD blend matches naive impl
- Streaming EncodeBatch

---

## TASKWARRIOR + CONTRACT UPDATE

```bash
# Mark tasks done
task project:1337 +prompt02 status:pending done

# Update CONTRACT.md
sed -i 's/| leet-service (gRPC) | PROMPT_02 | `\[ \]` PENDENTE/| leet-service (gRPC) | PROMPT_02 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

# Commit
git add -A
git commit -m "feat(prompt-02): leet-service gRPC + batch + SIMD

- proto/leet.proto: Encode, Decode, EncodeBatch, Delta, Recall, Health
- Projection engine with W matrix support
- PersonalStore: memory + SQLite backends
- BatchQueue with time-window flushing
- SIMD-accelerated cosine distance and blend
- Dockerfile for deployment
- CONTRACT.md + Taskwarrior updated"

git push origin main
```

---

## VERIFICATION

```bash
cargo build -p leet-service
cargo test -p leet-service

# Start service
LEET_PORT=50051 LEET_BACKEND=mock LEET_STORE=memory cargo run -p leet-service &
sleep 2

# If grpcurl available:
# grpcurl -plaintext localhost:50051 leet.LeetService/Health

# Kill
kill %1

task project:1337 +prompt02 list
```

**END OF PROMPT_02**
