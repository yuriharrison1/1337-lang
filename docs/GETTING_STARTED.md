# Getting Started with 1337

## Prerequisites

| Scenario | Requirements |
|----------|-------------|
| Python SDK only | Python 3.10+ |
| CLI + chat | Rust 1.75+, `LEET_API_KEY` |
| Distributed mode | Rust 1.75+, `LEET_API_KEY`, Linux + systemd |

---

## Installation

### Rust CLI (recommended to start)

```bash
git clone <repo>
cd 1337
cargo build --release -p leet-cli
```

Add to PATH:
```bash
export PATH="$PWD/target/release:$PATH"
```

Verify:
```bash
leet version
# leet 0.5.0 | spec v0.5.1
```

### Python SDK

```bash
cd 1337
pip install -e python/       # core SDK
pip install -e leet-py/      # simplified public SDK
```

---

## 5 Minutes with the CLI

### 1. Project text into a COGON

```bash
leet encode "critical system failure detected"
```

You will see colored bars representing each of the 32 semantic axes. The most active axes will be anomaly (P3), urgency (G8), and action (P7).

### 2. Inspect active axes

```bash
leet encode "critical system" | leet inspect
```

### 3. Measure semantic distance

```bash
leet dist "stable system" "critical system"
# 0.782 — semantically distant

leet dist "failure" "error"
# 0.143 — semantically close
```

### 4. Blend two concepts

```bash
leet blend "urgent" "routine" --alpha 0.7
# COGON that is 70% "urgent", 30% "routine"
```

### 5. List all axes

```bash
leet axes
# Table with all 32 canonical axes, groups, and descriptions
```

### 6. COGON_ZERO

```bash
leet zero
# Prints the identity COGON — initial protocol handshake
```

---

## First Multi-Agent Chat

### 1. Set up your API key

```bash
# Using pass
export LEET_API_KEY=$(pass show anthropic/my-key | tr -d '[:space:]')

# Or directly
export LEET_API_KEY=sk-ant-...
```

### 2. Start the chat

```bash
leet chat
```

You will see the welcome banner and the `YURI ›` prompt. Type anything in English or Portuguese.

### 3. Example session

```
 Connecting to Anthropic... OK
 COGON_ZERO transmitted ✓
────────────────────────────────────────────

 YURI › what is the status of our authentication system?

  ↳ ~9 tokens | 48B NL | 256B COGON | 5.3x NL size

  PULSE  "All auth endpoints responding within SLA. Zero 5xx errors in the last 2h."
  RAVEN  "No anomalies in login patterns. Success rate: 99.7%."
  CIPHER "No brute-force attempts detected. TLS certificates valid for 89 more days."

  latency: 2.8s | ~52 tok/s | 3 agents responded

────────────────────────────────────────────
```

---

## Python SDK — First Steps

### Basic types

```python
from leet import Cogon, blend, dist

# COGON_ZERO
zero = Cogon.zero()
print(zero.sem[:4])  # [1.0, 1.0, 1.0, 1.0]
print(zero.unc[:4])  # [0.0, 0.0, 0.0, 0.0]

# Create COGON manually
import uuid, time
cogon = Cogon(
    id=str(uuid.uuid4()),
    sem=[0.5] * 32,
    unc=[0.1] * 32,
    stamp=int(time.time() * 1e9),
)
```

### Operators

```python
from leet import blend, delta, dist, focus, anomaly_score

a = Cogon(id=str(uuid.uuid4()), sem=[0.2]*32, unc=[0.1]*32, stamp=0)
b = Cogon(id=str(uuid.uuid4()), sem=[0.8]*32, unc=[0.1]*32, stamp=0)

print(dist(a, b))            # cosine distance
print(blend(a, b, 0.5).sem)  # midpoint
```

### leet-py (simplified SDK)

```python
import sys
sys.path.insert(0, "leet-py")
import leet

# Mock (no API key required, for development)
client = leet.connect("mock")
result = client.encode("critical system")
print(result.sem[26])  # P3_ANOMALIA

# Anthropic (reads LEET_PROJECTION_ANTHROPIC_API_KEY)
client = leet.connect("anthropic")
```

---

## Distributed Mode — Quick Start

```bash
# Terminal 1: server
cargo build --release -p leet-service
./target/release/leet-server

# Terminal 2: 3 agents
for a in ATLAS RAVEN PULSE; do
    LEET_API_KEY=$LEET_API_KEY \
    ./target/release/leet-agent --name $a --llm anthropic &
done

# Terminal 3: chat via server
leet chat --connect 127.0.0.1:1337
```

---

## Next Steps

- [USER_GUIDE.md](USER_GUIDE.md) — all CLI commands with examples
- [PROTOCOL.md](PROTOCOL.md) — 32 axes specification and C5 handshake
- [API_REFERENCE.md](API_REFERENCE.md) — full Rust and Python API
- [DEPLOYMENT.md](DEPLOYMENT.md) — production deployment with systemd
