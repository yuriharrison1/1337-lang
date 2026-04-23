#!/bin/bash
# test_all.sh — Suite de testes completa do projeto 1337 v0.5.1

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

ok()   { echo -e "${GREEN}  ✓${NC} $*"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}  ✗${NC} $*"; FAIL=$((FAIL+1)); }
step() { echo ""; echo -e "${BLUE}▶ $*${NC}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════════"
echo "   🧪 TESTE COMPLETO — 1337 v0.5.1"
echo "═══════════════════════════════════════════════════════════════"

# ── 1. Rust: clippy ────────────────────────────────────────────────────────────
step "1. Clippy (-D warnings)"
if cargo clippy --workspace -- -D warnings 2>&1 | grep -q "^error"; then
    fail "clippy: erros encontrados"
else
    ok "clippy limpo"
fi

# ── 2. Rust: testes unitários ──────────────────────────────────────────────────
step "2. cargo test --workspace"
OUTPUT=$(cargo test --workspace --quiet 2>&1)
RESULTS=$(echo "$OUTPUT" | grep "test result:" || true)
FAILED=$(echo "$RESULTS" | grep -c "FAILED" || true)
PASSED_COUNT=$(echo "$RESULTS" | grep -oP '\d+ passed' | awk '{s+=$1} END{print s+0}')

if [[ "$FAILED" -gt 0 ]]; then
    fail "testes Rust: falhas detectadas"
    echo "$OUTPUT" | grep "FAILED" | sed 's/^/    /'
else
    ok "testes Rust: ${PASSED_COUNT} passaram"
fi

# ── 3. Versão consistente ──────────────────────────────────────────────────────
step "3. Versões de crate (deve ser 0.5.1 em todos)"
VERSION_MISMATCHES=$(cargo metadata --no-deps --format-version 1 2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
bad = [p['name'] + '=' + p['version'] for p in data['packages'] if p['version'] != '0.5.1']
print('\n'.join(bad))
" 2>/dev/null || true)

if [[ -z "$VERSION_MISMATCHES" ]]; then
    ok "todos os crates em v0.5.1"
else
    fail "versões divergentes: $VERSION_MISMATCHES"
fi

# ── 4. Zero nomes PT nos fontes Rust ──────────────────────────────────────────
step "4. Zero nomes PT em fontes .rs ativos"
PT_HITS=$(grep -rn \
    "ESSENCIA\|CORRESPONDENCIA\|VIBRACAO\|POLARIDADE\|RITMO\|ESTADO\|PROCESSO\|RELACAO\|SINAL\|ESTABILIDADE\|VALENCIA_ONT\|CAUSALIDADE\|VERIFICABILIDADE\|TEMPORALIDADE\|ANCORA_TEMPORAL\|COMPLETUDE\|REVERSIBILIDADE\|VALENCIA_EPIST\|URGENCIA\|IMPACTO\|ANOMALIA\|DEPENDENCIA\|VETOR_TEMPORAL\|CONFIANCA\|INTENCAO\|MASSA\|ENTROPIA\|COERENCIA\|GRADIENTE\|PROPAGACAO\|AFINIDADE\|DECAIMENTO\|INERCIA\|DENSIDADE\|TAXA_APRENDIZADO\|K_INTERACAO\|QUANTIZACAO\|RUIDO\|AFETO" \
    --include="*.rs" . 2>/dev/null | grep -v "target/" || true)

if [[ -z "$PT_HITS" ]]; then
    ok "zero nomes PT"
else
    fail "nomes PT encontrados:"
    echo "$PT_HITS" | head -10 | sed 's/^/    /'
fi

# ── 5. CLI smoke tests ─────────────────────────────────────────────────────────
step "5. CLI smoke tests"
LEET_BIN=""
if [[ -f "target/release/leet" ]]; then
    LEET_BIN="target/release/leet"
elif [[ -f "target/debug/leet" ]]; then
    LEET_BIN="target/debug/leet"
fi

if [[ -n "$LEET_BIN" ]]; then
    if $LEET_BIN version &>/dev/null; then
        ok "leet version"
    else
        fail "leet version falhou"
    fi

    if $LEET_BIN zero &>/dev/null; then
        ok "leet zero"
    else
        fail "leet zero falhou"
    fi

    if $LEET_BIN encode "urgente agora" &>/dev/null; then
        ok "leet encode"
    else
        fail "leet encode falhou"
    fi
else
    echo -e "  ${YELLOW}⚠  CLI não encontrado — rode 'cargo build -p leet-cli' primeiro${NC}"
fi

# ── 6. Python (opcional) ───────────────────────────────────────────────────────
step "6. Python (opcional)"
PYTHON_TESTED=false

for pkg_dir in python leet-py; do
    if [[ -d "$REPO_ROOT/$pkg_dir/tests" ]] && command -v python3 &>/dev/null; then
        if python3 -m pytest "$REPO_ROOT/$pkg_dir/tests" -q --tb=line 2>/dev/null; then
            ok "pytest $pkg_dir OK"
        else
            fail "pytest $pkg_dir falhou"
        fi
        PYTHON_TESTED=true
    fi
done

[[ "$PYTHON_TESTED" == "false" ]] && echo -e "  ${YELLOW}⚠  Python tests pulados (sem pytest ou sem tests/)${NC}"

# ── Resumo ─────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   📊 RESUMO"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Passou:  $PASS"
echo "  Falhou:  $FAIL"
echo ""

if [[ "$FAIL" -eq 0 ]]; then
    echo -e "${GREEN}  🎉 Todos os testes passaram!${NC}"
    exit 0
else
    echo -e "${RED}  ⚠  $FAIL verificação(ões) falharam.${NC}"
    exit 1
fi
