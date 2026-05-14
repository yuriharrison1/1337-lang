# leet-service

[![crates.io](https://img.shields.io/crates/v/leet-service.svg)](https://crates.io/crates/leet-service)
[![docs.rs](https://docs.rs/leet-service/badge.svg)](https://docs.rs/leet-service)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](../LICENSE)

gRPC + TCP service for the 1337 semantic protocol. Exposes batch COGON
operations and an agent engine over the network.

## Usage

```bash
cargo install leet-service
leet-server --port 1337
```

## What's here

- `LeetServiceImpl` — gRPC service implementation (tonic)
- `BatchQueue` — queued batch projection engine
- `AgentEngine` — multi-agent session management
- `projection::Engine` — text → sem[32] via leet-bridge

## Environment

| Variable | Description |
|---|---|
| `LEET_W_PATH` | Override W.bin path for calibrated projection |
| `LEET_API_KEY` | Anthropic API key (for Claude-backed agent engine) |

## License

Apache-2.0. Part of the [1337 project](https://github.com/leetlang/leet).
