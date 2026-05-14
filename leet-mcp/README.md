# leet-mcp

[![crates.io](https://img.shields.io/crates/v/leet-mcp.svg)](https://crates.io/crates/leet-mcp)
[![docs.rs](https://docs.rs/leet-mcp/badge.svg)](https://docs.rs/leet-mcp)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](../LICENSE)

Model Context Protocol server exposing 1337 tools to Claude Code, Cursor, and VS Code.

## Tools

| Tool | Description |
|---|---|
| `leet_recall` | Tiered semantic recall from project memory store (foundation + mid + raw) |
| `leet_remember` | Compress text → COGON and append to `.leet/store.bin` |
| `leet_encode` | Text → sem[32] vector (no persist) |
| `leet_decode` | sem[32] → dominant-axis narrative |
| `leet_dist` | Cosine distance weighted by P6_CONFIDENCE |
| `leet_recall_delta` | Patch vector since last recall cursor |

## Setup

```bash
cargo install leet-cli   # also installs leet-mcp binary
leet setup claude-code   # or: cursor / vscode
```

This writes the MCP server configuration into your IDE's settings file. The server
is spawned automatically as a subprocess (stdio JSON-RPC) when the IDE starts.

## Environment

| Variable | Description |
|---|---|
| `LEET_PROJECT_ROOT` | Project root (set automatically by Claude Code via workspace) |
| `LEET_W_PATH` | Override W.bin path for NL projection |
| `RUST_LOG` | Tracing filter (e.g. `leet_mcp=debug`) — output goes to stderr |

## Storage

Project memory lives in `.leet/store.bin` (append-only binary) and `.leet/index.bin`
(sidecar index for tiered recall). Both are git-ignored by default.

## License

Apache-2.0. Part of the [1337 project](https://github.com/leetlang/leet).
