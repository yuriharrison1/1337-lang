# PROMPT 10a — `leet-mcp` CRATE (MCP server for Claude Code)

Create a new workspace crate `leet-mcp` exposing 1337 functionality via the Model Context Protocol. Claude Code spawns this over stdio and calls tools like `leet_recall`, `leet_remember`, `leet_encode`, `leet_decode`, `leet_dist`. Zero-friction for the user: auto-creates `.leet/store.bin` on first use, no manual init.

**PRE-REQUISITES**: Fase A complete. `cargo test --workspace` green.

**SCOPE**: new `leet-mcp/` directory + add to workspace members. No changes to other crates beyond the root `Cargo.toml` members list.

**Taskwarrior**: `+prompt10a`.

---

## WHY

The user wants zero-touch integration with Claude Code. They run `leet setup claude-code` once, never think about it again. Every project they open in Claude Code automatically gains:

- On session start: Claude Code calls `leet_recall` to retrieve compressed prior context
- During conversation: Claude Code calls `leet_remember` when it detects a topic shift or structural decision
- Store lives in `.leet/store.bin` inside the project root — auto-created, auto-gitignored

The MCP server is the single technical interface. The skill (10d) teaches Claude *when* to call; this prompt creates *what* gets called.

---

## ARCHITECTURE

```
┌──────────────────┐       stdio (JSON-RPC)      ┌──────────────────┐
│   Claude Code    │◄──────────────────────────► │    leet-mcp      │
│                  │                              │   (this crate)   │
└──────────────────┘                              └────────┬─────────┘
                                                            │
                                                  ┌─────────┼─────────┐
                                                  ▼         ▼         ▼
                                              leet-core  leet-bridge PersonalStore
                                              (types,     (project,  (.leet/
                                               codec,      W matrix,  store.bin)
                                               algebra)    NL path)
```

`leet-mcp` is a thin orchestration layer. It:
1. Parses MCP tool calls from Claude Code
2. Routes to the right underlying crate (bridge for text→cogon, core for algebra, store for persistence)
3. Serializes results back as JSON-RPC responses

---

## FILE 1 — root `Cargo.toml` (add member)

```toml
[workspace]
members = [
    "leet-core",
    "leet-bridge",
    "leet-service",
    "leet-cli",
    "leet-mcp",          # NEW
]
resolver = "2"

# [workspace.package] and [workspace.dependencies] already present from 09a
```

---

## FILE 2 — `leet-mcp/Cargo.toml` (new)

```toml
[package]
name = "leet-mcp"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
authors.workspace = true
license.workspace = true
repository.workspace = true
homepage.workspace = true
description = "Model Context Protocol server exposing 1337 tools to Claude Code and other MCP clients"
keywords.workspace = true
categories.workspace = true

[[bin]]
name = "leet-mcp"
path = "src/main.rs"

[dependencies]
leet-core = { path = "../leet-core" }
leet-bridge = { path = "../leet-bridge" }

# Runtime
tokio = { workspace = true }
anyhow = { workspace = true }
thiserror = { workspace = true }

# Serialization
serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }

# Logging (always to stderr — stdout is MCP protocol)
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

# UUIDs for record IDs
uuid = { workspace = true }
```

---

## FILE 3 — `leet-mcp/src/main.rs` (new, entry point)

```rust
//! leet-mcp — Model Context Protocol server for the 1337 language.
//!
//! Transport: stdio (spawned as subprocess by Claude Code).
//! Runtime: single-threaded tokio — MCP is inherently sequential.
//!
//! All logging goes to stderr; stdout is reserved for JSON-RPC.

use anyhow::Result;
use tracing_subscriber::EnvFilter;

mod protocol;
mod server;
mod store;
mod tools;

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<()> {
    // Logging to stderr only. MCP protocol owns stdout.
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("leet_mcp=info")),
        )
        .init();

    tracing::info!("leet-mcp starting (v{})", env!("CARGO_PKG_VERSION"));

    // Determine project root. Default: current working directory.
    // Can be overridden via LEET_PROJECT_ROOT env var — useful when
    // Claude Code spawns leet-mcp from a different cwd than the project.
    let project_root = match std::env::var("LEET_PROJECT_ROOT") {
        Ok(p) => std::path::PathBuf::from(p),
        Err(_) => std::env::current_dir()?,
    };

    tracing::info!("project root: {}", project_root.display());

    // Open or create the store. This is zero-friction — user never runs `leet init`.
    let store = store::PersonalStore::open_or_create(&project_root)?;
    tracing::info!("store loaded: {} cogons", store.len());

    // Run the MCP loop over stdio until EOF or fatal error.
    server::run_stdio(store).await?;

    tracing::info!("leet-mcp exiting");
    Ok(())
}
```

---

## FILE 4 — `leet-mcp/src/protocol.rs` (new, minimal JSON-RPC 2.0 types)

We implement MCP directly against JSON-RPC 2.0 rather than pulling an SDK — MCP for tool-only servers is small, and vendoring an SDK adds dependency risk. If the `rmcp` crate becomes stable/available, migration is mechanical.

```rust
//! Minimal MCP protocol types — JSON-RPC 2.0 shape plus MCP-specific methods.
//! Reference: https://spec.modelcontextprotocol.io/

use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<Value>,      // null for notifications
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: &'static str,
    pub id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

impl JsonRpcResponse {
    pub fn ok(id: Value, result: Value) -> Self {
        Self { jsonrpc: "2.0", id, result: Some(result), error: None }
    }

    pub fn err(id: Value, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0",
            id,
            result: None,
            error: Some(JsonRpcError { code, message: message.into(), data: None }),
        }
    }
}

// MCP initialize response shape.
#[derive(Debug, Serialize)]
pub struct InitializeResult {
    #[serde(rename = "protocolVersion")]
    pub protocol_version: &'static str,
    pub capabilities: ServerCapabilities,
    #[serde(rename = "serverInfo")]
    pub server_info: ServerInfo,
}

#[derive(Debug, Serialize)]
pub struct ServerCapabilities {
    pub tools: ToolsCapability,
}

#[derive(Debug, Serialize)]
pub struct ToolsCapability {
    #[serde(rename = "listChanged")]
    pub list_changed: bool,
}

#[derive(Debug, Serialize)]
pub struct ServerInfo {
    pub name: &'static str,
    pub version: &'static str,
}

// Tool definition shape (MCP tools/list response item).
#[derive(Debug, Serialize, Clone)]
pub struct ToolDef {
    pub name: &'static str,
    pub description: &'static str,
    #[serde(rename = "inputSchema")]
    pub input_schema: Value,
}

// Tool call result — MCP expects content as array of typed items.
#[derive(Debug, Serialize)]
pub struct ToolResult {
    pub content: Vec<ContentItem>,
    #[serde(rename = "isError", skip_serializing_if = "Option::is_none")]
    pub is_error: Option<bool>,
}

#[derive(Debug, Serialize)]
#[serde(tag = "type")]
pub enum ContentItem {
    #[serde(rename = "text")]
    Text { text: String },
}

impl ToolResult {
    pub fn text(msg: impl Into<String>) -> Self {
        Self { content: vec![ContentItem::Text { text: msg.into() }], is_error: None }
    }

    pub fn error(msg: impl Into<String>) -> Self {
        Self { content: vec![ContentItem::Text { text: msg.into() }], is_error: Some(true) }
    }
}
```

---

## FILE 5 — `leet-mcp/src/server.rs` (new, main loop)

```rust
//! Main MCP server loop. Reads newline-delimited JSON-RPC from stdin,
//! dispatches to handlers, writes responses to stdout.

use anyhow::Result;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

use crate::protocol::*;
use crate::store::PersonalStore;
use crate::tools;

pub async fn run_stdio(mut store: PersonalStore) -> Result<()> {
    let stdin = tokio::io::stdin();
    let mut reader = BufReader::new(stdin).lines();
    let mut stdout = tokio::io::stdout();

    while let Some(line) = reader.next_line().await? {
        if line.trim().is_empty() {
            continue;
        }

        let req: JsonRpcRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                tracing::warn!("invalid JSON-RPC: {e}");
                continue;
            }
        };

        // Notifications (id=null) get no response.
        let id = match req.id.clone() {
            Some(v) => v,
            None => {
                // Handle notifications silently (e.g. initialized).
                tracing::debug!("notification: {}", req.method);
                continue;
            }
        };

        let response = match req.method.as_str() {
            "initialize" => handle_initialize(id),
            "tools/list" => handle_tools_list(id),
            "tools/call" => handle_tools_call(id, req.params, &mut store).await,
            "ping" => JsonRpcResponse::ok(id, json!({})),
            other => {
                JsonRpcResponse::err(id, -32601, format!("method not found: {other}"))
            }
        };

        let line = serde_json::to_string(&response)?;
        stdout.write_all(line.as_bytes()).await?;
        stdout.write_all(b"\n").await?;
        stdout.flush().await?;
    }

    Ok(())
}

fn handle_initialize(id: Value) -> JsonRpcResponse {
    let result = InitializeResult {
        protocol_version: "2024-11-05",
        capabilities: ServerCapabilities {
            tools: ToolsCapability { list_changed: false },
        },
        server_info: ServerInfo {
            name: "leet-mcp",
            version: env!("CARGO_PKG_VERSION"),
        },
    };
    JsonRpcResponse::ok(id, serde_json::to_value(result).unwrap())
}

fn handle_tools_list(id: Value) -> JsonRpcResponse {
    let tools = tools::tool_definitions();
    JsonRpcResponse::ok(id, json!({ "tools": tools }))
}

async fn handle_tools_call(
    id: Value,
    params: Value,
    store: &mut PersonalStore,
) -> JsonRpcResponse {
    let tool_name = match params.get("name").and_then(|v| v.as_str()) {
        Some(n) => n.to_string(),
        None => return JsonRpcResponse::err(id, -32602, "missing tool name"),
    };
    let arguments = params.get("arguments").cloned().unwrap_or(Value::Null);

    let result = match tool_name.as_str() {
        "leet_recall"   => tools::leet_recall(arguments, store).await,
        "leet_remember" => tools::leet_remember(arguments, store).await,
        "leet_encode"   => tools::leet_encode(arguments).await,
        "leet_decode"   => tools::leet_decode(arguments).await,
        "leet_dist"     => tools::leet_dist(arguments).await,
        other => Err(anyhow::anyhow!("unknown tool: {other}")),
    };

    match result {
        Ok(tr) => JsonRpcResponse::ok(id, serde_json::to_value(tr).unwrap()),
        Err(e) => {
            let tr = ToolResult::error(format!("tool error: {e}"));
            JsonRpcResponse::ok(id, serde_json::to_value(tr).unwrap())
        }
    }
}
```

---

## FILE 6 — `leet-mcp/src/store.rs` (new, PersonalStore facade)

This file is a THIN facade. The real binary append-only implementation is written in **PROMPT_10b**. This file declares the interface that 10b will satisfy.

```rust
//! PersonalStore — thin handle. Full impl comes in PROMPT_10b.

use std::path::{Path, PathBuf};
use anyhow::{Context, Result};
use leet_core::types::Cogon;

/// Records include a timestamp + short NL excerpt alongside the COGON bytes.
#[derive(Debug, Clone)]
pub struct StoreRecord {
    pub cogon: Cogon,
    pub excerpt: String,       // up to 256 chars of NL summary
    pub unix_ns: i64,
}

pub struct PersonalStore {
    path: PathBuf,
    records: Vec<StoreRecord>,
}

impl PersonalStore {
    /// Open or create `.leet/store.bin` under `project_root`.
    /// Also creates `.leet/.gitignore` on first init (ignores store.bin).
    pub fn open_or_create(project_root: &Path) -> Result<Self> {
        let leet_dir = project_root.join(".leet");
        std::fs::create_dir_all(&leet_dir)
            .with_context(|| format!("creating {}", leet_dir.display()))?;

        // On first creation, write a .gitignore so store.bin isn't committed
        // by default. Users can opt-in to commit it by editing this file.
        let gitignore = leet_dir.join(".gitignore");
        if !gitignore.exists() {
            std::fs::write(&gitignore, "# Auto-created by leet-mcp. Remove this\n# line to commit the store.\nstore.bin\n")?;
        }

        let path = leet_dir.join("store.bin");
        let records = if path.exists() {
            Self::load_all(&path)?
        } else {
            Vec::new()
        };

        Ok(Self { path, records })
    }

    pub fn len(&self) -> usize { self.records.len() }
    pub fn is_empty(&self) -> bool { self.records.is_empty() }
    pub fn records(&self) -> &[StoreRecord] { &self.records }
    pub fn path(&self) -> &Path { &self.path }

    /// Append a new record. Writes to disk immediately (fsync).
    pub fn append(&mut self, record: StoreRecord) -> Result<()> {
        // PROMPT_10b replaces this with the binary append-only impl.
        Self::append_to_file(&self.path, &record)?;
        self.records.push(record);
        Ok(())
    }

    fn load_all(path: &Path) -> Result<Vec<StoreRecord>> {
        // PROMPT_10b fills this in.
        let _ = path;
        Ok(Vec::new())
    }

    fn append_to_file(path: &Path, record: &StoreRecord) -> Result<()> {
        // PROMPT_10b fills this in.
        let _ = (path, record);
        Ok(())
    }
}
```

The two `load_all` / `append_to_file` stubs are deliberate. PROMPT_10b replaces them with the real implementation (little-endian binary format, 96-byte codec frame per record plus 8 bytes unix_ns and 256-byte excerpt field = 360 bytes per record fixed-size).

If Claude Code tries to call `leet_remember` before 10b lands, `append` succeeds in memory but records don't persist. That's acceptable as a transient state during development — the MCP contract still works, just without durability.

---

## FILE 7 — `leet-mcp/src/tools.rs` (new, the five tools)

```rust
//! Tool implementations. Each function matches one `tools/call` dispatch.

use anyhow::{anyhow, Result};
use serde::Deserialize;
use serde_json::{json, Value};

use leet_core::operators::dist;
use leet_core::types::Cogon;
use uuid::Uuid;

use crate::protocol::ToolDef;
use crate::store::{PersonalStore, StoreRecord};

// ─── Tool definitions (tools/list) ───────────────────────────────────────────

pub fn tool_definitions() -> Vec<ToolDef> {
    vec![
        ToolDef {
            name: "leet_recall",
            description: "Retrieve the most semantically relevant prior COGONs from the project's \
                          .leet/store.bin, ranked by distance to the optional query (or by recency \
                          if no query provided). Returns compressed context for continuing work.",
            input_schema: json!({
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language query to rank relevance against. Optional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum records to return (default 5).",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 5
                    }
                }
            }),
        },
        ToolDef {
            name: "leet_remember",
            description: "Compress the provided text into a COGON and append it to the project's \
                          .leet/store.bin. Call this when a topic is concluded, a decision is made, \
                          or the conversation shifts — anything worth recalling in a future session.",
            input_schema: json!({
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Natural-language text to remember. Usually a short summary \
                                        (1-3 sentences) of what was decided or discussed."
                    },
                    "session_excerpt": {
                        "type": "string",
                        "description": "Optional shorter excerpt (up to 256 chars) displayed in recalls. \
                                        Defaults to the first 256 chars of `text`."
                    }
                }
            }),
        },
        ToolDef {
            name: "leet_encode",
            description: "Convert natural-language text into a COGON semantic vector (sem[32]) \
                          without persisting it. Use for ad-hoc comparisons.",
            input_schema: json!({
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": { "type": "string" }
                }
            }),
        },
        ToolDef {
            name: "leet_decode",
            description: "Reverse-project a COGON sem[32] vector back to a natural-language \
                          description of its dominant semantic axes.",
            input_schema: json!({
                "type": "object",
                "required": ["sem"],
                "properties": {
                    "sem": {
                        "type": "array",
                        "items": { "type": "number" },
                        "minItems": 32,
                        "maxItems": 32
                    }
                }
            }),
        },
        ToolDef {
            name: "leet_dist",
            description: "Cosine distance between two sem[32] vectors, weighted by P6 confidence. \
                          Returns [0, 2] where 0 = identical and 2 = opposite.",
            input_schema: json!({
                "type": "object",
                "required": ["a", "b"],
                "properties": {
                    "a": { "type": "array", "items": { "type": "number" },
                           "minItems": 32, "maxItems": 32 },
                    "b": { "type": "array", "items": { "type": "number" },
                           "minItems": 32, "maxItems": 32 }
                }
            }),
        },
    ]
}

// ─── leet_recall ─────────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct RecallArgs {
    #[serde(default)]
    query: Option<String>,
    #[serde(default = "default_limit")]
    limit: usize,
}
fn default_limit() -> usize { 5 }

pub async fn leet_recall(args: Value, store: &PersonalStore) -> Result<crate::protocol::ToolResult> {
    let args: RecallArgs = serde_json::from_value(args).unwrap_or(RecallArgs {
        query: None,
        limit: default_limit(),
    });

    if store.is_empty() {
        return Ok(crate::protocol::ToolResult::text(
            "No prior context in this project. Starting fresh.".to_string(),
        ));
    }

    let ranked = match args.query {
        Some(q) if !q.is_empty() => {
            let query_cogon = encode_text(&q)?;
            let mut scored: Vec<(f32, &StoreRecord)> = store
                .records()
                .iter()
                .map(|r| (dist(&query_cogon, &r.cogon), r))
                .collect();
            scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
            scored
        }
        _ => {
            // No query — return most recent.
            store
                .records()
                .iter()
                .rev()
                .map(|r| (0.0_f32, r))
                .collect()
        }
    };

    let picks: Vec<_> = ranked.into_iter().take(args.limit).collect();

    let mut out = String::from("Recalled context from prior sessions:\n\n");
    for (i, (dist_val, rec)) in picks.iter().enumerate() {
        let ts = chrono_like(rec.unix_ns);
        out.push_str(&format!(
            "[{i}] {ts}  (distance={dist_val:.3})\n    {}\n\n",
            rec.excerpt
        ));
    }
    out.push_str(&format!(
        "({}/{} records shown. Use leet_recall with a narrower query to filter further.)",
        picks.len(),
        store.len()
    ));

    Ok(crate::protocol::ToolResult::text(out))
}

// ─── leet_remember ───────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct RememberArgs {
    text: String,
    #[serde(default)]
    session_excerpt: Option<String>,
}

pub async fn leet_remember(
    args: Value,
    store: &mut PersonalStore,
) -> Result<crate::protocol::ToolResult> {
    let args: RememberArgs = serde_json::from_value(args)
        .map_err(|e| anyhow!("bad args for leet_remember: {e}"))?;

    let cogon = encode_text(&args.text)?;
    let excerpt = args
        .session_excerpt
        .unwrap_or_else(|| truncate(&args.text, 256));

    let record = StoreRecord {
        cogon: cogon.clone(),
        excerpt: excerpt.clone(),
        unix_ns: now_ns(),
    };

    store.append(record)?;

    let msg = format!(
        "Remembered. Store now has {} record(s). Excerpt: \"{}\"",
        store.len(),
        truncate(&excerpt, 80)
    );
    Ok(crate::protocol::ToolResult::text(msg))
}

// ─── leet_encode ─────────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct EncodeArgs {
    text: String,
}

pub async fn leet_encode(args: Value) -> Result<crate::protocol::ToolResult> {
    let args: EncodeArgs = serde_json::from_value(args)?;
    let cogon = encode_text(&args.text)?;
    let payload = json!({
        "sem": cogon.sem.to_vec(),
        "p6_confidence": cogon.sem[29],
    });
    Ok(crate::protocol::ToolResult::text(payload.to_string()))
}

// ─── leet_decode ─────────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct DecodeArgs {
    sem: Vec<f32>,
}

pub async fn leet_decode(args: Value) -> Result<crate::protocol::ToolResult> {
    let args: DecodeArgs = serde_json::from_value(args)?;
    if args.sem.len() != 32 {
        return Err(anyhow!("sem must be exactly 32 values"));
    }
    let mut sem = [0.0_f32; 32];
    sem.copy_from_slice(&args.sem);

    // Find the axes furthest from 0.5 (most informative).
    let mut ranked: Vec<(usize, f32)> =
        sem.iter().enumerate().map(|(i, &v)| (i, (v - 0.5).abs())).collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    let top: Vec<_> = ranked.into_iter().take(5).collect();

    use leet_core::axes::CANONICAL_AXES;
    let mut out = String::from("Top semantic axes (furthest from neutral 0.5):\n");
    for (idx, _) in &top {
        let ax = &CANONICAL_AXES[*idx];
        out.push_str(&format!(
            "  [{}] {} {}: {:.3}  —  {}\n",
            ax.index, ax.code, ax.name, sem[*idx], ax.description
        ));
    }
    Ok(crate::protocol::ToolResult::text(out))
}

// ─── leet_dist ───────────────────────────────────────────────────────────────

#[derive(Deserialize)]
struct DistArgs {
    a: Vec<f32>,
    b: Vec<f32>,
}

pub async fn leet_dist(args: Value) -> Result<crate::protocol::ToolResult> {
    let args: DistArgs = serde_json::from_value(args)?;
    if args.a.len() != 32 || args.b.len() != 32 {
        return Err(anyhow!("a and b must each be exactly 32 values"));
    }

    let mut a_sem = [0.0_f32; 32];
    let mut b_sem = [0.0_f32; 32];
    a_sem.copy_from_slice(&args.a);
    b_sem.copy_from_slice(&args.b);

    let a = Cogon { id: Uuid::nil(), sem: a_sem, stamp: 0, raw: None };
    let b = Cogon { id: Uuid::nil(), sem: b_sem, stamp: 0, raw: None };
    let d = dist(&a, &b);

    Ok(crate::protocol::ToolResult::text(format!("{{\"distance\": {:.6}}}", d)))
}

// ─── helpers ─────────────────────────────────────────────────────────────────

fn encode_text(text: &str) -> Result<Cogon> {
    // Production: use leet_bridge::projector::project_text with the calibrated W.
    // For now we go through a fallback deterministic path that always works:
    // hash the text to produce a pseudo-embedding, then apply W if available,
    // else sensible defaults. This gives us something testable end-to-end until
    // the user runs calibration.

    // If leet_bridge exposes a project_text function that takes &str and returns
    // a Cogon, use it directly:
    match leet_bridge::projector::project_text_simple(text) {
        Ok(c) => Ok(c),
        Err(_) => {
            // Fallback: all-neutral COGON with P6=0.3 (low confidence).
            let mut sem = leet_core::axes::boot_vector();
            sem[29] = 0.3; // low P6 to signal "uncalibrated result"
            Ok(Cogon {
                id: Uuid::new_v4(),
                sem,
                stamp: now_ns(),
                raw: None,
            })
        }
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max { s.to_string() }
    else {
        let mut out: String = s.chars().take(max - 1).collect();
        out.push('…');
        out
    }
}

fn now_ns() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos() as i64)
        .unwrap_or(0)
}

fn chrono_like(unix_ns: i64) -> String {
    // No external dep — format a simple ISO-like string from unix nanoseconds.
    let secs = unix_ns / 1_000_000_000;
    let epoch_days = secs / 86400;
    let (year, month, day) = civil_from_days(epoch_days);
    let rem = secs % 86400;
    let hour = rem / 3600;
    let minute = (rem % 3600) / 60;
    format!("{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}")
}

/// Howard Hinnant's civil_from_days algorithm (public domain).
fn civil_from_days(z: i64) -> (i32, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z / 146097 } else { (z - 146096) / 146097 };
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i32 + era as i32 * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}
```

Note the `encode_text` function calls `leet_bridge::projector::project_text_simple`. If that function doesn't exist yet in `leet-bridge`, add a thin wrapper in `leet-bridge/src/projector.rs`:

```rust
/// Convenience: accept text, run through the default embedding + W pipeline,
/// return a Cogon. Used by leet-mcp when no embedding provider is configured.
/// Returns an error if W is unavailable and keyword-fallback is off.
pub fn project_text_simple(text: &str) -> Result<Cogon, BridgeError> {
    // Uses an internal default provider (hash-based pseudo-embedding for now,
    // real sentence-transformers via Python sidecar later).
    // Must work without external HTTP calls — MCP server can't block on network.
    let provider = crate::projector::default_local_provider();
    project_text(text, provider.as_ref())
}
```

If `default_local_provider` doesn't exist either, create a minimal deterministic hash-based pseudo-embedding provider that's good enough for DIST comparisons (not for publishing quality, but usable):

```rust
fn default_local_provider() -> Box<dyn EmbeddingProvider> {
    Box::new(HashBasedProvider::new())
}

struct HashBasedProvider;
impl HashBasedProvider {
    fn new() -> Self { Self }
}

impl EmbeddingProvider for HashBasedProvider {
    fn embed(&self, text: &str) -> Result<Vec<f32>, BridgeError> {
        use std::hash::{Hash, Hasher};
        let dim = 384;
        let mut out = vec![0.0_f32; dim];
        // Break text into character trigrams, hash each into `dim` buckets.
        let chars: Vec<char> = text.to_lowercase().chars().collect();
        for window in chars.windows(3) {
            let mut hasher = std::collections::hash_map::DefaultHasher::new();
            for c in window { c.hash(&mut hasher); }
            let h = hasher.finish() as usize;
            out[h % dim] += 1.0;
        }
        // Normalize.
        let norm: f32 = out.iter().map(|x| x * x).sum::<f32>().sqrt().max(1e-9);
        for v in out.iter_mut() { *v /= norm; }
        Ok(out)
    }

    fn dim(&self) -> usize { 384 }
}
```

This deterministic provider is enough for the MCP to be functional end-to-end today. Quality improves dramatically once the user runs calibration (PROMPT_06 flow, future work).

---

## FILE 8 — `leet-mcp/tests/smoke.rs` (new)

```rust
//! Smoke test — spawns leet-mcp as a subprocess, pipes JSON-RPC, verifies.

use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn initialize_and_list_tools() {
    // Skip if the binary hasn't been built yet (cargo test runs before cargo build for deps)
    let bin = env!("CARGO_BIN_EXE_leet-mcp");

    let tmp = tempfile::tempdir().expect("tempdir");
    let mut child = Command::new(bin)
        .current_dir(tmp.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn leet-mcp");

    let stdin = child.stdin.as_mut().unwrap();
    writeln!(
        stdin,
        r#"{{"jsonrpc":"2.0","id":1,"method":"initialize","params":{{}}}}"#
    )
    .unwrap();
    writeln!(
        stdin,
        r#"{{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{{}}}}"#
    )
    .unwrap();
    stdin.flush().unwrap();
    drop(child.stdin.take());

    let output = child.wait_with_output().expect("wait");
    let stdout = String::from_utf8_lossy(&output.stdout);

    assert!(stdout.contains("leet-mcp"));
    assert!(stdout.contains("leet_recall"));
    assert!(stdout.contains("leet_remember"));
}
```

Add `tempfile = "3"` under `[dev-dependencies]` in `leet-mcp/Cargo.toml`.

---

## VERIFICATION

```bash
# Gate
cargo build -p leet-mcp
cargo test -p leet-mcp
cargo test --workspace

# Smoke: manual JSON-RPC probe
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | cargo run -p leet-mcp

# Expected: single line of JSON with serverInfo.name="leet-mcp"
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt10a "Create leet-mcp crate with 5 MCP tools (recall/remember/encode/decode/dist)"
# work
task project:1337 +prompt10a done

git add Cargo.toml leet-mcp/ leet-bridge/src/projector.rs
git commit -m "feat(mcp): new leet-mcp crate exposing 1337 tools to Claude Code

Adds a Model Context Protocol server spoken over stdio. Claude Code
(or any MCP-compatible client) can call five tools:

- leet_recall   — retrieve relevant prior COGONs from .leet/store.bin
- leet_remember — append new COGON to the project store
- leet_encode   — text → sem[32]
- leet_decode   — sem[32] → top semantic axes narrative
- leet_dist     — cosine distance weighted by P6_CONFIDENCE

Transport is stdio JSON-RPC 2.0 (MCP standard). All logging goes to
stderr; stdout is reserved for the protocol.

Zero-friction UX: the server auto-creates .leet/ and .leet/.gitignore
on first use. No 'leet init' needed.

Also adds:
- leet_bridge::projector::project_text_simple (convenience wrapper)
- leet_bridge::projector::default_local_provider (hash-based trigram
  embedding for keyless operation)

Part of Claude Code integration, sub-prompt 10a."
git push origin main
```

---

**END OF PROMPT_10a**
