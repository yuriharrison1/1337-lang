# leet-core

Crate Rust de tipos, validação, operadores e codec binário do protocolo 1337.

## Responsabilidade

`leet-core` é a especificação executável do protocolo — nenhum outro crate define tipos ou regras. Não faz I/O, não chama rede.

## Tipos Principais

### `Cogon`

```rust
pub struct Cogon {
    pub id:    Uuid,
    pub sem:   SemVec,       // [f32; 32], todos em [0.0, 1.0]
    pub stamp: i64,          // Unix ms
    pub raw:   Option<RawField>,
}
```

Métodos:
- `Cogon::zero()` — retorna o COGON_ZERO canônico (spec § 2)
- `cogon.is_zero()` — verifica estrutura exata do COGON_ZERO
- `cogon.is_low_confidence()` — `sem[29] < 0.1` (R5)
- `cogon.to_bytes()` — serialização binária 96 bytes
- `Cogon::from_bytes(data)` — desserialização com verificação CRC32

### `Dag`

Grafo acíclico dirigido de COGONs — a "frase semântica".

```rust
pub struct Dag {
    pub root:  Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
}
```

Métodos:
- `dag.add_node(cogon)` — invalida cache topológico
- `dag.add_edge(edge)` — invalida cache topológico
- `dag.topological_order()` — algoritmo de Kahn, cacheado

### `Msg1337`

O envelope completo de uma mensagem:

```rust
pub struct Msg1337 {
    pub id:       Uuid,
    pub sender:   Uuid,
    pub receiver: Receiver,     // Agent(Uuid) | Broadcast
    pub intent:   Intent,       // ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK
    pub ref_hash: Option<[u8; 32]>,   // obrigatório para DELTA (R2)
    pub patch:    Option<SemVec>,      // obrigatório para DELTA (R2)
    pub payload:  Payload,      // Cogon | Dag
    pub c5:       C5Block,
    pub surface:  SurfaceBlock,
}
```

### `C5Block`

Bloco de espaço canônico para handshake e alinhamento entre agentes:

```rust
pub struct C5Block {
    pub zone_fixed:    SemVec,              // 32 eixos fixos
    pub zone_emergent: HashMap<Uuid, f32>,  // eixos emergentes
    pub schema_ver:    String,              // semver
    pub align_hash:    [u8; 32],            // SHA256 do alinhamento
}
```

### `EdgeType`

Tipos de aresta semântica em um DAG:

| Valor | Significado |
|-------|-------------|
| `CAUSA` | relação causal |
| `CONDICIONA` | relação condicional |
| `CONTRADIZ` | contradição |
| `REFINA` | refinamento/especialização |
| `EMERGE` | emergência |

## Eixos

```rust
use leet_core::axes::{CANONICAL_AXES, axis_by_code, axis_by_index, valence_axes};

let ax = axis_by_code("G8").unwrap();  // URGENCY, índice 23
let ax = axis_by_index(29).unwrap();   // TEMPORAL_VECTOR
let valences = valence_axes();         // [D6, G2, G7, P4, P8]
```

Os 5 eixos de valência têm baseline neutro em 0.5:

| Código | Nome | Escala |
|--------|------|--------|
| D6 | ONTOLOGICAL_VALENCE | 0=negativo · 0.5=neutro · 1=positivo |
| G2 | TEMPORAL_ANCHOR | 0=passado · 0.5=presente · 1=futuro |
| G7 | EPISTEMIC_VALENCE | 0=contraditório · 0.5=inconclusivo · 1=confirmatório |
| P4 | AFFECT | 0=negativo · 0.5=neutro · 1=positivo |
| P8 | ACTION_VALENCE | 0=alerta · 0.5=consulta · 1=confirmação |

## Operadores

```rust
use leet_core::operators::{blend, delta, dist, focus, anomaly_score};

// BLEND — fusão semântica com regras por eixo
let c = blend(&c1, &c2, 0.7);

// DELTA — diferença element-wise (pode ser negativa)
let patch: SemVec = delta(&c_prev, &c_curr);

// DIST — distância cosseno [0, 2], ponderada por P6
let d = dist(&c1, &c2);

// FOCUS — projeta sobre subconjunto de dimensões
let c_focused = focus(&cogon, &[8, 23, 26]);

// ANOMALY_SCORE — distância ao centróide histórico
let score = anomaly_score(&cogon, &history);
```

## Validação (R1–R23)

```rust
use leet_core::validate;

validate::validate(&msg)?;            // valida estrutura completa
let warnings = validate::check_confidence(&msg);  // warnings R5
```

Regras estruturais implementadas:

| Regra | Verificação |
|-------|-------------|
| R2 | DELTA requer `ref_hash` e `patch`; não-DELTA não pode ter `patch` |
| R3 | Todas as arestas do DAG referenciam nós existentes |
| R4 | DAG sem ciclos (Kahn's algorithm) |
| R5 | P6_TEMPORAL_VECTOR < 0.1 → warning de baixa confiança |
| R6 | `human_required=true` exige campo `urgency` |
| R7 | `zone_emergent` não vazio → `align_hash` não nulo |
| R8 | Broadcast permitido apenas para ANOMALY e SYNC |
| R9 | COGON com role EVIDENCE não pode ter sem all < 0.01 |
| R14 | No DAG, parents são processados antes dos filhos |
| R17 | Mensagem é serializável em JSON |
| R20 | id=nil_UUID → deve ser COGON_ZERO exato |
| R21 | raw.content não expõe chaves internas do protocolo |
| R22 | Todos os valores de sem em [0.0, 1.0] |
| R23 | stamp ≥ 0 |

Regras que dependem de estado multi-mensagem (R13, R15, R16, R18) são responsabilidade do bridge/operador layer.

## Codec Binário

```rust
use leet_core::codec::{encode_cogon, decode_cogon, TOTAL_SIZE};

let bytes = encode_cogon(&cogon);    // 96 bytes, sempre
let cogon = decode_cogon(&bytes)?;  // verifica magic, version, CRC32
```

Formato (96 bytes):

```
Offset  Tamanho  Campo
0       2        magic = 0x1337
2       1        version_flags = 0x20 (VERSION=2)
3       1        reserved = 0x00
4       16       UUID (id)
20      32       sem quantizado (uint8, [0..255])
52      32       reserved zeros (era unc em v0.4)
84      8        stamp big-endian i64
92      4        CRC32 dos bytes 0..92
```

Compatibilidade: frames v0.4 com bytes não-zero na região reserved são aceitos (CRC deve ser válido).

## Dependências

```toml
[dependencies]
serde       = { version = "1", features = ["derive"] }
serde_json  = "1"
uuid        = { version = "1", features = ["v4", "serde"] }
crc32fast   = "1"
```

## Testes

```bash
cargo test -p leet-core   # 69 testes
```
