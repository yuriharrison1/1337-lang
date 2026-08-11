# Getting Started

## Prerequisites

- Rust 1.75+ (`rustup update`)
- Python 3.11+
- `cargo` and `pip`

## 1. Clone and Build

```bash
git clone <repo>
cd 1337
cargo build --workspace --release
```

The main binary will be at `target/release/leet`.

## 2. Verify the Installation

```bash
./target/release/leet version
./target/release/leet axes    # lists the 32 canonical axes
```

## 3. First COGON

```bash
# Encode: text → semantic vector
./target/release/leet encode "deploy urgente falhou em produção"
```

Typical output:
```
G8  URGENCY          ████████████████████ 0.95
P3  ANOMALY          ███████████████████  0.90
D1  STATE            █████████████████    0.85
P7  ACTION           ████████████████     0.80
D2  PROCESS          ███████████████      0.75
...
```

## 4. Semantic Distance

```bash
./target/release/leet dist "urgente" "tranquilo"
# → 0.82 (very different)

./target/release/leet dist "deploy falhou" "falha no deploy"
# → 0.04 (semantically equivalent — skip re-send)
```

## 5. Context Blending

```bash
./target/release/leet blend "sistema estável" "alerta crítico" --alpha 0.3
# 30% stable, 70% critical
```

## 6. Python SDK

```bash
# Install dependencies
pip install -e python/
pip install -e leet-vm/
pip install -e leet-py/

# Test the import
python3 -c "import leet; print('OK')"
```

### Basic Usage

```python
import asyncio
import leet

async def main():
    # Mock mode (no API key required)
    client = leet.connect("mock")
    
    response = await client.chat("qual é o status?")
    print(response.text)
    print(f"Tokens saved: {response.tokens_saved}")

asyncio.run(main())
```

### With Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
client = leet.connect("anthropic")
response = await client.chat("resuma o contexto do projeto")
```

## 7. Test Suite

```bash
# Rust
cargo test --workspace

# Python
cd python && python -m pytest
cd ../leet-vm && python -m pytest
cd ../leet-py && python -m pytest

# Full audit (clippy + tests + PT names + CLI + Python)
bash test_all.sh
```

## 8. Verify the MCP Server

If you're using Claude Code, the MCP server is already configured via `.claude/settings.json`.

```bash
# Check that the server starts
python3 mcp/leet_mcp.py &

# In Claude Code, the tools will be available:
# encode(), dist(), blend(), axes(), inspect()
```

## Next Steps

- [COGON](../COGON.md) — understand the semantic vector and the 32 axes
- [leet-cli](../crates/leet-cli.md) — all subcommands
- [leet-py](../python/leet-py.md) — full Python SDK
- [Claude Code / MCP](mcp-claude-code.md) — integration with Claude Code
- [Deploy](deployment.md) — running in production with systemd
