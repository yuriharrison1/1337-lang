#!/bin/bash
# run_demo.sh — Sets up and starts the 1337 network with an interactive demo

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   1337 v0.5.1 — Interactive Demo${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Check LEET_API_KEY (Anthropic/Claude)
if [ -z "${LEET_API_KEY:-}" ]; then
    echo -e "${YELLOW}⚠  LEET_API_KEY not found. Using mock backend.${NC}"
    BACKEND="mock"
else
    echo -e "${GREEN}✅ LEET_API_KEY found${NC}"
    BACKEND="anthropic"
fi

# Setup Python
echo ""
echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
for pkg_dir in python leet-py; do
    if [[ -f "$REPO_ROOT/$pkg_dir/pyproject.toml" ]]; then
        pip install -e "$REPO_ROOT/$pkg_dir" --quiet
        echo -e "  ✓ $pkg_dir installed"
    fi
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 STARTING 1337 NETWORK${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Backend: $BACKEND"
echo "Scenario: devops (3 agents)"
echo ""
echo "Available commands:"
echo "  /status        - View agent state"
echo "  /inject <msg>  - Send a message to everyone"
echo "  /talk 1 <msg>  - Talk to a specific agent"
echo "  /agents chat   - Agents converse among themselves"
echo "  /heatmap all   - View axis heatmap"
echo "  /quit          - Exit"
echo ""
echo -e "${YELLOW}💡 Press ENTER to start or Ctrl+C to cancel${NC}"
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
echo -e "${GREEN}✅ Demo finished!${NC}"
echo "Log exported to: demo_log.json"
