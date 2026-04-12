# 1337 Architecture

## Overview

1337 is a semantic language protocol built around 32-dimensional vectors called **COGONs**. The goal is to enable LLM agents to communicate efficiently — compressing long messages into compact vectors and recovering semantic meaning when needed.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application / User                           │
│        Python scripts, LLM agents, automation                  │
└────────────────┬───────────────────────────────┬───────────────┘
                 │ Python SDK                    │ CLI
    ┌────────────▼─────────────┐    ┌────────────▼──────────────┐
    │  python/leet  (core SDK) │    │  leet  (CLI — 13 commands)│
    │  leet-py (public SDK)    │    │  leet chat / encode / etc │
    └────────────┬─────────────┘    └────────────┬──────────────┘
                 │                               │
    ┌────────────▼───────────────────────────────▼──────────────┐
    │               leet-bridge  (Rust)                         │
    │  nl_to_cogon()  cogon_to_nl()  infer_intent()             │
    │  AnthropicClient  →  Claude API  →  15 agents             │
    └────────────────────────────┬──────────────────────────────┘
                                 │
    ┌────────────────────────────▼──────────────────────────────┐
    │                leet-core  (Rust)                          │
    │  Cogon  Dag  Msg1337  Edge  Intent                        │
    │  blend  delta  dist  focus  anomaly_score                 │
    │  encode_cogon  decode_cogon  (96B binary)                 │
    │  validate  (R1–R21)                                        │
    └────────────────────────────┬──────────────────────────────┘
                                 │
    ┌────────────────────────────▼──────────────────────────────┐
    │              leet-service  (Rust daemon)                  │
    │  leet-server  TCP :1337 + Unix /run/leet/leet.sock        │
    │  leet-agent   15 independent processes                    │
    │  C5 handshake  PROBE→ECHO→ALIGN→VERIFY                   │
    │  routing:  broadcast + direct delivery                    │
    └───────────────────────────────────────────────────────────┘
```

---

## Components

### leet-core

Pure Rust library with fundamental types and operators. No network or I/O dependencies.

**Responsibilities:**
- Define `Cogon`, `Dag`, `Msg1337`, `Edge`, `Intent` types
- Implement 5 semantic operators: `blend`, `delta`, `dist`, `focus`, `anomaly_score`
- 96-byte binary codec (4-5× compression vs JSON)
- Message validation (rules R1–R21)
- C5 protocol: anchor COGONs and `align_hash` computation

**Version:** 0.4.0

---

### leet-bridge

Rust translation layer between natural language and COGON.

**Responsibilities:**
- `nl_to_cogon(text, lang)` — NL → semantic vector via ~80 keyword heuristic rules (PT + EN)
- `cogon_to_nl(cogon, lang)` — NL reconstruction from most active axes
- `infer_intent(text)` — classifies intent: QUERY / ANOMALY / SYNC / DELTA / ASSERT
- `AnthropicClient` — sends COGON to Claude API, receives responses from 15 agents
- Embedded system prompt with full v0.5.1 spec (32 axes, 15 agents, JSON format)

**Version:** 0.5.0

---

### leet-cli

`leet` binary with 13 subcommands for interactive use and scripting.

**Responsibilities:**
- Diagnostic tools: `encode`, `decode`, `inspect`, `axes`, `zero`
- Semantic operations: `dist`, `blend`
- Validation and benchmarking: `validate`, `bench`
- Multi-agent chat: `leet chat` (direct API mode or `--connect` to a server)
- Service health check: `health`

**Version:** 0.5.0

---

### leet-service

Network daemon hosting 15 autonomous agents and routing messages between them.

**Components:**
- `leet-server` — TCP/Unix server with C5 handshake, mpsc routing, metrics
- `leet-agent` — autonomous process that connects to the server, processes COGONs, and responds via LLM

**Wire protocol:** Newline-delimited JSON over TCP or Unix socket  
**Version:** 0.5.1

---

### Python SDK (python/leet and leet-py)

Two Python packages with different abstraction levels:

| Package | Purpose | Audience |
|---------|---------|----------|
| `python/leet` | Full core SDK with gRPC/ZMQ/WebSocket clients, IDE adapters, cache | Developers |
| `leet-py` | Simplified public SDK: `leet.connect()`, `@agent`, `AgentNetwork` | End users |

---

## Data Flow — `leet chat`

```
User types text
       │
       ▼
nl_to_cogon(text)      → Cogon { sem[32], unc[32] }
       │
       ▼
AnthropicClient.send_cogon(cogon, history, max_agents)
       │  INPUT_COGON + SELECT_AGENTS: N
       ▼
Claude API (Haiku by default)
       │  JSON array of N AgentResponse objects
       ▼
parse_agent_responses()
       │
       ├─ AgentResponse { agent, cogon, intent, nl_pt, nl_en }
       ├─ AgentResponse { ... }
       └─ ...
       │
       ▼
Colored terminal (crossterm)
  RAVEN  "response text"
  TENSOR "response text"
  ...
  latency: Xms | Y tok/s | N agents
```

---

## Data Flow — `leet-server` + `leet-agent`

```
leet-server starts
       │ bind TCP :1337 + Unix /run/leet/leet.sock
       ▼
leet-agent --name ATLAS connects
       │
       ├─ PROBE  →  Register { name: "ATLAS", role: "..." }
       ├─ ECHO   ←  Registered { agent_id, anchors: [5 COGONs] }
       ├─ ALIGN  →  Align { hash: SHA256("1337:v0.5.1:ATLAS") }
       └─ VERIFY ←  Ready
       │
       ▼  (15 agents connected)
User sends message via leet chat --connect 127.0.0.1:1337
       │
       ▼
leet-server.route(sender_id, msg)
       ├─ broadcast(exclude=sender) → all agents
       └─ deliver_to(target_id)     → specific agent
       │
       ▼
leet-agent receives Msg, processes via LLM, responds to server
```

---

## Binary Codec (96 bytes)

Each COGON can be serialized to exactly 96 bytes — 4-5× compression vs JSON.

```
Offset  Bytes  Field
──────  ─────  ─────────────────────────────────────
0       2      magic: 0x1337
2       1      version: 0x02
3       1      flags
4       32     sem[32] quantized: f32[0,1] → u8[0,255]
36      32     unc[32] quantized: f32[0,1] → u8[0,255]
68      16     UUID (id) — 16 raw bytes
84      8      stamp (i64 little-endian, nanoseconds)
92      4      CRC32 of payload (bytes 0-91)
──────  ─────
96      TOTAL
```

---

## Validation Rules (R1–R21)

Rules applied by `validate()` to every `Msg1337`:

| Group | Rules | What is checked |
|-------|-------|----------------|
| Structure | R1–R5 | non-zero sender, valid intent, non-negative stamp, sem/unc in [0,1] |
| Semantics | R6–R10 | unc[i] < 1.0 always, P3/P7 non-zero when required, valence coherence |
| Relations | R11–R15 | edge weights in [0,1], no trivial DAG cycles, valid EdgeType |
| Protocol | R16–R21 | COGON_ZERO only for handshake, ref_hash present when needed |

---

## Component Dependencies

```
leet-cli
  └── leet-bridge
  │     └── leet-core
  └── leet-service (for AgentClient in --connect mode)
        └── leet-bridge
              └── leet-core
```

No circular dependencies. `leet-core` only depends on `uuid`, `serde`, `sha2`.
