# leet-bridge

Crate Rust de tradução NL↔COGON. Implementa R21: nenhum internal do protocolo é exposto a sistemas externos.

## Responsabilidade

```
Sistema Externo
     │ (texto plano)
     ▼
┌─────────────┐
│  BridgeIn   │  encode(text) → Cogon
│  BridgeOut  │  decode(Cogon) → text
└─────────────┘
     │ (COGON / DAG — interno)
     ▼
 rede leet-core
```

## API Pública

```rust
use leet_bridge::{encode, decode, BridgeProjector, MockProjector};

// Encode: texto → COGON
let cogon = encode("deploy urgente falhou", &projector)?;

// Decode: COGON → texto
let text = decode(&cogon, &projector)?;
```

## BridgeProjector

Trait para diferentes backends de projeção:

```rust
pub trait BridgeProjector: Send + Sync {
    fn project(&self, text: &str) -> Result<Cogon, LeetError>;
    fn reconstruct(&self, cogon: &Cogon) -> Result<String, LeetError>;
}
```

### MockProjector

Implementação determinística para testes — sem rede, sem API.

Usa heurísticas de palavras-chave para ativar eixos semânticos:

```rust
let proj = MockProjector;
let cogon = proj.project("o servidor caiu")?;
// cogon.sem[8]  = 0.9  (D1_STATE)
// cogon.sem[26] = 0.9  (P3_ANOMALY)
// cogon.sem[13] = 0.15 (D6_ONTOLOGICAL_VALENCE — negativo)
```

## W Matrix (Caminho Primário)

A projeção principal usa uma matriz calibrada `W` de dimensões `[32 × D]`, onde D é a dimensão do embedding (ex: 768 ou 1536).

```
text → embedding → W @ embedding → clamp(0, 1) → sem[32]
```

### Carregamento

A W matrix é carregada uma única vez por processo (`OnceLock`). Ordem de busca:

1. `LEET_W_PATH` (variável de ambiente)
2. `./calibration/data/W.bin` (workspace local)
3. `/usr/share/leetlang/W.bin` (instalação do sistema)

```rust
use leet_bridge::projector::w_matrix;

if let Some(w) = w_matrix() {
    println!("W carregada: {}x{}", w.rows, w.cols);
}
```

### Formato do arquivo W.bin

```
Offset  Tamanho  Campo
0       4        u32 rows (sempre 32)
4       4        u32 cols (dimensão do embedding)
8       rows*cols*4  f32 little-endian, row-major
```

### Projeção via W

```rust
use leet_bridge::projector::{project_embedding, project_text, EmbeddingProvider};

// A partir de embedding pré-computado
let sem = project_embedding(&embedding_vec)?;

// A partir de texto + provider
let cogon = project_text("texto aqui", &provider)?;
```

### EmbeddingProvider

Trait para diferentes backends de embedding:

```rust
pub trait EmbeddingProvider: Send + Sync {
    fn embed(&self, text: &str) -> Result<Vec<f32>, BridgeError>;
    fn dim(&self) -> usize;
}
```

### Fallback

Com a feature `keyword-fallback` habilitada, se `W.bin` não estiver disponível o sistema cai para heurísticas de palavras-chave. Sem a feature, ausência de `W.bin` é um erro definitivo.

## Heurísticas (RULES)

Tabela de regras aplicadas pelo MockProjector e pelo fallback:

| Keywords | Eixo | Valor |
|----------|------|-------|
| caiu, falhou, erro, down, crash | D1_STATE (8) | 0.9 |
| caiu, falhou, erro, down, crash | P3_ANOMALY (26) | 0.9 |
| deploy, processo, pipeline, rodando | D2_PROCESS (9) | 0.85 |
| deploy, processo, pipeline, rodando | P7_ACTION (30) | 0.8 |
| reverter, desfazer, rollback, undo | G4_REVERSIBILITY (19) | 0.9 |
| reverter, desfazer, rollback, undo | P7_ACTION (30) | 0.85 |
| urgente, crítico, agora, imediato | G8_URGENCY (23) | 0.95 |

## nl_translator

Funções auxiliares para tradução NL↔COGON e inferência de intent:

```rust
use leet_bridge::{nl_to_cogon, cogon_to_nl, infer_intent};

let cogon = nl_to_cogon("deploy falhou", &projector)?;
let text  = cogon_to_nl(&cogon, &projector)?;
let intent = infer_intent("me diga o status");  // Intent::Query
```

## Anthropic Client

`leet_bridge::anthropic_client` — cliente HTTP para a API Anthropic, usado pelo modo `chat` do CLI.

Usa `LEET_API_KEY` como variável de ambiente.

## Claude 1337 Prompt

`leet_bridge::claude_1337_prompt` — system prompt configurado para que Claude Code opere em modo 1337 (comunicação COGON-first, notação compacta `⟨…⟩`).

## Testes

```bash
cargo test -p leet-bridge   # 12 testes
```

Todos os testes usam `MockProjector` — sem chamadas de rede.
