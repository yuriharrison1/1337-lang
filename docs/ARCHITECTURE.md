# Arquitetura do projeto 1337

## Visão geral

O 1337 é um protocolo de linguagem semântica baseado em vetores de 32 dimensões chamados **COGON**. O objetivo é permitir que agentes de LLM se comuniquem de forma eficiente — comprimindo mensagens longas em vetores compactos e recuperando o significado semântico quando necessário.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Aplicação / Usuário                          │
│        scripts Python, agentes LLM, automações                 │
└────────────────┬───────────────────────────────┬───────────────┘
                 │ Python SDK                    │ CLI
    ┌────────────▼─────────────┐    ┌────────────▼──────────────┐
    │  python/leet  (SDK core) │    │  leet  (CLI — 13 comandos)│
    │  leet-py (SDK público)   │    │  leet chat / encode / etc │
    └────────────┬─────────────┘    └────────────┬──────────────┘
                 │                               │
    ┌────────────▼───────────────────────────────▼──────────────┐
    │               leet-bridge  (Rust)                         │
    │  nl_to_cogon()  cogon_to_nl()  infer_intent()             │
    │  AnthropicClient  →  Claude API  →  15 agentes            │
    └────────────────────────────┬──────────────────────────────┘
                                 │
    ┌────────────────────────────▼──────────────────────────────┐
    │                leet-core  (Rust)                          │
    │  Cogon  Dag  Msg1337  Edge  Intent                        │
    │  blend  delta  dist  focus  anomaly_score                 │
    │  encode_cogon  decode_cogon  (96B binário)                │
    │  validate  (R1–R21)                                        │
    └────────────────────────────┬──────────────────────────────┘
                                 │
    ┌────────────────────────────▼──────────────────────────────┐
    │              leet-service  (Rust daemon)                  │
    │  leet-server  TCP :1337 + Unix /run/leet/leet.sock        │
    │  leet-agent   15 processos independentes                  │
    │  C5 handshake  PROBE→ECHO→ALIGN→VERIFY                   │
    │  roteamento:  broadcast + direct delivery                 │
    └───────────────────────────────────────────────────────────┘
```

---

## Componentes

### leet-core

Biblioteca Rust com os tipos e operadores fundamentais. Não tem dependências de rede ou I/O — é pura lógica.

**Responsabilidades:**
- Definir os tipos `Cogon`, `Dag`, `Msg1337`, `Edge`, `Intent`
- Implementar os 5 operadores semânticos: `blend`, `delta`, `dist`, `focus`, `anomaly_score`
- Codec binário de 96 bytes (compressão 4-5× vs JSON)
- Validação de mensagens (regras R1–R21)
- Protocolo C5: anchor COGONs e cálculo de `align_hash`

**Versão:** 0.4.0

---

### leet-bridge

Camada de tradução Rust entre linguagem natural e COGON.

**Responsabilidades:**
- `nl_to_cogon(text, lang)` — NL → vetor semântico via ~80 regras heurísticas (PT + EN)
- `cogon_to_nl(cogon, lang)` — reconstrução NL a partir dos eixos mais ativos
- `infer_intent(text)` — classifica intenção: QUERY / ANOMALY / SYNC / DELTA / ASSERT
- `AnthropicClient` — envia COGON para Claude API, recebe respostas dos 15 agentes
- System prompt embutido com spec v0.5.1 completa (32 eixos, 15 agentes, formato JSON)

**Versão:** 0.5.0

---

### leet-cli

Binário `leet` com 13 subcomandos para uso interativo e scripting.

**Responsabilidades:**
- Ferramentas de diagnóstico: `encode`, `decode`, `inspect`, `axes`, `zero`
- Operações semânticas: `dist`, `blend`
- Validação e benchmarking: `validate`, `bench`
- Chat multiagente: `leet chat` (modo direto via API ou `--connect` a um servidor)
- Verificação de saúde do serviço: `health`

**Versão:** 0.5.0

---

### leet-service

Daemon de rede que hospeda 15 agentes autônomos e roteia mensagens entre eles.

**Componentes:**
- `leet-server` — servidor TCP/Unix com handshake C5, mpsc routing, métricas
- `leet-agent` — processo autônomo que conecta ao servidor, processa COGONs e responde via LLM

**Protocolo de rede:** JSON newline-delimited sobre TCP ou Unix socket  
**Versão:** 0.5.1

---

### Python SDK (python/leet e leet-py)

Dois pacotes Python com diferentes níveis de abstração:

| Pacote | Propósito | Entrada |
|--------|-----------|---------|
| `python/leet` | SDK core completo com clientes gRPC/ZMQ/WebSocket, adaptadores de IDE, cache | Desenvolvedores |
| `leet-py` | SDK público simplificado: `leet.connect()`, `@agent`, `AgentNetwork` | Usuários finais Python |

---

## Fluxo de dados — `leet chat`

```
Usuário digita texto
       │
       ▼
nl_to_cogon(text)      → Cogon { sem[32], unc[32] }
       │
       ▼
AnthropicClient.send_cogon(cogon, history, max_agents)
       │  INPUT_COGON + SELECT_AGENTS: N
       ▼
Claude API (Haiku por padrão)
       │  JSON array de N AgentResponse
       ▼
parse_agent_responses()
       │
       ├─ AgentResponse { agent, cogon, intent, nl_pt, nl_en }
       ├─ AgentResponse { ... }
       └─ ...
       │
       ▼
Terminal colorido (crossterm)
  RAVEN  "texto em PT"
  TENSOR "texto em PT"
  ...
  latência: Xms | Y tok/s | N agentes
```

---

## Fluxo de dados — `leet-server` + `leet-agent`

```
leet-server inicia
       │ bind TCP :1337 + Unix /run/leet/leet.sock
       ▼
leet-agent --name ATLAS conecta
       │
       ├─ PROBE  →  Register { name: "ATLAS", role: "..." }
       ├─ ECHO   ←  Registered { agent_id, anchors: [5 COGONs] }
       ├─ ALIGN  →  Align { hash: SHA256("1337:v0.5.1:ATLAS") }
       └─ VERIFY ←  Ready
       │
       ▼  (15 agentes conectados)
Usuário envia mensagem via leet chat --connect 127.0.0.1:1337
       │
       ▼
leet-server.route(sender_id, msg)
       ├─ broadcast(exclude=sender) → todos os agentes
       └─ deliver_to(target_id)     → agente específico
       │
       ▼
leet-agent recebe Msg, processa via LLM, responde ao servidor
```

---

## Codec binário (96 bytes)

Cada COGON pode ser serializado em 96 bytes fixos — compressão de 4-5× vs JSON.

```
Offset  Bytes  Campo
──────  ─────  ─────────────────────────────────────
0       2      magic: 0x1337
2       1      version: 0x02
3       1      flags
4       32     sem[32] quantizado: f32[0,1] → u8[0,255]
36      32     unc[32] quantizado: f32[0,1] → u8[0,255]
68      16     UUID (id) — 16 bytes raw
84      8      stamp (i64 little-endian)
92      4      CRC32 do payload (bytes 0-91)
──────  ─────
96      TOTAL
```

---

## Protocolo de validação (R1–R21)

Regras aplicadas por `validate()` em todo `Msg1337`:

| Grupo | Regras | O que verifica |
|-------|--------|----------------|
| Estrutura | R1–R5 | sender não-zero, intent válido, stamp não-negativo, sem/unc em [0,1] |
| Semântica | R6–R10 | unc[i] < 1.0 sempre, P3/P7 não-zero (se anomalia/ação), valência coerente |
| Relações | R11–R15 | edges têm peso [0,1], sem ciclos triviais no DAG, EdgeType válido |
| Protocolo | R16–R21 | COGON_ZERO apenas para handshake, ref_hash presente quando necessário |

---

## Dependências de componente

```
leet-cli
  └── leet-bridge
  │     └── leet-core
  └── leet-service (para AgentClient em --connect)
        └── leet-bridge
              └── leet-core
```

Não há dependências circulares. `leet-core` não depende de nada externo além de `uuid`, `serde`, `sha2`.
