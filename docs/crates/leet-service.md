# leet-service

Rust gRPC/TCP service that exposes COGON operations over the network. Centralizes projection and storage for distributed agents.

## Architecture

```
Agents → gRPC (port 50051) → LeetServiceImpl
                                   ├── Engine (projection via W matrix)
                                   ├── Store  (memory | sqlite)
                                   └── BatchQueue (batch encode)
```

## Binaries

```bash
# gRPC server
cargo run --bin leet-server

# Agent client (standalone mode)
cargo run --bin leet-agent
```

## Configuration

All options via environment variables:

| Variable | Default | Description |
|----------|--------|-----------|
| `LEET_PORT` | `50051` | gRPC port |
| `LEET_STORE` | `memory` | Storage backend (`memory` or `sqlite`) |
| `LEET_SQLITE_PATH` | `.leet_store.db` | SQLite database path |
| `LEET_LOG` | `info` | Log level |
| `LEET_W_PATH` | — | Path to the W matrix (see leet-bridge) |

```bash
LEET_STORE=sqlite LEET_SQLITE_PATH=/data/leet.db ./leet-server
```

## gRPC API

Proto: `leet.proto` (included via `tonic::include_proto!("leet")`).

### `Encode`

Projects text into a COGON and persists it to the store.

```protobuf
rpc Encode(EncodeRequest) returns (EncodeResponse);

message EncodeRequest {
    string text     = 1;
    string agent_id = 2;
}

message EncodeResponse {
    string  cogon_id      = 1;
    repeated float sem    = 2;  // 32 values
    int64   stamp         = 3;  // Unix ms
    int64   tokens_saved  = 4;  // estimated tokens saved
}
```

### `EncodeBatch`

Bidirectional streaming — send multiple texts, receive COGONs as they become ready.

```protobuf
rpc EncodeBatch(stream EncodeRequest) returns (stream EncodeResponse);
```

### `Decode`

Reconstructs text from a sem vector.

```protobuf
rpc Decode(DecodeRequest) returns (DecodeResponse);

message DecodeRequest {
    repeated float sem = 1;
    string lang        = 2;  // "pt" | "en"
}
```

### `Delta`

Computes the difference between two sem vectors. Returns the patch and magnitude normalized by `√32 → [0, 1]`.

```protobuf
rpc Delta(DeltaRequest) returns (DeltaResponse);

message DeltaResponse {
    repeated float patch = 1;
    float magnitude      = 2;  // [0, 1]
}
```

### `Recall`

Semantic search in the agent's store — returns the k nearest COGONs.

```protobuf
rpc Recall(RecallRequest) returns (RecallResponse);

message RecallRequest {
    string agent_id    = 1;
    repeated float sem = 2;
    int32  k           = 3;
}
```

### `Health`

Service status.

```protobuf
rpc Health(HealthRequest) returns (HealthResponse);

message HealthResponse {
    string status  = 1;  // "ok"
    string backend = 2;  // "memory" | "sqlite"
    int64  uptime  = 3;  // seconds
}
```

## Store

### Memory Store

In-memory store — the default, with no persistence across restarts. Ideal for development and testing.

### SQLite Store

On-disk persistence. Each agent has its own table of COGONs indexed by `(agent_id, cogon_id, stamp)`.

```bash
LEET_STORE=sqlite leet-server
```

## BatchQueue

Internal queue for processing multiple encodes efficiently. Configured automatically by `LeetServiceImpl`.

## Modules

| Module | Responsibility |
|--------|------------------|
| `server` | Implementation of the `LeetService` trait (tonic) |
| `tcp_server` | Raw TCP wrapper (alternative to gRPC) |
| `projection` | Projection engine — wraps leet-bridge |
| `store` | `Store` trait + memory and sqlite backends |
| `batch` | `BatchQueue` for batch encoding |
| `config` | Reads environment variables |
| `agent_client` | gRPC client for connecting agents to the service |

## Checking Status

```bash
leet health                           # localhost:50051
leet health --url 192.168.1.10:50051  # remote host
```

## Tests

```bash
cargo test -p leet-service   # 22 tests
```
