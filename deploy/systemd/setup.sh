#!/usr/bin/env bash
# setup.sh — Install and enable 1337 systemd services
#
# Usage: sudo bash setup.sh
# Requires: systemd ≥ 255, cargo installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== 1337 Service Setup ==="
echo "Repository: ${REPO_ROOT}"

# ── Create system user ─────────────────────────────────────────────────────────
if ! id -u leet &>/dev/null; then
    echo "[1/6] Creating system user 'leet'..."
    sudo useradd --system --shell /sbin/nologin --no-create-home leet
else
    echo "[1/6] User 'leet' already exists."
fi

# ── Create directories ─────────────────────────────────────────────────────────
echo "[2/6] Creating directories..."
sudo mkdir -p /etc/leet/agents /var/log/leet
sudo chown -R leet:leet /etc/leet /var/log/leet
sudo chmod 750 /etc/leet /var/log/leet

# ── Write agent role files ─────────────────────────────────────────────────────
echo "[3/6] Writing agent role files..."
declare -A AGENTS=(
    [ATLAS]="Strategic planner & system architect"
    [CIPHER]="Security, cryptography, trust verification"
    [FORGE]="Builder, implementer, code generator"
    [NEXUS]="Network topology, agent connections"
    [ORACLE]="Prediction, foresight, trend analysis"
    [PULSE]="Real-time monitoring, health checks"
    [RAVEN]="Intelligence, deep research, knowledge retrieval"
    [SPARK]="Creative ideation, unconventional solutions"
    [TENSOR]="Mathematics, ML, numerical computation"
    [VORTEX]="Data processing, ETL, transformation pipelines"
    [ZERO]="Core systems, runtime, kernel-level ops"
    [FLUX]="State management, synchronization, cache"
    [ECHO]="Communication protocol, message relay"
    [DRIFT]="Anomaly detection, pattern deviation"
    [PRISM]="Multi-perspective analysis, bias detection"
)

for agent in "${!AGENTS[@]}"; do
    echo "${AGENTS[$agent]}" | sudo tee "/etc/leet/agents/${agent}.role" > /dev/null
done
sudo chown -R leet:leet /etc/leet/agents

# ── Create env file (if not exists) ──────────────────────────────────────────
if [ ! -f /etc/leet/env ]; then
    echo "[4a] Creating /etc/leet/env (edit to add LEET_API_KEY)..."
    sudo tee /etc/leet/env > /dev/null <<'ENVEOF'
# 1337 Service Environment
# Set your API key here:
# LEET_API_KEY=sk-ant-...
RUST_LOG=info
ENVEOF
    sudo chmod 600 /etc/leet/env
    sudo chown leet:leet /etc/leet/env
    echo "    !! Edit /etc/leet/env and add LEET_API_KEY before starting agents"
fi

# ── Build and install binaries ────────────────────────────────────────────────
echo "[4/6] Building release binaries..."
cd "${REPO_ROOT}"
cargo build --release -p leet-service -p leet-cli 2>&1

echo "[5/6] Installing binaries to /usr/local/bin..."
sudo cp target/release/leet-server /usr/local/bin/leet-server
sudo cp target/release/leet-agent  /usr/local/bin/leet-agent
sudo cp target/release/leet        /usr/local/bin/leet 2>/dev/null || true
sudo chmod 755 /usr/local/bin/leet-server /usr/local/bin/leet-agent

# ── Install and enable systemd units ─────────────────────────────────────────
echo "[6/6] Installing systemd unit files..."
sudo cp "${SCRIPT_DIR}/leet-service.service" /etc/systemd/system/
sudo cp "${SCRIPT_DIR}/leet-agent@.service"  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leet-service

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start the service:"
echo "  sudo systemctl start leet-service"
echo ""
echo "Start all 15 agents:"
echo "  for a in ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM; do"
echo "    sudo systemctl start leet-agent@\$a"
echo "  done"
echo ""
echo "Or enable agents to auto-start with the service:"
echo "  for a in ATLAS CIPHER FORGE NEXUS ORACLE; do"
echo "    sudo systemctl enable leet-agent@\$a"
echo "  done"
echo ""
echo "Connect from CLI:"
echo "  leet chat --connect 127.0.0.1:1337 --lang pt"
