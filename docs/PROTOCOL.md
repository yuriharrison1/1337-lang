# Protocolo 1337 — Especificação v0.5.1

## O que é o COGON

COGON é a unidade fundamental do protocolo 1337. É um vetor semântico de 32 dimensões que representa o *significado comprimido* de qualquer mensagem, conceito ou estado.

```rust
pub struct Cogon {
    pub id:    Uuid,           // identificador único
    pub sem:   [f32; 32],     // projeção semântica — valores em [0.0, 1.0]
    pub unc:   [f32; 32],     // incerteza por dimensão — 0=certeza, 1=total incerteza
    pub stamp: i64,            // timestamp em nanossegundos desde Unix epoch
    pub raw:   Option<RawField>, // conteúdo arbitrário opcional (texto, bytes, JSON)
}
```

**COGON_ZERO** — identidade, "eu existo":
```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "sem": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
  "unc": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "stamp": 0,
  "raw": null
}
```

---

## Os 32 eixos canônicos (v0.5.1)

Os 32 eixos são organizados em 4 blocos de 8. Todos os valores estão em `[0.0, 1.0]` exceto os **eixos de valência** que têm 0.5 como neutro.

### Bloco S — Semântico (índices 0–7)

| Idx | Nome | Descrição | Extremos |
|-----|------|-----------|----------|
| 0 | S1 ESSENCIA | O conceito existe por si mesmo | 0=dependente, 1=autoexistente |
| 1 | S2 CORRESPONDENCIA | Espelha padrões em outros níveis | 0=único, 1=analógico |
| 2 | S3 VIBRACAO | Movimento/transformação contínua | 0=estático, 1=transformando |
| 3 | S4 POLARIDADE | Posição num espectro de extremos | 0=polo negativo, 1=polo positivo |
| 4 | S5 RITMO | Padrão cíclico ou periódico | 0=irregular, 1=altamente periódico |
| 5 | S6 CAUSA_EFEITO | Agente causal vs efeito | 0=efeito puro, 1=causa pura |
| 6 | S7 GENERO | Generativo/ativo vs receptivo/passivo | 0=receptivo, 1=generativo |
| 7 | S8 SISTEMA | Conjunto com comportamento emergente | 0=átomo, 1=sistema complexo |

### Bloco D — Dinâmico (índices 8–15)

| Idx | Nome | Descrição | Extremos |
|-----|------|-----------|----------|
| 8 | D1 ESTADO | Configuração num momento | 0=desconhecido, 1=totalmente definido |
| 9 | D2 PROCESSO | Transformação ao longo do tempo | 0=estático, 1=processo ativo |
| 10 | D3 RELACAO | Conexão entre entidades | 0=isolado, 1=profundamente conectado |
| 11 | D4 SINAL | Informação portando variação | 0=ruído, 1=sinal claro |
| 12 | D5 ESTABILIDADE | Tendência ao equilíbrio | 0=divergindo, 1=muito estável |
| 13 | **D6 VALENCIA_ONT** ★ | Sinal intrínseco | 0=negativo, **0.5=neutro**, 1=positivo |
| 14 | D7 CAUSALIDADE | Origem identificável | 0=opaco, 1=causa clara |
| 15 | D8 VERIFICABILIDADE | Confirmável externamente | 0=inverificável, 1=verificável |

### Bloco G — Gravidade (índices 16–23)

| Idx | Nome | Descrição | Extremos |
|-----|------|-----------|----------|
| 16 | G1 TEMPORALIDADE | Âncora temporal definida | 0=atemporal, 1=ancorado no tempo |
| 17 | **G2 ANCORA_TEMPORAL** ★ | Orientação temporal | 0=passado, **0.5=presente**, 1=futuro |
| 18 | G3 COMPLETUDE | Resolvido ou aberto | 0=totalmente aberto, 1=totalmente resolvido |
| 19 | G4 REVERSIBILIDADE | Pode ser desfeito | 0=irreversível, 1=reversível |
| 20 | G5 CARGA | Carga cognitiva | 0=trivial, 1=carga máxima |
| 21 | G6 ORIGEM | Grau de observação | 0=assumido, 0.5=inferido, 1=observado |
| 22 | **G7 VALENCIA_EPIST** ★ | Sinal epistêmico | 0=contraditório, **0.5=inconclusivo**, 1=confirmatório |
| 23 | G8 URGENCIA | Pressão temporal | 0=nenhuma, 1=urgência máxima |

### Bloco P — Precisão (índices 24–31)

| Idx | Nome | Descrição | Extremos |
|-----|------|-----------|----------|
| 24 | P1 IMPACTO | Consequência esperada | 0=negligível, 1=impacto máximo |
| 25 | P2 VALOR | Conecta com o que importa | 0=irrelevante, 1=alto valor |
| 26 | P3 ANOMALIA | Desvio do padrão esperado | 0=normal, 1=anomalia forte |
| 27 | **P4 AFETO** ★ | Valência emocional | 0=negativo, **0.5=neutro**, 1=positivo |
| 28 | P5 DEPENDENCIA | Precisa de outro para existir | 0=independente, 1=totalmente dependente |
| 29 | P6 VETOR_TEMPORAL | Direção temporal | 0=orientado ao passado, 1=orientado ao futuro |
| 30 | P7 ACAO | Resposta ativa necessária | 0=passivo, 1=ação imediata |
| 31 | **P8 VALENCIA_ACAO** ★ | Sinal de intenção | 0=alerta, **0.5=consulta**, 1=confirmação |

★ **Eixos de valência** — têm baseline neutro em 0.5. Para calcular ativação, use `|valor - 0.5|`.

---

## Regras semânticas de coerência

Ao construir ou avaliar um COGON, estas relações devem ser respeitadas:

| Regra | Condição | Consequência |
|-------|----------|--------------|
| Anomalia forte | P3 > 0.8 | P7 (ação) deve ser > 0.6 |
| Urgência alta | G8 > 0.7 | G5 (carga) tende a > 0.5 |
| Mensagem positiva | D6 > 0.7 | P3 tende a < 0.3 |
| COGON_ZERO | sem = [1.0;32] | Usado apenas como handshake |
| Incerteza total | unc[i] = 1.0 | Não permitido — indica erro de codificação |
| Valência positiva | D6 ou G7 > 0.85 | Indica afirmação clara |
| Anomalia confirmada | Intent = ANOMALY | P3 > 0.7 obrigatório |

---

## MSG_1337 — mensagem completa do protocolo

```rust
pub struct Msg1337 {
    pub id:      Uuid,
    pub sender:  Uuid,
    pub receiver: Receiver,    // All, Agent(Uuid), Surface(String)
    pub intent:  Intent,       // ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK
    pub ref_hash: Option<[u8; 32]>,  // referência a mensagem anterior
    pub patch:   Option<Cogon>,       // delta semântico (para Intent::DELTA)
    pub payload: Cogon,               // conteúdo principal
    pub c5:      Option<CanonicalSpace>, // bloco de espaço canônico
    pub surface: Option<String>,      // superfície de destino
}
```

### Intent

| Valor | Uso |
|-------|-----|
| `ASSERT` | Afirmação informativa (padrão) |
| `QUERY` | Pedido de informação ou clarificação |
| `DELTA` | Mudança de estado (envia patch COGON) |
| `SYNC` | Sincronização de estado entre agentes |
| `ANOMALY` | Reporte ou escalada de erro |
| `ACK` | Confirmação de recebimento ou conclusão |

---

## Handshake C5

O handshake C5 é executado antes de qualquer troca de mensagens no modo servidor. Garante que o agente conhece a especificação 1337 v0.5.1.

### Fases

```
Cliente                         Servidor
   │                               │
   │── Register { name, role } ──▶│  PROBE
   │                               │  valida nome canônico
   │◀── Registered { id, anchors} ─│  ECHO
   │    5 COGONs âncora           │
   │                               │
   │── Align { hash } ────────────▶│  ALIGN
   │   SHA256("1337:v0.5.1:" + name)│  servidor recomputa e compara
   │                               │
   │◀── Ready ─────────────────────│  VERIFY (sucesso)
   │                              ou
   │◀── Error { "alignment rejected"} │  VERIFY (falha)
```

### Cálculo do align_hash

```rust
// SHA256("1337:v0.5.1:" + agent_name) em hex lowercase
let input = format!("1337:v0.5.1:{}", agent_name);
let hash = Sha256::digest(input.as_bytes());
let hex = hex::encode(hash);
```

Exemplos:
```
ATLAS  → sha256("1337:v0.5.1:ATLAS")  → a3f7...
CIPHER → sha256("1337:v0.5.1:CIPHER") → 9e2b...
```

O hash é **determinístico e público** — não é um segredo, é prova de que o agente conhece o protocolo.

### COGONs âncora (5 referências imutáveis)

| # | Nome | Eixos dominantes |
|---|------|-----------------|
| 0 | presence | S1=0.95, D1=0.90, G3=0.90 |
| 1 | absence | S1=0.05, D1=0.05, G3=0.15 |
| 2 | change | S3=0.95, D2=0.90, D7=0.80 |
| 3 | agency | S7=0.90, S6=0.90, P7=0.90 |
| 4 | uncertainty | G7=0.45, unc[*]=0.75 |

---

## Protocolo de wire (TCP/Unix)

Mensagens são JSON newline-delimited (`\n` como terminador).

### WireMsg (enum)

```json
// Cliente → Servidor: registro
{ "type": "register", "name": "ATLAS", "role": "Strategic planner" }

// Servidor → Cliente: confirmação com âncoras
{ "type": "registered", "agent_id": "<uuid>", "anchors": [<5 COGONs>] }

// Cliente → Servidor: alinhamento
{ "type": "align", "hash": "<sha256_hex>" }

// Servidor → Cliente: pronto
{ "type": "ready" }

// Ambos: mensagem normal
{
  "type": "msg",
  "id": "<uuid>",
  "sender": "<uuid>",
  "receiver": "all",           // ou { "agent": "<uuid>" }
  "intent": "ASSERT",
  "payload": { <Cogon> },
  "nl": "texto natural opcional"
}

// Servidor → Cliente: erro
{ "type": "error", "message": "alignment rejected" }
```

---

## Codec binário (96 bytes)

Formato de serialização compacto para armazenamento e transmissão eficiente.

```
Byte  Tamanho  Campo
────  ───────  ──────────────────────────────────────────
0-1   2        magic = 0x1337
2     1        version = 0x02
3     1        flags (reservado, = 0x00)
4-35  32       sem[32] quantizado: f32 × 255 → u8
36-67 32       unc[32] quantizado: f32 × 255 → u8
68-83 16       UUID (bytes raw, big-endian)
84-91 8        stamp: i64 little-endian (nanossegundos)
92-95 4        CRC32 dos bytes 0-91
─────────────────────────────────────────────────────
96    TOTAL
```

**Compressão:** JSON típico de um COGON tem ~450-600 bytes. O codec binário usa 96 bytes fixos — compressão de 4-5×.

**Precisão:** quantização f32→u8 tem erro máximo de `0.5/255 ≈ 0.002` por eixo — negligível para uso semântico.
