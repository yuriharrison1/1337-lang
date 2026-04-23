#!/bin/bash
# demo_auto.sh — Demo automático sem interação

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Verificar chave
if [ -z "${LEET_API_KEY:-}" ]; then
    echo -e "${YELLOW}LEET_API_KEY não encontrada. Usando mock.${NC}"
    BACKEND="mock"
else
    echo -e "${GREEN}✅ LEET_API_KEY encontrada${NC}"
    BACKEND="anthropic"
fi

# Setup Python
echo -e "${BLUE}🔧 Setup Python...${NC}"
for pkg_dir in python leet-py; do
    if [[ -f "$REPO_ROOT/$pkg_dir/pyproject.toml" ]]; then
        pip install -e "$REPO_ROOT/$pkg_dir" --quiet 2>/dev/null
    fi
done

echo -e "${BLUE}🚀 Iniciando REDE 1337 com $BACKEND${NC}"
echo ""

timeout 90 python net1337.py --scenario devops --backend "$BACKEND" << 'EOF' || true
/status
/inject Alerta CRÍTICO: Serviço de autenticação 503. Todos logins falhando desde 14h.
/agents chat
/heatmap all
/export demo_$(date +%s).json
/quit
EOF

echo ""
echo -e "${GREEN}✅ Demo finalizada!${NC}"
ls -la demo_*.json 2>/dev/null || echo "Nenhum log gerado"
