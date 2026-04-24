# COGON — Vetor Semântico Canônico

**COGON** (Compressed Ontological Graph Object Node) é o tipo de dado central do protocolo 1337. É um vetor de 32 dimensões em `[0, 1]^32` que codifica o estado semântico de um conceito, intenção ou contexto.

## Estrutura

```
Cogon {
    id:    UUID         -- identificador único
    sem:   [f32; 32]   -- vetor semântico, todos em [0.0, 1.0]
    stamp: i64          -- Unix timestamp em milissegundos
    raw:   Option<RawField>  -- anexo opcional (evidência, artefato, trace, bridge)
}
```

### RawField

Conteúdo arbitrário anexado a um COGON sem expor internals do protocolo (R21):

```
RawField {
    content_type: String        -- MIME type ou string de enum
    content:      JSON Value    -- payload arbitrário
    role:         RawRole       -- EVIDENCE | ARTIFACT | TRACE | BRIDGE
}
```

## Os 32 Eixos Canônicos

Organizados em 4 blocos de 8 eixos cada. Cada eixo é indexado por posição (R10).

### Bloco S — Semântico (índices 0–7)

| Índice | Código | Nome | Descrição |
|--------|--------|------|-----------|
| 0 | S1 | ESSENCE | Conceito existe por si mesmo |
| 1 | S2 | CORRESPONDENCE | Espelha padrões em outros níveis de abstração |
| 2 | S3 | VIBRATION | Movimento ou transformação contínua |
| 3 | S4 | POLARITY | Posição em um espectro entre extremos |
| 4 | S5 | RHYTHM | Padrão cíclico ou periódico |
| 5 | S6 | CAUSE_EFFECT | Agente causal vs efeito |
| 6 | S7 | GENERATIVITY | Generativo/ativo vs receptivo/passivo |
| 7 | S8 | SYSTEM | Conjunto com comportamento emergente |

### Bloco D — Dinâmico (índices 8–15)

| Índice | Código | Nome | Descrição |
|--------|--------|------|-----------|
| 8 | D1 | STATE | Configuração em um momento |
| 9 | D2 | PROCESS | Transformação ao longo do tempo |
| 10 | D3 | RELATION | Conexão entre entidades |
| 11 | D4 | SIGNAL | Variação portadora de informação |
| 12 | D5 | STABILITY | Tendência ao equilíbrio |
| 13 | D6 | ONTOLOGICAL_VALENCE ★ | Sinal intrínseco: 0=negativo, 0.5=neutro, 1=positivo |
| 14 | D7 | CAUSALITY | Origem identificável |
| 15 | D8 | VERIFIABILITY | Externamente confirmável |

### Bloco G — Gravidade (índices 16–23)

| Índice | Código | Nome | Descrição |
|--------|--------|------|-----------|
| 16 | G1 | TEMPORALITY | Âncora temporal definida |
| 17 | G2 | TEMPORAL_ANCHOR ★ | Orientação: 0=passado, 0.5=presente, 1=futuro |
| 18 | G3 | COMPLETENESS | Resolvido ou aberto |
| 19 | G4 | REVERSIBILITY | Pode ser desfeito |
| 20 | G5 | COGNITIVE_LOAD | Carga cognitiva |
| 21 | G6 | ORIGIN | Grau de observação: 0=assumido, 1=observado |
| 22 | G7 | EPISTEMIC_VALENCE ★ | Sinal epistêmico: 0=contraditório, 0.5=inconclusivo, 1=confirmatório |
| 23 | G8 | URGENCY | Pressão temporal: 0=nenhuma, 1=máxima urgência |

### Bloco P — Precisão (índices 24–31)

| Índice | Código | Nome | Descrição |
|--------|--------|------|-----------|
| 24 | P1 | IMPACT | Consequência esperada |
| 25 | P2 | VALUE | Conecta ao que realmente importa |
| 26 | P3 | ANOMALY | Desvio do padrão esperado |
| 27 | P4 | AFFECT ★ | Valência emocional: 0=negativo, 0.5=neutro, 1=positivo |
| 28 | P5 | DEPENDENCY | Precisa de outro para existir |
| 29 | P6 | TEMPORAL_VECTOR | Direção temporal: 0=passado, 1=futuro |
| 30 | P7 | ACTION | Resposta ativa exigida: 0=passivo, 1=ação imediata |
| 31 | P8 | ACTION_VALENCE ★ | Intenção de ação: 0=alerta, 0.5=consulta, 1=confirmação |

★ **Eixos de valência** — baseline neutro em 0.5.

## COGON_ZERO

O COGON canônico nulo (spec v0.5.1 § 2). Usado como estado inicial no handshake C5.

```
id:    00000000-0000-0000-0000-000000000000
stamp: 0
sem:   [1.0, 0.0, 0.0, 0.0,  0.0, 1.0, 1.0, 1.0,   -- S
         0.5, 0.0, 0.0, 1.0,  0.0, 1.0, 1.0, 0.0,   -- D
         1.0, 0.5, 1.0, 0.5,  0.5, 1.0, 0.1, 0.0,   -- G
         0.8, 0.0, 1.0, 0.0,  0.5, 1.0, 0.0, 0.0]   -- P
```

## Notação Compacta

Para exibir COGONs em linha, use apenas os eixos com ativação significativa:

```
⟨G8=0.95 P3=0.90 D1=0.85⟩
```

Convenção: listar eixos com valor > 0.3, em ordem decrescente.

## Operadores

### FOCUS(c, dims)

Projeta um COGON sobre um subconjunto de dimensões. Dimensões não selecionadas ficam em 0.

```rust
focus(&cogon, &[8, 23, 26])  // apenas D1, G8, P3
```

### DELTA(c_prev, c)

Diferença element-wise do vetor semântico. Pode ser negativo (não clamped).

```rust
let patch: SemVec = delta(&c_prev, &c_curr);
```

### BLEND(c1, c2, α)

Fusão semântica com regras por bloco:

| Eixo | Regra |
|------|-------|
| D4 (SIGNAL) | `min(c1, c2)` — conservador |
| G1 (TEMPORALITY) | `clamp(c1 + c2, 0, 1)` — acumulativo |
| G7 (EPISTEMIC_VALENCE) | `max(c1, c2)` — maior ganho vence |
| P6 (TEMPORAL_VECTOR) | `min(c1, c2)` — conservador |
| demais | `α·c1 + (1-α)·c2` — interpolação linear |

```rust
blend(&c1, &c2, 0.7)  // 70% c1, 30% c2
```

### DIST(c1, c2)

Distância cosseno ponderada por P6_TEMPORAL_VECTOR. Retorna `[0, 2]`:
- `0` = idênticos
- `1` = ortogonais
- `2` = opostos

```rust
let d = dist(&c1, &c2);
// d < 0.05 → skip re-envio (informação já presente)
```

### ANOMALY_SCORE(c, history)

Distância de `c` ao centróide histórico ponderado por G1_TEMPORALITY.
Retorna `0.5` para histórico vazio (neutro).

## Confiança

Um COGON é marcado de **baixa confiança** (R5) quando `P6_TEMPORAL_VECTOR < 0.1`.
Isso gera um warning, não um erro de validação.

## Codec Binário

Formato wire: **96 bytes fixos** com CRC32.

```
[HEADER 4B][PAYLOAD 88B][CHECKSUM 4B]

Header:   magic=0x1337 | version=0x02 | reserved
Payload:  UUID (16B) | sem quantizado (32B) | reserved zeros (32B) | stamp ms (8B)
Checksum: CRC32 dos 92 bytes anteriores
```

Quantização: `float [0, 1] ↔ uint8 [0, 255]` — precisão ±0.004.
Compressão vs JSON: ~4-5:1.
