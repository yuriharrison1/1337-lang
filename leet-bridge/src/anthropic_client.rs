//! Anthropic API client for the 1337 multi-agent chat.
//!
//! Sends COGONs to Claude and parses back a JSON array of AgentResponse objects.
//! The model is configured via `LEET_API_KEY` and optionally `LEET_MODEL`.

use leet_core::{Cogon, Intent};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// ── Public types ──────────────────────────────────────────────────────────────

/// One message in the conversation history, mirroring the Anthropic API format.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
}

/// Response from a single agent, extracted from Claude's JSON output.
#[derive(Debug, Clone)]
pub struct AgentResponse {
    pub agent: String,
    pub cogon: Cogon,
    pub intent: Intent,
    pub nl_pt: String,
    pub nl_en: String,
}

/// Errors that can occur when calling the Anthropic API.
#[derive(Debug)]
pub enum AnthropicError {
    /// `LEET_API_KEY` is not set.
    /// `LEET_API_KEY` is not set.
    MissingApiKey,
    /// HTTP transport failure.
    RequestFailed(String),
    /// Response JSON could not be parsed into AgentResponse objects.
    ParseFailed(String),
    /// API returned a non-200 status code.
    ApiError { status: u16, body: String },
}

impl std::fmt::Display for AnthropicError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingApiKey => write!(f, "LEET_API_KEY not set"),
            Self::RequestFailed(e) => write!(f, "request failed: {}", e),
            Self::ParseFailed(e) => write!(f, "parse failed: {}", e),
            Self::ApiError { status, body } => write!(f, "API error {}: {}", status, &body[..body.len().min(200)]),
        }
    }
}

// ── AnthropicClient ───────────────────────────────────────────────────────────

/// HTTP client wrapping the Anthropic Messages API.
pub struct AnthropicClient {
    api_key: String,
    model: String,
    client: reqwest::Client,
}

impl AnthropicClient {
    /// Create a new client.
    ///
    /// Reads `LEET_API_KEY` from the environment (required).
    /// Reads `LEET_MODEL` for the model override (default: `claude-sonnet-4-6`).
    pub fn new() -> Result<Self, AnthropicError> {
        let api_key = std::env::var("LEET_API_KEY")
            .map_err(|_| AnthropicError::MissingApiKey)?;
        let model = std::env::var("LEET_MODEL")
            .unwrap_or_else(|_| "claude-haiku-4-5-20251001".to_string());
        let client = reqwest::Client::new();
        Ok(Self { api_key, model, client })
    }

    /// Send a COGON to Claude and receive responses from `max_agents` agents.
    ///
    /// `history` contains the last N conversation turns (user + assistant).
    /// `max_agents` controls how many agents respond (clamped to 1–6, default 3).
    pub async fn send_cogon(
        &self,
        cogon: &Cogon,
        history: &[Message],
        max_agents: usize,
    ) -> Result<Vec<AgentResponse>, AnthropicError> {
        use crate::claude_1337_prompt::CLAUDE_1337_SYSTEM;

        let n = max_agents.clamp(1, 6);

        let cogon_json = serde_json::to_string(cogon)
            .map_err(|e| AnthropicError::ParseFailed(e.to_string()))?;

        // Build message list: history entries + current user turn
        let mut messages: Vec<serde_json::Value> = history
            .iter()
            .map(|m| serde_json::json!({ "role": m.role, "content": m.content }))
            .collect();

        messages.push(serde_json::json!({
            "role": "user",
            "content": format!(
                "INPUT_COGON:\n{}\nSELECT_AGENTS: respond as exactly {} agent(s) only.",
                cogon_json, n
            )
        }));

        // max_tokens scales with number of agents to avoid truncation
        let max_tokens = 512 + n * 512;

        let request_body = serde_json::json!({
            "model": self.model,
            "max_tokens": max_tokens,
            "system": CLAUDE_1337_SYSTEM,
            "messages": messages
        });

        let response = self
            .client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("content-type", "application/json")
            .json(&request_body)
            .send()
            .await
            .map_err(|e| AnthropicError::RequestFailed(e.to_string()))?;

        let status = response.status().as_u16();
        if status != 200 {
            let body = response.text().await.unwrap_or_default();
            return Err(AnthropicError::ApiError { status, body });
        }

        let resp_json: serde_json::Value = response
            .json()
            .await
            .map_err(|e| AnthropicError::ParseFailed(e.to_string()))?;

        let text = resp_json["content"][0]["text"]
            .as_str()
            .ok_or_else(|| AnthropicError::ParseFailed("no text field in response".to_string()))?;

        parse_agent_responses(text)
            .map_err(AnthropicError::ParseFailed)
    }
}

// ── Response parsing ──────────────────────────────────────────────────────────

/// Parse Claude's text response into a list of AgentResponse objects.
///
/// Locates the first JSON array in the text (Claude may prepend commentary
/// even when instructed not to) and deserializes it.
fn parse_agent_responses(text: &str) -> Result<Vec<AgentResponse>, String> {
    // Find JSON array boundaries — handle potential leading/trailing text
    let start = text.find('[').ok_or_else(|| "no JSON array '[' found in response".to_string())?;
    let end = text.rfind(']').ok_or_else(|| "no JSON array ']' found in response".to_string())? + 1;
    let json_str = &text[start..end];

    let raw: Vec<serde_json::Value> =
        serde_json::from_str(json_str).map_err(|e| format!("JSON parse error: {}", e))?;

    if raw.is_empty() {
        return Err("empty agent response array".to_string());
    }

    let mut responses = Vec::with_capacity(raw.len());

    for item in &raw {
        let agent = item["agent"]
            .as_str()
            .unwrap_or("UNKNOWN")
            .to_uppercase();

        let sem = parse_f32_array(&item["sem"], &agent, "sem")?;
        // unc field ignored in v0.5.1 — parsed for wire compat but not used
        let _unc = parse_f32_array(&item["unc"], &agent, "unc").unwrap_or_default();

        let intent = match item["intent"].as_str().unwrap_or("ASSERT").to_uppercase().as_str() {
            "QUERY"   => Intent::Query,
            "DELTA"   => Intent::Delta,
            "SYNC"    => Intent::Sync,
            "ANOMALY" => Intent::Anomaly,
            "ACK"     => Intent::Ack,
            _         => Intent::Assert,
        };

        let nl_pt = item["nl_pt"].as_str().unwrap_or("").to_string();
        let nl_en = item["nl_en"].as_str().unwrap_or("").to_string();

        let cogon = Cogon {
            id: Uuid::new_v4(),
            sem,
            stamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as i64)
                .unwrap_or(0),
            raw: None,
        };

        responses.push(AgentResponse { agent, cogon, intent, nl_pt, nl_en });
    }

    Ok(responses)
}

/// Parse a serde_json Value as a [f32; 32] array.
fn parse_f32_array(
    value: &serde_json::Value,
    agent: &str,
    field: &str,
) -> Result<[f32; 32], String> {
    let arr = value
        .as_array()
        .ok_or_else(|| format!("agent {}: '{}' is not an array", agent, field))?;

    if arr.len() != 32 {
        return Err(format!(
            "agent {}: '{}' has {} elements, expected 32",
            agent,
            field,
            arr.len()
        ));
    }

    let mut out = [0.5_f32; 32];
    for (i, v) in arr.iter().enumerate() {
        let f = v.as_f64().ok_or_else(|| {
            format!("agent {}: '{}[{}]' is not a number (got {:?})", agent, field, i, v)
        })?;
        out[i] = (f as f32).clamp(0.0, 1.0);
    }
    Ok(out)
}
