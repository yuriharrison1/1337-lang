# Deployment — 1337

## Overview

1337 can be deployed in three ways:

| Mode | Components | Use case |
|------|-----------|----------|
| **Standalone CLI** | `leet` + `LEET_API_KEY` | Personal use, scripts |
| **Local server** | `leet-server` + `leet-agent` × N | Dev/staging, local network |
| **Production (systemd)** | `leet-service.service` + `leet-agent@.service` | Linux servers |

---

## Build for Production

```bash
cargo build --release -p leet-cli -p leet-service

# Generated binaries:
ls -la target/release/leet target/release/leet-server target/release/leet-agent
```

---

## Local Server Mode (Development)

```bash
# Terminal 1: start server
./target/release/leet-server --tcp 127.0.0.1:1337

# Terminal 2: connect agents
for agent in ATLAS RAVEN TENSOR PULSE FORGE; do
    LEET_API_KEY=$LEET_API_KEY \
    ./target/release/leet-agent --name "$agent" --llm anthropic &
done

# Terminal 3: chat
LEET_API_KEY=$LEET_API_KEY ./target/release/leet chat --connect 127.0.0.1:1337
```

---

## systemd Deployment (Production)

### Prerequisites

- Linux with systemd
- Rust toolchain (for building)
- `sudo` privileges

### Automated Setup

```bash
sudo bash deploy/systemd/setup.sh
```

The script:
1. Creates the `leet` user (no shell, no home)
2. Creates directories: `/etc/leet/`, `/etc/leet/agents/`, `/var/log/leet/`
3. Generates role files for each agent in `/etc/leet/agents/<NAME>.role`
4. Creates `/etc/leet/env` (environment file — edit to add `LEET_API_KEY`)
5. Builds with `cargo build --release`
6. Copies binaries to `/usr/local/bin/`
7. Installs and enables `leet-service.service`

### Configure the API Key

```bash
sudo nano /etc/leet/env
```

Add:
```bash
LEET_API_KEY=sk-ant-...
LEET_MODEL=claude-haiku-4-5-20251001
RUST_LOG=info
```

```bash
sudo chmod 600 /etc/leet/env
sudo chown leet:leet /etc/leet/env
```

### Manage the Service

```bash
# Start server
sudo systemctl start leet-service
sudo systemctl status leet-service

# Start agents individually
sudo systemctl start leet-agent@ATLAS
sudo systemctl start leet-agent@RAVEN
sudo systemctl start leet-agent@TENSOR

# Start all 15 agents
for a in ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM; do
    sudo systemctl start leet-agent@$a
done

# Enable at boot
sudo systemctl enable leet-service
sudo systemctl enable leet-agent@ATLAS

# Reload config (without restart)
sudo systemctl reload leet-service

# Stop everything
sudo systemctl stop 'leet-agent@*'
sudo systemctl stop leet-service
```

### Logs

```bash
# Server logs
journalctl -u leet-service -f

# Specific agent
journalctl -u leet-agent@ATLAS -f

# All agents
journalctl -u 'leet-agent@*' -f
```

### Teardown

```bash
sudo bash deploy/systemd/teardown.sh
```

Removes units, stops services, and optionally removes binaries.

---

## Unit File: `leet-service.service`

```ini
[Unit]
Description=1337 Translation Service — Semantic Substrate
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/leet-server --tcp 0.0.0.0:1337 --unix /run/leet/leet.sock
Restart=on-failure
RestartSec=5

Environment=RUST_LOG=info
EnvironmentFile=-/etc/leet/env   # optional, does not fail if missing

RuntimeDirectory=leet            # systemd creates /run/leet automatically
User=leet
Group=leet
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict

[Install]
WantedBy=multi-user.target
```

## Unit File: `leet-agent@.service`

`%i` is substituted with the agent name at instantiation (`leet-agent@ATLAS.service` → `%i=ATLAS`).

```ini
[Unit]
Description=1337 Agent — %i
After=leet-service.service
Requires=leet-service.service
PartOf=leet-service.service

[Service]
Type=simple
ExecStart=/usr/local/bin/leet-agent \
    --name %i \
    --role-file /etc/leet/agents/%i.role \
    --server /run/leet/leet.sock \
    --llm anthropic
Restart=on-failure
RestartSec=10

EnvironmentFile=-/etc/leet/env
User=leet
Group=leet

[Install]
WantedBy=leet-service.service
```

---

## Monitoring

### Health check

```bash
leet health --url 127.0.0.1:1337
```

### Server metrics

The server exposes metrics via structured logs. With `RUST_LOG=info`:

```
[INFO] agent ATLAS connected (id=abc123, total=1)
[INFO] message routed: ATLAS → broadcast (12 agents)
[INFO] metrics: total_msgs=1024, agents_peak=15, nl_tokens=8432
```

### Quick check script

```bash
#!/bin/bash
echo "=== leet-service ==="
systemctl is-active leet-service

echo "=== Connected agents ==="
journalctl -u leet-service --since "5 min ago" | grep "connected" | wc -l

echo "=== Health ==="
leet health --url 127.0.0.1:1337 2>/dev/null || echo "not reachable"
```

---

## Security

### systemd Isolation

The units use:
- `User=leet` — dedicated non-root process
- `NoNewPrivileges=true` — prevents privilege escalation
- `PrivateTmp=true` — isolated `/tmp`
- `ProtectSystem=strict` — read-only filesystem
- `ReadWritePaths=/run/leet /var/log/leet` — only what is needed

### The `LEET_API_KEY`

- Stored in `/etc/leet/env` with permission `600` (leet-only)
- Never logged by the server
- Never committed — add `/etc/leet/env` to `.gitignore`

### Firewall

`leet-server` listens on `0.0.0.0:1337` by default. In production, restrict access:

```bash
# Localhost only
leet-server --tcp 127.0.0.1:1337

# Or via firewall
sudo ufw allow from 10.0.0.0/8 to any port 1337
sudo ufw deny 1337
```
