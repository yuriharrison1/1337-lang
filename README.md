# 1337 — Inter-Agent Communication Language

[![CI](https://github.com/leetlang/leet/actions/workflows/ci.yml/badge.svg)](https://github.com/leetlang/leet/actions/workflows/ci.yml)
[![crates.io](https://img.shields.io/crates/v/leet-core.svg)](https://crates.io/crates/leet-core)
[![docs.rs](https://docs.rs/leet-core/badge.svg)](https://docs.rs/leet-core)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**1337** is a semantic protocol for communication between AI agents. Instead of exchanging free text, agents encode their state, intent, and content into 32-dimensional semantic vectors called **COGONs** — achieving up to 90% token reduction without loss of structural information.

```
"deploy urgente falhou em produção"
      ↓  encode
⟨G8=0.95 P3=0.90 D1=0.85 P7=0.80⟩
      ↓  decode
"critical production failure — immediate action required"
```

## Install

```bash
cargo install leet-cli
leet setup claude-code   # or: cursor / vscode
```

## Quick Start

```bash
# Health check
leet doctor

# Encode text to COGON
leet encode "deploy urgente falhou"

# Semantic distance
leet dist "urgente" "tranquilo"

# List all 32 axes
leet axes

# Full test suite (dev)
bash test_all.sh
```

## Architecture

| Crate | Role | Docs |
|---|---|---|
| [`leet-core`](leet-core/) | COGON types, 32-axis algebra, protocol rules | [docs.rs](https://docs.rs/leet-core) |
| [`leet-bridge`](leet-bridge/) | NL→COGON projection, W matrix, embedding providers | [docs.rs](https://docs.rs/leet-bridge) |
| [`leet-mcp`](leet-mcp/) | MCP server (stdio JSON-RPC) for IDE integration | [docs.rs](https://docs.rs/leet-mcp) |
| [`leet-cli`](leet-cli/) | `leet` binary — encode/decode/doctor/setup/… | [docs.rs](https://docs.rs/leet-cli) |
| [`leet-service`](leet-service/) | gRPC + TCP service for network deployments | [docs.rs](https://docs.rs/leet-service) |

## Documentation

- **Protocol spec**: [leetlang.org/spec](https://leetlang.org/spec)
- **API reference**: [docs.rs/leet-core](https://docs.rs/leet-core)
- **Getting started**: [leetlang.org/getting-started](https://leetlang.org/getting-started)

## Project Structure

```
1337/
├── leet-core/          # COGON types, axes, protocol, validation (Rust)
├── leet-bridge/        # NL→COGON via heuristics + W matrix (Rust)
├── leet-service/       # TCP/gRPC service + storage (Rust)
├── leet-cli/           # Command-line tools (Rust)
├── python/             # Pure Python SDK (leet1337)
├── leet-vm/            # Agent orchestration VM (Python)
├── leet-py/            # Public SDK for integrations (Python)
├── mcp/                # MCP server for Claude Code
├── calibration/        # W matrix calibration pipeline
├── deploy/             # systemd scripts
└── docs/               # Complete documentation
```

## Documentation

| Document | Content |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System overview, component diagram, data flow |
| [COGON](docs/COGON.md) | Core data type, 32 canonical axes, semantic operators |
| [MSG_1337 Protocol](docs/PROTOCOL.md) | Message structure, R1–R23 rules, C5 handshake |
| [leet-core](docs/crates/leet-core.md) | Types, validation, operators, binary codec |
| [leet-bridge](docs/crates/leet-bridge.md) | NL↔COGON translation, W matrix, Anthropic client |
| [leet-service](docs/crates/leet-service.md) | TCP server, agent client, storage |
| [leet-cli](docs/crates/leet-cli.md) | All CLI commands with examples |
| [Python SDK](docs/python/leet-sdk.md) | Types, operators, bridge, cache, validation |
| [leet-vm](docs/python/leet-vm.md) | Orchestration VM, processing pipeline |
| [leet-py](docs/python/leet-py.md) | Public SDK, LeetClient, providers, @agent |
| [Getting Started](docs/guides/getting-started.md) | Installation, configuration, basic examples |
| [Claude Code / MCP](docs/guides/mcp-claude-code.md) | Claude Code integration, /leet skill |
| [Deploy](docs/guides/deployment.md) | Production with systemd, environment variables |
| [Calibration](docs/guides/calibration.md) | Training the W matrix |

## Version

**v0.5.1** — specification with 32 canonical axes, calibrated W matrix, C5 protocol.

## License

Apache 2.0 — see [LICENSE](LICENSE).
