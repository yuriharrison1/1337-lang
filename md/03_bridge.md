No workspace leet1337 que já existe (do prompt anterior), implemente o crate leet-bridge.

O bridge traduz texto humano → estruturas 1337 (COGONs, DAGs, MSG_1337) e vice-versa.
O bridge NÃO embute um LLM — define um trait que qualquer backend implementa.

---

# CONTEXTO RÁPIDO DA SPEC 1337 v0.4

- COGON: {id, sem[32], unc[32], stamp, raw?} — unidade atômica de significado
- DAG: {root, nodes[], edges[]} — frase/raciocínio composto
- MSG_1337: envelope completo (id, sender, receiver, intent, ref?, patch?, payload, c5, surface)
- 32 eixos canônicos: A0-A13 (ontológico), B1-B8 (epistêmico), C1-C10 (pragmático)
- Operadores: FOCUS, DELTA, BLEND, DIST, ANOMALY_SCORE
- O leet_core já tem todos os tipos, operadores e validação implementados

---

# ESTRUTURA

```
leet-bridge/
├── Cargo.toml
└── src/
    ├── lib.rs                 (re-exports + módulos)
    ├── error.rs               (BridgeError)
    ├── projector.rs           (trait SemanticProjector + MockProjector + prompt template)
    ├── human_to_1337.rs       (HumanBridge: texto → COGON/DAG/MSG_1337)
    └── leet_to_human.rs       (COGON/DAG/MSG_1337 → texto humano)
```

# REQUISITOS POR ARQUIVO

## Cargo.toml
```toml
[package]
name = "leet_bridge"
version = "0.4.0"
edition = "2021"

[dependencies]
leet_core = { path = "../leet-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "1"
async-trait = "0.1"
tokio = { version = "1", features = ["rt", "macros"], optional = true }

[features]
default = []
tokio-runtime = ["tokio"]

[dev-dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

## error.rs
```rust
#[derive(Debug, Error)]
pub enum BridgeError {
    #[error("Projection failed: {0}")]
    ProjectionFailed(String),

    #[error("Reconstruction failed: {0}")]
    ReconstructionFailed(String),

    #[error("Validation failed: {0}")]
    ValidationFailed(#[from] leet_core::LeetError),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Backend error: {0}")]
    Backend(String),
}
```

## projector.rs — O CORE DO BRIDGE

### Trait SemanticProjector
```rust
use async_trait::async_trait;
use leet_core::{Cogon, Dag};
use crate::error::BridgeError;

/// Trait que qualquer backend de projeção semântica implementa.
/// Anthropic Claude, OpenAI, modelo local, Ollama, whatever.
#[async_trait]
pub trait SemanticProjector: Send + Sync {
    /// Projeta texto humano nos 32 eixos canônicos.
    /// Retorna (sem[32], unc[32]).
    async fn project(&self, text: &str) -> Result<(Vec<f32>, Vec<f32>), BridgeError>;

    /// Reconstrói texto humano a partir de um COGON.
    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError>;

    /// Reconstrói texto a partir de um DAG completo.
    /// depth = quantos níveis reconstruir (de folha pra raiz).
    async fn reconstruct_dag(&self, dag: &Dag, depth: usize) -> Result<String, BridgeError>;
}
```

### MockProjector (para testes sem API key)
Implementa SemanticProjector com lógica determinística:
- project("urgente") → C1_URGÊNCIA=0.95, C3_AÇÃO=0.9, resto=0.5, unc=0.1 uniforme
- project("o servidor caiu") → A8_ESTADO=0.9, A9_PROCESSO=0.8, C5_ANOMALIA=0.9, C1_URGÊNCIA=0.85, unc=0.15
- project(qualquer outro) → sem=0.5 uniforme, unc=0.3 uniforme
- reconstruct(cogon) → gera string descritiva baseada nos eixos mais altos
- reconstruct_dag → concatena reconstruções dos nós em ordem topológica

### Prompt Template
Crie uma const/fn que gera o prompt que será enviado ao LLM para projeção nos 32 eixos:

```
pub fn projection_prompt(text: &str) -> String
```

O prompt deve:
1. Listar TODOS os 32 eixos com índice, código, nome e descrição
2. Dar o texto a projetar
3. Pedir resposta SOMENTE em JSON: {"sem": [32 floats 0-1], "unc": [32 floats 0-1]}
4. Explicar que unc é a incerteza da projeção em cada dimensão
5. Ser claro que valores são float entre 0.0 e 1.0

Faça o mesmo para reconstrução:
```
pub fn reconstruction_prompt(cogon: &Cogon) -> String
```
O prompt deve fornecer os 32 valores sem/unc com os nomes dos eixos e pedir texto natural.

## human_to_1337.rs

### HumanBridge struct
```rust
pub struct HumanBridge {
    projector: Box<dyn SemanticProjector>,
}

impl HumanBridge {
    pub fn new(projector: Box<dyn SemanticProjector>) -> Self;

    /// Texto → COGON. Projeta, valida R5 (low confidence).
    pub async fn text_to_cogon(&self, text: &str) -> Result<Cogon, BridgeError>;

    /// Texto complexo → DAG com múltiplos COGONs.
    /// Separa o texto em sentenças/conceitos, projeta cada um,
    /// infere edges entre eles (CAUSA, CONDICIONA, etc).
    pub async fn text_to_dag(&self, text: &str) -> Result<Dag, BridgeError>;

    /// Texto → MSG_1337 completa.
    /// Monta o envelope com todos os campos, valida com Validator.
    pub async fn text_to_msg(
        &self,
        text: &str,
        sender: Uuid,
        receiver: Receiver,
        intent: Intent,
    ) -> Result<Msg1337, BridgeError>;
}
```

Para text_to_dag: simplifique na primeira versão — se o texto tem uma frase, vira COGON único como raiz. Se tem múltiplas sentenças (split por '.'), cada uma vira um COGON, e elas se conectam com CONDICIONA (sequência lógica). A versão real usaria o LLM pra inferir edges — por agora, essa heurística funciona.

Para text_to_msg: preenche c5 com zone_fixed do COGON/DAG, zone_emergent vazio, schema_ver="0.4.0", align_hash genérico. Surface: human_required=false por default, urgency da dimensão C1, reconstruct_depth=3, lang="pt".

## leet_to_human.rs

```rust
/// COGON → texto humano.
pub async fn cogon_to_text(
    cogon: &Cogon,
    projector: &dyn SemanticProjector,
) -> Result<String, BridgeError>;

/// DAG → texto humano.
/// Respeita depth: reconstrói depth níveis de folha pra raiz.
pub async fn dag_to_text(
    dag: &Dag,
    projector: &dyn SemanticProjector,
    depth: usize,
) -> Result<String, BridgeError>;

/// MSG_1337 → texto humano.
/// Usa surface.reconstruct_depth. Inclui header com intent e urgency se relevante.
pub async fn msg_to_text(
    msg: &Msg1337,
    projector: &dyn SemanticProjector,
) -> Result<String, BridgeError>;
```

---

# TESTES

Todos com MockProjector (sem API key necessária):

```rust
#[tokio::test]
async fn test_text_to_cogon_basic()
// "olá" → COGON com 32 dims, unc razoável

#[tokio::test]
async fn test_text_to_cogon_urgent()
// "urgente" → C1_URGÊNCIA alto

#[tokio::test]
async fn test_text_to_dag_single_sentence()
// "o sol brilha" → DAG com 1 nó

#[tokio::test]
async fn test_text_to_dag_multi_sentence()
// "O servidor caiu. Precisamos agir." → DAG com 2 nós + edge

#[tokio::test]
async fn test_roundtrip()
// texto → COGON → texto → verifica que não perdeu urgência

#[tokio::test]
async fn test_msg_envelope()
// text_to_msg → valida que o envelope está completo e válido

#[tokio::test]
async fn test_cogon_to_text()
// MockProjector reconstrói texto baseado nos eixos dominantes
```

# CRITÉRIOS DE ACEITE

1. `cargo test -p leet_bridge` passa todos os testes
2. `cargo build` compila sem warnings
3. Trait SemanticProjector é extensível — qualquer backend pode implementar
4. MockProjector funciona sem API key, sem rede, sem nada externo
5. Prompt templates estão completos e prontos pra enviar a qualquer LLM
6. Validação via leet_core::Validator é chamada automaticamente em text_to_msg
