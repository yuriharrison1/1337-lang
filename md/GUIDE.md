# Guia Completo — Protocolo 1337

> Documentação técnica detalhada de todos os componentes, ferramentas e variáveis de configuração do protocolo 1337.

---

## Índice

1. [O que é o Protocolo 1337](#1-o-que-é-o-protocolo-1337)
2. [COGON — Unidade Semântica Atômica](#2-cogon--unidade-semântica-atômica)
3. [Os 32 Eixos Canônicos](#3-os-32-eixos-canônicos)
4. [Wire Format — Protocolo de Transmissão](#4-wire-format--protocolo-de-transmissão)
5. [Operadores Semânticos](#5-operadores-semânticos)
6. [leet-service — Serviço gRPC Rust](#6-leet-service--serviço-grpc-rust)
7. [leet-cli — Ferramenta de Linha de Comando](#7-leet-cli--ferramenta-de-linha-de-comando)
8. [Python SDK — `python/leet`](#8-python-sdk--pythonleet)
9. [leet-py — SDK de Alto Nível](#9-leet-py--sdk-de-alto-nível)
10. [comparison_1337_vs_english.py — Benchmark de Compressão](#10-comparison_1337_vs_englishpy--benchmark-de-compressão)
11. [setup.py — Configuração Interativa](#11-setuppy--configuração-interativa)
12. [Variáveis de Ambiente — Referência Completa](#12-variáveis-de-ambiente--referência-completa)
13. [Docker e Docker Compose](#13-docker-e-docker-compose)
14. [Arquivo .env — Formato e Exemplos](#14-arquivo-env--formato-e-exemplos)
15. [Fluxo de Desenvolvimento](#15-fluxo-de-desenvolvimento)

---

## 1. O que é o Protocolo 1337

O **1337** é um protocolo de comunicação formal para agentes de IA. Em vez de trocar linguagem natural (lenta, ambígua, cara em tokens), agentes comunicam via **COGONs** — vetores semânticos de 32 dimensões que codificam significado de forma precisa e comprimida.

### Analogias

| Protocolo | Analogia |
|-----------|----------|
| TCP/IP | 1337 para dados de rede |
| Protobuf | 1337 para semântica |
| MIDI | 1337 para significado entre agentes |

### Por que usar 1337?

| Problema | Linguagem Natural | Solução 1337 |
|----------|------------------|-------------|
| Largura de banda | 100–500 tokens/msg | 128 bytes (sem[32] × f32) |
| Latência | 2–5 s (geração LLM) | < 1 ms (operações vetoriais) |
| Custo | $0.002–0.02/msg | ~$0 (zero tokens de transporte) |
| Ambiguidade | "alta prioridade" = ? | Urgência = 0.85 (exato) |
| Verificação | impossível | Regras R1–R21 formais |
| Compressão delta | nenhuma | SparseDelta: só eixos alterados |

### Compressão medida com DeepSeek real (25 rounds, 15 agentes)

```
Bytes English:  89,812 B
Bytes 1337:     17,339 B
Compressão:         5.18×  (−80.7%)

Com SparseDelta (68.5% das msgs):
  COGON completo: 166 B
  SparseDelta:     52 B  (−68.6%)
  Total economizado: 29,255 B
```

---

## 2. COGON — Unidade Semântica Atômica

Um **COGON** é a unidade básica de comunicação no protocolo 1337.

### Estrutura

```rust
struct Cogon {
    id:    Uuid,       // identificador único v4
    sem:   [f32; 32],  // vetor semântico — 32 dimensões canônicas
    unc:   [f32; 32],  // incerteza por dimensão — 0.0=certo, 1.0=desconhecido
    stamp: i64,        // timestamp nanosegundos (Unix epoch)
    raw:   Option<Raw> // payload bruto opcional (evidência, artefato)
}
```

### Invariantes

| Regra | Descrição |
|-------|-----------|
| `sem[i] ∈ [0.0, 1.0]` | Todos os valores semânticos normalizados |
| `unc[i] ∈ [0.0, 1.0]` | Incerteza normalizada |
| `len(sem) == 32` | Dimensão fixa — `FIXED_DIMS = 32` |
| `len(unc) == 32` | Mesma dimensão |
| `id != nil` | Exceto COGON_ZERO |
| `stamp > 0` | Exceto COGON_ZERO |

### COGON_ZERO — "EU SOU"

O COGON primordial. Representa presença pura antes de qualquer qualificação.

```python
# Python
from leet import Cogon
zero = Cogon.zero()
# sem = [1.0, 1.0, ..., 1.0]  (32 × 1.0)
# unc = [0.0, 0.0, ..., 0.0]  (32 × 0.0)
# id  = 00000000-0000-0000-0000-000000000000
# stamp = 0
```

```rust
// Rust
let zero = Cogon::zero();
assert!(zero.is_zero());
```

### Construindo um COGON manualmente

```python
from leet import Cogon

# COGON representando "anomalia urgente, alta certeza"
cogon = Cogon(
    sem=[
        0.5, 0.5, 0.5, 0.5,   # A0–A3: ontológico neutro
        0.5, 0.5, 0.5, 0.5,   # A4–A7
        0.5, 0.5, 0.5, 0.5,   # A8–A11
        0.5, 0.5,              # A12–A13
        0.9, 0.8, 0.7, 0.6,   # B1–B4: epistêmico — alta verificabilidade
        0.5, 0.5, 0.5, 0.9,   # B5–B8: valência positiva
        0.95, 0.9, 0.8, 0.5,  # C1–C4: urgência alta, impacto alto
        0.85, 0.2, 0.3, 0.5,  # C5–C8: anomalia detectada
        0.5, 0.5, 0.5, 0.5    # C9–C10
    ],
    unc=[0.05] * 32  # alta certeza em todas as dimensões
)
print(cogon.to_json())
```

### Interpretando sem[i]

```
0.0 ────── 0.5 ────── 1.0
mínimo    neutro    máximo

Exemplos:
  C1 (Urgência):
    0.0 = sem pressa nenhuma
    0.5 = urgência moderada
    1.0 = emergência crítica

  A13 (Valência Ontológica):
    0.0 = negativo/contrativo
    0.5 = neutro
    1.0 = positivo/expansivo
```

### unc — Incerteza

```
unc[i] = 0.0  →  certeza total nessa dimensão
unc[i] = 0.5  →  incerteza moderada
unc[i] = 1.0  →  completamente desconhecido

LOW_CONFIDENCE_THRESHOLD = 0.9
  → dimensões com unc > 0.9 são marcadas como "baixa confiança"
```

---

## 3. Os 32 Eixos Canônicos

### Grupo A — Ontológico (eixos 0–13)

Descreve **o que é** o conceito — sua natureza intrínseca.

| Idx | Código | Nome | Descrição Curta |
|-----|--------|------|----------------|
| 0 | A0 | VIA | Existência por si mesmo vs dependente |
| 1 | A1 | CORRESPONDÊNCIA | Espelha padrões em múltiplas escalas |
| 2 | A2 | VIBRAÇÃO | Em movimento contínuo vs estático |
| 3 | A3 | POLARIDADE | Posicionado num espectro extremo |
| 4 | A4 | RITMO | Padrão cíclico ou periódico |
| 5 | A5 | CAUSA E EFEITO | Agente causal vs consequência |
| 6 | A6 | GÊNERO | Princípio ativo vs receptivo |
| 7 | A7 | SISTEMA | Conjunto com comportamento emergente |
| 8 | A8 | ESTADO | Configuração num dado momento |
| 9 | A9 | PROCESSO | Transformação no tempo |
| 10 | A10 | RELAÇÃO | Conexão entre entidades |
| 11 | A11 | SINAL | Informação carregando variação |
| 12 | A12 | ESTABILIDADE | Tendência ao equilíbrio vs caos |
| 13 | A13 | VALÊNCIA ONTOLÓGICA | Negativo←0.5→Positivo |

### Grupo B — Epistêmico (eixos 14–21)

Descreve **o que se sabe** — a epistemologia do conceito.

| Idx | Código | Nome | Descrição Curta |
|-----|--------|------|----------------|
| 14 | B1 | VERIFICABILIDADE | Pode ser confirmado externamente |
| 15 | B2 | TEMPORALIDADE | Tem âncora temporal definida |
| 16 | B3 | COMPLETUDE | Resolvido vs aberto/em construção |
| 17 | B4 | CAUSALIDADE | Origem identificável vs opaca |
| 18 | B5 | REVERSIBILIDADE | Pode ser desfeito vs irreversível |
| 19 | B6 | CARGA | Custo cognitivo — pesado vs automático |
| 20 | B7 | ORIGEM | Observado vs inferido vs assumido |
| 21 | B8 | VALÊNCIA EPISTÊMICA | Contraditório←0.5→Confirmatório |

### Grupo C — Pragmático (eixos 22–31)

Descreve **o que fazer** — implicações de ação.

| Idx | Código | Nome | Descrição Curta |
|-----|--------|------|----------------|
| 22 | C1 | URGÊNCIA | Exige resposta imediata |
| 23 | C2 | IMPACTO | Gera consequências no sistema |
| 24 | C3 | AÇÃO | Demanda execução vs puramente informativo |
| 25 | C4 | VALOR | Conecta com algo que importa |
| 26 | C5 | ANOMALIA | Desvio do padrão esperado |
| 27 | C6 | AFETO | Valência emocional relevante |
| 28 | C7 | DEPENDÊNCIA | Acoplado a outro vs autônomo |
| 29 | C8 | VETOR TEMPORAL | Passado←0.5→Futuro |
| 30 | C9 | NATUREZA | Tipo fundamental do conceito |
| 31 | C10 | VALÊNCIA AÇÃO | Negativo←0.5→Positivo (pragmático) |

### Listar eixos via CLI

```bash
# Todos os eixos
leet axes

# Somente grupo ontológico
leet axes --group A

# Somente grupo epistêmico
leet axes --group B

# Somente grupo pragmático
leet axes --group C
```

---

## 4. Wire Format — Protocolo de Transmissão

O wire format é a camada de transporte compacta para comunicação inter-agente. Usa **MessagePack** (binário posicional) em vez de JSON.

### Comparação de tamanhos

```
MSG_1337 completo (JSON):    ~700–900 bytes
WireMsg COGON (MsgPack):      ~166 bytes
WireMsg SparseDelta:           ~52 bytes  (média, 4 eixos)

Economia total com SparseDelta: −68.6% vs COGON completo
```

### WireCogon

```rust
struct WireCogon {
    id:    [u8; 16],   // UUID bytes (16 bytes, sem hífens)
    sem:   [f32; 32],  // 128 bytes (32 × 4 bytes f32)
    stamp: i64,        // 8 bytes
    // unc OMITIDO — receiver recomputa deterministicamente
}
// Total payload: 152 bytes
```

**Por que unc é omitido?**
`unc` é completamente determinístico a partir de `sem`:
```
unc[i] = (1 − |sem[i] − 0.5| × 2).clamp(0, 1)
```
Isso economiza 128 bytes (32 × f32) por mensagem.

### SparseDelta

```rust
struct SparseDelta {
    ref_id:  [u8; 16],         // UUID do COGON base (16 bytes)
    changes: Vec<(u8, f32)>,   // só eixos alterados: (índice, novo valor)
    // Cada entrada: 1 byte (índice) + 4 bytes (f32) = 5 bytes
}
```

**Quando usar SparseDelta?**

O delta é enviado quando `|sem_curr[i] − sem_prev[i]| > threshold` para pelo menos um eixo. Com `threshold = 0.01`:
- Ruído de fundo (±0.005): nunca entra no delta
- Mudança por keyword (±0.3–0.7): sempre entra no delta

```
Pior caso: 32 eixos × 5 bytes = 160 bytes + header (17 bytes) = 177 bytes
Caso típico: 4 eixos × 5 bytes = 20 bytes + header (17 bytes) + envelope (14 bytes) = 51 bytes
```

### SessionId

```rust
struct SessionId {
    prefix: [u8; 4],  // primeiros 4 bytes do UUID da sessão
    seq:    u32,       // sequência monotônica crescente
}
// Total: 8 bytes vs 32 bytes de dois UUIDs completos → −75%
```

### WireIntent

```rust
enum WireIntent {
    Assert  = 0,  // "estou afirmando este estado"
    Query   = 1,  // "qual é o estado de X?"
    Delta   = 2,  // "transmitindo mudança em relação ao estado anterior"
    Sync    = 3,  // "sincronizando estado completo"
    Anomaly = 4,  // "detectei desvio inesperado"
    Ack     = 5,  // "recebi e processei"
}
```

### WireMsg — Envelope completo

```rust
struct WireMsg {
    sid:        SessionId,    // 8 bytes
    intent:     WireIntent,   // 1 byte
    align_hash: [u8; 4],      // 4 bytes (primeiros 4 do C5 SHA-256)
    payload:    WirePayload,  // Cogon | Dag | Delta
}
// Header total: 14 bytes fixos
```

### Codec — uso em Rust

```rust
use leet_core::wire::{WireMsg, WireCogon, encode, decode};

// Codificar (MsgPack binário)
let bytes: Vec<u8> = encode(&msg)?;

// Decodificar
let msg: WireMsg = decode(&bytes)?;

// Recompor unc após receber WireCogon
let wc: WireCogon = /* recebido */;
let unc = wc.recompute_unc();
let full_cogon = wc.to_cogon();
```

### Codec — uso em Python (comparison script)

```python
from comparison_1337_vs_english import (
    encode_wire_cogon, encode_wire_delta, sparse_delta, recompute_unc
)

# Codificar COGON completo
wire_bytes = encode_wire_cogon(cogon, session_prefix=b"\xde\xad\xbe\xef", seq=1, align_hash=b"\x00"*4)
print(f"{len(wire_bytes)} bytes")  # → 166 bytes

# Calcular delta
changes = sparse_delta(prev_cogon, curr_cogon, threshold=0.01)
# → [(22, 0.85), (26, 0.9)]  — índice, novo valor

# Codificar delta
delta_bytes = encode_wire_delta(ref_id, changes, session_prefix, seq, align_hash)
print(f"{len(delta_bytes)} bytes")  # → ~51 bytes para 2 eixos

# Recompor unc no receiver
unc = recompute_unc(sem)
# unc[i] = (1 − |sem[i] − 0.5| × 2).clamp(0, 1)
```

---

## 5. Operadores Semânticos

Definidos em `leet-core/src/operators.rs` e `python/leet/__init__.py`.

### BLEND — Fusão Semântica

Interpola dois COGONs com peso `α`.

```
sem_out[i] = α × sem_1[i] + (1 − α) × sem_2[i]
unc_out[i] = max(unc_1[i], unc_2[i])   ← conservador
```

```python
from leet import blend

# Fundir dois estados com peso igual
resultado = blend(cogon_a, cogon_b, alpha=0.5)

# Pesar mais o cogon_a
resultado = blend(cogon_a, cogon_b, alpha=0.8)
```

```bash
# Via CLI Python
leet blend cogon_a.json cogon_b.json --alpha 0.5 > resultado.json
```

### DIST — Distância Semântica

Distância cosseno ponderada por `(1 − max_unc)`. Dimensões incertas contribuem menos.

```
dist ∈ [0.0, 1.0]
  0.0 = idênticos
  1.0 = opostos
```

```python
from leet import dist

d = dist(cogon_a, cogon_b)
print(f"Distância: {d:.4f}")
```

```bash
leet dist "amor é eterno" "amor é passageiro" --service localhost:50051
```

### FOCUS — Projeção em Subconjunto

Zera todas as dimensões exceto as selecionadas, com `unc=1.0` nas zerradas.

```python
from leet import focus

# Focar apenas em urgência (C1) e anomalia (C5)
urgencia_anomalia = focus(cogon, dims=[22, 26])
```

### DELTA — Diferença Vetorial

Diferença ponto-a-ponto entre dois estados.

```python
from leet import delta

diff = delta(estado_anterior, estado_atual)
# diff[i] = estado_atual.sem[i] − estado_anterior.sem[i]
# diff: List[float], len=32
```

### SPARSE_DELTA — Delta Comprimido para Wire

```python
from leet import sparse_delta, apply_sparse_patch

# Calcular eixos que mudaram além do threshold
changes = sparse_delta(prev_cogon, curr_cogon, threshold=0.01)
# → [(idx: int, new_val: float), ...]

# Aplicar patch recebido a um COGON base
patched = apply_sparse_patch(base_cogon, changes)
```

```rust
// Rust
use leet_core::{sparse_delta, apply_sparse_patch};

let changes = sparse_delta(&prev, &curr, 0.01)?;
let patched  = apply_sparse_patch(&base, &changes)?;
```

### ANOMALY_SCORE — Desvio em relação ao histórico

```python
from leet import anomaly_score

score = anomaly_score(cogon_atual, historico=[c1, c2, c3, ...])
# score ∈ [0.0, 1.0]
# > 0.5 → desvio significativo do padrão histórico
```

---

## 6. leet-service — Serviço gRPC Rust

O `leet-service` é o backend central que expõe encoding semântico via gRPC.

### Iniciar

```bash
# Development
cargo run --release -p leet-service

# Com variáveis de ambiente
LEET_PORT=50051 LEET_EMBED_MODEL=mock cargo run --release -p leet-service

# Via .env
source .env && cargo run --release -p leet-service

# Via Docker
docker compose up leet-service
```

### Variáveis de Ambiente

| Variável | Padrão | Tipo | Descrição |
|----------|--------|------|-----------|
| `LEET_PORT` | `50051` | u16 | Porta gRPC do serviço |
| `LEET_BACKEND` | `simd` | string | Backend de computação: `simd`, `cpu`, `mock` |
| `LEET_STORE` | `memory` | string | URL do store (ver abaixo) |
| `LEET_W_PATH` | _(nenhum)_ | path | Caminho para arquivo da matriz W |
| `LEET_BATCH_WINDOW` | `10` | ms | Janela de batch para agrupamento de chamadas |
| `LEET_BATCH_MAX` | `64` | int | Máximo de itens por batch |
| `LEET_EMBED_MODEL` | `mock` | string | Modelo de embedding: `mock`, `openai` |
| `LEET_EMBED_URL` | _(nenhum)_ | URL | Endpoint do serviço de embedding |
| `LEET_EMBED_KEY` | _(nenhum)_ | string | Chave API do serviço de embedding |
| `RUST_LOG` | `info` | string | Nível de log: `error`, `warn`, `info`, `debug`, `trace` |

### Stores suportados

```bash
# In-memory (padrão, perde ao reiniciar)
LEET_STORE=memory

# Redis (persistente, recomendado para produção)
LEET_STORE=redis://localhost:6379
LEET_STORE=redis://:senha@redis:6379/0
LEET_STORE=rediss://redis-tls:6380  # TLS

# SQLite (futuro — ainda não implementado)
LEET_STORE=sqlite://./leet.db
```

### Matriz W — Pesos de Projeção

A matriz W projeta embeddings de alta dimensão (ex: 1536 dims OpenAI) para os 32 eixos canônicos.

```bash
# Usar identidade (padrão — adequado para testes e mock)
# Sem variável LEET_W_PATH — usa WMatrix::identity_init()

# Usar matriz treinada
LEET_W_PATH=/caminho/para/w_matrix.bin

# Formato do arquivo: 8 bytes header + f32 data
# Header: rows(u32 LE) + cols(u32 LE)
# Data:   rows × cols × 4 bytes (f32 LE)
```

### Batch de Encoding — Otimização GEMM

O serviço agrupa requisições dentro de uma janela de tempo e executa um único `GEMM` (multiplicação de matrizes) com SIMD (AVX2/AVX-512 via `matrixmultiply`):

```
Janela: LEET_BATCH_WINDOW=10ms
Máximo: LEET_BATCH_MAX=64 itens

Fluxo:
  cliente A envia "amor"   ─┐
  cliente B envia "morte"   ├─ batch coletado → GEMM único → resultados distribuídos
  cliente C envia "força"  ─┘
```

### Cache LRU de Embeddings

O serviço mantém cache LRU de 1024 entradas para embeddings já computados. Textos idênticos (comum em broadcasts/tópicos) nunca chamam o embedder duas vezes.

```
Cache hit:  ~0.1 ms (acesso à memória)
Cache miss: depende do embedder
  mock:    ~0.01 ms
  openai:  ~200–800 ms (HTTP)
```

---

## 7. leet-cli — Ferramenta de Linha de Comando

### Instalação

```bash
cd leet1337
cargo build --release -p leet-cli
# Binário em: ./target/release/leet

# Ou instalar no PATH
cargo install --path leet-cli
```

### Uso geral

```bash
leet [--service HOST:PORT] <SUBCOMMAND>

# Padrão: --service localhost:50051
```

### Subcomandos

#### `encode` — Texto → COGON

Converte texto em vetor semântico de 32 dimensões via leet-service.

```bash
# Saída padrão (compacta)
leet encode "o amor é eterno"

# Saída JSON completa
leet encode "o amor é eterno" --json

# Conectar em serviço remoto
leet --service prod.server.com:50051 encode "anomalia detectada"

# Exemplos de saída JSON:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "sem": [0.82, 0.61, 0.74, ...],
#   "unc": [0.18, 0.39, 0.26, ...],
#   "stamp": 1774839777000000000
# }
```

#### `decode` — COGON → Texto

Decodifica um vetor semântico em descrição textual.

```bash
leet decode "0.82,0.61,0.74,0.5,0.5,..."
# → "conceito de alta correspondência (A1=0.61) com urgência moderada (C1=0.74)"
```

#### `inspect` — Inspecionar COGON JSON

Exibe análise detalhada de um COGON.

```bash
leet inspect cogon.json
# Mostra: eixos mais ativos, eixos incertos, grupo dominante, etc.
```

#### `dist` — Distância entre dois textos

```bash
leet dist "amor é eterno" "amor é passageiro"
# Distância semântica: 0.2341

leet dist "emergência crítica" "situação normal"
# Distância semântica: 0.8912
```

#### `bench` — Benchmark de throughput

```bash
# 1000 encodings sequenciais
leet bench --n 1000

# 1000 encodings em paralelo
leet bench --n 1000 --parallel

# Saída: throughput em msgs/s, latência P50/P95/P99
```

#### `health` — Verificar saúde do serviço

```bash
leet health
# ✓ Service healthy at localhost:50051
# Uptime: 2h34m
# Encodings: 48,291
# Cache hit rate: 73.2%
```

#### `axes` — Listar eixos canônicos

```bash
leet axes
# [ 0] A0  VIA                      (Ontological)
# [ 1] A1  CORRESPONDÊNCIA          (Ontological)
# ...
# [26] C5  ANOMALIA                 (Pragmatic)

leet axes --group A  # apenas ontológico
leet axes --group B  # apenas epistêmico
leet axes --group C  # apenas pragmático
```

#### `version` — Versão

```bash
leet version
# leet-cli 0.1.0 (leet-core 0.4.0)
```

---

## 8. Python SDK — `python/leet`

### Instalação

```bash
cd python
pip install -e .
# ou
pip install -e ".[dev]"  # com dependências de teste
```

### Importação básica

```python
from leet import (
    Cogon,          # tipo COGON
    blend,          # BLEND operator
    dist,           # DIST operator
    delta,          # DELTA operator
    focus,          # FOCUS operator
    anomaly_score,  # ANOMALY_SCORE
)
from leet.types import Msg1337, Intent, Surface, CanonicalSpace
from leet.axes import CANONICAL_AXES, AxisGroup, axes_in_group
from leet.validate import validate
```

### CLI Python — `leet`

Instalado automaticamente pelo `pip install`.

```bash
# Verificar versão
leet version

# COGON_ZERO
leet zero

# Listar eixos
leet axes
leet axes --group A
leet axes --group B
leet axes --group C

# Codificar texto
leet encode "o amor é eterno"
leet encode "emergência no sistema de pagamentos" --projector mock

# Decodificar COGON
leet decode cogon.json
leet decode cogon.json --projector anthropic

# Validar MSG_1337
leet validate mensagem.json

# Fundir dois COGONs
leet blend cogon_a.json cogon_b.json
leet blend cogon_a.json cogon_b.json --alpha 0.3

# Distância semântica
leet dist cogon_a.json cogon_b.json
```

### API Python — Exemplos

```python
from leet import Cogon, blend, dist, focus, anomaly_score
import asyncio

# ── Criar e serializar ──────────────────────────────────────────────────
cogon = Cogon(sem=[0.5]*32, unc=[0.1]*32)
json_str = cogon.to_json()
cogon2 = Cogon.from_json(json_str)

# ── BLEND ──────────────────────────────────────────────────────────────
c_fusao = blend(cogon_a, cogon_b, alpha=0.5)
# sem_fusao[i] = 0.5 * sem_a[i] + 0.5 * sem_b[i]
# unc_fusao[i] = max(unc_a[i], unc_b[i])

# ── DIST ───────────────────────────────────────────────────────────────
d = dist(cogon_a, cogon_b)
# d ∈ [0.0, 1.0], ponderado por (1 - max_unc)

# ── FOCUS ──────────────────────────────────────────────────────────────
# Focar em Urgência (C1=22) e Anomalia (C5=26)
c_foco = focus(cogon, dims=[22, 26])
# c_foco.sem[22] = cogon.sem[22]
# c_foco.sem[i] = 0.0 para i ≠ 22 e i ≠ 26
# c_foco.unc[i] = 1.0 para i não selecionado

# ── ANOMALY_SCORE ──────────────────────────────────────────────────────
historico = [cogon_t0, cogon_t1, cogon_t2, cogon_t3]
score = anomaly_score(cogon_atual, historico)
if score > 0.5:
    print(f"Anomalia detectada! score={score:.3f}")

# ── Encode via projector ────────────────────────────────────────────────
from leet.bridge import MockProjector, encode, decode

projector = MockProjector()
cogon = asyncio.run(encode("amor é eterno", projector))
texto = asyncio.run(decode(cogon, projector))
```

### Configuração via Python SDK

```python
from leet.config import LeetConfig, ServerConfig, CacheConfig

# Configuração manual
config = LeetConfig(
    server=ServerConfig(host="localhost", port=50051, timeout=30.0),
    cache=CacheConfig(backend="memory", ttl_seconds=3600),
    debug=False,
    log_level="INFO",
)

# Carregar de arquivo
config = LeetConfig.from_file("config.json")   # JSON
config = LeetConfig.from_file("config.yaml")   # YAML
config = LeetConfig.from_file("config.toml")   # TOML

# Carregar de variáveis de ambiente (prefixo LEET_)
config = LeetConfig.from_env()

# Usar instância global
from leet.config import get_config
cfg = get_config()
```

### Validação de MSG_1337

```python
from leet.validate import validate
from leet.types import Msg1337

msg = Msg1337.from_json(json_str)
error = validate(msg)

if error is None:
    print("✓ MSG_1337 válida")
else:
    print(f"✗ Erro: {error}")
    # Exemplos de erros:
    # "R1: sem length must be 32"
    # "R3: sem values must be in [0, 1]"
    # "R5: id must not be nil"
    # "R7: stamp must be > 0"
```

---

## 9. leet-py — SDK de Alto Nível

SDK simplificado para uso de 1337 em projetos Python com múltiplos providers.

### Instalação

```bash
pip install -e leet-py/
```

### Uso básico

```python
import leet

# Conectar ao provider (escolha um)
client = leet.connect("mock")                         # sem API, local
client = leet.connect("anthropic")                    # usa ANTHROPIC_API_KEY
client = leet.connect("openai")                       # usa OPENAI_API_KEY
client = leet.connect("deepseek")                     # usa DEEPSEEK_API_KEY
client = leet.connect("gemini")                       # usa GEMINI_API_KEY
client = leet.connect("ollama", model="llama3.2")     # local via Ollama

# Parâmetros completos
client = leet.connect(
    provider="anthropic",
    model="claude-opus-4-6",          # model específico (opcional)
    base_url="https://...",           # endpoint customizado (opcional)
    api_key="sk-ant-...",             # ou usa env var ANTHROPIC_API_KEY
    service="auto",                   # "auto" | URL gRPC | "local"
    store="auto",                     # "auto" | redis:// | "memory"
    agent_id="agente-001",            # ID do agente nessa sessão
)
```

### Providers disponíveis

| Provider | Env Var | Modelo Padrão |
|----------|---------|---------------|
| `mock` | — | local |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-opus-4-6 |
| `openai` | `OPENAI_API_KEY` | gpt-4o |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat |
| `gemini` | `GEMINI_API_KEY` | gemini-2.0-flash |
| `ollama` | — | llama3.2 |

---

## 10. comparison_1337_vs_english.py — Benchmark de Compressão

Script de simulação de discussão filosófica entre 15 agentes usando 1337 vs linguagem natural, com métricas completas de compressão, latência e custo.

### Execução

```bash
# Modo mock (sem API, rápido — bom para testar o script)
python comparison_1337_vs_english.py

# Com mais rounds
python comparison_1337_vs_english.py --rounds 25

# Com API DeepSeek real
python comparison_1337_vs_english.py --rounds 25 --deepseek

# Paralelo com 8 workers (mais rápido com DeepSeek)
python comparison_1337_vs_english.py --rounds 25 --deepseek --workers 8

# Tópico personalizado
python comparison_1337_vs_english.py --rounds 10 --topic "Justiça"

# Sem output detalhado por round
python comparison_1337_vs_english.py --rounds 50 --quiet

# Sem salvar relatório JSON
python comparison_1337_vs_english.py --rounds 5 --no-save

# Diretório customizado para relatórios
python comparison_1337_vs_english.py --report-dir /tmp/relatorios

# Threshold de delta personalizado
python comparison_1337_vs_english.py --threshold 0.05
```

### Flags

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `-r, --rounds N` | `25` | Número de rounds de discussão |
| `-t, --topic TEXT` | `"Eros (Amor)"` | Tópico filosófico da discussão |
| `--threshold F` | `0.01` | Threshold para SparseDelta — |Δ| acima disso entra no delta |
| `--deepseek` | _(off)_ | Usar DeepSeek API real (requer `DEEPSEEK_API_KEY`) |
| `--workers N` | `5` | Workers paralelos para chamadas DeepSeek |
| `-q, --quiet` | _(off)_ | Suprimir output por round, mostrar só relatório final |
| `--no-save` | _(off)_ | Não salvar relatório JSON |
| `--report-dir PATH` | `./comparison_reports` | Diretório para salvar relatórios |

### Requisito para modo DeepSeek

```bash
export DEEPSEEK_API_KEY="sk-..."
python comparison_1337_vs_english.py --deepseek
```

### Os 15 Agentes

| Agente | Personalidade | Keywords de Ativação |
|--------|--------------|---------------------|
| Sócrates | Maiêutica, ironia socrática | filosofia, verdade, alma |
| Fedro | Discípulo entusiasmado | beleza, inspiração, amor |
| Pausânias | Distinção entre amores | eros, celestial, comum |
| Erixímaco | Médico, equilíbrio universal | medicina, harmonia, corpo |
| Aristófanes | Mitologia cômica, seres primordiais | mito, completude, metades |
| Agaton | Poeta, Eros jovem e belo | beleza, poesia, criação |
| Diótima | Sacerdotisa, escala do amor | escada, eternidade, divino |
| Alcibíades | Político ébrio e apaixonado | belo, sábio, vinho |
| Contador Carlos | ROI, planilhas, custo-benefício | custo, retorno, investimento |
| Técnico Tiago | Latência, bits, otimização | protocolo, sistema, rede |
| Padre Pedro | Fé, agapê, transcendência | deus, graça, fé |
| Comunista Carlos | Alienação, amor como luta de classes | classe, alienação, capital |
| Matemático Euler | Axiomas, provas formais, QED | prova, teorema, axioma |
| Pinóquio | Mentira com nariz crescente | mentira, nariz, verdade |
| Dr. Who | Time Lord, TARDIS, todas as eras | tardis, tempo, galifrey |

### Output do relatório

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELATÓRIO: 1337 vs ENGLISH — Eros (Amor)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────┬──────────────────┬─────────────┐
│ Bytes totais            │   17,339 / 89,812│ +80.7%      │
│ Compressão              │       5.18×       │             │
│ Tokens totais           │    0 / 57,787     │ +100%       │
│ Custo total (USD)       │  $0 / $0.0363     │ 100%        │
│ Delta coverage          │          68.5%    │             │
│ Bytes salvos (delta)    │         29,255 B  │             │
└─────────────────────────┴──────────────────┴─────────────┘

VELOCIDADE E LATÊNCIA
  Throughput geral: 1.2 msgs/s | 0.1 KB/s (1337) | 0.3 KB/s (EN)

  Latência 1337 (µs)  [encode + delta]:
    P50=305  P95=450  P99=717  max=2284  avg=323

  Latência DeepSeek (ms):
    P50=3736  P95=4947  P99=5529  max=6693  avg=3777

CONVERGÊNCIA SEMÂNTICA
  0.0697 → 0.0678  [convergindo Δ=+0.0019 +2.7%]
  Sparkline: ▅▂▂▄▁▂▃▆█▂▃▃▁▆▃▁▃▄▂▆▄▃▁▆▄

CUSTO POR AGENTE
  Matemático Euler:  8,767B EN | 5.90× | 4,781 tokens | $0.0034
  Padre Pedro:       7,486B EN | 6.23× | 4,186 tokens | $0.0028
  ...

CUSTO TOTAL
  Tokens input:   32,850
  Tokens output:  24,937
  Custo English:  $0.0363
  Custo 1337:     $0.0000  ← zero tokens de transporte
```

### Relatório JSON salvo

```json
{
  "timestamp": 1774844090,
  "config": {"rounds": 25, "topic": "Eros (Amor)", "mode": "deepseek"},
  "summary": {
    "bytes_1337": 17339,
    "bytes_en": 89812,
    "compression": 5.18,
    "tokens_total": 57787,
    "cost_usd": 0.0363
  },
  "per_agent": {...},
  "convergence": [0.0697, 0.0651, ...]
}
```

---

## 11. setup.py — Configuração Interativa

Script de configuração interativa que lê/salva `.env` e opcionalmente atualiza `docker-compose.yml`.

### Execução

```bash
python setup.py
```

### Menu Principal

```
════════════════════════════════════════════════
  ⚙  CONFIGURAÇÃO DO PROTOCOLO 1337
════════════════════════════════════════════════

  O que deseja configurar?

  1)  Serviço 1337 (porta, backend, store, batch)
  2)  Embedding (modelo, URL, chave, matriz W)
  3)  Chaves de API (DeepSeek, Anthropic, OpenAI, Gemini…)
  4)  Python SDK (host, cache, projeção, log)
  5)  Experimento de comparação (rounds, tópico, threshold)
  6)  Docker (atualizar docker-compose.yml)
  7)  Mostrar configuração atual
  s)  Salvar .env e sair
  q)  Sair sem salvar

  Opção:
```

### Comportamento das Prompts

```
# Prompt com valor atual entre colchetes
# Enter mantém o valor atual

  › Porta gRPC [50051]: _
                ^^^^^  ← pressionar Enter mantém "50051"

# Opções numeradas (● = atual)
  › Backend de projeção vetorial
    ● 1. simd   ← atual
    ○ 2. cpu
    ○ 3. mock
  Escolha (número ou Enter para manter [simd]):

# Chaves secretas — mostradas mascaradas
  › Chave DeepSeek [********af41]: _
                    ^^^^^^^^^^^^^ ← mascara tudo exceto últimos 4
```

### Seção 1 — Serviço 1337

Configura: `LEET_PORT`, `LEET_BACKEND`, `LEET_STORE`, `LEET_BATCH_WINDOW`, `LEET_BATCH_MAX`, `RUST_LOG`

```
# Store: escolher entre memory / redis / sqlite
# Se redis: pede URL completa
# Se sqlite: pede path do arquivo
```

### Seção 2 — Embedding

Configura: `LEET_EMBED_MODEL`, `LEET_EMBED_URL` (se openai), `LEET_EMBED_KEY` (se openai), `LEET_W_PATH`

```
# Se modelo = "mock": sem URL nem chave
# Se modelo = "openai": pede URL + chave
# W_PATH: deixar vazio para usar identidade init
```

### Seção 3 — Chaves de API

Configura: `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MOONSHOT_API_KEY`

```
# Chaves já configuradas aparecem com status: ✓ configurado
# Chaves não configuradas: não configurado
# Pergunta se quer configurar cada uma individualmente
# Opção de remover chave existente
```

### Seção 4 — Python SDK

Configura: `LEET_SERVER_HOST`, `LEET_SERVER_PORT`, `LEET_SERVER_TIMEOUT`, `LEET_CACHE_BACKEND`, `LEET_CACHE_TTL_SECONDS`, `LEET_PROJECTION_BACKEND`, `LEET_DEBUG`, `LEET_LOG_LEVEL`

### Seção 5 — Experimento de Comparação

Configura variáveis lidas pelo `comparison_1337_vs_english.py`:

| Variável | Padrão | Uso |
|----------|--------|-----|
| `LEET_EXP_ROUNDS` | `25` | `--rounds` default |
| `LEET_EXP_TOPIC` | `Eros (Amor)` | `--topic` default |
| `LEET_EXP_THRESHOLD` | `0.01` | `--threshold` default |
| `LEET_EXP_WORKERS` | `5` | `--workers` default |
| `LEET_EXP_REPORT_DIR` | `./comparison_reports` | `--report-dir` default |

### Seção 6 — Docker

Atualiza `docker-compose.yml` com os valores atuais do `.env`.

```bash
# Processo:
# 1. Faz backup: docker-compose.yml.bak
# 2. Substitui variáveis de ambiente inline no arquivo
# 3. Variáveis atualizadas: LEET_PORT, LEET_BACKEND, LEET_STORE,
#    LEET_BATCH_WINDOW, LEET_BATCH_MAX, LEET_EMBED_MODEL, RUST_LOG
```

### Seção 7 — Mostrar configuração atual

Exibe todas as variáveis agrupadas por seção. Chaves secretas aparecem mascaradas (ex: `********af41`). Variáveis não configuradas aparecem como `—`.

### Salvar (`s`)

```bash
# Grava .env preservando:
# - Comentários existentes
# - Ordem de variáveis já no arquivo
# - Variáveis não gerenciadas pelo script
# - Novas variáveis são adicionadas ao final

# Exibe instruções pós-save:
# Para aplicar ao serviço Rust:
#   source .env && cargo run --release -p leet-service
# Para aplicar com Docker:
#   docker compose up --env-file .env
```

---

## 12. Variáveis de Ambiente — Referência Completa

### Serviço Rust (leet-service)

| Variável | Padrão | Descrição | Exemplo |
|----------|--------|-----------|---------|
| `LEET_PORT` | `50051` | Porta gRPC | `50051` |
| `LEET_BACKEND` | `simd` | Backend: `simd` \| `cpu` \| `mock` | `simd` |
| `LEET_STORE` | `memory` | URL do store | `redis://localhost:6379` |
| `LEET_W_PATH` | _(nenhum)_ | Caminho da matriz W | `/data/w_matrix.bin` |
| `LEET_BATCH_WINDOW` | `10` | Janela de batch (ms) | `10` |
| `LEET_BATCH_MAX` | `64` | Máx itens por batch | `64` |
| `LEET_EMBED_MODEL` | `mock` | Modelo: `mock` \| `openai` | `openai` |
| `LEET_EMBED_URL` | _(nenhum)_ | URL do embedder | `https://api.openai.com/v1/embeddings` |
| `LEET_EMBED_KEY` | _(nenhum)_ | Chave do embedder | `sk-...` |
| `RUST_LOG` | `info` | Log Rust | `debug` |

### Python SDK

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_SERVER_HOST` | `localhost` | Host do leet-service |
| `LEET_SERVER_PORT` | `50051` | Porta do leet-service |
| `LEET_SERVER_TIMEOUT` | `30.0` | Timeout de conexão (s) |
| `LEET_SERVER_FALLBACK_HOSTS` | _(nenhum)_ | Hosts alternativos (CSV) |
| `LEET_RETRY_ENABLED` | `true` | Habilitar retry automático |
| `LEET_RETRY_MAX_RETRIES` | `3` | Máximo de tentativas |
| `LEET_CIRCUIT_BREAKER_ENABLED` | `true` | Circuit breaker ativo |
| `LEET_CACHE_BACKEND` | `memory` | Cache: `memory` \| `redis` \| `sqlite` |
| `LEET_CACHE_TTL_SECONDS` | `3600` | TTL do cache (s) |
| `LEET_PROJECTION_BACKEND` | `mock` | Projeção: `mock` \| `anthropic` \| `openai` \| `grpc` |
| `LEET_PROJECTION_ANTHROPIC_API_KEY` | _(nenhum)_ | Chave Anthropic para projeção |
| `LEET_PROJECTION_OPENAI_API_KEY` | _(nenhum)_ | Chave OpenAI para projeção |
| `LEET_METRICS_ENABLED` | `true` | Coletar métricas |
| `LEET_DEBUG` | `false` | Modo debug |
| `LEET_LOG_LEVEL` | `INFO` | Log Python |

### Chaves de API (providers)

| Variável | Provider | Onde usar |
|----------|----------|-----------|
| `DEEPSEEK_API_KEY` | DeepSeek | `comparison_1337_vs_english.py --deepseek`, `leet.connect("deepseek")` |
| `ANTHROPIC_API_KEY` | Anthropic | `leet.connect("anthropic")`, `leet encode --projector anthropic` |
| `OPENAI_API_KEY` | OpenAI | `leet.connect("openai")`, `LEET_EMBED_MODEL=openai` |
| `GEMINI_API_KEY` | Google Gemini | `leet.connect("gemini")` |
| `MOONSHOT_API_KEY` | Moonshot/Kimi | `leet.connect("moonshot")` |

### Experimento de comparação

| Variável | Padrão | Flag correspondente |
|----------|--------|---------------------|
| `LEET_EXP_ROUNDS` | `25` | `--rounds` |
| `LEET_EXP_TOPIC` | `Eros (Amor)` | `--topic` |
| `LEET_EXP_THRESHOLD` | `0.01` | `--threshold` |
| `LEET_EXP_WORKERS` | `5` | `--workers` |
| `LEET_EXP_REPORT_DIR` | `./comparison_reports` | `--report-dir` |

---

## 13. Docker e Docker Compose

### Iniciar todos os serviços

```bash
docker compose up
```

### Iniciar só o serviço 1337 (sem prometheus/grafana)

```bash
docker compose up leet-service redis
```

### Com variáveis de ambiente do .env

```bash
docker compose --env-file .env up
```

### Serviços disponíveis

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `leet-service` | `50051` | gRPC principal |
| `redis` | `6379` | Store e cache |
| `prometheus` | `9090` | Métricas (opcional) |
| `grafana` | `3000` | Dashboards (opcional) |

### ZeroMQ — Portas

| Porta | Padrão ZMQ | Uso |
|-------|-----------|-----|
| `5555` | REQ/REP | Requisição/Resposta síncrona |
| `5556` | PUB/SUB | Broadcast de COGONs |
| `5557` | PUSH/PULL | Pipeline unidirecional |
| `5558` | ROUTER | Roteamento multi-agente |

### Build da imagem

```bash
docker build -t leet-service:latest .
docker run -p 50051:50051 -e LEET_EMBED_MODEL=mock leet-service:latest
```

---

## 14. Arquivo .env — Formato e Exemplos

### Formato

```bash
# Comentários com #
VARIAVEL=valor        # sem aspas para strings simples
VARIAVEL="com espaços"
VARIAVEL=             # vazio = desabilitado
```

### .env para desenvolvimento local (mock)

```bash
# ─── Serviço ─────────────────────────────────────────────
LEET_PORT=50051
LEET_BACKEND=simd
LEET_STORE=memory
LEET_BATCH_WINDOW=10
LEET_BATCH_MAX=64
LEET_EMBED_MODEL=mock
RUST_LOG=debug

# ─── Python SDK ──────────────────────────────────────────
LEET_SERVER_HOST=localhost
LEET_SERVER_PORT=50051
LEET_CACHE_BACKEND=memory
LEET_PROJECTION_BACKEND=mock
LEET_DEBUG=true
LEET_LOG_LEVEL=DEBUG

# ─── Chaves API ──────────────────────────────────────────
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ─── Experimento ─────────────────────────────────────────
LEET_EXP_ROUNDS=10
LEET_EXP_TOPIC=Eros (Amor)
LEET_EXP_THRESHOLD=0.01
LEET_EXP_WORKERS=3
```

### .env para produção

```bash
# ─── Serviço ─────────────────────────────────────────────
LEET_PORT=50051
LEET_BACKEND=simd
LEET_STORE=redis://redis:6379
LEET_BATCH_WINDOW=10
LEET_BATCH_MAX=64
LEET_EMBED_MODEL=openai
LEET_EMBED_URL=https://api.openai.com/v1/embeddings
LEET_EMBED_KEY=sk-...
LEET_W_PATH=/data/w_matrix.bin
RUST_LOG=info

# ─── Python SDK ──────────────────────────────────────────
LEET_SERVER_HOST=leet-service
LEET_SERVER_PORT=50051
LEET_CACHE_BACKEND=redis
LEET_CACHE_TTL_SECONDS=7200
LEET_PROJECTION_BACKEND=grpc
LEET_DEBUG=false
LEET_LOG_LEVEL=WARNING

# ─── Chaves API ──────────────────────────────────────────
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Carregar .env no shell

```bash
# Método 1: source (exporta para o processo atual)
source .env
cargo run --release -p leet-service

# Método 2: export inline (só para um comando)
export $(grep -v '^#' .env | xargs) && cargo run --release -p leet-service

# Método 3: Docker Compose lê automaticamente
docker compose up

# Método 4: Docker Compose com .env explícito
docker compose --env-file .env up
```

---

## 15. Fluxo de Desenvolvimento

### Primeira vez

```bash
# 1. Configurar variáveis de ambiente
python setup.py
# → escolher opção 3 para configurar chaves de API
# → escolher opção 1 para configurar o serviço
# → pressionar s para salvar .env

# 2. Construir o serviço Rust
cd leet1337
cargo build --release

# 3. Instalar Python SDK
cd ../python
pip install -e .

# 4. Iniciar o serviço
source ../.env && cargo run --release -p leet-service

# 5. Testar com a CLI
leet health
leet encode "amor é eterno"
leet axes
```

### Rodando o benchmark de compressão

```bash
# Modo mock (sem API, imediato)
python comparison_1337_vs_english.py --rounds 5

# Modo DeepSeek (requer DEEPSEEK_API_KEY no .env)
source .env
python comparison_1337_vs_english.py --rounds 25 --deepseek --workers 5

# Resultado esperado: ~5× compressão, ~0 tokens de transporte
```

### Estrutura de arquivos

```
1337/
├── setup.py                          # ← configuração interativa
├── comparison_1337_vs_english.py     # ← benchmark de compressão
├── .env                              # ← gerado pelo setup.py
├── GUIDE.md                          # ← este arquivo
├── README.md                         # ← visão geral do projeto
│
├── leet1337/                         # Código Rust
│   ├── leet-core/                    # Tipos, operadores, wire format
│   │   └── src/
│   │       ├── types.rs              # Cogon, DAG, MSG_1337, Intent
│   │       ├── operators.rs          # blend, dist, focus, delta, sparse_delta
│   │       ├── wire.rs               # WireMsg, WireCogon, SparseDelta, codec
│   │       ├── axes.rs               # 32 eixos canônicos
│   │       └── validate.rs           # Regras R1–R21
│   ├── leet-service/                 # Servidor gRPC
│   │   └── src/
│   │       ├── config.rs             # Config::from_env()
│   │       └── projection/
│   │           ├── engine.rs         # Engine (LRU cache + encode_batch)
│   │           ├── matrix.rs         # WMatrix (SIMD GEMM)
│   │           ├── batch.rs          # BatchQueue (worker + oneshot)
│   │           └── embed.rs          # Embedder trait (Mock, OpenAI)
│   ├── leet-cli/                     # Binário `leet`
│   └── leet-bridge/                  # Bridge Python↔Rust
│
├── python/leet/                      # Python SDK
│   ├── __init__.py                   # API pública
│   ├── cli.py                        # Comando `leet`
│   ├── config.py                     # LeetConfig, from_env, from_file
│   ├── types.py                      # Msg1337, Intent, Surface
│   ├── axes.py                       # CANONICAL_AXES, AxisGroup
│   ├── validate.py                   # validate(msg)
│   └── bridge.py                     # MockProjector, AnthropicProjector
│
├── leet-py/                          # SDK de alto nível
│   └── leet/
│       ├── __init__.py               # leet.connect()
│       └── providers.py              # PROVIDER_PRESETS
│
├── comparison_reports/               # Relatórios JSON salvos
└── docker-compose.yml                # Orquestração Docker
```

### Ciclo de teste

```bash
# Testes Rust
cd leet1337
cargo test                            # todos os testes
cargo test -p leet-core               # só leet-core
cargo test wire                       # testes do wire format
cargo test sparse                     # testes do SparseDelta

# Testes Python
cd python
pytest tests/
pytest tests/test_cli.py -v
pytest tests/test_adapters.py -v

# Benchmark rápido (mock, 5 rounds)
python comparison_1337_vs_english.py --rounds 5 --quiet
```
