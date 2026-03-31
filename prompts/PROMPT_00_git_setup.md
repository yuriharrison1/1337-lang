# PROMPT 00 — GIT SETUP + CONTRATO + TASKWARRIOR

Este prompt faz o housekeeping do repositório e prepara a infraestrutura de tracking.
Executar ANTES de qualquer prompt de implementação.

---

## CONTEXTO

O repositório `leet1337` já existe com código da fase anterior (leet-core, leet-bridge, net1337.py).
Esse código está numa branch que precisa ser preservada como histórico filosófico/exploratório.
A nova implementação vai ser a `main` oficial.

---

## PASSO 1 — COMMIT E PUSH DO ESTADO ATUAL

```bash
cd ~/leet1337  # ou onde estiver o repo

# Verifica estado
git status
git log --oneline -5

# Stage tudo que tiver pendente
git add -A
git commit -m "chore: snapshot estado atual antes de reestruturação v0.4

Preserva todo o trabalho exploratório:
- leet-core v0.4 (Rust)
- leet-bridge (Rust)
- python/leet wrapper
- net1337.py simulador
- prompts anteriores (01-06)

Este branch será renomeado para 'filosofico' — registro histórico.
A nova main terá implementação limpa a partir do zero."

# Push
git push origin HEAD
```

Se der conflito ou o remote não existir, configure:
```bash
# Se não tiver remote
git remote add origin git@github.com:yuriharrison/leet1337.git
# Ou HTTPS
git remote add origin https://github.com/yuriharrison/leet1337.git
git push -u origin HEAD
```

---

## PASSO 2 — RENOMEAR BRANCH ATUAL PARA `filosofico`

```bash
# Descobre o nome da branch atual
CURRENT_BRANCH=$(git branch --show-current)
echo "Branch atual: $CURRENT_BRANCH"

# Renomeia local
git branch -m "$CURRENT_BRANCH" filosofico

# Atualiza remote
git push origin filosofico
# Se a branch antiga já existia no remote, deleta
git push origin --delete "$CURRENT_BRANCH" 2>/dev/null || true

echo "Branch '$CURRENT_BRANCH' renomeada para 'filosofico'"
```

---

## PASSO 3 — CRIAR NOVA `main` LIMPA

```bash
# Cria branch main a partir do estado atual (herda o histórico)
git checkout -b main

# Push como branch principal
git push -u origin main

# Configura main como default no Git
git remote set-head origin main
```

> NOTA: Se o repo no GitHub tiver branch default diferente, 
> acessar Settings > Branches > Default branch e mudar para `main` manualmente.

---

## PASSO 4 — CRIAR CONTRACT.md NO REPO

Crie o arquivo `CONTRACT.md` na raiz do repositório com o conteúdo abaixo.
Este documento é o contrato mestre — todo prompt de implementação DEVE atualizá-lo.

```bash
cat > CONTRACT.md << 'HEREDOC'
# PROJETO 1337 — CONTRATO DE IMPLEMENTAÇÃO

**Versão**: v0.4 (32 eixos canônicos)  
**Autor**: Yuri Harrison — Fortaleza, Ceará, Brasil  
**Data de criação**: $(date +%Y-%m-%d)  
**Última atualização**: $(date +%Y-%m-%d)  

---

## STATUS GERAL

| Componente | Prompt | Status | Data Início | Data Conclusão |
|-----------|--------|--------|-------------|----------------|
| Git Setup + Contract + Taskwarrior | PROMPT_00 | `[x]` CONCLUÍDO | $(date +%Y-%m-%d) | $(date +%Y-%m-%d) |
| leet-core (Rust) | PROMPT_01 | `[ ]` PENDENTE | — | — |
| leet-service (gRPC) | PROMPT_02 | `[ ]` PENDENTE | — | — |
| leet-vm (Python) | PROMPT_03 | `[ ]` PENDENTE | — | — |
| leet-py (SDK público) | PROMPT_04 | `[ ]` PENDENTE | — | — |
| leet-cli (ferramentas) | PROMPT_05 | `[ ]` PENDENTE | — | — |
| W matrix calibração | PROMPT_06 | `[ ]` PENDENTE | — | — |

---

## COMPONENTES E TAREFAS

### PROMPT_01 — LEET-CORE (Rust Foundation)
- [ ] T01.01 — SKILL.md com spec v0.4 completa
- [ ] T01.02 — Cargo workspace setup
- [ ] T01.03 — types.rs (Cogon, Edge, Dag, Msg1337, RawField, Intent, EdgeType)
- [ ] T01.04 — axes.rs (32 eixos com metadados)
- [ ] T01.05 — operators.rs (FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE)
- [ ] T01.06 — validate.rs (R1–R21)
- [ ] T01.07 — error.rs (LeetError enum)
- [ ] T01.08 — ffi.rs (C ABI)
- [ ] T01.09 — python.rs (PyO3)
- [ ] T01.10 — projector.rs (trait + MockProjector)
- [ ] T01.11 — human_bridge.rs
- [ ] T01.12–T01.17 — Python wrapper completo + CLI
- [ ] T01.18 — net1337.py simulador
- [ ] T01.19 — Testes Rust (≥40)
- [ ] T01.20 — Testes Python (≥25)

### PROMPT_02 — LEET-SERVICE (gRPC · Rust · Tokio)
- [ ] T02.01 — leet.proto
- [ ] T02.02 — build.rs (tonic)
- [ ] T02.03 — config.rs
- [ ] T02.04 — projection.rs (W matrix engine)
- [ ] T02.05 — store.rs (Redis | SQLite | InMemory)
- [ ] T02.06 — batch.rs (BatchQueue)
- [ ] T02.07 — server.rs (tonic service)
- [ ] T02.08 — accel.rs (SIMD/BLAS)
- [ ] T02.09 — main.rs
- [ ] T02.10 — Dockerfile
- [ ] T02.11 — Testes (≥20)

### PROMPT_03 — LEET-VM (Python)
- [ ] T03.01–T03.06 — Adapters (text, jsonrpc, mcp, rest, auto-detect)
- [ ] T03.07–T03.09 — Projector (gRPC, local, mock)
- [ ] T03.10–T03.12 — Runtime (SessionDAG, DAG router, validator)
- [ ] T03.13–T03.14 — Store (PersonalStore, ContextCache)
- [ ] T03.15 — Surface C4
- [ ] T03.16 — LeetVM.process() orchestrador
- [ ] T03.17 — Testes (≥30)

### PROMPT_04 — LEET-PY (SDK Público)
- [ ] T04.01 — LeetClient (chat, recall, remember, encode, decode, forget)
- [ ] T04.02–T04.06 — Providers (anthropic, openai, deepseek, mock)
- [ ] T04.07 — @agent decorator + AgentNetwork
- [ ] T04.08 — leet.connect() factory
- [ ] T04.09 — Stats dataclass
- [ ] T04.10 — Testes (≥20)
- [ ] T04.11–T04.12 — Examples

### PROMPT_05 — LEET-CLI (Ferramentas)
- [ ] T05.01–T05.12 — Subcomandos (encode, decode, dist, blend, axes, zero, validate, bench, inspect, health, version)
- [ ] T05.13 — Testes (≥15)

### PROMPT_06 — CALIBRAÇÃO W MATRIX
- [ ] T06.01 — generate_dataset.py
- [ ] T06.02 — train_w.py (Ridge regression)
- [ ] T06.03 — evaluate.py
- [ ] T06.04 — export.py (W.bin)
- [ ] T06.05 — config.yaml
- [ ] T06.06 — run_pipeline.py
- [ ] T06.07 — README.md
- [ ] T06.08 — Testes (≥10)

---

## MÉTRICAS GLOBAIS

| Métrica | Target | Atual |
|---------|--------|-------|
| Testes Rust total | ≥ 75 | 0 |
| Testes Python total | ≥ 85 | 0 |
| Cobertura R1–R21 | 100% | 0% |
| Token reduction | ≥ 60% | — |
| Latência encode p95 | < 10ms | — |

---

## CHANGELOG DO CONTRATO

| Data | Prompt | Mudança |
|------|--------|---------|
| $(date +%Y-%m-%d) | PROMPT_00 | Criação do contrato |

HEREDOC
```

---

## PASSO 5 — CONFIGURAR TASKWARRIOR

```bash
# Instala taskwarrior se não tiver
which task || sudo apt-get install -y taskwarrior

# Cria .taskrc se não existir
if [ ! -f ~/.taskrc ]; then
  task rc.confirmation=off config default.project 1337
fi

# ─── PROMPT_01 tasks ───
task add project:1337 priority:H due:eow +prompt01 "T01.01 — SKILL.md com spec v0.4"
task add project:1337 priority:H due:eow +prompt01 "T01.02 — Cargo workspace setup"
task add project:1337 priority:H due:eow +prompt01 "T01.03 — types.rs (Cogon, Edge, Dag, Msg1337)"
task add project:1337 priority:H due:eow +prompt01 "T01.04 — axes.rs (32 eixos canônicos)"
task add project:1337 priority:H due:eow +prompt01 "T01.05 — operators.rs (FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE)"
task add project:1337 priority:H due:eow +prompt01 "T01.06 — validate.rs (R1–R21)"
task add project:1337 priority:H due:eow +prompt01 "T01.07 — error.rs (LeetError)"
task add project:1337 priority:H due:eow +prompt01 "T01.08 — ffi.rs (C ABI)"
task add project:1337 priority:H due:eow +prompt01 "T01.09 — python.rs (PyO3)"
task add project:1337 priority:H due:eow +prompt01 "T01.10 — projector.rs (trait + Mock)"
task add project:1337 priority:H due:eow +prompt01 "T01.11 — human_bridge.rs"
task add project:1337 priority:M due:eow +prompt01 "T01.12 — Python types.py"
task add project:1337 priority:M due:eow +prompt01 "T01.13 — Python axes.py"
task add project:1337 priority:M due:eow +prompt01 "T01.14 — Python operators.py"
task add project:1337 priority:M due:eow +prompt01 "T01.15 — Python validate.py"
task add project:1337 priority:M due:eow +prompt01 "T01.16 — Python bridge.py"
task add project:1337 priority:M due:eow +prompt01 "T01.17 — Python cli.py"
task add project:1337 priority:M due:eow +prompt01 "T01.18 — net1337.py simulador"
task add project:1337 priority:H due:eow +prompt01 "T01.19 — Testes Rust (≥40)"
task add project:1337 priority:H due:eow +prompt01 "T01.20 — Testes Python (≥25)"

# ─── PROMPT_02 tasks ───
task add project:1337 priority:H +prompt02 "T02.01 — leet.proto"
task add project:1337 priority:H +prompt02 "T02.02 — build.rs tonic"
task add project:1337 priority:H +prompt02 "T02.03 — config.rs"
task add project:1337 priority:H +prompt02 "T02.04 — projection.rs (W matrix)"
task add project:1337 priority:H +prompt02 "T02.05 — store.rs (Redis|SQLite|InMemory)"
task add project:1337 priority:H +prompt02 "T02.06 — batch.rs (BatchQueue)"
task add project:1337 priority:H +prompt02 "T02.07 — server.rs (tonic)"
task add project:1337 priority:M +prompt02 "T02.08 — accel.rs (SIMD/BLAS)"
task add project:1337 priority:H +prompt02 "T02.09 — main.rs"
task add project:1337 priority:M +prompt02 "T02.10 — Dockerfile"
task add project:1337 priority:H +prompt02 "T02.11 — Testes (≥20)"

# ─── PROMPT_03 tasks ───
task add project:1337 priority:H +prompt03 "T03.01 — AdapterFrame + BaseAdapter"
task add project:1337 priority:H +prompt03 "T03.02 — TextAdapter"
task add project:1337 priority:M +prompt03 "T03.03 — JSONRPCAdapter"
task add project:1337 priority:M +prompt03 "T03.04 — MCPAdapter"
task add project:1337 priority:M +prompt03 "T03.05 — RESTAdapter"
task add project:1337 priority:H +prompt03 "T03.06 — auto_detect"
task add project:1337 priority:H +prompt03 "T03.07 — GrpcProjector"
task add project:1337 priority:M +prompt03 "T03.08 — LocalProjector"
task add project:1337 priority:M +prompt03 "T03.09 — MockProjector"
task add project:1337 priority:H +prompt03 "T03.10 — SessionDAG + DELTA"
task add project:1337 priority:H +prompt03 "T03.11 — DAG router"
task add project:1337 priority:H +prompt03 "T03.12 — Validator pipeline"
task add project:1337 priority:H +prompt03 "T03.13 — PersonalStore"
task add project:1337 priority:M +prompt03 "T03.14 — ContextCache"
task add project:1337 priority:H +prompt03 "T03.15 — Surface C4"
task add project:1337 priority:H +prompt03 "T03.16 — LeetVM.process()"
task add project:1337 priority:H +prompt03 "T03.17 — Testes (≥30)"

# ─── PROMPT_04 tasks ───
task add project:1337 priority:H +prompt04 "T04.01 — LeetClient"
task add project:1337 priority:H +prompt04 "T04.02 — BaseProvider"
task add project:1337 priority:H +prompt04 "T04.03 — AnthropicProvider"
task add project:1337 priority:M +prompt04 "T04.04 — OpenAIProvider"
task add project:1337 priority:M +prompt04 "T04.05 — DeepSeekProvider"
task add project:1337 priority:H +prompt04 "T04.06 — MockProvider"
task add project:1337 priority:M +prompt04 "T04.07 — @agent + AgentNetwork"
task add project:1337 priority:H +prompt04 "T04.08 — leet.connect() factory"
task add project:1337 priority:M +prompt04 "T04.09 — Stats dataclass"
task add project:1337 priority:H +prompt04 "T04.10 — Testes (≥20)"
task add project:1337 priority:L +prompt04 "T04.11 — examples/quickstart.py"
task add project:1337 priority:L +prompt04 "T04.12 — examples/multi_agent.py"

# ─── PROMPT_05 tasks ───
task add project:1337 priority:H +prompt05 "T05.01 — clap setup + subcomandos"
task add project:1337 priority:H +prompt05 "T05.02 — leet encode"
task add project:1337 priority:M +prompt05 "T05.03 — leet decode"
task add project:1337 priority:H +prompt05 "T05.04 — leet dist"
task add project:1337 priority:M +prompt05 "T05.05 — leet blend"
task add project:1337 priority:H +prompt05 "T05.06 — leet axes"
task add project:1337 priority:H +prompt05 "T05.07 — leet zero"
task add project:1337 priority:M +prompt05 "T05.08 — leet validate"
task add project:1337 priority:M +prompt05 "T05.09 — leet bench"
task add project:1337 priority:L +prompt05 "T05.10 — leet inspect"
task add project:1337 priority:L +prompt05 "T05.11 — leet health"
task add project:1337 priority:L +prompt05 "T05.12 — leet version"
task add project:1337 priority:H +prompt05 "T05.13 — Testes (≥15)"

# ─── PROMPT_06 tasks ───
task add project:1337 priority:H +prompt06 "T06.01 — generate_dataset.py"
task add project:1337 priority:H +prompt06 "T06.02 — train_w.py (Ridge)"
task add project:1337 priority:H +prompt06 "T06.03 — evaluate.py"
task add project:1337 priority:H +prompt06 "T06.04 — export.py (W.bin)"
task add project:1337 priority:M +prompt06 "T06.05 — config.yaml"
task add project:1337 priority:H +prompt06 "T06.06 — run_pipeline.py"
task add project:1337 priority:M +prompt06 "T06.07 — README.md"
task add project:1337 priority:H +prompt06 "T06.08 — Testes (≥10)"

# Mostra resumo
echo ""
echo "═══════════════════════════════════════════"
echo "TASKWARRIOR — PROJETO 1337"
echo "═══════════════════════════════════════════"
task project:1337 count
echo ""
task project:1337 summary
echo ""
echo "Por prompt:"
for tag in prompt01 prompt02 prompt03 prompt04 prompt05 prompt06; do
  count=$(task +$tag count 2>/dev/null || echo 0)
  echo "  $tag: $count tarefas"
done
```

---

## PASSO 6 — COMMIT DO SETUP

```bash
cd ~/leet1337

# Adiciona o contrato e qualquer config nova
git add CONTRACT.md .taskrc 2>/dev/null
git add -A

git commit -m "chore(prompt-00): setup contrato + taskwarrior

- CONTRACT.md com todas as tarefas de implementação
- Taskwarrior configurado com projeto 1337
- Branch 'filosofico' preserva trabalho anterior
- Branch 'main' pronta para implementação limpa"

git push origin main
```

---

## PASSO 7 — VERIFICAÇÃO FINAL

```bash
echo "=== GIT ==="
git branch -a
git log --oneline -3
echo ""

echo "=== CONTRACT ==="
head -20 CONTRACT.md
echo ""

echo "=== TASKWARRIOR ==="
task project:1337 summary
echo ""

echo "=== PROMPT_00 CONCLUÍDO ==="
```

---

## ATUALIZAR CONTRACT.md

Depois de tudo acima executado com sucesso, edite CONTRACT.md:
- Mude PROMPT_00 de `[ ] PENDENTE` para `[x] CONCLUÍDO`
- Preencha Data Início e Data Conclusão com a data de hoje
- Atualize "Última atualização" no cabeçalho

```bash
# Marca no taskwarrior (não tem tasks específicas do P00 — o setup É a task)
echo "PROMPT_00 completo. Taskwarrior pronto. Contrato criado."

# Commit final
git add CONTRACT.md
git commit -m "chore(prompt-00): marca setup como concluído"
git push origin main
```

---

**FIM DO PROMPT_00**
