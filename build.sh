#!/bin/bash
# Build script para o projeto 1337
# Compila Rust, Python e cria containers Docker

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  1337 — Build Completo"
echo "═══════════════════════════════════════════════════════════════"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Build Rust
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🦀 Building Rust workspace...${NC}"
cd leet1337

echo "  → Checking format..."
cargo fmt -- --check 2>/dev/null || echo "    (format issues found, run 'cargo fmt')"

echo "  → Running clippy..."
cargo clippy --all-targets --all-features -- -D warnings 2>/dev/null || echo "    (warnings found)"

echo "  → Building release..."
cargo build --release

echo "  → Running tests..."
cargo test --all --quiet

cd ..

echo -e "${GREEN}✅ Rust build complete${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Build Python
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🐍 Building Python package...${NC}"
cd python

echo "  → Installing dependencies..."
pip install -e ".[dev]" --quiet

echo "  → Running tests..."
pytest --tb=short -q

cd ..

echo -e "${GREEN}✅ Python build complete${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Build Docker
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}🐳 Building Docker image...${NC}"
docker build -t leet-service:latest .

echo -e "${GREEN}✅ Docker build complete${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Verificação final
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${YELLOW}📊 Build Summary:${NC}"
echo "  → Rust binaries:    leet1337/target/release/"
echo "  → Python package:   python/leet/"
echo "  → Docker image:     leet-service:latest"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════"
echo "  🎉 Build completo!"
echo "═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Para iniciar o serviço:"
echo "  docker-compose up -d"
echo ""
echo "Ou localmente:"
echo "  cd leet1337 && cargo run --release -p leet-service"
