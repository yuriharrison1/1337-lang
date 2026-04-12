# API Reference — 1337

## leet-core

### Core Types

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
    CAUSA,        // A causes B
    CONDICIONA,   // A conditions B
    CONTRADIZ,    // A contradicts B
    REFINA,       // A refines B
    EMERGE,       // B emerges from A
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
    ASSERT,   // informational statement
    QUERY,    // request for information
    DELTA,    // state change
    SYNC,     // synchronization
    ANOMALY,  // error report
    ACK,      // acknowledgement
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

### Semantic Operators

```rust
// Interpolate two COGONs: alpha * a + (1-alpha) * b
pub fn blend(a: &Cogon, b: &Cogon, alpha: f32) -> Cogon

// Semantic difference: b.sem[i] - a.sem[i]
pub fn delta(a: &Cogon, b: &Cogon) -> Cogon

// Cosine distance between two COGONs: result in [0.0, 2.0]
pub fn dist(a: &Cogon, b: &Cogon) -> f32

// Amplify the N most active axes, suppress the rest
pub fn focus(cogon: &Cogon, top_n: usize) -> Cogon

// Anomaly score: average of deviation axes (P3, G8, etc.)
pub fn anomaly_score(cogon: &Cogon) -> f32
```

**Example:**

```rust
use leet_core::{blend, delta, dist, focus, anomaly_score};

let a = nl_to_cogon("stable system", "en");
let b = nl_to_cogon("critical system", "en");

let distance = dist(&a, &b);          // e.g. 0.78
let midpoint  = blend(&a, &b, 0.5);   // semantic midpoint
let change    = delta(&a, &b);         // what changed from a to b
let score     = anomaly_score(&b);     // e.g. 0.82 (high anomaly)
let focused   = focus(&b, 6);          // amplify top-6 axes
```

---

### Binary Codec

```rust
// Serialize a Cogon into exactly 96 bytes
pub fn encode_cogon(cogon: &Cogon) -> [u8; 96]

// Deserialize — error if CRC32 invalid or magic incorrect
pub fn decode_cogon(bytes: &[u8]) -> Result<Cogon, LeetError>

// Fixed size (always 96)
pub fn binary_size() -> usize

// Returns (binary_size, json_size) for comparison
pub fn compare_sizes(cogon: &Cogon) -> (usize, usize)
```

---

### Validation

```rust
// Validate Msg1337 against rules R1–R21
// Returns Ok(()) or Err(LeetError::ValidationFailed { rule, message })
pub fn validate(msg: &Msg1337) -> Result<(), LeetError>

// Check if unc[i] <= max_unc for all i
pub fn check_confidence(cogon: &Cogon, max_unc: f32) -> bool
```

---

### C5 Protocol

```rust
// Return anchor COGON: 0=presence, 1=absence, 2=change, 3=agency, 4=uncertainty
pub fn anchor_cogon(index: usize) -> Cogon

// Return all 5 anchor COGONs
pub fn all_anchors() -> [Cogon; 5]

// SHA256("1337:v0.5.1:" + agent_name) as [u8; 32]
pub fn compute_align_hash(agent_name: &str) -> [u8; 32]

pub const ANCHOR_NAMES: [&str; 5] = [
    "presence", "absence", "change", "agency", "uncertainty"
];
```

---

## leet-bridge

### NL ↔ COGON Translation

```rust
// Project text (PT or EN) into a COGON via ~80 keyword heuristic rules
pub fn nl_to_cogon(text: &str, lang: &str) -> Cogon

// Reconstruct natural text from the most activated axes
pub fn cogon_to_nl(cogon: &Cogon, lang: &str) -> String

// Infer intent: QUERY | ANOMALY | DELTA | SYNC | ASSERT
pub fn infer_intent(text: &str) -> Intent
```

**Example:**

```rust
use leet_bridge::{nl_to_cogon, cogon_to_nl, infer_intent};

let cogon  = nl_to_cogon("Critical system! Failure detected.", "en");
let intent = infer_intent("Critical system! Failure detected.");
// intent == Intent::ANOMALY

let text = cogon_to_nl(&cogon, "en");
// "urgent, anomaly, action required"
```

### AnthropicClient

```rust
pub struct AnthropicClient { /* private */ }

impl AnthropicClient {
    // Reads LEET_API_KEY (required) and LEET_MODEL from environment
    // Default model: claude-haiku-4-5-20251001
    pub fn new() -> Result<Self, AnthropicError>

    // Send COGON to Claude and receive responses from max_agents agents (1–6)
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
    pub nl_pt:  String,   // response in Portuguese
    pub nl_en:  String,   // response in English
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
pub struct AgentClient { /* partially private */ }

impl AgentClient {
    pub fn new(id: Uuid, name: &str, role: &str) -> Self

    // Connect and execute the full C5 handshake
    // addr: "127.0.0.1:1337" or "/run/leet/leet.sock"
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

## Environment Variables

### Rust (leet-cli, leet-bridge, leet-service)

| Variable | Default | Description |
|----------|---------|-------------|
| `LEET_API_KEY` | — | Anthropic key for `leet chat` and `leet-agent --llm anthropic` |
| `LEET_MODEL` | `claude-haiku-4-5-20251001` | Claude model used by chat and agents |
| `LEET_PORT` | `50051` | gRPC server port (legacy) |
| `LEET_STORE` | `memory` | Storage backend: `memory` or `sqlite` |
| `LEET_SQLITE_PATH` | `.leet_store.db` | SQLite database path |
| `LEET_LOG` | `info` | Log level |
| `RUST_LOG` | — | Tracing filter override (e.g. `leet_service=debug`) |

### Python (python/leet)

| Variable | Default | Description |
|----------|---------|-------------|
| `LEET_SERVER_HOST` | `localhost` | gRPC server host |
| `LEET_SERVER_PORT` | `50051` | gRPC server port |
| `LEET_RETRY_ENABLED` | `true` | Enable automatic retry |
| `LEET_PROJECTION_BACKEND` | `anthropic` | Projection backend |
| `LEET_PROJECTION_ANTHROPIC_API_KEY` | — | Anthropic key for Python projection |
| `LEET_CACHE_BACKEND` | `memory` | Cache: `memory`, `sqlite`, `redis`, `mongo` |
