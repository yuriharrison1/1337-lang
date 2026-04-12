# User Guide — 1337

## What is 1337

1337 is a compressed semantic communication system between AI agents. Instead of exchanging long texts, agents encode meaning into 32-dimensional vectors called **COGONs** — 256 bytes per message, regardless of the original content size.

This guide covers:
1. [Installation and build](#1-installation)
2. [CLI — day-to-day commands](#2-cli)
3. [leet chat — multi-agent terminal](#3-leet-chat)
4. [leet-server and leet-agent — distributed mode](#4-distributed-mode)
5. [Configuration](#5-configuration)

---

## 1. Installation

### Requirements

- Rust 1.75+ (`rustup install stable`)
- `LEET_API_KEY` with an Anthropic key (only for `leet chat`)

### Build

```bash
git clone <repo>
cd 1337
cargo build --release
```

Binaries are in `target/release/`:

| Binary | Description |
|--------|-------------|
| `leet` | Main CLI with 13 commands |
| `leet-server` | Network daemon (TCP + Unix socket) |
| `leet-agent` | Autonomous agent process |

### Install globally (optional)

```bash
cargo install --path leet-cli
```

---

## 2. CLI

### `leet encode` — project text into a COGON

```bash
leet encode "critical system, failure detected"
```

Output: colored bars per axis showing `sem` and `unc` values.

```bash
# Save to file
leet encode "urgent" > cogon.json

# View full JSON
leet encode "urgent" | python3 -m json.tool
```

---

### `leet decode` — reconstruct text from a COGON

```bash
# From argument
leet decode '{"id":"...","sem":[...],"unc":[...],"stamp":0,"raw":null}'

# From file
leet encode "critical system" > cogon.json
leet decode < cogon.json

# Pipeline
leet encode "anomaly detected" | leet decode
```

---

### `leet inspect` — semantic interpretation

```bash
leet inspect '{"id":"...","sem":[...],...}'

# Shows the 6 most active axes with values
# Example output:
#  G8_URGENCIA    0.92  ████████████
#  P3_ANOMALIA    0.87  ███████████
#  P7_ACAO        0.81  ██████████
#  D6_VALENCIA    0.72  █████████
```

---

### `leet dist` — semantic distance

```bash
leet dist "stable system" "critical system"
# output: 0.782

leet dist "hello world" "hi there"
# output: 0.124  (semantically close)

leet dist "peace" "war"
# output: 1.431  (semantic opposites)
```

---

### `leet blend` — semantic blending

```bash
# Equal blend (default)
leet blend "urgent" "routine"

# 70% closer to "urgent"
leet blend "urgent" "routine" --alpha 0.7

# Output: intermediate COGON in semantic space
```

---

### `leet axes` — list all axes

```bash
leet axes
# Displays table with index, code, name, and description for all 32 axes
```

---

### `leet zero` — COGON_ZERO

```bash
leet zero
# Prints COGON_ZERO JSON (sem=[1.0;32], unc=[0.0;32])
# Used as the initial protocol handshake
```

---

### `leet validate` — validate MSG_1337

```bash
# From file
leet validate < msg.json

# From argument
leet validate '{"id":"...","sender":"...","payload":{...},...}'

# Validates against rules R1–R21
# Output: "valid" or error with the violated rule
```

---

### `leet bench` — performance benchmark

```bash
# 1000 projections (default)
leet bench

# 10,000 projections
leet bench --n 10000

# Example output:
#  10000 encodes in 142ms
#  70422 ops/s
#  14.2µs per operation
```

---

### `leet health` — check service

```bash
# Check localhost:50051 (gRPC, default)
leet health

# Check TCP server on port 1337
leet health --url 127.0.0.1:1337
```

---

### `leet version`

```bash
leet version
# leet 0.5.0 | spec v0.5.1 | commit abc1234
```

---

## 3. leet chat

`leet chat` is an interactive terminal that connects you to 15 specialized AI agents. You write in English or Portuguese, the text is converted to a COGON and sent to Claude, which responds as the most relevant agents.

### Requirements

```bash
# Export the key (use pass or set directly)
export LEET_API_KEY=$(pass show anthropic/my-key | tr -d '[:space:]')
```

### Start

```bash
leet chat
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--lang pt\|en` | `pt` | Language for agent responses |
| `--show-cogon` | off | Display COGON summary after each response |
| `--agents N` | `3` | Number of agents responding per round (1–6) |
| `--connect <addr>` | — | Connect to a `leet-server` instead of direct API |

### Examples

```bash
# Basic chat (haiku, 3 agents, PT)
leet chat

# With COGON visualization
leet chat --show-cogon

# English responses, 5 agents
leet chat --lang en --agents 5

# Use Sonnet for more elaborate responses
LEET_MODEL=claude-sonnet-4-6 leet chat

# Connected to local server
leet chat --connect 127.0.0.1:1337
```

### How it works

```
 Connecting to Anthropic... OK
 COGON_ZERO transmitted ✓
────────────────────────────────────────────

 YURI › what is the status of our system?

  ↳ ~7 tokens | 32B NL | 256B COGON | 8.0x NL size

  PULSE  "All services operational. p95 latency within SLA."
  RAVEN  "No anomalies detected in the last 24h. Patterns within expected range."
  ATLAS  "Infrastructure stable. Recommend weekly capacity review."

  latency: 2841ms | ~48 tok/s | 3 agents responded

────────────────────────────────────────────
```

### Session stats (every 5 rounds)

```
 ━━ SESSION STATS (round 5) ━━
  NL tokens: 45 | COGON bytes: 1280 | 2.1x compressed vs NL
  Avg latency: 2950ms | Rounds: 5
  Most active: RAVEN(5) > PULSE(4) > TENSOR(3) > ATLAS(3) > ORACLE(2)
```

### The 15 Agents

| Agent | Specialty |
|-------|-----------|
| **ATLAS** | Strategy, system architecture, long-term vision |
| **CIPHER** | Security, cryptography, trust verification |
| **FORGE** | Implementation, code generation, plan execution |
| **NEXUS** | Network topology, dependencies, agent connectivity |
| **ORACLE** | Forecasting, trend analysis, future state projection |
| **PULSE** | Real-time monitoring, health checks, SLA tracking |
| **RAVEN** | Deep research, knowledge retrieval, hidden patterns |
| **SPARK** | Creative ideation, unconventional solutions |
| **TENSOR** | Mathematics, ML, numerical computation, probabilities |
| **VORTEX** | Data processing, ETL, transformation pipelines |
| **ZERO** | Core systems, runtime, kernel-level operations |
| **FLUX** | State management, synchronization, cache |
| **ECHO** | Communication protocol, message routing |
| **DRIFT** | Anomaly detection, pattern deviation |
| **PRISM** | Multi-perspective analysis, bias detection |

### Commands during chat

| Input | Action |
|-------|--------|
| `exit` or `quit` | End the chat |
| `Ctrl+D` | End by EOF |
| any text | Sent as a message |

---

## 4. Distributed Mode

In distributed mode, `leet-server` hosts the network and `leet-agent` instances connect as independent processes.

### Start the server

```bash
# TCP on port 1337 + Unix socket
leet-server

# Custom port
leet-server --tcp 0.0.0.0:9000

# With detailed logging
leet-server --log-level debug
```

Expected output:
```
[INFO] leet-server v0.5.1 starting
[INFO] TCP listening on 0.0.0.0:1337
[INFO] Unix socket at /run/leet/leet.sock
```

### Connect an agent

```bash
# ATLAS agent with default role
leet-agent --name ATLAS

# Agent with custom role
leet-agent --name FORGE --role "Rust and embedded systems specialist"

# Role from file
leet-agent --name ORACLE --role-file /etc/leet/agents/ORACLE.role

# Custom server
leet-agent --name PULSE --server 192.168.1.10:1337

# With LLM (uses LEET_API_KEY)
leet-agent --name RAVEN --llm anthropic
```

### Connect all 15 agents

```bash
AGENTS="ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM"
for agent in $AGENTS; do
    leet-agent --name "$agent" --llm anthropic &
done
```

### Chat connected to server

```bash
# Uses the server with real agents instead of calling the API directly
leet chat --connect 127.0.0.1:1337
```

---

## 5. Configuration

### Minimal configuration

```bash
# Only for leet chat (direct mode)
export LEET_API_KEY=sk-ant-...
leet chat
```

### Environment file (recommended)

Create `~/.config/leet/env`:

```bash
# Anthropic key for 1337
LEET_API_KEY=sk-ant-...

# Default model (haiku is faster, sonnet is more precise)
LEET_MODEL=claude-haiku-4-5-20251001

# Log level for leet-service
LEET_LOG=info
```

Load with: `source ~/.config/leet/env`

### Available models

| Model | Speed | Quality | Recommended use |
|-------|-------|---------|----------------|
| `claude-haiku-4-5-20251001` | ~3s | good | Daily chat (default) |
| `claude-sonnet-4-6` | ~15s | excellent | Complex analyses |
| `claude-opus-4-6` | ~30s | maximum | Critical cases |

```bash
# Use Sonnet for a specific session
LEET_MODEL=claude-sonnet-4-6 leet chat --agents 2
```

### Using `pass` for the key

```bash
# Store
pass insert anthropic/leet-key

# Use
LEET_API_KEY=$(pass show anthropic/leet-key | tr -d '[:space:]') leet chat
```

### Useful aliases

```bash
# In ~/.bashrc or ~/.zshrc
alias leet-chat='LEET_API_KEY=$(pass show anthropic/leet-key | tr -d "[:space:]") leet chat'
alias leet-chat-sonnet='LEET_API_KEY=$(pass show anthropic/leet-key | tr -d "[:space:]") LEET_MODEL=claude-sonnet-4-6 leet chat'
```

---

## Deployment with systemd

For production environments, use the included unit files:

```bash
# Full setup (requires sudo)
sudo bash deploy/systemd/setup.sh

# Start the server
sudo systemctl start leet-service

# Start individual agents
sudo systemctl start leet-agent@ATLAS
sudo systemctl start leet-agent@RAVEN

# Enable at boot
sudo systemctl enable leet-service
sudo systemctl enable leet-agent@ATLAS

# Check status
systemctl status leet-service
journalctl -u leet-service -f

# Teardown
sudo bash deploy/systemd/teardown.sh
```

Set `LEET_API_KEY` in `/etc/leet/env`:

```bash
sudo nano /etc/leet/env
# Add:
# LEET_API_KEY=sk-ant-...
```

---

## Troubleshooting

### "LEET_API_KEY not set"

```bash
export LEET_API_KEY=$(pass show anthropic/my-key | tr -d '[:space:]')
```

**Note:** Always use `tr -d '[:space:]'` when retrieving from `pass` to strip the trailing newline.

### "API error 401: authentication_error"

The key may have an extra character. Verify:
```bash
pass show anthropic/my-key | wc -c
# should be 109 (108 chars + 1 newline)
```

### High latency (>10s)

Use the haiku model (default) and reduce agent count:
```bash
leet chat --agents 2
```

### Agent fails to connect to server

Check if the server is running:
```bash
leet health --url 127.0.0.1:1337
# or
nc -z 127.0.0.1 1337 && echo "ok"
```

The agent retries 5 times before giving up. Check logs:
```bash
RUST_LOG=debug leet-agent --name ATLAS
```
