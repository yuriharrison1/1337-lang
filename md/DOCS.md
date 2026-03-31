# Protocolo 1337 — Documentação Completa

> Linguagem nativa de comunicação entre agentes de IA.
> Versão **0.5.0** · Python 3.10+ · Rust (opcional)

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Como o Protocolo Funciona](#2-como-o-protocolo-funciona)
3. [Arquitetura do Projeto](#3-arquitetura-do-projeto)
4. [Features Implementadas](#4-features-implementadas)
5. [Instalação](#5-instalação)
6. [Conceitos Fundamentais](#6-conceitos-fundamentais)
7. [SDK Python — Guia Completo de Uso](#7-sdk-python--guia-completo-de-uso)
   - 7.1 [Tipos do protocolo](#71-tipos-do-protocolo)
   - 7.2 [Operadores semânticos](#72-operadores-semânticos)
   - 7.3 [Bridge: texto ↔ COGON](#73-bridge-texto--cogon)
   - 7.4 [Validação R1–R21](#74-validação-r1r21)
   - 7.5 [Contexto e perfis](#75-contexto-e-perfis)
   - 7.6 [Cache](#76-cache)
   - 7.7 [Batch processing](#77-batch-processing)
   - 7.8 [Métricas e observabilidade](#78-métricas-e-observabilidade)
   - 7.9 [Clientes de rede](#79-clientes-de-rede)
   - 7.10 [Agente completo](#710-agente-completo)
   - 7.11 [Adaptadores IDE](#711-adaptadores-ide)
8. [leet-py — SDK de Alto Nível](#8-leet-py--sdk-de-alto-nível)
9. [leet-service — Backend Rust](#9-leet-service--backend-rust)
10. [leet-cli — Ferramentas de Linha de Comando](#10-leet-cli--ferramentas-de-linha-de-comando)
11. [Wire Format — Protocolo de Transmissão](#11-wire-format--protocolo-de-transmissão)
12. [Os 32 Eixos Canônicos](#12-os-32-eixos-canônicos)
13. [Configuração e Variáveis de Ambiente](#13-configuração-e-variáveis-de-ambiente)
14. [Exemplos de Ponta a Ponta](#14-exemplos-de-ponta-a-ponta)

---

## 1. Visão Geral

O **1337** é um protocolo de comunicação formal construído para agentes de IA se comunicarem de forma direta, sem usar linguagem natural como intermediário. Em vez de trocar frases, agentes trocam **COGONs** — vetores semânticos de 32 dimensões que codificam significado de forma comprimida, verificável e sem ambiguidade.

### O problema que o 1337 resolve

Quando dois agentes de IA se comunicam via linguagem natural, cada mensagem:
- Consome **100–500 tokens** para expressar um estado
- Exige **2–5 segundos** de geração (latência LLM)
- Custa **$0.002–0.02** por mensagem
- É **ambígua** por natureza ("alta prioridade" significa o quê, exatamente?)
- **Não pode ser verificada** formalmente

Com 1337, a mesma informação é transmitida como 128 bytes de floats. Determinístico. Verificável. Gratuito para transportar.

### Resultado medido (25 rounds, 15 agentes, DeepSeek real)

```
Bytes totais — English:    89.812 B
Bytes totais — 1337:       17.339 B
Compressão:                5,18×   (−80,7%)

Com SparseDelta (68,5% das mensagens):
  COGON completo:          166 B
  SparseDelta médio:        52 B   (−68,6%)

Tokens consumidos pelo transporte 1337:   0
Custo de transporte 1337:                 $0,00
```

---

## 2. Como o Protocolo Funciona

### Fluxo de uma mensagem

```
Agente A                                    Agente B
   │                                            │
   │  texto: "emergência no pagamento"          │
   │         │                                  │
   │    [SemanticProjector]                     │
   │         │                                  │
   │   COGON(sem=[...], unc=[...])              │
   │         │                                  │
   │   [Wire Encoder]                           │
   │         │                                  │
   │  WireMsg (166B ou SparseDelta 52B) ───────>│
   │                                            │
   │                                     [Wire Decoder]
   │                                            │
   │                                     COGON reconstruído
   │                                            │
   │                                     [SemanticProjector.reconstruct]
   │                                            │
   │                              "pagamento com anomalia crítica,
   │                               urgência máxima, ação requerida"
```

### O que acontece em cada etapa

**1. Projeção semântica (Texto → COGON)**

O texto de entrada é mapeado para um ponto no espaço semântico de 32 dimensões. Cada dimensão tem um significado preciso — por exemplo, `C1 (URGÊNCIA)` vai de `0.0` (sem pressa) a `1.0` (emergência crítica). O mapeamento pode ser feito por:
- **MockProjector**: heurística baseada em palavras-chave (sem API)
- **AnthropicProjector**: Claude interpreta semanticamente cada eixo

**2. Wire encoding**

O COGON é serializado em **MessagePack** (binário posicional). O campo `unc` é **omitido** pois pode ser recomputado deterministicamente no receptor. A partir do segundo COGON de um agente, apenas os **eixos que mudaram** (SparseDelta) são transmitidos.

**3. Validação R1–R21**

Antes de ser aceita, cada mensagem passa por 21 regras formais que garantem integridade estrutural — sem ciclos no DAG, dimensões corretas, intents válidos, etc.

**4. Reconstrução**

O receptor reconstrói o COGON, recomputa `unc`, aplica delta se necessário, e pode opcionalmente gerar texto descritivo a partir do vetor semântico.

---

## 3. Arquitetura do Projeto

```
1337/
│
├── python/leet/                 ← SDK Python principal (v0.5.0)
│   ├── __init__.py              ← API pública — imports consolidados
│   ├── types.py                 ← Cogon, Dag, Msg1337, Intent, Edge, Raw
│   ├── axes.py                  ← 32 eixos canônicos com descrições
│   ├── operators.py             ← blend, dist, delta, focus, anomaly_score
│   ├── bridge.py                ← SemanticProjector, MockProjector, encode/decode
│   ├── validate.py              ← validate() e check_confidence() — R1-R21
│   ├── context.py               ← ContextProfile, ContextManager (5 perfis embutidos)
│   ├── cache.py                 ← Cache multi-backend: Memory, SQLite, Redis, MongoDB
│   ├── batch.py                 ← BatchProcessor, ProjectionBatcher, StreamingBatcher
│   ├── metrics.py               ← MetricsCollector, Prometheus, OpenTelemetry
│   ├── config.py                ← LeetConfig, from_env(), from_file()
│   ├── cli.py                   ← CLI `leet` (encode, decode, blend, dist, axes, validate)
│   ├── adapters/                ← Adaptadores para ferramentas IDE
│   │   ├── base.py              ← BaseIDEAdapter, AdapterContext, AdapterResponse
│   │   ├── claude_code.py       ← Claude Code CLI (Anthropic)
│   │   ├── codex.py             ← OpenAI Codex
│   │   ├── kimi.py              ← Moonshot Kimi
│   │   └── aider.py             ← Aider (multi-LLM)
│   └── client/                  ← Clientes de rede
│       ├── grpc_client.py       ← GrpcClient → leet-service
│       ├── zmq_client.py        ← ZmqClient (PUB/SUB, REQ/REP, PUSH/PULL)
│       ├── websocket_client.py  ← WebSocketClient (real-time)
│       ├── agent.py             ← Agent1337 (participante completo)
│       ├── pool.py              ← ClientPool, StickyClientPool
│       └── resilient_client.py  ← Retry, circuit breaker, fallback
│
├── leet-py/leet/                ← SDK leve de alto nível
│   ├── __init__.py              ← connect() — único ponto de entrada
│   ├── client.py                ← LeetClient
│   ├── providers.py             ← ProviderAdapter (Anthropic, OpenAI, DeepSeek, Gemini, Ollama)
│   ├── network.py               ← AgentNetwork
│   ├── agent.py                 ← @agent decorator, AgentContext
│   ├── response.py              ← Response types
│   └── stats.py                 ← Estatísticas de sessão
│
├── leet1337/ (Rust)
│   ├── leet-core/               ← Tipos, operadores, wire format, validação
│   │   └── src/
│   │       ├── types.rs         ← Cogon, Dag, Msg1337 (espelham Python)
│   │       ├── operators.rs     ← blend, dist, delta, sparse_delta, apply_patch
│   │       ├── wire.rs          ← WireMsg, WireCogon, SparseDelta, codec MsgPack
│   │       ├── axes.rs          ← 32 eixos com constantes A0–C10
│   │       └── validate.rs      ← Validador Rust R1–R21
│   ├── leet-service/            ← Servidor gRPC (Rust)
│   │   └── src/
│   │       ├── config.rs        ← Config::from_env()
│   │       └── projection/
│   │           ├── engine.rs    ← Engine com LRU cache (1024 entradas)
│   │           ├── matrix.rs    ← WMatrix SIMD GEMM (AVX2/AVX-512)
│   │           ├── batch.rs     ← BatchQueue — coleta e dispatch único
│   │           └── embed.rs     ← Embedder trait (Mock, OpenAI)
│   ├── leet-cli/                ← Binário `leet` (Rust)
│   └── leet-bridge/             ← Bridge texto↔semântico
│
├── comparison_1337_vs_english.py  ← Benchmark com 15 agentes + DeepSeek
├── setup.py                       ← Configuração interativa (.env)
├── docker-compose.yml             ← leet-service + Redis + Prometheus + Grafana
└── Dockerfile                     ← Imagem do leet-service
```

---

## 4. Features Implementadas

### Protocolo e tipos
- [x] **COGON** — unidade semântica atômica: `id + sem[32] + unc[32] + stamp`
- [x] **COGON_ZERO** — "EU SOU" — utterance primordial (`sem=[1]*32, unc=[0]*32`)
- [x] **DAG** — grafo acíclico para conceitos compostos com 5 tipos de aresta
- [x] **MSG_1337** — envelope completo com sender, receiver, intent, payload, C5
- [x] **6 Intents**: ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK
- [x] **Raw payload** com roles: EVIDENCE, ARTIFACT, TRACE, BRIDGE
- [x] **32 eixos canônicos** em 3 grupos: Ontológico (A), Epistêmico (B), Pragmático (C)

### Validação
- [x] **21 regras R1–R21** aplicadas a toda mensagem
- [x] **check_confidence()** — flags de dimensões com `unc > 0.9`
- [x] Validação disponível em Python e Rust (seleção automática de backend)

### Operadores semânticos
- [x] **BLEND** — fusão interpolada de dois COGONs com peso `α`
- [x] **DIST** — distância cosseno ponderada por incerteza
- [x] **DELTA** — diferença vetorial entre estados
- [x] **FOCUS** — projeção em subconjunto de dimensões
- [x] **ANOMALY_SCORE** — desvio em relação ao histórico
- [x] **APPLY_PATCH** — reconstrói COGON a partir de delta

### Bridge semântico
- [x] **MockProjector** — heurística por palavras-chave, sem API, determinístico
- [x] **AnthropicProjector** — Claude como motor de projeção semântica
- [x] `encode(text)` e `decode(cogon)` como funções de conveniência

### Wire format (compressão de transporte)
- [x] **MessagePack** — serialização binária posicional (sem nomes de campo)
- [x] **WireCogon** — `unc` omitido, recomputado deterministicamente no receptor
- [x] **SparseDelta** — só transmite eixos alterados (média: 4 eixos = 52B vs 166B)
- [x] **SessionId** compacto: 4B prefix + 4B seq (vs 32B dois UUIDs)
- [x] **WireIntent** enum 1 byte
- [x] `encode()` / `decode()` disponíveis em Rust e Python

### Context-aware projection
- [x] **ContextProfile** — lente semântica por domínio (`axis_weights[32]`, `temperature`)
- [x] **5 perfis embutidos**: `technical`, `emergency`, `philosophical`, `planning`, `social`
- [x] **ContextManager** — histórico com janela deslizante e fator de decaimento
- [x] **Detecção de drift** de contexto com threshold configurável
- [x] Criação de perfis customizados a partir de exemplos

### Cache multi-backend
- [x] **MemoryCache** — LRU thread-safe, sem persistência
- [x] **SQLiteCache** — persistente em arquivo `.leet_cache.db`, TTL por entrada
- [x] **RedisCache** — distribuído, TTL automático, prefixo `leet:`
- [x] **MongoCache** — cluster MongoDB, índice TTL, LRU por `last_accessed`
- [x] Interface unificada — trocar backend sem mudar código
- [x] `get_or_compute()` — padrão cache-aside em uma linha

### Batch processing
- [x] **BatchProcessor** — genérico, paralelismo controlado, progress callback
- [x] **ProjectionBatcher** — especializado para text→COGON em lote
- [x] **StreamingBatcher** — processa fluxo contínuo sem acumular tudo em memória

### Métricas e observabilidade
- [x] **MetricsCollector** — contadores, histogramas, taxas de acerto de cache
- [x] **Exportação Prometheus** — endpoint compatível com `/metrics`
- [x] **Decorator `@timed`** e context manager `timed_context()`
- [x] Estrutura pronta para **OpenTelemetry**

### Clientes de rede
- [x] **GrpcClient** — conecta ao leet-service: encode, decode, delta, recall, health
- [x] **ZmqClient** — ZeroMQ com 4 modos: PUB/SUB, REQ/REP, PUSH/PULL, ROUTER
- [x] **WebSocketClient** — real-time, auto-reconnect, backoff exponencial
- [x] **ClientPool** — round-robin entre múltiplos endpoints
- [x] **StickyClientPool** — mesmo agente sempre no mesmo cliente
- [x] **ResilientClient** — retry, circuit breaker, fallback automático

### Agente completo
- [x] **Agent1337** — participante de primeira classe na rede 1337
- [x] `send_assert()`, `send_query()`, `send_delta()`, `send_anomaly()`, `send_ack()`
- [x] `receive()` — iterator assíncrono de mensagens recebidas

### Adaptadores IDE
- [x] **ClaudeCodeAdapter** — integra com `claude` CLI (Anthropic), projeta respostas para COGON
- [x] **CodexAdapter** — integra com OpenAI Codex
- [x] **KimiAdapter** — integra com Moonshot Kimi (até 2M tokens de contexto)
- [x] **AiderAdapter** — integra com Aider (multi-LLM), auto-commit, test/lint hooks
- [x] `create_adapter(name)` — factory function unificada

### Backend Rust (leet-service)
- [x] Servidor **gRPC** em Rust com Tokio
- [x] **SIMD GEMM** via `matrixmultiply` (AVX2/AVX-512 automático)
- [x] **Batch de encoding**: coleta requisições em janela de 10ms, 1 multiplicação de matriz
- [x] **LRU cache** de embeddings (1024 entradas) — textos repetidos sem chamada ao embedder
- [x] **3 stores**: memory, Redis, SQLite (em andamento)
- [x] **2 embedders**: mock, OpenAI API
- [x] **Docker** completo com Redis, Prometheus, Grafana

---

## 5. Instalação

### Requisitos
- Python 3.10 ou superior
- Rust 1.75+ (apenas para o backend Rust — opcional)

### Instalação do SDK Python

```bash
# Básico (apenas dependência aiohttp)
pip install -e python/

# Com suporte a Anthropic
pip install -e "python/[anthropic]"

# Com suporte a OpenAI
pip install -e "python/[openai]"

# Com suporte a gRPC
pip install -e "python/[grpc]"

# Com suporte a Redis
pip install -e "python/[redis]"

# Tudo incluído
pip install -e "python/[all]"

# Para desenvolvimento (inclui pytest, black, mypy, ruff)
pip install -e "python/[dev]"
```

### Instalação do leet-py (SDK leve)

```bash
pip install -e leet-py/
```

### Build do backend Rust (opcional)

```bash
cd leet1337
cargo build --release

# Instalar o CLI no PATH
cargo install --path leet-cli

# Verificar
leet version
```

### Iniciar com Docker

```bash
# Tudo com Redis, Prometheus e Grafana
docker compose up

# Só o essencial
docker compose up leet-service redis
```

---

## 6. Conceitos Fundamentais

### COGON — Unidade Semântica Atômica

```
COGON = id (UUID) + sem[32] (f32) + unc[32] (f32) + stamp (i64 ns)
```

- **`sem[i]`** ∈ [0.0, 1.0] — valor semântico na dimensão `i`
  - `0.0` = ausência / mínimo da dimensão
  - `0.5` = neutro
  - `1.0` = máximo / presença total
- **`unc[i]`** ∈ [0.0, 1.0] — incerteza na dimensão `i`
  - `0.0` = certeza total
  - `0.9+` = baixa confiança (flag R5)
  - `1.0` = dimensão completamente desconhecida

### Espaço de 32 Dimensões

As 32 dimensões estão organizadas em 3 grupos que respondem perguntas diferentes:

| Grupo | Índices | Pergunta |
|-------|---------|----------|
| **A — Ontológico** | 0–13 | O que *é* este conceito? |
| **B — Epistêmico** | 14–21 | O que se *sabe* sobre ele? |
| **C — Pragmático** | 22–31 | O que *fazer* com ele? |

### DAG — Conceitos Compostos

Quando uma ideia é muito complexa para um único COGON, usa-se um DAG:

```
"A anomalia nos pagamentos causou aumento de urgência"

Nó A (anomalia)  ──CAUSA──>  Nó B (urgência)
                             ──REFINA──>  Nó C (pagamentos)
```

Tipos de aresta: `CAUSA`, `CONDICIONA`, `CONTRADIZ`, `REFINA`, `EMERGE`

### MSG_1337 — Envelope Completo

```python
MSG_1337 = {
    "id": uuid,
    "sender": "agente-001",
    "receiver": "agente-002" | None,  # None = broadcast
    "intent": ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK,
    "payload": Cogon | Dag,
    "c5": CanonicalSpace,    # zona de handshake
    "surface": Surface,      # metadados legíveis por humano
    "ref_hash": str | None,  # para DELTA: hash da msg de referência
    "patch": [f32] | None,   # para DELTA: diferença vetorial
}
```

---

## 7. SDK Python — Guia Completo de Uso

### Importação

```python
# API completa — importar direto de `leet`
from leet import (
    # Tipos
    Cogon, Dag, Edge, Msg1337, Raw, RawRole,
    Intent, EdgeType, Receiver, Surface, CanonicalSpace,
    # Operadores
    blend, dist, delta, focus, anomaly_score, apply_patch,
    # Eixos
    Axis, AxisGroup, CANONICAL_AXES, axis, axes_in_group,
    # Bridge
    SemanticProjector, MockProjector, encode, decode,
    # Contexto
    ContextProfile, ContextManager,
    get_context_manager, set_context_profile, adjust_with_context,
    # Cache
    Cache, get_cache, set_cache,
    # Validação
    validate, check_confidence,
    # Configuração
    LeetConfig, get_config,
    # Versão e constantes
    __version__, FIXED_DIMS, BACKEND,
)
```

---

### 7.1 Tipos do protocolo

#### Cogon

```python
from leet import Cogon, Raw, RawRole
import asyncio

# ── Criação ─────────────────────────────────────────────────────────────────

# Auto UUID + timestamp atual
cogon = Cogon.new(
    sem=[0.5] * 32,  # neutro em todas as dimensões
    unc=[0.1] * 32,  # alta certeza
)

# COGON_ZERO — "EU SOU" — utterance primordial
zero = Cogon.zero()
print(zero.is_zero())  # True
# sem = [1.0, 1.0, ..., 1.0]
# unc = [0.0, 0.0, ..., 0.0]
# id  = 00000000-0000-0000-0000-000000000000
# stamp = 0

# Com valores específicos por dimensão
sem = [0.5] * 32
sem[22] = 0.95   # C1_URGÊNCIA — urgência crítica
sem[26] = 0.88   # C5_ANOMALIA — anomalia detectada
sem[23] = 0.90   # C2_IMPACTO  — alto impacto
sem[14] = 0.85   # B1_VERIFICABILIDADE — verificável
unc = [0.05] * 32  # alta certeza geral

cogon = Cogon.new(sem=sem, unc=unc)

# ── Inspecionar ─────────────────────────────────────────────────────────────

print(f"ID: {cogon.id}")
print(f"Urgência:  {cogon.sem[22]:.2f}")  # C1
print(f"Anomalia:  {cogon.sem[26]:.2f}")  # C5
print(f"Incerteza média: {sum(cogon.unc)/32:.3f}")

low_conf = cogon.low_confidence_dims()
# Eixos com unc > 0.9 (R5)

# ── Payload bruto (RAW) ──────────────────────────────────────────────────────

raw = Raw(
    content_type="text/plain",
    content="Pagamento #4421 rejeitado inesperadamente",
    role=RawRole.EVIDENCE,
)
cogon_com_evidencia = cogon.with_raw(raw)

# ── Serialização ─────────────────────────────────────────────────────────────

json_str = cogon.to_json()
cogon2   = Cogon.from_json(json_str)
```

#### Dag

```python
from leet import Cogon, Dag, Edge, EdgeType

# Construir conceito composto: "anomalia causou urgência"
c_anomalia = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
c_anomalia.sem[26] = 0.9  # C5

c_urgencia = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
c_urgencia.sem[22] = 0.95  # C1

# Montar DAG
dag = Dag.from_root(c_anomalia)
dag.add_node(c_urgencia)
dag.add_edge(Edge(
    from_id=c_anomalia.id,
    to_id=c_urgencia.id,
    edge_type=EdgeType.CAUSA,
    weight=0.9,
))

# Navegar
pais = dag.parents_of(c_urgencia.id)  # [c_anomalia.id]
ordem = dag.topological_order()        # [c_anomalia, c_urgencia]
```

#### Msg1337

```python
from leet import Cogon, Msg1337, Intent, Surface, CanonicalSpace
import uuid, time

cogon = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)

msg = Msg1337(
    id=str(uuid.uuid4()),
    sender="agente-monitor",
    receiver="agente-resposta",       # None = broadcast
    intent=Intent.ASSERT,
    payload=cogon,
    c5=CanonicalSpace(
        align_hash="sha256_primeiros_4_bytes",
        zone_emergent={},
    ),
    surface=Surface(
        text="Anomalia detectada no gateway de pagamentos",
        lang="pt-BR",
        confidence=0.92,
    ),
    ref_hash=None,
    patch=None,
)

# Hash da mensagem (para DELTA posterior)
h = msg.hash()

# Serializar
json_str = msg.to_json()
msg2     = Msg1337.from_json(json_str)

# Mensagem DELTA — atualização incremental
patch_vector = [0.0] * 32
patch_vector[22] = +0.05  # urgência subiu um pouco

msg_delta = Msg1337(
    id=str(uuid.uuid4()),
    sender="agente-monitor",
    receiver="agente-resposta",
    intent=Intent.DELTA,
    payload=cogon,
    c5=msg.c5,
    surface=Surface(text="Urgência aumentou", lang="pt-BR", confidence=0.8),
    ref_hash=h,          # hash da mensagem de referência
    patch=patch_vector,  # diferença semântica
)
```

---

### 7.2 Operadores semânticos

```python
from leet import Cogon, blend, dist, delta, focus, anomaly_score, apply_patch

c1 = Cogon.new(sem=[0.8]*32, unc=[0.1]*32)
c2 = Cogon.new(sem=[0.2]*32, unc=[0.3]*32)

# ── BLEND — fusão ponderada ─────────────────────────────────────────────────
# sem_out[i] = α × sem1[i] + (1−α) × sem2[i]
# unc_out[i] = max(unc1[i], unc2[i])  ← conservador

fusao     = blend(c1, c2, alpha=0.5)  # peso igual
peso_c1   = blend(c1, c2, alpha=0.8)  # favorece c1
peso_c2   = blend(c1, c2, alpha=0.2)  # favorece c2

# ── DIST — distância semântica ──────────────────────────────────────────────
# Coseno ponderado por (1 − max_unc)
# 0.0 = idênticos | 1.0 = opostos

d = dist(c1, c2)
print(f"Distância: {d:.4f}")  # → ~0.6 para vetores divergentes

# ── DELTA — diferença vetorial ──────────────────────────────────────────────
# patch[i] = c2.sem[i] − c1.sem[i]

patch = delta(c1, c2)  # list[float], len=32
print(f"Eixo 22 mudou: {patch[22]:+.3f}")

# ── APPLY_PATCH — reconstrói COGON a partir de delta ────────────────────────
# sem_result[i] = clamp(base.sem[i] + patch[i], 0, 1)

c_atualizado = apply_patch(c1, patch)

# ── FOCUS — projeção em subconjunto de dimensões ────────────────────────────
# Dims selecionadas: mantém sem/unc
# Dims não selecionadas: sem=0.0, unc=1.0

# Focar apenas no grupo Pragmático (C1-C10 = eixos 22-31)
c_pragmatico = focus(c1, dims=list(range(22, 32)))

# Focar só em urgência (C1) e anomalia (C5)
c_alerta = focus(c1, dims=[22, 26])

# ── ANOMALY_SCORE — desvio do histórico ─────────────────────────────────────
# Retorna distância média do cogon ao centroide do histórico
# 1.0 se histórico vazio | > 0.5 = desvio significativo

historico = [Cogon.new(sem=[0.5]*32, unc=[0.1]*32) for _ in range(10)]
novo_cogon = Cogon.new(sem=[0.9]*32, unc=[0.05]*32)

score = anomaly_score(novo_cogon, historico)
if score > 0.5:
    print(f"Anomalia detectada! score={score:.3f}")
```

---

### 7.3 Bridge: texto ↔ COGON

```python
import asyncio
from leet import encode, decode, MockProjector

# ── encode — texto para COGON ────────────────────────────────────────────────

async def exemplo_encode():
    # MockProjector por padrão (sem API)
    cogon = await encode("emergência crítica no sistema de pagamentos")
    print(f"C1 (Urgência):  {cogon.sem[22]:.3f}")  # alto
    print(f"C5 (Anomalia):  {cogon.sem[26]:.3f}")  # alto
    print(f"C2 (Impacto):   {cogon.sem[23]:.3f}")  # alto

    # MockProjector explícito
    projector = MockProjector()
    cogon2 = await encode("amor é eterno", projector)
    print(f"C6 (Afeto):   {cogon2.sem[27]:.3f}")   # alto

    # AnthropicProjector (requer ANTHROPIC_API_KEY)
    from leet.bridge import AnthropicProjector
    proj_claude = AnthropicProjector()
    cogon3 = await encode("o sistema está instável", proj_claude)

    return cogon

cogon = asyncio.run(exemplo_encode())

# ── decode — COGON para texto ────────────────────────────────────────────────

async def exemplo_decode():
    projector = MockProjector()
    texto = await decode(cogon, projector)
    print(texto)
    # → descrição do estado semântico em linguagem natural

asyncio.run(exemplo_decode())
```

**Palavras-chave que ativam eixos no MockProjector:**

| Palavras | Eixos ativados |
|----------|----------------|
| urgente, crítico, emergência | C1 (Urgência) ↑ |
| anomalia, erro, falha, caiu | C5 (Anomalia) ↑, A8 (Estado) ↑ |
| amor, belo, afeto | C6 (Afeto) ↑, A13 (Valência) ↑ |
| causa, efeito, porque | A5 (Causa) ↑, B4 (Causalidade) ↑ |
| sistema, rede, protocolo | A7 (Sistema) ↑ |
| prova, teorema, axioma | B1 (Verificabilidade) ↑ |

---

### 7.4 Validação R1–R21

```python
from leet import validate, check_confidence, Msg1337, Intent

# ── validate() — retorna None se ok, string de erro se inválido ──────────────

error = validate(msg)
if error is None:
    print("✓ Mensagem válida")
else:
    print(f"✗ Inválida: {error}")
    # Exemplos:
    # "R2: DELTA intent requires ref_hash and patch"
    # "R3: Edge references unknown node abc-123"
    # "R4: DAG contains a cycle"
    # "R8: BROADCAST receiver only for ANOMALY/SYNC"
    # "R10: sem must have 32 dimensions, got 16"

# ── check_confidence() — dimensões com unc > 0.9 ────────────────────────────

warnings = check_confidence(msg)
for cogon_id, dim_idx, unc_val in warnings:
    from leet import axis
    ax = axis(dim_idx)
    print(f"Atenção: {ax.name} (eixo {dim_idx}) incerteza={unc_val:.2f}")

# ── Regras R1–R21 resumidas ──────────────────────────────────────────────────

# R1  Single Intent  — todo MSG tem exatamente um intent
# R2  Delta Ref      — DELTA exige ref_hash + patch; outros não podem ter patch
# R3  DAG Nodes      — toda aresta referencia nó presente em DAG.nodes
# R4  No Cycles      — DAG deve ser acíclico (Kahn's algorithm)
# R5  Low Confidence — unc[i] > 0.9 dispara flag (não é erro, é aviso)
# R6  Urgency        — human_required=true exige campo urgency não-nulo
# R7  Zone Emergent  — chaves de zone_emergent referenciam IDs de handshake
# R8  Broadcast      — receiver=None só para ANOMALY e SYNC
# R9  Evidence       — RAW EVIDENCE exige sem não-zero e unc baixa
# R10 Vector Dims    — sem e unc devem ter exatamente 32 dimensões
# R11 Append Only    — chaves emergentes devem ter índice >= 32
# R14 Parents First  — nós pai processados antes dos filhos no DAG
# R17 Canonical Order — serialização JSON em ordem canônica
# R19 Depth          — herança máx 4 níveis (MAX_INHERITANCE_DEPTH = 4)
# R20 COGON_ZERO     — agentes transmitem COGON_ZERO ao iniciar sessão
# R21 Bridge Security — bridge nunca expõe interior da rede 1337
```

---

### 7.5 Contexto e perfis

```python
from leet import (
    ContextManager, ContextProfile,
    get_context_manager, set_context_profile, adjust_with_context,
)

# ── Perfis embutidos ─────────────────────────────────────────────────────────

# "technical"     — sistemas, processos, estados
# "emergency"     — urgência máxima, ação imediata
# "philosophical" — essência, correspondência, completude
# "planning"      — processo, reversibilidade, vetor temporal
# "social"        — relação, sinal, afeto, valor

# ── Usar perfil global ───────────────────────────────────────────────────────

set_context_profile("technical")

# Ajustar projeção com contexto atual
sem = [0.5] * 32
unc = [0.2] * 32
sem_ajustado, unc_ajustado = adjust_with_context(sem, unc, context_alpha=0.2)
# context_alpha = quanto o perfil influencia (0 = sem influência, 1 = só perfil)

# ── Usar ContextManager diretamente ─────────────────────────────────────────

mgr = ContextManager(
    window_size=10,     # janela de histórico
    decay_factor=0.8,   # peso de COGONs antigos decai por 0.8 a cada passo
)

# Ativar perfil
perfil = mgr.set_profile("emergency")

# Acumular histórico
mgr.add_to_history(cogon_anterior)
mgr.add_to_history(cogon_atual)

# COGON representando o contexto acumulado
contexto = mgr.get_context_cogon(alpha=0.3)

# Ajustar projeção com contexto
sem_adj, unc_adj = mgr.adjust_projection(sem, unc, context_alpha=0.2)

# Detectar drift de contexto
aviso = mgr.detect_context_drift(threshold=0.5)
if aviso:
    print(f"Contexto mudou: {aviso}")

# ── Criar perfil customizado ─────────────────────────────────────────────────

perfil_custom = ContextProfile(
    name="financeiro",
    description="Domínio financeiro — foco em estado, causalidade, urgência",
    axis_weights=[
        0.5, 0.5, 0.4, 0.5,  # A0-A3
        0.5, 0.8, 0.6, 0.8,  # A4-A7: sistema, causa
        0.9, 0.8, 0.7, 0.7,  # A8-A11: estado, processo
        0.7, 0.5,             # A12-A13
        0.9, 0.7, 0.8, 0.9,  # B1-B4: verificável, causal
        0.7, 0.5, 0.8, 0.7,  # B5-B8
        0.8, 0.9, 0.8, 0.7,  # C1-C4: urgência, impacto, ação
        0.8, 0.4, 0.8, 0.5,  # C5-C8: anomalia
        0.5, 0.6,             # C9-C10
    ],
    temperature=1.2,
    dominant_axes=[8, 17, 22, 23, 26],  # A8, B4, C1, C2, C5
)

mgr_custom = ContextManager()
mgr_custom.profiles["financeiro"] = perfil_custom
mgr_custom.set_profile("financeiro")

# Exportar / importar perfil
mgr.export_profile("technical", "perfil_tecnico.json")
mgr.import_profile("perfil_tecnico.json")
```

---

### 7.6 Cache

```python
from leet import Cache, get_cache, set_cache

# ── Memory (padrão — LRU, sem persistência) ──────────────────────────────────

cache_mem = Cache(backend="memory", max_size=10_000)

# ── SQLite (persistente em arquivo) ─────────────────────────────────────────

cache_sqlite = Cache(backend="sqlite", path=".leet_cache.db")

# ── Redis (distribuído) ──────────────────────────────────────────────────────

cache_redis = Cache(backend="redis", url="redis://localhost:6379")

# ── MongoDB ──────────────────────────────────────────────────────────────────

cache_mongo = Cache(
    backend="mongodb",
    uri="mongodb://localhost:27017",
    db_name="leet_cache",
)

# ── Interface unificada ──────────────────────────────────────────────────────

cache = cache_sqlite  # trocar backend sem mudar código abaixo

cache.set("minha-chave", {"dados": 42}, ttl_seconds=3600)
valor = cache.get("minha-chave")
cache.delete("minha-chave")
cache.clear()

# Stats
stats = cache.get_stats()
print(stats)  # {"backend": "sqlite", "size": 1234, "default_ttl_seconds": 3600}

# Cache-aside em uma linha
resultado = cache.get_or_compute(
    key="embedding:amor",
    compute_fn=lambda: projetor.project("amor"),
    ttl_seconds=86_400,
)

# Cache de projeções (chave automática por hash do texto)
cache.set_projection("amor é eterno", sem=[...], unc=[...], ttl_seconds=3600)
cached = cache.get_projection("amor é eterno")

# ── Cache global singleton ────────────────────────────────────────────────────

global_cache = get_cache()       # instância global (Memory por padrão)
set_cache(cache_redis)           # substituir instância global
```

---

### 7.7 Batch processing

```python
import asyncio
from leet.batch import BatchProcessor, BatchConfig, ProjectionBatcher, StreamingBatcher
from leet import MockProjector, encode

# ── BatchProcessor genérico ──────────────────────────────────────────────────

async def processar_texto(texto: str):
    return await encode(texto)

processor = BatchProcessor(
    processar_texto,
    BatchConfig(
        batch_size=100,
        max_concurrency=10,     # máx 10 chamadas simultâneas
        continue_on_error=True, # não abortar se um item falhar
        error_threshold=0.5,    # abortar se >50% de erros
        progress_interval=10,   # reportar a cada 10 itens
    ),
)

textos = ["texto 1", "texto 2", "texto 3", "..."]

# Iterador assíncrono
async def processar_batch():
    async for resultado in processor.process(textos):
        if resultado.success:
            print(f"[{resultado.index}] sem[22]={resultado.output.sem[22]:.3f}")
        else:
            print(f"[{resultado.index}] ERRO: {resultado.error}")

    # Ou coletar tudo de uma vez
    resultados = await processor.process_to_list(textos)
    cogons = [r.output for r in resultados if r.success]

asyncio.run(processar_batch())

# ── ProjectionBatcher — especializado para text→COGON ───────────────────────

async def projetar_lote():
    projector = MockProjector()
    batcher   = ProjectionBatcher(projector, BatchConfig(max_concurrency=5))

    textos = ["amor", "morte", "urgência", "sistema", "anomalia"]
    pares  = await batcher.project(textos)  # [(texto, cogon), ...]

    for texto, cogon in pares:
        print(f"{texto:15s} → urgência={cogon.sem[22]:.3f} afeto={cogon.sem[27]:.3f}")

    # Com cache integrado
    from leet import get_cache
    pares_cacheados = await batcher.project_with_cache(textos, get_cache())

asyncio.run(projetar_lote())

# ── StreamingBatcher — fluxo contínuo sem acumular em memória ────────────────

async def processar_stream():
    batcher = StreamingBatcher(
        process_fn=processar_texto,
        max_buffer=100,
        max_concurrency=10,
    )

    # Alimentar stream
    for texto in fonte_de_dados_infinita():
        await batcher.put(texto)

    # Consumir resultados
    async for resultado in batcher.results():
        print(resultado.output)

    # Fechar e coletar restantes
    ultimos = await batcher.close()
```

---

### 7.8 Métricas e observabilidade

```python
from leet.metrics import MetricsCollector, get_metrics, timed_context
import functools

# ── Coletor ──────────────────────────────────────────────────────────────────

metrics = MetricsCollector()

# Registrar manualmente
metrics.record_projection(duration_ms=150.0, cached=False)
metrics.record_projection(duration_ms=0.5,   cached=True)
metrics.record_operation("blend", duration_ms=0.3)
metrics.record_cache_hit()
metrics.record_cache_miss()
metrics.record_request(duration_ms=200.0, success=True)
metrics.record_request(duration_ms=5000.0, success=False)

# Consultar
print(f"Cache hit rate:    {metrics.cache_hit_rate:.1%}")
print(f"Request success:   {metrics.request_success_rate:.1%}")

# ── Decorator @timed ─────────────────────────────────────────────────────────

from leet.metrics import timed

@timed("projection", metrics)
async def encode_monitorado(texto: str):
    return await encode(texto)

# ── Context manager ──────────────────────────────────────────────────────────

with timed_context("blend", metrics):
    resultado = blend(c1, c2, alpha=0.5)

# ── Prometheus export ─────────────────────────────────────────────────────────

prometheus_text = metrics.export_prometheus()
print(prometheus_text)
# # HELP leet_projections_total Total de projeções
# # TYPE leet_projections_total counter
# leet_projections_total 2.0
# leet_projections_cached 1.0
# leet_projection_duration_ms_bucket{le="1"} 1
# ...

# ── Exportar como dicionário ──────────────────────────────────────────────────

dados = metrics.export_dict()
# {
#   "projections_total": 2,
#   "projections_cached": 1,
#   "cache_hit_rate": 0.5,
#   "projection_p50_ms": 75.0,
#   "projection_p95_ms": 142.0,
#   ...
# }

# ── Métricas globais ──────────────────────────────────────────────────────────

global_metrics = get_metrics()  # singleton compartilhado por todo o SDK
```

---

### 7.9 Clientes de rede

```python
import asyncio
from leet.client import GrpcClient, GrpcConfig, ZmqClient, ZmqMode, WebSocketClient

# ── gRPC ─────────────────────────────────────────────────────────────────────

async def usar_grpc():
    config = GrpcConfig(host="localhost", port=50051, timeout=30.0)

    async with GrpcClient(config) as client:
        # Codificar texto → COGON
        result = await client.encode("emergência no gateway", agent_id="monitor-01")
        cogon  = result.to_cogon()
        print(f"Urgência: {cogon.sem[22]:.3f}")

        # Decodificar COGON → texto
        texto = await client.decode(cogon)

        # Delta entre dois estados
        patch = await client.delta(cogon_anterior, cogon_atual)

        # Busca por similaridade
        similares = await client.recall(query_cogon, limit=10)

        # Saúde
        ok = await client.health()
        print("Serviço OK" if ok else "Serviço fora")

asyncio.run(usar_grpc())

# ── ZeroMQ ───────────────────────────────────────────────────────────────────

async def usar_zmq():
    # PUB/SUB — broadcast de COGONs
    pub = ZmqClient(ZmqConfig(address="tcp://localhost:5556", mode=ZmqMode.PUB))
    await pub.send(cogon)

    sub = ZmqClient(ZmqConfig(address="tcp://localhost:5556", mode=ZmqMode.SUB))
    async for msg in sub.receive():
        print(f"Recebido: {msg.cogon.sem[22]:.3f}")

    # REQ/REP — síncrono
    req = ZmqClient(ZmqConfig(address="tcp://localhost:5555", mode=ZmqMode.REQ))
    response = await req.request(cogon)

asyncio.run(usar_zmq())

# ── WebSocket ─────────────────────────────────────────────────────────────────

async def usar_ws():
    client = WebSocketClient("ws://localhost:8765")
    await client.connect()

    # Enviar COGON
    await client.send(cogon)

    # Receber mensagens
    async for msg in client.receive():
        print(msg.cogon.id)

    await client.disconnect()

asyncio.run(usar_ws())

# ── Connection Pool ───────────────────────────────────────────────────────────

from leet.client import ClientPool, StickyClientPool

pool = ClientPool(
    addresses=["localhost:50051", "localhost:50052", "localhost:50053"],
    max_connections=10,
)

# Round-robin
client = pool.get_client()

# Mesmo agente sempre no mesmo cliente
sticky = StickyClientPool(addresses=[...])
client = sticky.get_sticky("agente-financeiro")
```

---

### 7.10 Agente completo

```python
import asyncio
from leet.client import Agent1337, AgentConfig, AgentState

async def rodar_agente():
    config = AgentConfig(
        name="Agente Monitor",
        version="1.0.0",
        capabilities=["encode", "decode", "blend", "anomaly"],
    )

    agente = Agent1337(config)
    await agente.start()

    # Fase 1 — identificação (R20: COGON_ZERO primeiro)
    # (automático ao chamar start())

    # Enviar ASSERT — "estou afirmando este estado"
    await agente.send_assert("Sistema de pagamentos operacional")

    # Enviar QUERY — pergunta a outro agente
    await agente.send_query("Qual o estado atual do gateway?")

    # Enviar DELTA — atualização incremental (economiza banda)
    patch = [0.0] * 32
    patch[22] = +0.15  # urgência aumentou
    await agente.send_delta(ref_hash="abc123", patch=patch)

    # Enviar ANOMALY — broadcast para todos
    await agente.send_anomaly("Pico de latência detectado — P99 = 8s")

    # Enviar ACK — confirmação de recebimento
    await agente.send_ack(ref_msg_id="msg-uuid-456")

    # Receber mensagens
    async for msg in agente.receive():
        print(f"De: {msg.sender}")
        print(f"Intent: {msg.intent}")
        print(f"Urgência: {msg.payload.sem[22]:.3f}")

        if msg.intent.value == "QUERY":
            await agente.send_assert("Gateway operacional, latência P50=120ms")

    await agente.stop()

asyncio.run(rodar_agente())
```

---

### 7.11 Adaptadores IDE

```python
import asyncio
from leet.adapters import (
    ClaudeCodeAdapter, CodexAdapter, KimiAdapter, AiderAdapter,
    AdapterContext, create_adapter, list_adapters,
)

# ── Claude Code ───────────────────────────────────────────────────────────────

async def usar_claude_code():
    adapter = ClaudeCodeAdapter(
        project_dir="/caminho/do/projeto",
        model="claude-sonnet-4-6",
        auto_accept=False,  # pede confirmação antes de modificar arquivos
    )

    if not adapter.is_available():
        print("Claude Code CLI não instalado")
        return

    print(f"Versão: {adapter.get_version()}")

    # Enviar mensagem com contexto de arquivo
    response = await adapter.send_message(
        "Explique a função encode() e sugira melhorias",
        context=AdapterContext(
            file_path="python/leet/bridge.py",
            selection="async def encode(text: str, projector=None) -> Cogon:",
            extra={"task": "review"},
        ),
    )

    print(f"Resposta: {response.text[:200]}...")
    print(f"Arquivos modificados: {response.files_modified}")
    print(f"Urgência semântica: {response.cogon.sem[22]:.3f}")

    # Streaming
    async for chunk in adapter.stream_message("Refatore o método project()"):
        print(chunk, end="", flush=True)

    # Git integration
    diff = await adapter.diff()
    await adapter.accept_changes()  # ou reject_changes()

asyncio.run(usar_claude_code())

# ── Aider ─────────────────────────────────────────────────────────────────────

async def usar_aider():
    adapter = AiderAdapter(
        project_dir="/caminho/do/projeto",
        model="gpt-4o",
        editor_model="gpt-4o-mini",      # modelo mais leve para edições simples
        auto_commit=True,                 # commit automático após mudanças
        test_cmd="pytest tests/ -q",      # rodar testes após mudanças
        lint_cmd="ruff check python/leet/",
    )

    response = await adapter.send_message(
        "Adicione type hints ao arquivo operators.py",
        context=AdapterContext(file_path="python/leet/operators.py"),
    )
    print(response.text)

asyncio.run(usar_aider())

# ── Factory function ─────────────────────────────────────────────────────────

adapter = create_adapter("claude", project_dir="/projeto")
adapter = create_adapter("codex",  model="gpt-4o")
adapter = create_adapter("kimi",   model="kimi-k1.5")
adapter = create_adapter("aider",  auto_commit=False)

disponiveis = list_adapters()  # ["claude", "codex", "kimi", "aider"]
```

---

## 8. leet-py — SDK de Alto Nível

O `leet-py` é um SDK separado e mais simples, ideal para usar 1337 em aplicações que precisam de um único ponto de entrada e suporte a múltiplos providers LLM.

### Instalação

```bash
pip install -e leet-py/
```

### Uso básico

```python
import leet

# ── connect() — único ponto de entrada ───────────────────────────────────────

# Escolher um provider
client = leet.connect("mock")       # sem API — para testes
client = leet.connect("anthropic")  # lê ANTHROPIC_API_KEY do ambiente
client = leet.connect("openai")     # lê OPENAI_API_KEY
client = leet.connect("deepseek")   # lê DEEPSEEK_API_KEY
client = leet.connect("gemini")     # lê GEMINI_API_KEY
client = leet.connect("ollama", model="llama3.2")  # local, sem API

# Parâmetros completos
client = leet.connect(
    provider="anthropic",
    model="claude-opus-4-6",           # modelo específico (opcional)
    base_url="https://...",            # endpoint customizado
    api_key="sk-ant-...",              # ou usa variável de ambiente
    service="auto",                    # "auto" | URL gRPC | "local"
    store="auto",                      # "auto" | redis:// | "memory"
    agent_id="meu-agente",
)
```

### Providers disponíveis

| Provider | Variável de ambiente | Modelo padrão |
|----------|---------------------|---------------|
| `mock` | — | local |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-opus-4-6 |
| `openai` | `OPENAI_API_KEY` | gpt-4o |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat |
| `gemini` | `GEMINI_API_KEY` | gemini-2.0-flash |
| `ollama` | — | llama3.2 |

### Decorator @agent

```python
import leet
from leet import agent, AgentContext

client = leet.connect("anthropic")

@agent(client)
async def monitor_pagamentos(ctx: AgentContext) -> str:
    """Agente que monitora o sistema de pagamentos."""
    # ctx.cogon — estado semântico atual do contexto
    # ctx.history — histórico de COGONs
    # ctx.send() — enviar mensagem
    # ctx.receive() — receber mensagens

    urgencia = ctx.cogon.sem[22]
    if urgencia > 0.8:
        await ctx.send("ALERTA: sistema com urgência crítica")

    return "ok"

# Iniciar o agente
await monitor_pagamentos.run()
```

### Rede de agentes

```python
import leet
from leet import AgentNetwork

# Criar rede
network = AgentNetwork()

client_a = leet.connect("anthropic", agent_id="agente-a")
client_b = leet.connect("deepseek",  agent_id="agente-b")
client_c = leet.connect("mock",      agent_id="agente-c")

network.add(client_a)
network.add(client_b)
network.add(client_c)

# Broadcast para todos
await network.broadcast(cogon)

# Mensagem direta
await network.send("agente-a", cogon, to="agente-b")
```

---

## 9. leet-service — Backend Rust

Servidor gRPC de alta performance que expõe encoding semântico.

### Iniciar

```bash
# Development
LEET_EMBED_MODEL=mock cargo run --release -p leet-service

# Com .env
source .env && cargo run --release -p leet-service

# Docker
docker compose up leet-service redis
```

### Arquitetura interna

```
Requisição de encode("texto")
         │
         ▼
   BatchQueue (coleta por 10ms ou até 64 itens)
         │
         ▼
   Engine.encode_batch(["texto1", "texto2", ...])
         │
    ┌────┴────┐
    │  LRU Cache  │  ← hit? retorna direto
    └────┬────┘
         │ miss
         ▼
   Embedder.embed(texto)         ← mock: ~0.01ms | openai: ~300ms
         │
         ▼
   WMatrix.project_batch()       ← SIMD GEMM único para N textos
   (Array[N, embed_dim].dot(W))  ← AVX2/AVX-512 automático
         │
         ▼
   [Cogon, Cogon, ...]           ← distribuídos aos chamadores via oneshot
```

### Otimizações implementadas

| Técnica | Ganho | Detalhe |
|---------|-------|---------|
| Batch GEMM | ~N× vs serial | N textos → 1 multiplicação de matriz |
| SIMD | ~4–8× | matrixmultiply crate, AVX2/AVX-512 automático |
| LRU cache | ~∞ vs miss | 1024 entradas, textos repetidos = 0 latência |
| SparseDelta | −68.6% banda | só eixos alterados no wire |
| unc omitido | −128B/msg | recomputado deterministicamente |
| SessionId compacto | −75% header | 8B vs 32B dois UUIDs |

---

## 10. leet-cli — Ferramentas de Linha de Comando

### Instalar

```bash
cd leet1337 && cargo install --path leet-cli
```

### Comandos

```bash
# Codificar texto em COGON
leet encode "emergência crítica no gateway"
leet encode "amor é eterno" --json          # saída JSON completa
leet --service prod:50051 encode "teste"    # serviço remoto

# Decodificar vetor semântico
leet decode "0.9,0.5,0.8,0.5,..."

# Inspecionar COGON
leet inspect cogon.json
# Exibe: eixos mais ativos, eixos incertos, grupo dominante, etc.

# Distância semântica entre dois textos
leet dist "amor é eterno" "amor é passageiro"
# Distância semântica: 0.2341

leet dist "emergência crítica" "situação normal"
# Distância semântica: 0.8912

# Benchmark de throughput
leet bench --n 1000             # 1000 encodings sequenciais
leet bench --n 1000 --parallel  # em paralelo

# Verificar saúde do serviço
leet health
# ✓ Service healthy at localhost:50051

# Listar eixos canônicos
leet axes              # todos os 32 eixos
leet axes --group A    # apenas ontológico (0-13)
leet axes --group B    # apenas epistêmico (14-21)
leet axes --group C    # apenas pragmático (22-31)

# Versão
leet version
# leet-cli 0.1.0 (leet-core 0.4.0)
```

### CLI Python (`leet`)

```bash
# Instalado com: pip install -e python/

leet version
leet zero                                     # COGON_ZERO como JSON

leet encode "amor é eterno"
leet encode "emergência" --projector mock
leet encode "urgência" --projector anthropic  # requer ANTHROPIC_API_KEY

leet decode cogon.json
leet decode cogon.json --projector anthropic

leet validate mensagem.json                   # valida R1-R21

leet blend cogon_a.json cogon_b.json          # BLEND com α=0.5
leet blend cogon_a.json cogon_b.json --alpha 0.3

leet dist cogon_a.json cogon_b.json           # distância

leet axes
leet axes --group A
leet axes --group B
leet axes --group C
```

---

## 11. Wire Format — Protocolo de Transmissão

### Tamanhos comparados

```
JSON completo (MSG_1337):      ~700–900 bytes
WireMsg COGON (MsgPack):          166 bytes
WireMsg SparseDelta (4 eixos):     52 bytes

Vs linguagem natural: 5,18× compressão medida
```

### Estrutura do WireMsg

```
┌──────────────────────────────────────────────┐
│ HEADER (14 bytes fixos)                      │
│  SessionId: prefix(4B) + seq(4B)    = 8B    │
│  WireIntent: enum                   = 1B    │
│  align_hash: primeiros 4B de SHA256 = 4B    │
│  payload_tag: Cogon|DAG|Delta       = 1B    │
├──────────────────────────────────────────────┤
│ PAYLOAD                                      │
│                                              │
│ WireCogon:                                   │
│   id(16B) + sem[32×f32=128B] + stamp(8B)    │
│   Total: 152 bytes                           │
│   unc: OMITIDO → recomputado no receptor     │
│                                              │
│ SparseDelta:                                 │
│   ref_id(16B) + n_changes(1B)      = 17B    │
│   changes: n × (idx(1B) + val(4B)) = n×5B  │
│   4 eixos: 17B + 20B = 37B + 14B header     │
└──────────────────────────────────────────────┘
```

### Fórmula de recompute unc

`unc` é omitido do wire e recomputado deterministicamente:

```
unc[i] = (1 − |sem[i] − 0.5| × 2).clamp(0, 1)
```

Intuição: dimensões com valor extremo (0.0 ou 1.0) têm unc=0 (alta certeza), valores centrais (0.5) têm unc=1 (máxima incerteza).

### Quando usar SparseDelta

SparseDelta é enviado quando `|sem_curr[i] − sem_prev[i]| > threshold` (padrão: 0.01).

```
Ruído de fundo (±0.005):   < threshold → nunca entra no delta
Ativação por keyword (±0.3–0.7): > threshold → entra no delta

Resultado típico: 4 eixos alterados por round = 52B vs 166B (−68.6%)
```

---

## 12. Os 32 Eixos Canônicos

### Grupo A — Ontológico (0–13): *O que é?*

| Idx | Código | Nome | Interpretação |
|-----|--------|------|--------------|
| 0 | A0 | VIA | 0=depende de outro / 1=existe por si mesmo |
| 1 | A1 | CORRESPONDÊNCIA | 0=único / 1=padrão em múltiplas escalas |
| 2 | A2 | VIBRAÇÃO | 0=estático / 1=em transformação contínua |
| 3 | A3 | POLARIDADE | 0=neutro / 1=fortemente polar |
| 4 | A4 | RITMO | 0=irregular / 1=padrão cíclico claro |
| 5 | A5 | CAUSA E EFEITO | 0=consequência pura / 1=causa primária |
| 6 | A6 | GÊNERO | 0=princípio receptivo / 1=princípio ativo |
| 7 | A7 | SISTEMA | 0=elemento isolado / 1=conjunto emergente |
| 8 | A8 | ESTADO | 0=sem configuração definida / 1=estado claro |
| 9 | A9 | PROCESSO | 0=estático / 1=transformação no tempo |
| 10 | A10 | RELAÇÃO | 0=autônomo / 1=conexão entre entidades |
| 11 | A11 | SINAL | 0=sem informação / 1=carregado de variação |
| 12 | A12 | ESTABILIDADE | 0=instável/caótico / 1=convergente |
| 13 | A13 | VALÊNCIA ONTOLÓGICA | 0=negativo/contrativo / 0.5=neutro / 1=positivo |

### Grupo B — Epistêmico (14–21): *O que se sabe?*

| Idx | Código | Nome | Interpretação |
|-----|--------|------|--------------|
| 14 | B1 | VERIFICABILIDADE | 0=não falsificável / 1=verificável externamente |
| 15 | B2 | TEMPORALIDADE | 0=atemporal / 1=âncora temporal precisa |
| 16 | B3 | COMPLETUDE | 0=aberto/em construção / 1=fechado/conclusivo |
| 17 | B4 | CAUSALIDADE | 0=origem opaca / 1=causa identificável |
| 18 | B5 | REVERSIBILIDADE | 0=irreversível / 1=completamente reversível |
| 19 | B6 | CARGA | 0=automático/fluido / 1=pesado cognitivamente |
| 20 | B7 | ORIGEM | 0=suposição pura / 1=observação direta |
| 21 | B8 | VALÊNCIA EPISTÊMICA | 0=evidência contraditória / 0.5=inconclusivo / 1=confirmatório |

### Grupo C — Pragmático (22–31): *O que fazer?*

| Idx | Código | Nome | Interpretação |
|-----|--------|------|--------------|
| 22 | C1 | URGÊNCIA | 0=sem pressa / 1=emergência crítica |
| 23 | C2 | IMPACTO | 0=inócuo / 1=muda estado do sistema |
| 24 | C3 | AÇÃO | 0=puramente informativo / 1=demanda execução |
| 25 | C4 | VALOR | 0=neutro axiologicamente / 1=carregado de significado |
| 26 | C5 | ANOMALIA | 0=dentro do normal / 1=ruptura forte |
| 27 | C6 | AFETO | 0=neutro emocionalmente / 1=forte carga afetiva |
| 28 | C7 | DEPENDÊNCIA | 0=autônomo / 1=totalmente acoplado |
| 29 | C8 | VETOR TEMPORAL | 0=passado / 0.5=presente / 1=futuro |
| 30 | C9 | NATUREZA | 0=coisa (noun) / 1=ação (verb) |
| 31 | C10 | VALÊNCIA AÇÃO | 0=intenção negativa / 0.5=neutra / 1=positiva |

### Acessar eixos no código

```python
from leet import axis, axes_in_group, AxisGroup, CANONICAL_AXES

# Por índice
ax = axis(22)
print(ax.code)         # "C1"
print(ax.name)         # "URGÊNCIA"
print(ax.description)  # "Grau em que o conceito exige resposta imediata..."
print(ax.group)        # AxisGroup.PRAGMATIC

# Por grupo
pragmaticos = axes_in_group(AxisGroup.PRAGMATIC)   # eixos 22-31
ontologicos = axes_in_group(AxisGroup.ONTOLOGICAL)  # eixos 0-13
epistemicos = axes_in_group(AxisGroup.EPISTEMIC)    # eixos 14-21

# Todos os eixos
for ax in CANONICAL_AXES:
    print(f"[{ax.index:2d}] {ax.code:3} {ax.name}")

# Constantes nomeadas (Rust e Python)
from leet.axes import (
    A0_VIA, A7_SISTEMA, A8_ESTADO, A9_PROCESSO,
    B1_VERIFICABILIDADE, B4_CAUSALIDADE,
    C1_URGENCIA, C2_IMPACTO, C3_ACAO, C5_ANOMALIA, C6_AFETO,
)

# Usar constante em vez de número mágico
sem[C1_URGENCIA] = 0.95
sem[C5_ANOMALIA] = 0.88
```

---

## 13. Configuração e Variáveis de Ambiente

### Configurar interativamente

```bash
python setup.py           # menu interativo
python setup.py --help    # ajuda detalhada
python setup.py --show    # exibir configuração atual
```

### Via código

```python
from leet.config import LeetConfig, get_config, init_config

# Carregar de variáveis de ambiente (prefixo LEET_)
config = LeetConfig.from_env()

# Carregar de arquivo
config = LeetConfig.from_file("config.json")   # JSON
config = LeetConfig.from_file("config.yaml")   # YAML
config = LeetConfig.from_file("config.toml")   # TOML

# Inicializar instância global
init_config(config)

# Acessar instância global
cfg = get_config()
```

### Referência de variáveis

**leet-service (Rust)**

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_PORT` | `50051` | Porta gRPC |
| `LEET_BACKEND` | `simd` | Backend: `simd` \| `cpu` \| `mock` |
| `LEET_STORE` | `memory` | `memory` \| `redis://...` \| `sqlite://...` |
| `LEET_BATCH_WINDOW` | `10` | Janela de batch (ms) |
| `LEET_BATCH_MAX` | `64` | Máximo de itens por batch |
| `LEET_EMBED_MODEL` | `mock` | `mock` \| `openai` |
| `LEET_EMBED_URL` | — | URL do embedder |
| `LEET_EMBED_KEY` | — | Chave do embedder |
| `LEET_W_PATH` | — | Caminho da matriz W |
| `RUST_LOG` | `info` | `error` \| `warn` \| `info` \| `debug` \| `trace` |

**Python SDK**

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_SERVER_HOST` | `localhost` | Host do leet-service |
| `LEET_SERVER_PORT` | `50051` | Porta do leet-service |
| `LEET_SERVER_TIMEOUT` | `30.0` | Timeout (s) |
| `LEET_CACHE_BACKEND` | `memory` | `memory` \| `redis` \| `sqlite` \| `mongodb` |
| `LEET_CACHE_TTL_SECONDS` | `3600` | TTL padrão do cache |
| `LEET_PROJECTION_BACKEND` | `mock` | `mock` \| `anthropic` \| `openai` \| `grpc` |
| `LEET_DEBUG` | `false` | Modo debug |
| `LEET_LOG_LEVEL` | `INFO` | Nível de log |

**Chaves de API**

| Variável | Uso |
|----------|-----|
| `DEEPSEEK_API_KEY` | comparison_1337_vs_english.py, leet.connect("deepseek") |
| `ANTHROPIC_API_KEY` | AnthropicProjector, ClaudeCodeAdapter, leet.connect("anthropic") |
| `OPENAI_API_KEY` | leet.connect("openai"), LEET_EMBED_MODEL=openai |
| `GEMINI_API_KEY` | leet.connect("gemini") |
| `MOONSHOT_API_KEY` | leet.connect("moonshot"), KimiAdapter |

---

## 14. Exemplos de Ponta a Ponta

### Exemplo 1 — Monitor de anomalias

```python
"""
Monitor que detecta anomalias semânticas em um fluxo de eventos,
usa 1337 para comunicação interna e envia alertas via ANOMALY.
"""
import asyncio
from leet import encode, anomaly_score, blend, focus
from leet.client import Agent1337, AgentConfig

HISTORICO_MAX = 50

async def monitor_principal():
    agente = Agent1337(AgentConfig(name="Monitor", capabilities=["encode", "anomaly"]))
    await agente.start()

    historico = []

    eventos = [
        "pagamento processado com sucesso",
        "gateway respondendo em 120ms",
        "transação aprovada",
        "ALERTA: timeout após 8000ms — gateway sem resposta",  # anomalia
        "retry automático — tentativa 2/3",
        "sistema parcialmente degradado",
    ]

    for evento in eventos:
        cogon = await encode(evento)

        score = anomaly_score(cogon, historico)
        historico.append(cogon)
        if len(historico) > HISTORICO_MAX:
            historico.pop(0)

        print(f"[score={score:.3f}] {evento[:50]}")

        if score > 0.5:
            await agente.send_anomaly(f"Evento anômalo detectado: {evento}")
            print("  → ANOMALY enviada para a rede")

    await agente.stop()

asyncio.run(monitor_principal())
```

### Exemplo 2 — Pipeline de encoding em lote

```python
"""
Pipeline que processa um corpus de textos em lote,
armazena COGONs no SQLite e exporta métricas Prometheus.
"""
import asyncio
from leet import get_cache, set_cache, Cache
from leet.batch import ProjectionBatcher, BatchConfig
from leet.metrics import get_metrics
from leet import MockProjector

async def pipeline_corpus():
    # Configurar cache persistente
    set_cache(Cache(backend="sqlite", path="corpus_cache.db"))

    # Configurar métricas
    metrics = get_metrics()

    # Textos a processar
    corpus = [
        "amor é a força que move o universo",
        "sistema de pagamentos instável",
        "emergência crítica no gateway",
        "filosofia como busca da verdade",
        "algoritmo convergiu com erro mínimo",
        # ... centenas de textos
    ]

    # Processar em lote com cache
    batcher = ProjectionBatcher(
        projector=MockProjector(),
        config=BatchConfig(max_concurrency=5),
    )

    print(f"Processando {len(corpus)} textos...")
    pares = await batcher.project_with_cache(corpus, get_cache())

    for texto, cogon in pares:
        urgencia = cogon.sem[22]
        anomalia = cogon.sem[26]
        afeto    = cogon.sem[27]
        print(f"{texto[:40]:40s} | U={urgencia:.2f} A={anomalia:.2f} ♥={afeto:.2f}")

    # Exportar métricas
    prometheus = get_metrics().export_prometheus()
    with open("metrics.txt", "w") as f:
        f.write(prometheus)
    print("\nMétricas exportadas em metrics.txt")

asyncio.run(pipeline_corpus())
```

### Exemplo 3 — Discussão filosófica com DeepSeek

```bash
# Rodar experimento completo de comparação 1337 vs English
# com 15 agentes filosóficos + DeepSeek real

export DEEPSEEK_API_KEY="sk-..."

python comparison_1337_vs_english.py \
    --rounds 25 \
    --deepseek \
    --workers 5 \
    --topic "Justiça"

# Resultado esperado:
# Compressão: ~5× vs English
# Delta coverage: ~68% das mensagens
# Custo transporte 1337: $0.00
# Relatório JSON salvo em ./comparison_reports/
```

### Exemplo 4 — Contexto de emergência

```python
"""
Agente que adapta suas projeções ao domínio de emergência
e detecta drift de contexto.
"""
import asyncio
from leet import (
    set_context_profile, get_context_manager,
    adjust_with_context, encode, validate,
)
from leet import Msg1337, Intent, Surface, CanonicalSpace
import uuid

async def agente_emergencia():
    # Configurar perfil de emergência globalmente
    set_context_profile("emergency")

    mgr = get_context_manager()

    eventos = [
        "sistema operacional",
        "latência aumentando — P95=500ms",
        "CRÍTICO: gateway de pagamentos fora — timeout total",
        "equipe acionada — incidente aberto",
        "rollback iniciado",
        "serviço recuperado — P95=120ms",
    ]

    for i, evento in enumerate(eventos):
        # Codificar com contexto de emergência
        cogon_base = await encode(evento)
        sem_adj, unc_adj = adjust_with_context(
            cogon_base.sem, cogon_base.unc, context_alpha=0.25,
        )

        from leet import Cogon
        cogon = Cogon.new(sem=sem_adj, unc=unc_adj)
        mgr.add_to_history(cogon)

        # Detectar drift
        aviso = mgr.detect_context_drift(threshold=0.4)
        drift_str = f" [DRIFT: {aviso}]" if aviso else ""

        print(f"[{i:2d}] U={cogon.sem[22]:.2f} A={cogon.sem[26]:.2f} | {evento[:50]}{drift_str}")

asyncio.run(agente_emergencia())
```

### Exemplo 5 — Adapter IDE para refatoração

```python
"""
Usar ClaudeCodeAdapter para revisar código 1337-aware:
resposta do Claude é projetada em COGON para análise semântica.
"""
import asyncio
from leet.adapters import ClaudeCodeAdapter, AdapterContext
from leet import dist

async def revisar_codigo():
    adapter = ClaudeCodeAdapter(
        project_dir=".",
        model="claude-sonnet-4-6",
    )

    if not adapter.is_available():
        print("Instale claude CLI: pip install claude-code")
        return

    # Primeira revisão — código original
    resp_antes = await adapter.send_message(
        "Analise o arquivo operators.py e avalie a qualidade semântica do código",
        context=AdapterContext(file_path="python/leet/operators.py"),
    )

    # Segunda revisão — após mudanças
    resp_depois = await adapter.send_message(
        "Após adicionar type hints, como ficou a clareza do código?",
        context=AdapterContext(file_path="python/leet/operators.py"),
    )

    # Comparar semanticamente as duas respostas
    d = dist(resp_antes.cogon, resp_depois.cogon)
    print(f"Distância semântica antes/depois: {d:.4f}")
    print(f"  0 = respostas idênticas | 1 = completamente diferentes")

    if d < 0.2:
        print("  → Mudanças não impactaram a percepção semântica")
    elif d > 0.5:
        print("  → Mudança significativa na percepção do código")

asyncio.run(revisar_codigo())
```

---

*Documentação gerada para o protocolo 1337 v0.5.0*
*Para configuração interativa: `python setup.py`*
*Para referência de variáveis de ambiente: `GUIDE.md`*
