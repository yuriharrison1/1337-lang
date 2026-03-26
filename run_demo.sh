#!/bin/bash
# Script completo: configura, testa e inicia a rede 1337 com DeepSeek

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   1337 v0.4 - Setup e Demo Automático${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Verificar DEEPSEEK_API_KEY
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  DEEPSEEK_API_KEY não encontrada. Usando backend mock.${NC}"
    BACKEND="mock"
else
    echo -e "${GREEN}✅ DEEPSEEK_API_KEY encontrada${NC}"
    BACKEND="deepseek"
fi

echo ""
echo -e "${BLUE}📦 Passo 1: Instalando pacote Python...${NC}"
cd python
pip install -e ".[dev]" -q
python -c "import leet; print(f'✅ leet {leet.__version__} instalado')"

echo ""
echo -e "${BLUE}🦀 Passo 2: Compilando Rust (FFI)...${NC}"
cd ../leet1337
cargo build --release 2>&1 | tail -3
if [ -f target/release/libleet_core.so ] || [ -f target/release/libleet_core.dylib ]; then
    echo -e "${GREEN}✅ Biblioteca Rust compilada${NC}"
else
    echo -e "${YELLOW}⚠️ Compilação Rust pode ter falhado${NC}"
fi

echo ""
echo -e "${BLUE}🧪 Passo 3: Rodando testes...${NC}"
cd ../python

# Testes rápidos
python -m pytest tests/test_types.py tests/test_operators.py -q --tb=line 2>&1 | tail -5

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

cd ..

# Iniciar net1337 com comandos pré-programados
python net1337.py --scenario devops --backend $BACKEND << 'PYTHON_EOF'
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
