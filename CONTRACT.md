# PROJETO 1337 — CONTRATO DE IMPLEMENTAÇÃO

**Versão**: v0.4 (32 eixos canônicos)  
**Autor**: Yuri Harrison — Fortaleza, Ceará, Brasil  
**Data de criação**: 2026-03-31  
**Última atualização**: 2026-03-31  

---

## STATUS GERAL

| Componente | Prompt | Status | Data Início | Data Conclusão |
|-----------|--------|--------|-------------|----------------|
| Git Setup + Contract + Taskwarrior | PROMPT_00 | `[x]` CONCLUÍDO | 2026-03-31 | 2026-03-31 |
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
- [ ] T01.12 — Python types.py
- [ ] T01.13 — Python axes.py
- [ ] T01.14 — Python operators.py
- [ ] T01.15 — Python validate.py
- [ ] T01.16 — Python bridge.py
- [ ] T01.17 — Python cli.py
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
- [ ] T03.01 — AdapterFrame + BaseAdapter
- [ ] T03.02 — TextAdapter
- [ ] T03.03 — JSONRPCAdapter
- [ ] T03.04 — MCPAdapter
- [ ] T03.05 — RESTAdapter
- [ ] T03.06 — auto_detect
- [ ] T03.07 — GrpcProjector
- [ ] T03.08 — LocalProjector
- [ ] T03.09 — MockProjector
- [ ] T03.10 — SessionDAG + DELTA
- [ ] T03.11 — DAG router
- [ ] T03.12 — Validator pipeline
- [ ] T03.13 — PersonalStore
- [ ] T03.14 — ContextCache
- [ ] T03.15 — Surface C4
- [ ] T03.16 — LeetVM.process()
- [ ] T03.17 — Testes (≥30)

### PROMPT_04 — LEET-PY (SDK Público)
- [ ] T04.01 — LeetClient (chat, recall, remember, encode, decode, forget)
- [ ] T04.02 — BaseProvider
- [ ] T04.03 — AnthropicProvider
- [ ] T04.04 — OpenAIProvider
- [ ] T04.05 — DeepSeekProvider
- [ ] T04.06 — MockProvider
- [ ] T04.07 — @agent decorator + AgentNetwork
- [ ] T04.08 — leet.connect() factory
- [ ] T04.09 — Stats dataclass
- [ ] T04.10 — Testes (≥20)
- [ ] T04.11 — examples/quickstart.py
- [ ] T04.12 — examples/multi_agent.py

### PROMPT_05 — LEET-CLI (Ferramentas)
- [ ] T05.01 — clap setup + subcomandos
- [ ] T05.02 — leet encode
- [ ] T05.03 — leet decode
- [ ] T05.04 — leet dist
- [ ] T05.05 — leet blend
- [ ] T05.06 — leet axes
- [ ] T05.07 — leet zero
- [ ] T05.08 — leet validate
- [ ] T05.09 — leet bench
- [ ] T05.10 — leet inspect
- [ ] T05.11 — leet health
- [ ] T05.12 — leet version
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
| 2026-03-31 | PROMPT_00 | Criação do contrato |
