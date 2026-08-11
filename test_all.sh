#!/bin/bash
# test_all.sh — Full test suite for the 1337 v0.5.1 project

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
echo "   🧪 FULL TEST — 1337 v0.5.1"
echo "═══════════════════════════════════════════════════════════════"

# ── 1. Rust: clippy ────────────────────────────────────────────────────────────
step "1. Clippy (-D warnings)"
if cargo clippy --workspace -- -D warnings 2>&1 | grep -q "^error"; then
    fail "clippy: errors found"
else
    ok "clippy clean"
fi

# ── 2. Rust: unit tests ─────────────────────────────────────────────────────────
step "2. cargo test --workspace"
OUTPUT=$(cargo test --workspace --quiet 2>&1)
RESULTS=$(echo "$OUTPUT" | grep "test result:" || true)
FAILED=$(echo "$RESULTS" | grep -c "FAILED" || true)
PASSED_COUNT=$(echo "$RESULTS" | grep -oP '\d+ passed' | awk '{s+=$1} END{print s+0}')

if [[ "$FAILED" -gt 0 ]]; then
    fail "Rust tests: failures detected"
    echo "$OUTPUT" | grep "FAILED" | sed 's/^/    /'
else
    ok "Rust tests: ${PASSED_COUNT} passed"
fi

# ── 3. Consistent version ───────────────────────────────────────────────────────
step "3. Crate versions (should be 0.5.1 across the board)"
VERSION_MISMATCHES=$(cargo metadata --no-deps --format-version 1 2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
bad = [p['name'] + '=' + p['version'] for p in data['packages'] if p['version'] != '0.5.1']
print('\n'.join(bad))
" 2>/dev/null || true)

if [[ -z "$VERSION_MISMATCHES" ]]; then
    ok "all crates on v0.5.1"
else
    fail "version mismatches: $VERSION_MISMATCHES"
fi

# ── 4. Zero PT names in Rust sources ────────────────────────────────────────────
step "4. Zero PT names in active .rs sources"
PT_HITS=$(grep -rn \
    "ESSENCIA\|CORRESPONDENCIA\|VIBRACAO\|POLARIDADE\|RITMO\|ESTADO\|PROCESSO\|RELACAO\|SINAL\|ESTABILIDADE\|VALENCIA_ONT\|CAUSALIDADE\|VERIFICABILIDADE\|TEMPORALIDADE\|ANCORA_TEMPORAL\|COMPLETUDE\|REVERSIBILIDADE\|VALENCIA_EPIST\|URGENCIA\|IMPACTO\|ANOMALIA\|DEPENDENCIA\|VETOR_TEMPORAL\|CONFIANCA\|INTENCAO\|MASSA\|ENTROPIA\|COERENCIA\|GRADIENTE\|PROPAGACAO\|AFINIDADE\|DECAIMENTO\|INERCIA\|DENSIDADE\|TAXA_APRENDIZADO\|K_INTERACAO\|QUANTIZACAO\|RUIDO\|AFETO" \
    --include="*.rs" . 2>/dev/null | grep -v "target/" || true)

if [[ -z "$PT_HITS" ]]; then
    ok "zero PT names"
else
    fail "PT names found:"
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
        fail "leet version failed"
    fi

    if $LEET_BIN zero &>/dev/null; then
        ok "leet zero"
    else
        fail "leet zero failed"
    fi

    if $LEET_BIN encode "urgente agora" &>/dev/null; then
        ok "leet encode"
    else
        fail "leet encode failed"
    fi
else
    echo -e "  ${YELLOW}⚠  CLI not found — run 'cargo build -p leet-cli' first${NC}"
fi

# ── 6. Python (optional) ────────────────────────────────────────────────────────
step "6. Python (optional)"
PYTHON_TESTED=false

for pkg_dir in python leet-py; do
    if [[ -d "$REPO_ROOT/$pkg_dir/tests" ]] && command -v python3 &>/dev/null; then
        if python3 -m pytest "$REPO_ROOT/$pkg_dir/tests" -q --tb=line 2>/dev/null; then
            ok "pytest $pkg_dir OK"
        else
            fail "pytest $pkg_dir failed"
        fi
        PYTHON_TESTED=true
    fi
done

[[ "$PYTHON_TESTED" == "false" ]] && echo -e "  ${YELLOW}⚠  Python tests skipped (no pytest or no tests/)${NC}"

# ── Summary ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   📊 SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Passed:  $PASS"
echo "  Failed:  $FAIL"
echo ""

if [[ "$FAIL" -eq 0 ]]; then
    echo -e "${GREEN}  🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}  ⚠  $FAIL check(s) failed.${NC}"
    exit 1
fi
