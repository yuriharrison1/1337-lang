# PROMPT 12-P-01 — CARGO METADATA + README POR CRATE

Completar os campos necessários para `cargo publish` em todos os crates, criar README.md por crate (exibido no crates.io), e garantir que o root README.md está pronto para o GitHub.

**PRÉ-REQUISITOS**: Fases 12-T, 12-U, 12-W executadas. `cargo publish --dry-run` verde em todos os crates.

**ESCOPO**: Edits em `Cargo.toml` de cada crate + criação de `README.md` por crate (5 arquivos novos) + revisão do root `README.md`. Zero mudanças de código.

**Taskwarrior**: `+prompt12_P_01`.

---

## CAMPOS FALTANDO POR CRATE

Todos os crates herdam `version`, `edition`, `rust-version`, `authors`, `license`, `repository`, `homepage`, `keywords`, `categories` do workspace. Faltam:

| Campo | Workspace | Por crate |
|---|---|---|
| `documentation` | — | Adicionar: `"https://docs.rs/<crate-name>"` |
| `readme` | — | Adicionar: `"README.md"` |
| `exclude` | — | Adicionar list de artefatos de dev |

### `leet-core/Cargo.toml`

```toml
[package]
# ...existing...
documentation = "https://docs.rs/leet-core"
readme = "README.md"
exclude = ["tests/fixtures/*", "benches/*"]
```

### `leet-bridge/Cargo.toml`

```toml
[package]
# ...existing...
documentation = "https://docs.rs/leet-bridge"
readme = "README.md"
exclude = ["calibration/data/*", "tests/fixtures/*"]
```

### `leet-mcp/Cargo.toml`

```toml
[package]
# ...existing...
documentation = "https://docs.rs/leet-mcp"
readme = "README.md"
```

### `leet-cli/Cargo.toml`

```toml
[package]
# ...existing...
documentation = "https://docs.rs/leet-cli"
readme = "README.md"
```

### `leet-service/Cargo.toml`

```toml
[package]
# ...existing...
documentation = "https://docs.rs/leet-service"
readme = "README.md"
```

---

## README.md POR CRATE

Cada crate precisa de um README.md mínimo que funcione no crates.io e no GitHub como subdir. Modelo abaixo — adaptar a descrição de cada crate.

### `leet-core/README.md`

```markdown
# leet-core

Core types and algebra for the **1337 semantic protocol** — the inter-agent
communication language for AI systems.

## What's in here

- `Cogon` — the 32-axis semantic vector type (`sem: [f32; 32]`)
- `SemVec` — type alias for `[f32; 32]`
- Axis definitions: 32 canonical axes across 4 blocks (S/D/G/P)
- Algebra: `blend`, `dist`, `cogon_zero`
- Protocol validation: R1–R25 structural rules
- `UserFacingError` — typed errors for CLI/MCP boundaries

## Usage

```toml
[dependencies]
leet-core = "0.5"
```

```rust
use leet_core::{Cogon, blend, dist};
```

## License

Apache-2.0. See [LICENSE](../LICENSE).
```

### `leet-bridge/README.md`

```markdown
# leet-bridge

NL↔1337 bridge layer: projects natural language into COGON semantic vectors.

## What's in here

- `project_text_simple(text)` — NL → `Cogon` (no API key needed, hash-trigram)
- `WMatrix` — calibrated projection matrix (W.bin); load, project, save
- `default_user_w_path()` — where `leet calibrate --download` installs W.bin
- `EmbeddingProvider` trait — plug in OpenAI, sentence-transformers, etc.
- `MockProjector` — deterministic projector for tests

## Features

- `keyword-fallback` — fall back to heuristic rules when W.bin is missing

## Usage

```toml
[dependencies]
leet-bridge = { version = "0.5", features = ["keyword-fallback"] }
```

## License

Apache-2.0.
```

### `leet-mcp/README.md`

```markdown
# leet-mcp

Model Context Protocol server exposing 1337 tools to Claude Code, Cursor,
and VS Code via MCP.

## Tools exposed

| Tool | Description |
|---|---|
| `leet_recall` | Tiered semantic recall from project memory store |
| `leet_remember` | Compress text → COGON and append to store |
| `leet_encode` | Text → sem[32] vector (no persist) |
| `leet_decode` | sem[32] → dominant-axis narrative |
| `leet_dist` | Cosine distance weighted by P6_CONFIDENCE |
| `leet_recall_delta` | Patch vector since last recall cursor |

## Setup

```bash
cargo install leet-cli   # installs leet-mcp binary alongside leet
leet setup claude-code   # or: cursor / vscode
```

## Protocol

stdio JSON-RPC 2.0 (spawned as subprocess by the IDE).

## License

Apache-2.0.
```

### `leet-cli/README.md`

```markdown
# leet-cli

Command-line tools for the 1337 semantic protocol.

## Install

```bash
cargo install leet-cli
```

## Quick start

```bash
# Check setup
leet doctor

# Encode text to a COGON
leet encode "Decided to use Postgres for session store"

# List the 32 canonical axes
leet axes

# Set up IDE integration
leet setup claude-code
```

## Commands

| Command | Description |
|---|---|
| `leet doctor` | System health check |
| `leet setup` | Configure IDE integrations |
| `leet calibrate` | Download / manage W matrix |
| `leet encode` | Project text to sem[32] |
| `leet decode` | Interpret sem[32] as narrative |
| `leet dist` | Distance between two COGONs |
| `leet blend` | Blend two COGONs |
| `leet axes` | List 32 canonical axes |
| `leet zero` | Print COGON_ZERO |
| `leet inspect` | Storage statistics |
| `leet absorb` | Import session history |
| `leet consolidate` | Manage consolidation pyramid |
| `leet help` | Categorized command overview |

Run `leet <command> --help` for details.

## License

Apache-2.0.
```

### `leet-service/README.md`

```markdown
# leet-service

gRPC + TCP service for the 1337 semantic protocol. Exposes batch COGON
operations and an agent engine over the network.

## Usage

```bash
cargo install leet-service
leet-server --port 1337
```

## License

Apache-2.0.
```

---

## ROOT README.md

Verificar se existe. Se não, criar. Se existe, garantir que tem:

1. Badge CI: `[![CI](https://github.com/leetlang/leet/actions/workflows/ci.yml/badge.svg)](https://github.com/leetlang/leet/actions/workflows/ci.yml)`
2. Badge crates.io: `[![crates.io](https://img.shields.io/crates/v/leet-core.svg)](https://crates.io/crates/leet-core)`
3. Quick install + quick start
4. Link para `leetlang.org`
5. Link para docs.rs

Estrutura mínima do root README.md:

```markdown
# 1337 — Semantic Communication Protocol for AI Agents

[![CI](https://github.com/leetlang/leet/actions/workflows/ci.yml/badge.svg)](https://github.com/leetlang/leet/actions/workflows/ci.yml)
[![crates.io](https://img.shields.io/crates/v/leet-core.svg)](https://crates.io/crates/leet-core)
[![docs.rs](https://docs.rs/leet-core/badge.svg)](https://docs.rs/leet-core)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

1337 encodes natural language into 32-axis semantic vectors (COGONs) and
provides a persistent memory layer for AI coding agents. Claude Code,
Cursor, and VS Code access it via MCP — no API keys required for basic use.

## Install

```bash
cargo install leet-cli
leet setup claude-code   # or: cursor / vscode
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

## License

Apache-2.0 — see [LICENSE](LICENSE).
```

---

## GATES

```bash
# Todos os dry-runs passam
for crate in leet-core leet-bridge leet-mcp leet-cli leet-service; do
  cargo publish --dry-run -p $crate 2>&1 | tail -1
done
# Esperado: cada termina com "Finished" ou "ok"

# README.md existe em cada crate
for crate in leet-core leet-bridge leet-mcp leet-cli leet-service; do
  test -f $crate/README.md && echo "OK: $crate" || echo "MISSING: $crate"
done
# Esperado: "OK:" para todos

# documentation field presente
for crate in leet-core leet-bridge leet-mcp leet-cli; do
  grep -q "documentation" $crate/Cargo.toml && echo "OK: $crate" || echo "MISSING: $crate"
done
# Esperado: "OK:" para todos

# Build ainda verde
cargo build --workspace
# Esperado: 0 errors, 0 warnings
```
