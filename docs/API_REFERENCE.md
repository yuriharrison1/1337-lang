# Referência de API — 1337

## leet-core

### Tipos principais

#### `Cogon`

```rust
pub struct Cogon {
    pub id:    Uuid,
    pub sem:   [f32; 32],
    pub unc:   [f32; 32],
    pub stamp: i64,
    pub raw:   Option<RawField>,
}

impl Cogon {
    pub fn zero() -> Self         // COGON_ZERO: sem=[1.0;32], unc=[0.0;32]
    pub fn is_zero(&self) -> bool
}
```

#### `Dag`

```rust
pub struct Dag {
    pub root:  Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
}
```

#### `Edge`

```rust
pub struct Edge {
    pub from:      Uuid,
    pub to:        Uuid,
    pub edge_type: EdgeType,
    pub weight:    f32,   // [0.0, 1.0]
}

pub enum EdgeType {
    CAUSA,        // A causa B
    CONDICIONA,   // A condiciona B
    CONTRADIZ,    // A contradiz B
    REFINA,       // A refina B
    EMERGE,       // B emerge de A
}
```

#### `Msg1337`

```rust
pub struct Msg1337 {
    pub id:       Uuid,
    pub sender:   Uuid,
    pub receiver: Receiver,
    pub intent:   Intent,
    pub ref_hash: Option<[u8; 32]>,
    pub patch:    Option<Cogon>,
    pub payload:  Cogon,
    pub c5:       Option<CanonicalSpace>,
    pub surface:  Option<String>,
}

impl Msg1337 {
    pub fn new_sync(agent_id: Uuid, name: &str, role: &str) -> Self
    pub fn new_ack(agent_id: Uuid, hash: [u8; 32]) -> Self
    pub fn new_cogon_zero(agent_id: Uuid) -> Self
    pub fn new_nl_message(sender: Uuid, cogon: Cogon, nl: &str) -> Self
}
```

#### `Intent`

```rust
pub enum Intent {
    ASSERT,   // afirmação informativa
    QUERY,    // pedido de informação
    DELTA,    // mudança de estado
    SYNC,     // sincronização
    ANOMALY,  // reporte de erro
    ACK,      // confirmação
}
```

#### `Receiver`

```rust
pub enum Receiver {
    All,
    Agent(Uuid),
    Surface(String),
}
```

---

### Operadores semânticos

```rust
// Interpola dois COGONs: alpha * a + (1-alpha) * b
pub fn blend(a: &Cogon, b: &Cogon, alpha: f32) -> Cogon

// Diferença semântica: b.sem[i] - a.sem[i]
pub fn delta(a: &Cogon, b: &Cogon) -> Cogon

// Distância cosseno entre dois COGONs: resultado em [0.0, 2.0]
pub fn dist(a: &Cogon, b: &Cogon) -> f32

// Amplifica os N eixos mais ativos, suprime os demais
pub fn focus(cogon: &Cogon, top_n: usize) -> Cogon

// Score de anomalia: média dos eixos de desvio (P3, G8, etc.)
pub fn anomaly_score(cogon: &Cogon) -> f32
```

**Exemplo:**

```rust
use leet_core::{blend, delta, dist, focus, anomaly_score};

let a = nl_to_cogon("sistema estável", "pt");
let b = nl_to_cogon("sistema crítico", "pt");

let distancia = dist(&a, &b);          // ex: 0.78
let mistura   = blend(&a, &b, 0.5);    // ponto médio semântico
let mudanca   = delta(&a, &b);         // o que mudou de a para b
let score     = anomaly_score(&b);     // ex: 0.82 (alta anomalia)
let focado    = focus(&b, 6);          // amplifica top-6 eixos
```

---

### Codec binário

```rust
// Serializa um Cogon em 96 bytes fixos
pub fn encode_cogon(cogon: &Cogon) -> [u8; 96]

// Desserializa — erro se CRC32 inválido ou magic incorreto
pub fn decode_cogon(bytes: &[u8]) -> Result<Cogon, LeetError>

// Tamanho fixo (sempre 96)
pub fn binary_size() -> usize

// Retorna (tamanho_binário, tamanho_json) para comparação
pub fn compare_sizes(cogon: &Cogon) -> (usize, usize)
```

---

### Validação

```rust
// Valida Msg1337 contra as regras R1–R21
// Retorna Ok(()) ou Err(LeetError::ValidationFailed { rule, message })
pub fn validate(msg: &Msg1337) -> Result<(), LeetError>

// Verifica se unc[i] <= max_unc para todo i
pub fn check_confidence(cogon: &Cogon, max_unc: f32) -> bool
```

---

### Protocolo C5

```rust
// Retorna COGON âncora: 0=presence, 1=absence, 2=change, 3=agency, 4=uncertainty
pub fn anchor_cogon(index: usize) -> Cogon

// Retorna todos os 5 COGONs âncora
pub fn all_anchors() -> [Cogon; 5]

// SHA256("1337:v0.5.1:" + agent_name) como [u8; 32]
pub fn compute_align_hash(agent_name: &str) -> [u8; 32]

pub const ANCHOR_NAMES: [&str; 5] = [
    "presence", "absence", "change", "agency", "uncertainty"
];
```

---

## leet-bridge

### Tradução NL ↔ COGON

```rust
// Projeta texto (PT ou EN) para COGON via ~80 regras heurísticas de keywords
pub fn nl_to_cogon(text: &str, lang: &str) -> Cogon

// Reconstrói texto natural a partir dos eixos mais ativados
pub fn cogon_to_nl(cogon: &Cogon, lang: &str) -> String

// Infere intenção: QUERY | ANOMALY | DELTA | SYNC | ASSERT
pub fn infer_intent(text: &str) -> Intent
```

**Exemplo:**

```rust
use leet_bridge::{nl_to_cogon, cogon_to_nl, infer_intent};

let cogon  = nl_to_cogon("Sistema crítico! Falha detectada.", "pt");
let intent = infer_intent("Sistema crítico! Falha detectada.");
// intent == Intent::ANOMALY

let texto = cogon_to_nl(&cogon, "pt");
// "urgente, anomalia, ação necessária"
```

### AnthropicClient

```rust
pub struct AnthropicClient { /* privado */ }

impl AnthropicClient {
    // Lê LEET_API_KEY (obrigatório) e LEET_MODEL do ambiente
    // Modelo padrão: claude-haiku-4-5-20251001
    pub fn new() -> Result<Self, AnthropicError>

    // Envia COGON para Claude e recebe respostas de max_agents agentes (1–6)
    pub async fn send_cogon(
        &self,
        cogon: &Cogon,
        history: &[Message],
        max_agents: usize,
    ) -> Result<Vec<AgentResponse>, AnthropicError>
}

pub struct AgentResponse {
    pub agent:  String,   // "ATLAS", "RAVEN", etc.
    pub cogon:  Cogon,
    pub intent: Intent,
    pub nl_pt:  String,
    pub nl_en:  String,
}

pub enum AnthropicError {
    MissingApiKey,
    RequestFailed(String),
    ParseFailed(String),
    ApiError { status: u16, body: String },
}
```

---

## leet-service

### AgentClient

```rust
pub struct AgentClient { /* parcialmente privado */ }

impl AgentClient {
    pub fn new(id: Uuid, name: &str, role: &str) -> Self

    // Conecta e executa handshake C5 completo
    // addr: "127.0.0.1:1337" ou "/run/leet/leet.sock"
    pub async fn connect(&mut self, addr: &str) -> Result<(), AgentError>

    pub async fn send_nl(&mut self, text: &str) -> Result<(), AgentError>
    pub async fn send_cogon(&mut self, cogon: Cogon) -> Result<(), AgentError>
    pub async fn send_msg(&mut self, msg: &Msg1337) -> Result<(), AgentError>

    pub async fn recv(&mut self) -> Result<Option<Msg1337>, AgentError>
    pub async fn recv_timeout(&mut self, d: Duration) -> Result<Option<Msg1337>, AgentError>
}

pub enum AgentError {
    Io(std::io::Error),
    Json(serde_json::Error),
    Protocol(String),
}
```

### LeetServer

```rust
impl LeetServer {
    pub fn new() -> Arc<Self>
    pub async fn start_background(tcp_addr: &str) -> Result<SocketAddr>
    pub async fn route(sender_id: Uuid, msg: Msg1337)
    pub async fn broadcast(exclude_id: Uuid, msg: Msg1337)
    pub async fn agent_count() -> usize
    pub async fn agent_names() -> Vec<String>
}
```

---

## Variáveis de ambiente

### Rust (leet-cli, leet-bridge, leet-service)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_API_KEY` | — | Chave Anthropic para `leet chat` e `leet-agent --llm anthropic` |
| `LEET_MODEL` | `claude-haiku-4-5-20251001` | Modelo Claude usado pelo chat e agentes |
| `LEET_PORT` | `50051` | Porta do servidor gRPC (legado) |
| `LEET_STORE` | `memory` | Backend: `memory` ou `sqlite` |
| `LEET_SQLITE_PATH` | `.leet_store.db` | Caminho do banco SQLite |
| `LEET_LOG` | `info` | Nível de log |
| `RUST_LOG` | — | Override do tracing filter (ex: `leet_service=debug`) |

### Python (python/leet)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LEET_SERVER_HOST` | `localhost` | Host do servidor gRPC |
| `LEET_SERVER_PORT` | `50051` | Porta do servidor gRPC |
| `LEET_RETRY_ENABLED` | `true` | Habilita retry automático |
| `LEET_PROJECTION_BACKEND` | `anthropic` | Backend de projeção |
| `LEET_PROJECTION_ANTHROPIC_API_KEY` | — | Chave Anthropic para projeção Python |
| `LEET_CACHE_BACKEND` | `memory` | Cache: `memory`, `sqlite`, `redis`, `mongo` |
