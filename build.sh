#!/bin/bash
# build.sh — Full build for the 1337 v0.5.1 project
#
# Usage:
#   ./build.sh           → build + tests (Rust + Python if available)
#   ./build.sh --release → Rust release build
#   ./build.sh --rust    → Rust only
#   ./build.sh --python  → Python only

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

RELEASE=false
ONLY_RUST=false
ONLY_PYTHON=false

for arg in "$@"; do
    case "$arg" in
        --release) RELEASE=true ;;
        --rust)    ONLY_RUST=true ;;
        --python)  ONLY_PYTHON=true ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════════"
echo "  1337 — Build v0.5.1"
echo "═══════════════════════════════════════════════════════════════"

# ── Rust workspace ─────────────────────────────────────────────────────────────

if [[ "$ONLY_PYTHON" != "true" ]]; then
    echo ""
    echo -e "${BLUE}🦀 Rust workspace...${NC}"

    echo "  → cargo fmt --check"
    cargo fmt --check 2>/dev/null || echo -e "    ${YELLOW}(run 'cargo fmt' to fix formatting)${NC}"

    echo "  → cargo clippy -D warnings"
    cargo clippy --workspace -- -D warnings

    if [[ "$RELEASE" == "true" ]]; then
        echo "  → cargo build --workspace --release"
        cargo build --workspace --release
        echo -e "${GREEN}  ✓ Release binaries: target/release/${NC}"
    else
        echo "  → cargo build --workspace"
        cargo build --workspace
    fi

    echo "  → cargo test --workspace"
    cargo test --workspace --quiet

    echo -e "${GREEN}✅ Rust OK${NC}"
fi

# ── Python packages ────────────────────────────────────────────────────────────

if [[ "$ONLY_RUST" != "true" ]]; then
    PYTHON_BUILT=false

    for pkg_dir in python leet-py; do
        if [[ -f "$REPO_ROOT/$pkg_dir/pyproject.toml" || -f "$REPO_ROOT/$pkg_dir/setup.py" ]]; then
            echo ""
            echo -e "${BLUE}🐍 Python: $pkg_dir${NC}"
            echo "  → pip install -e ."
            pip install -e "$REPO_ROOT/$pkg_dir" --quiet
            if [[ -d "$REPO_ROOT/$pkg_dir/tests" ]]; then
                echo "  → pytest $pkg_dir/tests"
                python -m pytest "$REPO_ROOT/$pkg_dir/tests" -q --tb=short 2>/dev/null \
                    || echo -e "    ${YELLOW}(pytest failed or not installed)${NC}"
            fi
            PYTHON_BUILT=true
        fi
    done

    if [[ "$PYTHON_BUILT" == "true" ]]; then
        echo -e "${GREEN}✅ Python OK${NC}"
    else
        echo -e "    ${YELLOW}No Python package found (python/ or leet-py/)${NC}"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}  ✓ Build complete${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "To start the service:"
echo "  cargo run --release -p leet-service --bin leet-server"
echo ""
echo "To use the CLI:"
echo "  cargo run -p leet-cli -- encode 'urgente deploy falhou'"
echo "  cargo run -p leet-cli -- chat"
