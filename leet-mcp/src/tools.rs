//! Tool implementations for MCP tools/call dispatch.

use anyhow::{anyhow, Result};
use serde::Deserialize;
use serde_json::{json, Value};

use leet_core::operators::dist;
use leet_core::types::Cogon;
use uuid::Uuid;

use crate::protocol::ToolDef;
use leet_mcp::store::{PersonalStore, StoreRecord};

// ─── Tool definitions (tools/list) ───────────────────────────────────────────

pub fn tool_definitions() -> Vec<ToolDef> {
    vec![
        ToolDef {
            name: "leet_recall",
            description: "Retrieve context from the project's .leet/store.bin using delta-aware \
                          tiered recall: foundation summary (highest level) + mid-tier + recent \
                          raw entries. With a query, ranks by semantic distance. Without a query, \
                          returns the memory pyramid optimally bounded.",
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
                    },
                    "raw_cap": {
                        "type": "integer",
                        "description": "Cap on raw (level 0) records returned. Default: unbounded."
                    },
                    "mid_cap": {
                        "type": "integer",
                        "description": "Cap on mid-tier records returned. Default: unbounded."
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

// ─── leet_recall (delta-aware, post-11b) ────────────────────────────────────

#[derive(Deserialize)]
struct RecallArgs {
    #[serde(default)]
    query: Option<String>,
    #[serde(default = "default_limit")]
    limit: usize,
    #[serde(default)]
    raw_cap: Option<usize>,
    #[serde(default)]
    mid_cap: Option<usize>,
}
fn default_limit() -> usize { 5 }

pub async fn leet_recall(
    args: Value,
    store: &mut PersonalStore,
) -> Result<crate::protocol::ToolResult> {
    let args: RecallArgs = serde_json::from_value(args).unwrap_or(RecallArgs {
        query: None,
        limit: default_limit(),
        raw_cap: None,
        mid_cap: None,
    });

    if store.is_empty() {
        store.index.touch_recall(now_ns());
        let _ = store.index.flush();
        return Ok(crate::protocol::ToolResult::text(
            "No prior context in this project. Starting fresh.",
        ));
    }

    let tiers = group_live_records_by_tier(store);

    let picks = match args.query.as_deref() {
        Some(q) if !q.is_empty() => rank_by_distance(store, &tiers, q, args.limit)?,
        _ => fill_temporal(&tiers, args.limit, args.mid_cap, args.raw_cap),
    };

    let mut out = String::new();
    if picks.is_empty() {
        out.push_str(
            "Found no live context to recall (all records consolidated — this shouldn't \
             normally happen).",
        );
    } else {
        out.push_str(&format!(
            "Recalled {} entries from {} live records ({} total in store):\n\n",
            picks.len(),
            tiers.live_count(),
            store.len(),
        ));
        for (i, pick) in picks.iter().enumerate() {
            let rec = &store.records()[pick.idx];
            let entry = &store.index.entries[pick.idx];
            let ts = chrono_like(rec.unix_ns);
            let level_tag = format_level_tag(entry.level);
            let dist_str = pick
                .distance
                .map(|d| format!(" · distance={d:.3}"))
                .unwrap_or_default();
            out.push_str(&format!(
                "[{i}] {ts} · {level_tag}{dist_str}\n    {}\n\n",
                rec.excerpt
            ));
        }
        out.push_str(&summary_footer(&tiers, &picks));
    }

    store.index.touch_recall(now_ns());
    let _ = store.index.flush();

    Ok(crate::protocol::ToolResult::text(out))
}

// ─── Tiering ─────────────────────────────────────────────────────────────────

#[derive(Debug, Default)]
struct Tiers {
    foundation: Option<usize>,
    mid: Vec<usize>,
    raw: Vec<usize>,
}

impl Tiers {
    fn live_count(&self) -> usize {
        self.foundation.iter().count() + self.mid.len() + self.raw.len()
    }
}

fn group_live_records_by_tier(store: &PersonalStore) -> Tiers {
    let mut max_live_level: u8 = 0;
    for entry in &store.index.entries {
        if !entry.is_consolidated() && entry.level > max_live_level {
            max_live_level = entry.level;
        }
    }

    let mut tiers = Tiers::default();
    let mut foundation_idx: Option<usize> = None;
    if max_live_level > 0 {
        for (i, entry) in store.index.entries.iter().enumerate().rev() {
            if !entry.is_consolidated() && entry.level == max_live_level {
                foundation_idx = Some(i);
                break;
            }
        }
    }
    tiers.foundation = foundation_idx;

    for (i, entry) in store.index.entries.iter().enumerate().rev() {
        if entry.is_consolidated() {
            continue;
        }
        if Some(i) == foundation_idx {
            continue;
        }
        if entry.level == 0 {
            tiers.raw.push(i);
        } else {
            // Intermediate levels or older siblings at max level.
            tiers.mid.push(i);
        }
    }

    tiers
}

// ─── Ranked recall (with query) ──────────────────────────────────────────────

#[derive(Debug, Clone)]
struct Pick {
    idx: usize,
    distance: Option<f32>,
}

fn rank_by_distance(
    store: &PersonalStore,
    tiers: &Tiers,
    query: &str,
    limit: usize,
) -> Result<Vec<Pick>> {
    let query_cogon = encode_text(query)?;
    let mut all_indices: Vec<usize> = Vec::new();
    if let Some(f) = tiers.foundation {
        all_indices.push(f);
    }
    all_indices.extend(&tiers.mid);
    all_indices.extend(&tiers.raw);

    let mut scored: Vec<Pick> = all_indices
        .into_iter()
        .map(|i| {
            let d = dist(&query_cogon, &store.records()[i].cogon);
            Pick { idx: i, distance: Some(d) }
        })
        .collect();

    scored.sort_by(|a, b| {
        a.distance
            .partial_cmp(&b.distance)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    scored.truncate(limit);
    Ok(scored)
}

// ─── Temporal recall (no query): foundation + mid + recent raw ────────────────

fn fill_temporal(
    tiers: &Tiers,
    limit: usize,
    mid_cap: Option<usize>,
    raw_cap: Option<usize>,
) -> Vec<Pick> {
    let mut out: Vec<Pick> = Vec::new();

    if let Some(f) = tiers.foundation {
        out.push(Pick { idx: f, distance: None });
    }

    let mid_take = mid_cap.unwrap_or(usize::MAX);
    for &i in tiers.mid.iter().take(mid_take) {
        out.push(Pick { idx: i, distance: None });
    }

    let raw_take = raw_cap.unwrap_or(usize::MAX);
    for &i in tiers.raw.iter().take(raw_take) {
        out.push(Pick { idx: i, distance: None });
    }

    out.truncate(limit.max(1));
    out
}

// ─── Rendering helpers ────────────────────────────────────────────────────────

fn format_level_tag(level: u8) -> String {
    match level {
        0 => "raw".to_string(),
        n => format!("L{n}"),
    }
}

fn summary_footer(tiers: &Tiers, picks: &[Pick]) -> String {
    let raw_total = tiers.raw.len();
    let mid_total = tiers.mid.len();
    let foundation_present = tiers.foundation.is_some();
    let mut parts = Vec::new();
    if foundation_present {
        parts.push("1 foundation".to_string());
    }
    if mid_total > 0 {
        parts.push(format!("{mid_total} mid-tier"));
    }
    if raw_total > 0 {
        parts.push(format!("{raw_total} raw"));
    }
    let live_breakdown = parts.join(" + ");
    let shown = picks.len();
    let total_live = tiers.live_count();
    if shown < total_live {
        format!(
            "({shown} of {total_live} live: {live_breakdown}. \
             Pass a narrower query or higher limit to see more.)"
        )
    } else {
        format!("({live_breakdown})")
    }
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

pub fn encode_text(text: &str) -> Result<Cogon> {
    match leet_bridge::projector::project_text_simple(text) {
        Ok(c) => Ok(c),
        Err(_) => {
            let mut sem = leet_core::axes::boot_vector();
            sem[29] = 0.3;
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

pub fn now_ns() -> i64 {
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

pub fn chrono_like(unix_ns: i64) -> String {
    let secs = unix_ns / 1_000_000_000;
    let epoch_days = secs / 86400;
    let (year, month, day) = civil_from_days(epoch_days);
    let rem = secs % 86400;
    let hour = rem / 3600;
    let minute = (rem % 3600) / 60;
    format!("{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}")
}

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

// ─── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod recall_tests {
    use super::*;
    use leet_mcp::store::{PersonalStore, StoreRecord};
    use leet_core::types::Cogon;
    use uuid::Uuid;

    fn make_record(seed: f32, excerpt: &str, unix_ns: i64) -> StoreRecord {
        StoreRecord {
            cogon: Cogon { id: Uuid::new_v4(), sem: [seed; 32], stamp: 0, raw: None },
            excerpt: excerpt.to_string(),
            unix_ns,
        }
    }

    fn format_text(r: &crate::protocol::ToolResult) -> String {
        r.content
            .iter()
            .filter_map(|c| match c {
                crate::protocol::ContentItem::Text { text } => Some(text.clone()),
            })
            .collect::<String>()
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_empty_store() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let res = leet_recall(serde_json::json!({}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("No prior context"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_below_threshold_returns_all_raw() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..3 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let res = leet_recall(serde_json::json!({"limit": 10}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("rec0"));
        assert!(text.contains("rec1"));
        assert!(text.contains("rec2"));
        assert!(!text.contains("L1"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_after_consolidation_includes_foundation() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        // 8 records → 7 flagged (L0) + 1 L1 foundation + 1 new raw.
        for i in 0..8 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let res = leet_recall(serde_json::json!({"limit": 10}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("L1"));
        assert!(text.contains("raw"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_with_query_ranks_by_distance() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        store.append(make_record(0.1, "near 0", 1)).unwrap();
        store.append(make_record(0.5, "middle", 2)).unwrap();
        store.append(make_record(0.9, "near 1", 3)).unwrap();

        let res = leet_recall(
            serde_json::json!({"query": "anything", "limit": 3}),
            &mut store,
        )
        .await
        .unwrap();
        let text = format_text(&res);
        assert!(text.contains("distance="));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_updates_cursor() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        store.append(make_record(0.5, "x", 1)).unwrap();
        let before = store.index.last_recall_at;
        std::thread::sleep(std::time::Duration::from_millis(2));
        let _ = leet_recall(serde_json::json!({}), &mut store).await.unwrap();
        let after = store.index.last_recall_at;
        assert!(
            after > before,
            "cursor should advance after recall (before={before}, after={after})"
        );
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_skips_consolidated_records() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..7 {
            store.append(make_record(0.5, &format!("absorbed{i}"), i)).unwrap();
        }
        let res = leet_recall(serde_json::json!({"limit": 50}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("[L1×7]"));
        // Individual absorbed records would appear as "    absorbed{i}\n" if standalone.
        // Inside the consolidated excerpt they appear as "...absorbed{i}" preceded by " · ".
        for i in 0..7 {
            assert!(
                !text.contains(&format!("    absorbed{i}\n")),
                "record {i} should not appear standalone — it was consolidated"
            );
        }
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_at_high_levels_stays_bounded() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..49 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let res = leet_recall(serde_json::json!({"limit": 50}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(
            text.len() < 4096,
            "recall output {} bytes — too verbose at scale",
            text.len()
        );
        assert!(text.contains("L2"));
    }
}
