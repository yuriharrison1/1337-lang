# Production Deployment

## Prerequisites

- Linux system with systemd
- Compiled Rust (`cargo build --workspace --release`)
- Python 3.11+ for the Python services
- (Optional) SQLite for persistence

## Binaries

```bash
# Compile in release mode
cargo build --workspace --release

# Binaries produced:
# target/release/leet          — CLI / MCP backend
# target/release/leet-server   — gRPC service
# target/release/leet-agent    — standalone agent client
```

## Configuration via Environment Variables

| Variable | Default | Description |
|----------|--------|-----------|
| `LEET_PORT` | `50051` | gRPC port for leet-server |
| `LEET_STORE` | `memory` | Storage backend: `memory` or `sqlite` |
| `LEET_SQLITE_PATH` | `.leet_store.db` | SQLite database path |
| `LEET_LOG` | `info` | Log level (`debug`, `info`, `warn`, `error`) |
| `LEET_W_PATH` | — | Path to the calibrated W matrix (`W.bin`) |
| `LEET_API_KEY` | — | API key for `leet chat` mode |

## Systemd — leet-server

Unit file: `/etc/systemd/system/leet-server.service`

```ini
[Unit]
Description=1337 leet-service gRPC server
After=network.target

[Service]
Type=simple
User=leet
WorkingDirectory=/opt/leet
ExecStart=/opt/leet/leet-server
Environment=LEET_PORT=50051
Environment=LEET_STORE=sqlite
Environment=LEET_SQLITE_PATH=/var/lib/leet/store.db
Environment=LEET_LOG=info
Environment=LEET_W_PATH=/opt/leet/W.bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Install
sudo cp target/release/leet-server /opt/leet/
sudo useradd -r -s /sbin/nologin leet
sudo mkdir -p /var/lib/leet && sudo chown leet:leet /var/lib/leet

# Enable
sudo systemctl daemon-reload
sudo systemctl enable leet-server
sudo systemctl start leet-server
sudo systemctl status leet-server
```

## Systemd — MCP Server (Claude Code)

Unit file: `/etc/systemd/system/leet-mcp.service`

```ini
[Unit]
Description=1337 MCP server for Claude Code
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/1337
ExecStart=/usr/bin/python3 mcp/leet_mcp.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Health Check

```bash
# Via CLI
./target/release/leet health
./target/release/leet health --url 192.168.1.10:50051

# Via systemd
sudo systemctl status leet-server
sudo journalctl -u leet-server -f   # real-time logs
```

## SQLite vs Memory

| | Memory | SQLite |
|-|--------|--------|
| Persistence | Restart wipes data | Persists across restarts |
| Performance | Faster | Slightly slower |
| Use case | Dev, testing | Production |
| Configuration | `LEET_STORE=memory` | `LEET_STORE=sqlite` |

## W Matrix in Production

For high-quality semantic projection, provide the calibrated W matrix:

```bash
# Copy W.bin to the server
scp calibration/data/W.bin servidor:/opt/leet/W.bin

# Configure in systemd
Environment=LEET_W_PATH=/opt/leet/W.bin
```

Without `W.bin`, leet-bridge uses the `MockProjector` with keyword heuristics. See [Calibration](calibration.md) to generate a custom W matrix.

## Multiple Agents

Each agent identifies itself with a unique `agent_id`. Store namespacing is done by `agent_id`:

```bash
# Agent 1
LEET_API_KEY=... ./target/release/leet-agent --id "agente-prod-1" --server localhost:50051

# Agent 2
LEET_API_KEY=... ./target/release/leet-agent --id "agente-prod-2" --server localhost:50051
```

## Logs

```bash
# Level of detail
LEET_LOG=debug leet-server    # includes every projection operation
LEET_LOG=warn  leet-server    # warnings and errors only

# With journald
sudo journalctl -u leet-server --since "1 hour ago"
```

## Security

- leet-service has no native authentication — use a firewall or SSH tunneling to restrict access
- `LEET_API_KEY` should not be committed — use systemd environment variables or a secrets manager
- SQLite database permissions: `chmod 600 /var/lib/leet/store.db`
