# Claude Code / MCP

1337 exposes its semantic operations as MCP tools for Claude Code, enabling COGON-first communication within development sessions.

## How It Works

The MCP server (`mcp/leet_mcp.py`) invokes the `leet` binary (leet-cli) and exposes 5 tools:

| Tool | Description |
|------|-----------|
| `encode(text)` | Projects text → active axes + values |
| `dist(text_a, text_b)` | Cosine distance; skip re-send if < 0.05 |
| `blend(text_a, text_b, alpha)` | Interpolates two semantic contexts |
| `axes()` | Reference for the 32 canonical axes |
| `inspect(cogon_json)` | Decodes a COGON JSON → top-10 axes |

## Configuration

The MCP is already configured in `.claude/settings.json`. When you open the project in Claude Code, the server is activated automatically.

### Prerequisite

The `leet` binary must be built:

```bash
cargo build --release -p leet-cli
# target/release/leet — the MCP detects it automatically (release before debug)
```

### Manual Verification

```bash
python3 mcp/leet_mcp.py
# The server should start without errors
```

## `/leet` Skill

The `/leet` skill activates COGON-first communication mode for the session:

```
/leet
/leet <specific task>
```

In leet mode, Claude:
- Uses `encode()` for semantic fingerprinting of context
- Checks `dist()` before re-sending information (token savings)
- Displays compact summaries `⟨G8=0.95 P3=0.90⟩` instead of long text
- Uses `blend()` for context fusion between turns

## Using the Tools in Claude Code

### `encode`

```
encode("deploy urgente falhou em produção")
→ G8_URGENCY 0.95 | P3_ANOMALY 0.90 | D1_STATE 0.85 | P7_ACTION 0.80
```

Use it to:
- Compress long context blocks (~90% token reduction)
- Fingerprint concepts for future comparison via `dist()`
- Generate summary tokens `⟨G8=0.95 P3=0.90⟩`

### `dist`

```
dist("deploy falhou", "falha no deploy")
→ 0.04 — semantically equivalent
```

Rule: if `dist < 0.05`, the receiver already has this information — skip re-sending.

### `blend`

```
blend("sistema estável", "alerta crítico", alpha=0.3)
→ merged COGON: 30% stable, 70% critical
```

Use it for gradual context transitions between conversation turns.

### `axes`

```
axes()
→ Full list of the 32 axes with code, name, and description
```

Use it when you need to map an `⟨…⟩` token back to human-readable meaning.

### `inspect`

```
inspect('{"id":"...","sem":[0.9,0.0,...]}')
→ Top-10 axes with values and interpretation
```

Use it to decode COGON payloads received from other agents.

## COGON Communication Protocol

Within a session with `/leet` active:

```
[turn 1]
  Agent A: encode("long context here")
  → ⟨G8=0.72 D2=0.68 P7=0.61⟩

[turn 2]
  Agent B: dist("previous context", "new info")
  → 0.03 < 0.05 → skip, information already present
  → continue with delta only

[turn 3]
  blend(previous_state, new_state, alpha=0.6)
  → context updated smoothly
```

## Token Savings

Estimated reduction:

| Method | Original tokens | COGON tokens | Reduction |
|--------|-----------------|--------------|---------|
| `encode()` | ~200 (context block) | ~32 (vector) | ~84% |
| `dist()` + skip | ~200 | 0 (skip) | ~100% |
| `⟨…⟩` notation | ~50 (description) | ~10 (compact) | ~80% |

## Troubleshooting

**MCP does not appear in Claude Code:**
- Check `.claude/settings.json` for the `leet-1337` server entry
- Run `/hooks` in Claude Code to reload configuration
- Confirm that `target/release/leet` exists

**Tool returns `ERROR: leet binary not found`:**
```bash
cargo build --release -p leet-cli
```

**Tool returns `ERROR: leet timed out`:**
- Default timeout: 10 seconds
- Check whether `LEET_W_PATH` is set correctly if using an external W matrix
