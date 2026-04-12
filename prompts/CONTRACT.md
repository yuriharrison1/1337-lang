# PROJETO 1337 — CONTRATO DE IMPLEMENTAÇÃO

**Versão**: v0.4 (32 eixos canônicos)
**Autor**: Yuri Harrison — Fortaleza, Ceará, Brasil
**Data de criação**: 2026-03-31
**Última atualização**: _PENDENTE_

---

## STATUS GERAL

| Componente | Prompt | Status | Data Início | Data Conclusão |
|-----------|--------|--------|-------------|----------------|
| Git Setup + Contract + Taskwarrior | PROMPT_00 | `[ ]` PENDENTE | — | — |
| leet-core (Rust) | PROMPT_01 | `[ ]` PENDENTE | — | — |
| leet-service (gRPC) | PROMPT_02 | `[ ]` PENDENTE | — | — |
| leet-vm (Python) | PROMPT_03 | `[ ]` PENDENTE | — | — |
| leet-py (SDK público) | PROMPT_04 | `[ ]` PENDENTE | — | — |
| leet-cli (ferramentas) | PROMPT_05 | `[ ]` PENDENTE | — | — |
| W matrix calibração | PROMPT_06 | `[ ]` PENDENTE | — | — |

---

## PROMPT_00 — GIT SETUP + CONTRATO + TASKWARRIOR

### Tarefas
- [ ] `T00.1` — Commit all current work (stage + commit + push)
- [ ] `T00.2` — Rename current branch to `filosofico`
- [ ] `T00.3` — Create new `main` branch from `filosofico`
- [ ] `T00.4` — Push `main` como branch principal
- [ ] `T00.5` — Criar CONTRACT.md no repositório
- [ ] `T00.6` — Configurar Taskwarrior com projeto `1337`
- [ ] `T00.7` — Importar todas as tarefas no Taskwarrior
- [ ] `T00.8` — Commit + push do setup

---

## PROMPT_01 — LEET-CORE + TRADUTOR (Rust Foundation + Bridge)

### Entregáveis
- `leet-core/` — Crate Rust com tipos, operadores, validação R1–R21, C ABI FFI, PyO3
- `leet-bridge/` — Tradutor completo: SemanticProjector trait, MockProjector (heurísticas por eixo), HumanBridge (text→cogon/dag/msg), leet_to_human (cogon/dag/msg→text), prompt templates para LLMs
- `python/leet/` — Pacote Python com MockProjector, AnthropicProjector, CLI completa
- `net1337.py` — Simulador multi-agente interativo
- `SKILL.md` — Contexto completo do projeto para Claude Code

### Tarefas Detalhadas — leet-core
- [ ] `T01.01` — Criar SKILL.md com spec v0.4 completa
- [ ] `T01.02` — Cargo workspace setup (leet-core, leet-bridge)
- [ ] `T01.03` — leet-core/src/types.rs — Cogon, Edge, Dag, Msg1337, RawField, Intent, EdgeType
- [ ] `T01.04` — leet-core/src/axes.rs — 32 eixos canônicos com metadados (nome, código, grupo, descrição)
- [ ] `T01.05` — leet-core/src/operators.rs — FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE
- [ ] `T01.06` — leet-core/src/validate.rs — R1–R21 completas, validate_msg(), validate_dag(), validate_cogon()
- [ ] `T01.07` — leet-core/src/error.rs — LeetError enum com todos os erros tipados
- [ ] `T01.08` — leet-core/src/ffi.rs — C ABI: leet_cogon_zero(), leet_blend(), leet_dist(), leet_validate()
- [ ] `T01.09` — leet-core/src/python.rs — PyO3 bindings: PyCogon, PyDag, py_blend(), py_dist()

### Tarefas Detalhadas — leet-bridge (Tradutor)
- [ ] `T01.10` — leet-bridge/src/error.rs — BridgeError enum (EmptyInput, ProjectionFailed, ReconstructionFailed, ValidationFailed, JsonParse)
- [ ] `T01.11` — leet-bridge/src/projector.rs — trait SemanticProjector (project, reconstruct, reconstruct_dag)
- [ ] `T01.12` — leet-bridge/src/projector.rs — MockProjector com heurísticas por eixo (keywords para URGÊNCIA, ANOMALIA, AÇÃO, PROCESSO, SISTEMA, ESTADO, IMPACTO, AFETO, VALOR, COMPLETUDE, REVERSIBILIDADE, CARGA, VETOR TEMPORAL, NATUREZA, VALÊNCIA DE AÇÃO) + fallback SHA256 hash
- [ ] `T01.13` — leet-bridge/src/prompts.rs — projection_prompt(text) com todos os 32 eixos listados + reconstruction_prompt(sem, unc)
- [ ] `T01.14` — leet-bridge/src/human_to_1337.rs — HumanBridge<P> com text_to_cogon(), text_to_dag() (split por sentenças, CONDICIONA edges), text_to_msg() (envelope completo com c5 e surface)
- [ ] `T01.15` — leet-bridge/src/leet_to_human.rs — cogon_to_text(), dag_to_text() (leaf→root com conectores por edge type), msg_to_text() (header com intent + urgência)
- [ ] `T01.16` — Testes bridge Rust: mínimo 15 testes (text_to_cogon urgente/sistema/ação/emocional/genérico, text_to_dag single/multi, text_to_msg envelope, cogon_to_text roundtrip, dag_to_text, mock determinístico, prompt templates completos)

### Tarefas Detalhadas — Python
- [ ] `T01.17` — python/leet/types.py — dataclasses Cogon, Edge, Dag, Msg1337
- [ ] `T01.18` — python/leet/axes.py — CANONICAL_AXES com todos os 32 eixos
- [ ] `T01.19` — python/leet/operators.py — blend(), focus(), delta(), dist(), anomaly_score()
- [ ] `T01.20` — python/leet/validate.py — validate_cogon(), validate_dag(), validate_msg()
- [ ] `T01.21` — python/leet/bridge.py — MockProjector (mesmas heurísticas do Rust), AnthropicProjector (com prompt completo dos 32 eixos), encode(), decode()
- [ ] `T01.22` — python/leet/cli.py — Comandos completos: encode, decode, zero, blend, dist, axes, validate
- [ ] `T01.23` — net1337.py — Simulador IRC-style com 3 agentes autônomos

### Tarefas Detalhadas — Testes e Finalização
- [ ] `T01.24` — Testes Rust: cargo test --workspace (mínimo 55 testes: 40 core + 15 bridge)
- [ ] `T01.25` — Testes Python: pytest tests/ -v (mínimo 25 testes)
- [ ] `T01.26` — Atualizar CONTRACT.md com status
- [ ] `T01.27` — Commit + push

### Critérios de Aceite
- `cargo build --workspace` sem warnings
- `cargo test --workspace` — todos passam (≥55 testes)
- MockProjector: "urgente" → sem[22]>0.8, "servidor caiu" → sem[8]>0.7 + sem[26]>0.7
- HumanBridge: text_to_dag("A. B.") → 2 nós + 1 edge CONDICIONA
- Prompt templates: projection_prompt() lista todos os 32 eixos com descrições
- cogon_to_text() + dag_to_text() produzem texto legível
- `pip install -e python/` funciona
- `leet zero` / `leet encode "texto"` / `leet axes` funcionam
- AnthropicProjector tem prompt completo (mesmo sem API key pra testar)
- `python net1337.py` inicia sem erros
- Taskwarrior atualizado

---

## PROMPT_02 — LEET-SERVICE (gRPC · Rust · Tokio)

### Entregáveis
- `leet-service/` — Binário gRPC stateless
- `proto/leet.proto` — Contrato gRPC compartilhado

### Tarefas Detalhadas
- [ ] `T02.01` — proto/leet.proto — Encode, Decode, EncodeBatch, Delta, Recall, Health
- [ ] `T02.02` — leet-service/build.rs — tonic_build
- [ ] `T02.03` — leet-service/src/config.rs — Config::from_env() (port, backend, store, W matrix path)
- [ ] `T02.04` — leet-service/src/projection.rs — Engine com W matrix loaded, text→sem[32]+unc[32]
- [ ] `T02.05` — leet-service/src/store.rs — PersonalStore backend (Redis | SQLite | InMemory)
- [ ] `T02.06` — leet-service/src/batch.rs — BatchQueue com janela de tempo + flush automático
- [ ] `T02.07` — leet-service/src/server.rs — Implementação LeetService trait do tonic
- [ ] `T02.08` — leet-service/src/accel.rs — SIMD/BLAS backend via ndarray
- [ ] `T02.09` — leet-service/src/main.rs — Entry point com tracing + graceful shutdown
- [ ] `T02.10` — Dockerfile multi-stage para deploy
- [ ] `T02.11` — Testes: cargo test -p leet-service (mínimo 20 testes)
- [ ] `T02.12` — Atualizar CONTRACT.md com status
- [ ] `T02.13` — Commit + push

### Critérios de Aceite
- `cargo build -p leet-service` compila
- `cargo run -p leet-service` inicia e responde em :50051
- `grpcurl localhost:50051 leet.LeetService/Health` retorna OK
- Batch queue processa requests corretamente
- Taskwarrior atualizado

---

## PROMPT_03 — LEET-VM (Python · Adapters · Projector · PersonalStore)

### Entregáveis
- `leet-vm/` — Pacote Python com a Virtual Machine completa

### Tarefas Detalhadas
- [ ] `T03.01` — leet-vm/adapters/base.py — AdapterFrame dataclass + BaseAdapter ABC
- [ ] `T03.02` — leet-vm/adapters/text.py — TextAdapter (texto puro → AdapterFrame)
- [ ] `T03.03` — leet-vm/adapters/jsonrpc.py — JSONRPCAdapter (JSON-RPC → AdapterFrame)
- [ ] `T03.04` — leet-vm/adapters/mcp.py — MCPAdapter (MCP protocol → AdapterFrame)
- [ ] `T03.05` — leet-vm/adapters/rest.py — RESTAdapter (REST → AdapterFrame)
- [ ] `T03.06` — leet-vm/adapters/detector.py — auto_detect(payload) → Adapter correto
- [ ] `T03.07` — leet-vm/projector/grpc_client.py — GrpcProjector (conecta ao leet-service)
- [ ] `T03.08` — leet-vm/projector/local.py — LocalProjector (PyO3 direto, sem rede)
- [ ] `T03.09` — leet-vm/projector/mock.py — MockProjector (heurísticas, zero dependências)
- [ ] `T03.10` — leet-vm/runtime/session_dag.py — SessionDAG com DELTA compression
- [ ] `T03.11` — leet-vm/runtime/dag_router.py — Roteamento por prioridade (ANOMALY > URGÊNCIA > topológico)
- [ ] `T03.12` — leet-vm/runtime/validator.py — Pipeline de validação R1–R21
- [ ] `T03.13` — leet-vm/store/personal_store.py — PersonalStore com DIST ponderado, DELTA, Zona Emergente
- [ ] `T03.14` — leet-vm/store/context_cache.py — Cache com align_hash, correlation table
- [ ] `T03.15` — leet-vm/surface/c4.py — Surface C4: DAG → linguagem natural (determinístico)
- [ ] `T03.16` — leet-vm/vm.py — LeetVM.process(text, agent_id, session_id) → orchestrador central
- [ ] `T03.17` — Testes: pytest tests/ -v (mínimo 30 testes)
- [ ] `T03.18` — Atualizar CONTRACT.md com status
- [ ] `T03.19` — Commit + push

### Critérios de Aceite
- `pip install -e leet-vm/` funciona
- auto_detect identifica protocolo corretamente em 4 tipos
- PersonalStore.recall() retorna top-k por DIST
- SessionDAG comprime sessão com DELTA
- Surface C4 reconstrói DAG em texto legível
- LeetVM.process() faz o pipeline completo
- Taskwarrior atualizado

---

## PROMPT_04 — LEET-PY (SDK Público)

### Entregáveis
- `leet-py/` — `pip install leet` — API pública para end users

### Tarefas Detalhadas
- [ ] `T04.01` — leet-py/client.py — LeetClient com chat(), recall(), remember(), encode(), decode(), forget()
- [ ] `T04.02` — leet-py/providers/base.py — BaseProvider ABC
- [ ] `T04.03` — leet-py/providers/anthropic.py — AnthropicProvider
- [ ] `T04.04` — leet-py/providers/openai.py — OpenAIProvider
- [ ] `T04.05` — leet-py/providers/deepseek.py — DeepSeekProvider (via base_url)
- [ ] `T04.06` — leet-py/providers/mock.py — MockProvider (para testes)
- [ ] `T04.07` — leet-py/agent.py — @agent decorator + AgentNetwork para multi-agente
- [ ] `T04.08` — leet-py/connect.py — leet.connect("anthropic") factory
- [ ] `T04.09` — leet-py/stats.py — Stats dataclass (tokens_saved, cogons_stored, sessions)
- [ ] `T04.10` — Testes: pytest tests/ -v (mínimo 20 testes)
- [ ] `T04.11` — examples/quickstart.py — 4 linhas
- [ ] `T04.12` — examples/multi_agent.py — rede de agentes
- [ ] `T04.13` — Atualizar CONTRACT.md com status
- [ ] `T04.14` — Commit + push

### Critérios de Aceite
- `pip install -e leet-py/` funciona
- `leet.connect("mock")` retorna LeetClient funcional
- `client.chat("texto")` retorna Response com text e tokens_saved
- `client.stats` acumula métricas
- @agent decorator registra agente funcional
- Taskwarrior atualizado

---

## PROMPT_05 — LEET-CLI (Ferramentas de Debug)

### Entregáveis
- `leet-cli/` — Binário Rust `leet` com comandos de debug

### Tarefas Detalhadas
- [ ] `T05.01` — leet-cli/src/main.rs — clap v4 com subcomandos
- [ ] `T05.02` — leet-cli/src/cmd/encode.rs — `leet encode "texto"` com barras coloridas por eixo
- [ ] `T05.03` — leet-cli/src/cmd/decode.rs — `leet decode <json>` → texto reconstruído
- [ ] `T05.04` — leet-cli/src/cmd/dist.rs — `leet dist "a" "b"` com contribuição por eixo
- [ ] `T05.05` — leet-cli/src/cmd/blend.rs — `leet blend "a" "b" --alpha 0.6` com visualização
- [ ] `T05.06` — leet-cli/src/cmd/axes.rs — `leet axes` imprime 32 eixos coloridos por grupo
- [ ] `T05.07` — leet-cli/src/cmd/zero.rs — `leet zero` imprime COGON_ZERO formatado
- [ ] `T05.08` — leet-cli/src/cmd/validate.rs — `leet validate <msg.json>` valida contra R1–R21
- [ ] `T05.09` — leet-cli/src/cmd/bench.rs — `leet bench --n 1000` com percentis (p50/p95/p99)
- [ ] `T05.10` — leet-cli/src/cmd/inspect.rs — `leet inspect <cogon.json>` mostra interpretação semântica
- [ ] `T05.11` — leet-cli/src/cmd/health.rs — `leet health` checa leet-service
- [ ] `T05.12` — leet-cli/src/cmd/version.rs — `leet version` com spec version + build info
- [ ] `T05.13` — Testes: cargo test -p leet-cli (mínimo 15 testes)
- [ ] `T05.14` — Atualizar CONTRACT.md com status
- [ ] `T05.15` — Commit + push

### Critérios de Aceite
- `cargo install --path leet-cli` instala binário `leet`
- Todos os subcomandos funcionam
- Output colorido e formatado
- `leet bench` reporta latências reais
- Taskwarrior atualizado

---

## PROMPT_06 — CALIBRAÇÃO DA MATRIZ W

### Entregáveis
- `calibration/` — Pipeline completa de calibração

### Tarefas Detalhadas
- [ ] `T06.01` — calibration/generate_dataset.py — Gera pares (texto, sem[32]) via LLM scoring
- [ ] `T06.02` — calibration/train_w.py — Treina W via regressão Ridge (embedding → sem[32])
- [ ] `T06.03` — calibration/evaluate.py — Avalia coerência semântica (DIST entre conceitos similares)
- [ ] `T06.04` — calibration/export.py — Exporta W.bin para leet-service
- [ ] `T06.05` — calibration/config.yaml — Configuração do pipeline (modelo embedding, LLM, hiperparâmetros)
- [ ] `T06.06` — calibration/run_pipeline.py — Orquestrador: generate → train → evaluate → export
- [ ] `T06.07` — calibration/README.md — Documentação de uso
- [ ] `T06.08` — Testes: pytest calibration/tests/ (mínimo 10 testes)
- [ ] `T06.09` — Atualizar CONTRACT.md com status
- [ ] `T06.10` — Commit + push

### Critérios de Aceite
- Pipeline roda end-to-end com LLM mock
- W.bin gerado é carregável pelo leet-service
- Avaliação mostra coerência > 0.7 nos benchmarks
- Taskwarrior atualizado

---

## MÉTRICAS GLOBAIS

| Métrica | Target |
|---------|--------|
| Testes Rust total | ≥ 90 |
| Testes Python total | ≥ 85 |
| Cobertura de regras R1–R21 | 100% |
| Token reduction (benchmark) | ≥ 60% |
| Latência encode (p95) | < 10ms |

---

## NOTAS

- Spec v0.4 é a ÚNICA fonte de verdade. Versões anteriores são históricas.
- Todo prompt é self-contained — spec embutida onde necessário.
- Taskwarrior project: `1337`
- Cada prompt DEVE atualizar este documento ao finalizar.
- Ordem de execução: 00 → 01 → 02 → 03 → 04 → 05 → 06 (estrita)

---

*Documento gerado automaticamente. Atualizado por cada prompt durante execução.*
