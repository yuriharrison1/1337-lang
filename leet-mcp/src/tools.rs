//! Tool implementations for MCP tools/call dispatch.

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

pub async fn leet_recall(args: Value, store: &mut PersonalStore) -> Result<crate::protocol::ToolResult> {
    let args: RecallArgs = serde_json::from_value(args).unwrap_or(RecallArgs {
        query: None,
        limit: default_limit(),
    });

    if store.is_empty() {
        store.index.touch_recall(now_ns());
        let _ = store.index.flush();
        return Ok(crate::protocol::ToolResult::text(
            "No prior context in this project. Starting fresh.",
        ));
    }

    // Pre-collect live indices (not consolidated) to avoid borrow conflicts below.
    let live_indices: Vec<usize> = (0..store.records().len())
        .filter(|&i| !store.index.entries[i].is_consolidated())
        .collect();

    let ranked: Vec<(f32, usize)> = match args.query {
        Some(q) if !q.is_empty() => {
            let query_cogon = encode_text(&q)?;
            let mut scored: Vec<(f32, usize)> = live_indices
                .iter()
                .map(|&i| (dist(&query_cogon, &store.records()[i].cogon), i))
                .collect();
            scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
            scored
        }
        _ => live_indices.iter().rev().map(|&i| (0.0_f32, i)).collect(),
    };

    let picks: Vec<_> = ranked.into_iter().take(args.limit).collect();

    let mut out = String::from("Recalled context from prior sessions:\n\n");
    for (j, (dist_val, idx)) in picks.iter().enumerate() {
        let rec = &store.records()[*idx];
        let ts = chrono_like(rec.unix_ns);
        out.push_str(&format!(
            "[{j}] {ts}  (distance={dist_val:.3})\n    {}\n\n",
            rec.excerpt
        ));
    }
    out.push_str(&format!(
        "({}/{} live records shown. Use leet_recall with a narrower query to filter further.)",
        picks.len(),
        live_indices.len()
    ));

    store.index.touch_recall(now_ns());
    let _ = store.index.flush();

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
        cogon,
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

    Ok(crate::protocol::ToolResult::text(format!("{{\"distance\": {d:.6}}}")))
}

// ─── helpers ─────────────────────────────────────────────────────────────────

fn encode_text(text: &str) -> Result<Cogon> {
    match leet_bridge::projector::project_text_simple(text) {
        Ok(c) => Ok(c),
        Err(_) => {
            let mut sem = leet_core::axes::boot_vector();
            sem[29] = 0.3; // low P6_CONFIDENCE — uncalibrated result
            Ok(Cogon {
                id: Uuid::new_v4(),
                sem,
                stamp: now_ms(),
                raw: None,
            })
        }
    }
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
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

fn now_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

fn chrono_like(unix_ns: i64) -> String {
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
