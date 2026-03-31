#!/usr/bin/env bash
# ============================================================
# run.sh — Executor de prompts para o Claude Code
# Projeto 1337 — build automatizado completo
#
# Uso:
#   ./run.sh              → executa todos os prompts (0–6)
#   ./run.sh 0            → executa só o PROMPT_00 (git setup)
#   ./run.sh 1 2          → executa PROMPT_01 e PROMPT_02
#   ./run.sh --from 3     → executa do PROMPT_03 em diante
#   ./run.sh --dry-run    → mostra o que seria executado
#   ./run.sh --status     → mostra status do taskwarrior
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR"

# Cores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ────────────────────────────────────────
# Mapa de prompts
# ────────────────────────────────────────

declare -A PROMPT_FILES=(
  [0]="PROMPT_00_git_setup.md"
  [1]="PROMPT_01_foundation.md"
  [2]="PROMPT_02_leet_service.md"
  [3]="PROMPT_03_leet_vm.md"
  [4]="PROMPT_04_leet_py.md"
  [5]="PROMPT_05_leet_cli.md"
  [6]="PROMPT_06_calibration.md"
)

declare -A PROMPT_DESC=(
  [0]="git setup + CONTRACT.md + Taskwarrior"
  [1]="leet-core (Rust) + bridge + Python + net1337 + SKILL"
  [2]="leet-service (gRPC · Rust · Tokio · batch · SIMD)"
  [3]="leet-vm (Python · adapters · projector · PersonalStore)"
  [4]="leet-py (SDK público · LeetClient · providers)"
  [5]="leet-cli (ferramentas de debug · bench · inspect)"
  [6]="calibração W matrix (dataset → treino → export)"
)

declare -A PROMPT_TAGS=(
  [0]="prompt00"
  [1]="prompt01"
  [2]="prompt02"
  [3]="prompt03"
  [4]="prompt04"
  [5]="prompt05"
  [6]="prompt06"
)

# ────────────────────────────────────────
# Funções
# ────────────────────────────────────────

log()  { echo -e "${CYAN}[1337]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; exit 1; }

show_header() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║        PROJETO 1337 — BUILD SYSTEM           ║${NC}"
  echo -e "${BOLD}║        Spec v0.4 · 32 eixos canônicos        ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

show_plan() {
  log "Plano de execução:"
  echo ""
  for n in "$@"; do
    local file="${PROMPT_FILES[$n]}"
    local desc="${PROMPT_DESC[$n]}"
    local tag="${PROMPT_TAGS[$n]}"
    local pending=""
    if command -v task &>/dev/null; then
      pending=$(task project:1337 +"$tag" status:pending count 2>/dev/null || echo "?")
      pending=" (${pending} tarefas pendentes)"
    fi
    echo -e "  ${BOLD}[$n]${NC} $desc$pending"
    echo -e "      ${BLUE}$file${NC}"
  done
  echo ""
}

show_status() {
  if ! command -v task &>/dev/null; then
    warn "Taskwarrior não instalado"
    return
  fi
  echo ""
  log "Status do Taskwarrior — Projeto 1337"
  echo ""
  task project:1337 summary 2>/dev/null || true
  echo ""
  for n in $(seq 0 6); do
    local tag="${PROMPT_TAGS[$n]}"
    local desc="${PROMPT_DESC[$n]}"
    local total=$(task project:1337 +"$tag" count 2>/dev/null || echo 0)
    local completed=$(task project:1337 +"$tag" status:completed count 2>/dev/null || echo 0)
    printf "  [%d] %-50s %s/%s concluídas\n" "$n" "$desc" "$completed" "$total"
  done
  echo ""
}

check_claude_code() {
  if ! command -v claude &>/dev/null; then
    err "Claude Code não encontrado. Instale: npm install -g @anthropic-ai/claude-code"
  fi
  ok "Claude Code encontrado: $(claude --version 2>/dev/null || echo 'ok')"
}

run_prompt() {
  local n=$1
  local file="${PROMPTS_DIR}/${PROMPT_FILES[$n]}"
  local desc="${PROMPT_DESC[$n]}"

  echo ""
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}  PROMPT [$n] — $desc${NC}"
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""

  local start=$(date +%s)

  # Todos os prompts vão pro Claude Code via pipe
  log "Alimentando Claude Code..."
  cat "$file" | claude --dangerously-skip-permissions

  local end=$(date +%s)
  local elapsed=$((end - start))

  echo ""
  ok "Prompt [$n] concluído em ${elapsed}s"

  # Mostra status do taskwarrior pra este prompt
  if command -v task &>/dev/null; then
    local tag="${PROMPT_TAGS[$n]}"
    local completed=$(task project:1337 +"$tag" status:completed count 2>/dev/null || echo 0)
    local total=$(task project:1337 +"$tag" count 2>/dev/null || echo 0)
    log "Taskwarrior: $completed/$total tarefas concluídas para $tag"
  fi

  return 0
}

# ────────────────────────────────────────
# Parse de argumentos
# ────────────────────────────────────────

DRY_RUN=false
FROM_PROMPT=-1
SHOW_STATUS=false
SPECIFIC=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true; shift ;;
    --from)     FROM_PROMPT="$2"; shift 2 ;;
    --status)   SHOW_STATUS=true; shift ;;
    --help|-h)
      echo "Uso: ./run.sh [opções] [números]"
      echo ""
      echo "Opções:"
      echo "  --dry-run        Mostra o plano sem executar"
      echo "  --from N         Executa do prompt N em diante"
      echo "  --status         Mostra status do Taskwarrior"
      echo "  --help           Mostra esta ajuda"
      echo ""
      echo "Prompts:"
      echo "  0  Git setup + CONTRACT.md + Taskwarrior"
      echo "  1  leet-core + bridge + Python + net1337"
      echo "  2  leet-service (gRPC)"
      echo "  3  leet-vm (adapters, projector, store)"
      echo "  4  leet-py (SDK público)"
      echo "  5  leet-cli (debug tools)"
      echo "  6  W matrix calibração"
      echo ""
      echo "Exemplos:"
      echo "  ./run.sh              # tudo (0–6)"
      echo "  ./run.sh 0            # só git setup"
      echo "  ./run.sh 1 2          # foundation + service"
      echo "  ./run.sh --from 3     # do 3 em diante"
      echo "  ./run.sh --status     # mostra progresso"
      exit 0
      ;;
    [0-6])  SPECIFIC+=("$1"); shift ;;
    *)      err "Argumento desconhecido: $1" ;;
  esac
done

# ────────────────────────────────────────
# Main
# ────────────────────────────────────────

show_header

if [[ "$SHOW_STATUS" == "true" ]]; then
  show_status
  exit 0
fi

# Determina targets
TARGETS=()
if [[ ${#SPECIFIC[@]} -gt 0 ]]; then
  TARGETS=("${SPECIFIC[@]}")
elif [[ $FROM_PROMPT -ge 0 ]]; then
  for n in $(seq "$FROM_PROMPT" 6); do TARGETS+=("$n"); done
else
  TARGETS=(0 1 2 3 4 5 6)
fi

if [[ "$DRY_RUN" == "true" ]]; then
  warn "DRY RUN — nenhum comando será executado"
  show_plan "${TARGETS[@]}"
  exit 0
fi

check_claude_code

# Verifica arquivos
log "Verificando prompts..."
for n in "${TARGETS[@]}"; do
  file="${PROMPTS_DIR}/${PROMPT_FILES[$n]}"
  if [[ ! -f "$file" ]]; then
    err "Faltando: $file"
  fi
  ok "[$n] ${PROMPT_FILES[$n]} ($(wc -l < "$file") linhas)"
done

echo ""
show_plan "${TARGETS[@]}"

# Confirmação
if [[ ${#TARGETS[@]} -gt 1 ]]; then
  echo -e "${YELLOW}Isso vai executar ${#TARGETS[@]} prompts sequencialmente.${NC}"
  read -rp "Continuar? [s/N] " confirm
  [[ "$confirm" =~ ^[sS]$ ]] || { log "Cancelado."; exit 0; }
fi

# Executa
TOTAL_START=$(date +%s)
FAILED=()
SUCCEEDED=()

for n in "${TARGETS[@]}"; do
  if run_prompt "$n"; then
    SUCCEEDED+=("$n")
  else
    FAILED+=("$n")
    warn "Prompt [$n] falhou."
    if [[ ${#TARGETS[@]} -gt 1 ]]; then
      read -rp "Continuar com os próximos? [s/N] " cont
      [[ "$cont" =~ ^[sS]$ ]] || break
    fi
  fi
done

TOTAL_END=$(date +%s)
TOTAL=$((TOTAL_END - TOTAL_START))

# Resumo final
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  RESUMO${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

[[ ${#SUCCEEDED[@]} -gt 0 ]] && ok "Concluídos: ${SUCCEEDED[*]}"
[[ ${#FAILED[@]} -gt 0 ]]    && echo -e "${RED}  ✗ Falharam: ${FAILED[*]}${NC}"

echo -e "  Tempo total: ${TOTAL}s ($(( TOTAL / 60 ))m $(( TOTAL % 60 ))s)"

if command -v task &>/dev/null; then
  echo ""
  show_status
fi

echo ""
[[ ${#FAILED[@]} -eq 0 ]] && ok "Build completo." || exit 1
