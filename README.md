# 1337 — Inter-Agent Communication Language

[![CI](https://github.com/leetlang/leet/actions/workflows/ci.yml/badge.svg)](https://github.com/leetlang/leet/actions/workflows/ci.yml)
[![crates.io](https://img.shields.io/crates/v/leet-core.svg)](https://crates.io/crates/leet-core)
[![docs.rs](https://docs.rs/leet-core/badge.svg)](https://docs.rs/leet-core)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**1337** é um protocolo semântico para comunicação entre agentes de IA. Em vez de trocar texto livre, agentes codificam seu estado, intenção e conteúdo em vetores semânticos de 32 dimensões chamados **COGONs** — alcançando até 90% de redução de tokens sem perda de informação estrutural.

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

## Estrutura do Projeto

```
1337/
├── leet-core/          # Tipos COGON, eixos, protocolo, validação (Rust)
├── leet-bridge/        # NL→COGON via heurísticas + W matrix (Rust)
├── leet-service/       # Serviço TCP/gRPC + armazenamento (Rust)
├── leet-cli/           # Ferramentas de linha de comando (Rust)
├── python/             # SDK Python puro (leet1337)
├── leet-vm/            # VM de orquestração de agentes (Python)
├── leet-py/            # SDK público para integrações (Python)
├── mcp/                # Servidor MCP para Claude Code
├── calibration/        # Pipeline de calibração da W matrix
├── deploy/             # Scripts systemd
└── docs/               # Documentação completa
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [Arquitetura](docs/ARCHITECTURE.md) | Visão geral do sistema, diagrama de componentes, fluxo de dados |
| [COGON](docs/COGON.md) | Tipo de dado central, 32 eixos canônicos, operadores semânticos |
| [Protocolo MSG_1337](docs/PROTOCOL.md) | Estrutura da mensagem, regras R1–R23, handshake C5 |
| [leet-core](docs/crates/leet-core.md) | Tipos, validação, operadores, codec binário |
| [leet-bridge](docs/crates/leet-bridge.md) | Tradução NL↔COGON, W matrix, cliente Anthropic |
| [leet-service](docs/crates/leet-service.md) | Servidor TCP, cliente de agente, storage |
| [leet-cli](docs/crates/leet-cli.md) | Todos os comandos CLI com exemplos |
| [SDK Python](docs/python/leet-sdk.md) | Tipos, operadores, bridge, cache, validação |
| [leet-vm](docs/python/leet-vm.md) | VM de orquestração, pipeline de processamento |
| [leet-py](docs/python/leet-py.md) | SDK público, LeetClient, providers, @agent |
| [Primeiros Passos](docs/guides/getting-started.md) | Instalação, configuração, exemplos básicos |
| [Claude Code / MCP](docs/guides/mcp-claude-code.md) | Integração com Claude Code, skill /leet |
| [Deploy](docs/guides/deployment.md) | Produção com systemd, variáveis de ambiente |
| [Calibração](docs/guides/calibration.md) | Treino da W matrix |

## Versão

**v0.5.1** — especificação com 32 eixos canônicos, W matrix calibrada, protocolo C5.

## Licença

Apache 2.0 — veja [LICENSE](LICENSE).
