//! Main MCP server loop. Reads newline-delimited JSON-RPC from stdin,
//! dispatches to handlers, writes responses to stdout.

use anyhow::Result;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

use crate::protocol::*;
use leet_mcp::store::PersonalStore;
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

        let id = match req.id.clone() {
            Some(v) => v,
            None => {
                tracing::debug!("notification: {}", req.method);
                continue;
            }
        };

        let response = match req.method.as_str() {
            "initialize" => handle_initialize(id),
            "tools/list" => handle_tools_list(id),
            "tools/call" => handle_tools_call(id, req.params, &mut store).await,
            "ping" => JsonRpcResponse::ok(id, json!({})),
            other => JsonRpcResponse::err(id, -32601, format!("method not found: {other}")),
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
        "leet_recall"       => tools::leet_recall(arguments, store).await,
        "leet_recall_delta" => tools::leet_recall_delta(arguments, store).await,
        "leet_remember"     => tools::leet_remember(arguments, store).await,
        "leet_encode"       => tools::leet_encode(arguments).await,
        "leet_decode"       => tools::leet_decode(arguments).await,
        "leet_dist"         => tools::leet_dist(arguments).await,
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
