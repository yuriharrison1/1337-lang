#!/usr/bin/env bash
# teardown.sh — Stop and disable all 1337 systemd services
set -euo pipefail

AGENTS=(ATLAS CIPHER FORGE NEXUS ORACLE PULSE RAVEN SPARK TENSOR VORTEX ZERO FLUX ECHO DRIFT PRISM)

echo "=== 1337 Service Teardown ==="

echo "Stopping and disabling agents..."
for a in "${AGENTS[@]}"; do
    sudo systemctl stop    "leet-agent@${a}" 2>/dev/null || true
    sudo systemctl disable "leet-agent@${a}" 2>/dev/null || true
done

echo "Stopping and disabling leet-service..."
sudo systemctl stop    leet-service 2>/dev/null || true
sudo systemctl disable leet-service 2>/dev/null || true

echo "Removing unit files..."
sudo rm -f /etc/systemd/system/leet-service.service
sudo rm -f /etc/systemd/system/leet-agent@.service
sudo systemctl daemon-reload

echo "=== All 1337 services stopped and disabled ==="
echo "Binaries remain at /usr/local/bin/leet-server, /usr/local/bin/leet-agent, /usr/local/bin/leet"
echo "Config remains at /etc/leet/"
