# leet-cli

Command-line toolkit for the 1337 protocol. Subcommands for encode, decode, semantic distance, blend, inspection, and multi-agent chat.

## Installation

```bash
cargo build --release -p leet-cli
# Binary at: target/release/leet
```

## Subcommands

### `encode`

Projects text into a COGON and displays the activated axes with visual bars.

```bash
leet encode "deploy urgente falhou em produção"
```

Output: list of axes with value > 0, with a proportional activation bar.

---

### `decode`

Reconstructs text from a COGON JSON.

```bash
# Pass JSON as an argument
leet decode '{"id":"...","sem":[...],"stamp":0}'

# Read from stdin
cat cogon.json | leet decode -
leet decode  # reads stdin if no argument is given
```

---

### `dist`

Semantic cosine distance between two texts. Returns a value in `[0, 2]`.

```bash
leet dist "urgente" "tranquilo"
leet dist "deploy falhou" "sistema em produção"
```

Interpretation:
- `< 0.05` → semantically equivalent information, skip re-send
- `0.0–0.3` → very close
- `0.3–0.7` → related
- `> 0.7` → different

---

### `blend`

Interpolates two semantic contexts.

```bash
leet blend "sistema estável" "alerta crítico" --alpha 0.7
# 70% "sistema estável", 30% "alerta crítico"

leet blend "texto A" "texto B"           # default alpha: 0.5
leet blend "texto A" "texto B" --alpha 0.3
```

---

### `axes`

Lists the 32 canonical axes with code, name, block, and description.

```bash
leet axes
```

---

### `zero`

Displays COGON_ZERO (the canonical initial state).

```bash
leet zero
```

---

### `validate`

Validates a MSG_1337 JSON against rules R1–R23.

```bash
leet validate '{"id":"...","sender":"...",...}'
cat msg.json | leet validate -
leet validate  # stdin
```

Returns exit code 0 if valid, 1 if invalid (with an error description).

---

### `inspect`

Interprets a COGON JSON — displays the top-10 activated axes with values.

```bash
leet inspect '{"id":"...","sem":[...]}'
cat cogon.json | leet inspect -
leet inspect  # stdin
```

---

### `bench`

Encode performance benchmark.

```bash
leet bench          # 1000 encodes (default)
leet bench -n 5000  # 5000 encodes
```

---

### `health`

Checks whether leet-service is reachable.

```bash
leet health                            # localhost:50051
leet health --url 192.168.1.10:50051   # remote host
```

---

### `version`

Displays the CLI and protocol version.

```bash
leet version
```

---

### `chat`

Interactive multi-agent chat. Requires `LEET_API_KEY` or `--connect`.

```bash
# Direct API mode (calls Anthropic)
export LEET_API_KEY=sk-ant-...
leet chat

# With options
leet chat --lang en --show-cogon --agents 4

# Connects to a running leet-server
leet chat --connect 127.0.0.1:1337
leet chat --connect /run/leet/leet.sock
```

Flags:

| Flag | Default | Description |
|------|--------|-----------|
| `--lang` | `pt` | Output language (`pt` or `en`) |
| `--show-cogon` | false | Displays an inline COGON summary with each message |
| `--agents` | `3` | Maximum agents per round (1–6) |
| `--connect` | — | TCP address or Unix socket of the leet-server |

---

## Reading from Stdin

The `decode`, `validate`, and `inspect` subcommands accept:
- JSON as a direct argument
- explicit `-` for stdin
- No argument → automatically reads stdin

```bash
echo '{"id":"..."}' | leet inspect
leet inspect - < cogon.json
```

## Environment Variables

| Variable | Use |
|----------|-----|
| `LEET_API_KEY` | Key for the direct-API `chat` mode |
| `LEET_W_PATH` | Path to the calibration W matrix |
