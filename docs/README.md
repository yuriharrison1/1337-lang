# 1337 — Native Inter-Agent Communication Language

## What It Is

1337 is a communication protocol designed for AI agents. Instead of exchanging verbose natural language or JSON, 1337 agents encode each concept as a **COGON** — a 32-dimensional semantic vector with a companion uncertainty vector. This representation is compact, semantically precise, and computationally cheap.

The protocol solves a concrete problem: when two agents need to coordinate actions, sending the full text "the authentication system is down with maximum urgency, needs immediate rollback on the login service" is expensive in tokens and ambiguous. In 1337, that concept becomes 256 bytes with axes `G8_URGENCIA=0.95`, `P3_ANOMALIA=0.90`, `G4_REVERSIBILIDADE=0.90` already activated.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Application / User                        │
└────────────────┬────────────────────────┬──────────────────┘
                 │ Python SDK             │ CLI
    ┌────────────▼──────────┐  ┌──────────▼────────────────┐
    │  leet-py (public SDK) │  │  leet  (13 commands)      │
    │  python/leet (core)   │  │  encode decode chat ...   │
    └────────────┬──────────┘  └──────────┬────────────────┘
                 │                        │
    ┌────────────▼────────────────────────▼────────────────┐
    │                  leet-bridge (Rust)                  │
    │  nl_to_cogon  cogon_to_nl  AnthropicClient           │
    └────────────────────────┬─────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────┐
    │                  leet-core (Rust)                    │
    │  Cogon  Dag  Msg1337  blend  dist  delta  validate   │
    └────────────────────────┬─────────────────────────────┘
                             │
    ┌────────────────────────▼─────────────────────────────┐
    │               leet-service (Rust daemon)             │
    │  leet-server  TCP :1337 + Unix socket                │
    │  leet-agent   15 independent processes               │
    │  C5 handshake  PROBE→ECHO→ALIGN→VERIFY               │
    └──────────────────────────────────────────────────────┘
```

---

## Quick Start

### CLI (Rust)

```bash
cargo build --release -p leet-cli

# Project text into a COGON
./target/release/leet encode "critical system failure detected"

# Multi-agent chat with 15 AI agents
export LEET_API_KEY=sk-ant-...
./target/release/leet chat
```

### Python SDK

```python
import sys
sys.path.insert(0, "python")
from leet import Cogon, blend, dist

a = Cogon.zero()
print(a.sem[:4])  # [1.0, 1.0, 1.0, 1.0]
```

---

## Compression

| Format | Typical bytes |
|--------|--------------|
| Natural language text | ~400B |
| COGON JSON | ~480B |
| **Binary codec (96B)** | **96B — 4× smaller** |
| SparseDelta (n=4 axes) | 37B — 10× smaller |

---

## Tests

```bash
# Rust workspace
cargo test --workspace
# 97 tests: leet-core(30) + leet-bridge(16) + leet-cli(21) + leet-service(30)
```

---

## Documentation

| Document | Contents |
|----------|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | Full user guide — CLI, chat, distributed mode |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Component architecture and data flow |
| [PROTOCOL.md](PROTOCOL.md) | COGON v0.5.1 spec — 32 axes, C5 handshake |
| [API_REFERENCE.md](API_REFERENCE.md) | Full Rust and Python API reference |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment with systemd |

---

## Status

| Component | Tests | Version |
|-----------|-------|---------|
| leet-core (Rust) | 30 ✓ | 0.4.0 |
| leet-bridge (Rust) | 16 ✓ | 0.5.0 |
| leet-service (Rust) | 30 ✓ | 0.5.1 |
| leet-cli (Rust) | 21 ✓ | 0.5.0 |
| python/leet (core SDK) | — | 0.5.0 |
| leet-py (public SDK) | — | 0.5.0 |
