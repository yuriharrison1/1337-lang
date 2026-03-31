# Phase 2 — Runtime (v0.5.0)

Esta fase implementa a camada de runtime do protocolo 1337, incluindo transporte, handshake e containerização.

## 🚀 Componentes Implementados

### 1. Protocol Buffers Schema ✅

Local: `leet1337/leet-service/proto/leet.proto`

Serviços gRPC:
- `Encode` — Texto → COGON (sem[32], unc[32])
- `Decode` — COGON → Texto reconstruído
- `EncodeBatch` — Batch streaming para alta throughput
- `Delta` — Computa diferença entre COGONs
- `Recall` — Recupera COGONs similares do store
- `Health` — Health check do serviço

### 2. ZeroMQ Transport Layer ✅

Local: `leet1337/leet-service/src/transport/`

Padrões de comunicação suportados:
- **REQ/REP** — RPC síncrono
- **PUB/SUB** — Broadcast para múltiplos agentes
- **PUSH/PULL** — Work queue distribuída
- **DEALER/ROUTER** — Async routing avançado

Portas padrão:
- `5555` — REQ/REP (comandos)
- `5556` — PUB/SUB (broadcast)
- `5557` — PUSH/PULL (workers)
- `5558` — ROUTER (routing)

Exemplo de uso:
```rust
use leet_service::transport::{ZmqTransport, ZmqTransportBuilder, ZmqSocketType};

let transport = ZmqTransportBuilder::new()
    .bind_addr("tcp://*:5555")
    .socket_type(ZmqSocketType::Rep)
    .build()?;

transport.init().await?;
```

### 3. C5 Handshake ✅

Local: `leet1337/leet-service/src/c5/`

Implementação completa do protocolo de 4 fases:

```
FASE 1: PROBE  → Agente envia 5 âncoras + schema_ver
FASE 2: ECHO   → Rede responde com mesmas âncoras
FASE 3: ALIGN  → Computa matriz de projeção M
FASE 4: VERIFY → Confirma alinhamento via align_hash
```

As 5 Âncoras (valores fixos):
1. **Presença** — algo existe agora
2. **Ausência** — algo não existe
3. **Mudança** — estado anterior ≠ atual
4. **Agência** — ator causando algo
5. **Incerteza** — grau de desconhecimento

Exemplo:
```rust
use leet_service::c5::C5Handshake;

let c5 = C5Handshake::new();

// Fase 1: PROBE
let probe = c5.probe(agent_id).await?;

// Fase 2: ECHO
let echo = c5.echo(agent_id).await?;

// Fase 3: ALIGN
let align = c5.align(agent_id).await?;

// Fase 4: VERIFY
let verify = c5.verify(agent_id, &align.align_hash).await?;
assert!(verify.success);
```

### 4. Semantic Projection Service ✅

Local: `leet1337/leet-service/src/projection/`

Engine de projeção semântica com:
- **SIMD acceleration** (ndarray + BLAS)
- **Batching automático** (janela de 10ms, max 64)
- **Múltiplos backends** (mock, openai, local)
- **Matriz de projeção W** (calibrável)

Endpoints:
- gRPC: `localhost:50051`
- REST: (opcional, via proxy)
- ZeroMQ: `localhost:5555-5558`

### 5. Docker Container ✅

Local: `Dockerfile`, `docker-compose.yml`

Multi-stage build otimizado:
- **Builder**: rust:1.75-slim-bookworm
- **Runtime**: debian:bookworm-slim (~50MB)

Serviços incluídos:
- `leet-service` — Serviço principal
- `redis` — Cache e persistência
- `prometheus` — Métricas (opcional)
- `grafana` — Dashboards (opcional)

Uso:
```bash
# Build
docker build -t leet-service .

# Run
docker run -p 50051:50051 -p 5555-5558:5555-5558 leet-service

# Ou com compose
docker-compose up -d
docker-compose logs -f
```

## 📊 Arquitetura do Runtime

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTES                                  │
│  (Python SDK, CLI, IDE Adapters, Outros Agentes)                │
└─────────────────┬───────────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│  gRPC  │  │  ZeroMQ  │  │  WebSock │  (Transport Layer)
│ :50051 │  │ :5555-8  │  │  (futuro)│
└────┬───┘  └────┬─────┘  └────┬─────┘
     │           │             │
     └───────────┴─────────────┘
                 │
     ┌───────────▼───────────┐
     │   leet-service        │
     │   ─────────────────   │
     │   • C5 Handshake      │
     │   • Projection Engine │
     │   • Validation R1-R21 │
     │   • Store (Redis)     │
     └───────────┬───────────┘
                 │
         ┌───────▼───────┐
         │    Redis      │
         │   (cache)     │
         └───────────────┘
```

## 🔧 Configuração

Variáveis de ambiente:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_PORT` | 50051 | Porta gRPC |
| `LEET_BACKEND` | simd | Backend de projeção |
| `LEET_STORE` | memory | URL do store |
| `LEET_BATCH_WINDOW` | 10 | Janela de batch (ms) |
| `LEET_BATCH_MAX` | 64 | Tamanho máximo do batch |
| `LEET_EMBED_MODEL` | mock | Modelo de embedding |
| `LEET_EMBED_URL` | - | URL da API de embeddings |
| `LEET_EMBED_KEY` | - | API key |

## 🧪 Testes

```bash
# Testes Rust
cd leet1337
cargo test --all

# Testes de integração
cargo test -p leet-service -- --ignored

# Teste de carga (requiere ghz ou similar)
ghz --insecure --proto ./proto/leet.proto \
    --call leet.LeetService/Encode \
    -d '{"text":"hello","agent_id":"test"}' \
    localhost:50051
```

## 📦 Deploy

### Docker Swarm
```bash
docker stack deploy -c docker-compose.yml leet
```

### Kubernetes
```bash
kubectl apply -f k8s/
```

## 🔄 Roadmap para Phase 3

- [ ] LangGraph adapter
- [ ] AutoGen communicator
- [ ] CrewAI integration
- [ ] MCP bridge
- [ ] IDE Adapters (Claude Code, Codex, Kimi, Aider)
