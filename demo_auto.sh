#!/bin/bash
# Demo automático - executa imediatamente

set -e
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar chave
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}DEEPSEEK_API_KEY não encontrada. Usando mock.${NC}"
    BACKEND="mock"
else
    echo -e "${GREEN}✅ DEEPSEEK_API_KEY encontrada${NC}"
    BACKEND="deepseek"
fi

# Setup rápido
echo -e "${BLUE}🔧 Setup rápido...${NC}"
cd python && pip install -e ".[dev]" -q 2>/dev/null && cd ..
cd leet1337 && cargo build --release 2>&1 | tail -1 && cd ..

echo -e "${BLUE}🚀 Iniciando REDE 1337 com $BACKEND${NC}"
echo ""

# Executar net1337 com comandos pré-programados
timeout 90 python net1337.py --scenario devops --backend $BACKEND << 'EOF' || true
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
