#!/bin/bash
# run_demo.sh — Configura e inicia a rede 1337 com demo interativa

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   1337 v0.5.1 — Demo Interativa${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Verificar LEET_API_KEY (Anthropic/Claude)
if [ -z "${LEET_API_KEY:-}" ]; then
    echo -e "${YELLOW}⚠  LEET_API_KEY não encontrada. Usando backend mock.${NC}"
    BACKEND="mock"
else
    echo -e "${GREEN}✅ LEET_API_KEY encontrada${NC}"
    BACKEND="anthropic"
fi

# Setup Python
echo ""
echo -e "${BLUE}🐍 Instalando dependências Python...${NC}"
for pkg_dir in python leet-py; do
    if [[ -f "$REPO_ROOT/$pkg_dir/pyproject.toml" ]]; then
        pip install -e "$REPO_ROOT/$pkg_dir" --quiet
        echo -e "  ✓ $pkg_dir instalado"
    fi
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 INICIANDO REDE 1337${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Backend: $BACKEND"
echo "Cenário: devops (3 agentes)"
echo ""
echo "Comandos disponíveis:"
echo "  /status        - Ver estado dos agentes"
echo "  /inject <msg>  - Enviar mensagem para todos"
echo "  /talk 1 <msg>  - Falar com agente específico"
echo "  /agents chat   - Agentes conversam entre si"
echo "  /heatmap all   - Ver heatmap dos eixos"
echo "  /quit          - Sair"
echo ""
echo -e "${YELLOW}💡 Pressione ENTER para iniciar ou Ctrl+C para cancelar${NC}"
read

python net1337.py --scenario devops --backend "$BACKEND" << 'PYTHON_EOF'
/status
/inject O serviço de autenticação está retornando 503. Todos os logins estão falhando.
/agents chat 2
/status
/heatmap all
/export demo_log.json
/quit
PYTHON_EOF

echo ""
echo -e "${GREEN}✅ Demo finalizada!${NC}"
echo "Log exportado para: demo_log.json"
