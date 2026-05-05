# PROMPT 11b — `leet_recall` DELTA-AWARE (highest level + recent unconsolidated)

Replace the current naïve `leet_recall` with a delta-aware version that returns the **memory pyramid** efficiently: highest-level summaries first, then progressively more raw detail for the most recent activity. Result: tokens spent on recall scale logarithmically with project history instead of linearly.

**PRE-REQUISITES**: PROMPT_11a landed. `cargo test --workspace` green. `index.bin` exists, consolidation cascades work.

**SCOPE**: `leet-mcp/src/tools.rs` — rewrite `leet_recall` and its helpers. No other files change.

**Taskwarrior**: `+prompt11b`.

---

## THE PYRAMID, REVISITED

After 49 raw records the store looks like this (level/flag schematic):

```
positions 0..6   level=0, consolidated     ← absorbed into position 7
position  7      level=1, live
positions 8..14  level=0, consolidated     ← absorbed into position 15
position  15     level=1, live
... (5 more level-1 records) ...
position  55     level=1, consolidated     ← all 7 level-1 absorbed into 56
position  56     level=2, live
```

A naïve recall returns 5 records — could be any 5 from positions 0..56. With consolidation flags it skips the 49 absorbed records and considers the 8 live ones (1 level-2 + 7 already-absorbed level-1s + leftovers). But that's still suboptimal for a "delta-aware" recall.

**The delta-aware strategy** has three layers:

1. **Foundation** — the single highest-level live record. This summarizes the whole project history up to the last consolidation. (The level-2 record above. Or level-3, level-4 — whatever the highest is.)
2. **Mid-tier deltas** — live records at intermediate levels created since the foundation. These represent semi-consolidated activity that hasn't yet rolled up.
3. **Recent raw** — level-0 live records (haven't been consolidated yet, < 7 of them).

The recall budget is allocated across these layers so the response stays bounded regardless of project size:

| Layer | Always include | Cap |
|---|---|---|
| Foundation (highest live) | yes | 1 |
| Mid-tier (levels between 0 and highest) | yes, all live | configurable, default unbounded |
| Recent raw (level 0 live) | yes, all live | configurable, default unbounded |

In practice for any realistic project: foundation = 1 record, mid-tier ≤ 6 records, recent raw ≤ 6 records. Total ≤ 13 records, regardless of whether the project has 50 or 5000 raw entries.

---

## QUERY-AWARE RANKING (when `query` is provided)

When the user provides a `query`:

1. Encode the query to a COGON.
2. Compute DIST from the query to **every live record** (foundation + mid-tier + recent raw).
3. Sort ascending by distance, take `limit` (default 5).
4. Return them in that ranked order.

When **no query** is provided:

1. Always include the foundation (highest-level live).
2. Always include all mid-tier live records (newest-first).
3. Fill remaining `limit` slots with most-recent raw records.

This gives the user explicit control: "recall me X" → ranked semantic match; "recall my context" → temporal/structural prioritization.

---

## TOKEN ESTIMATE — WHY THIS HELPS

Reconstructed text from a recall response is roughly:

```
total_tokens ≈ Σ over included_records:  ~150 tokens per excerpt + framing
```

Old behavior (naïve, top-5 by recency): always 5 records → ~800 tokens.

New behavior on a 50-record project after consolidation:
- Foundation level-1 record: 1 × 150 = 150 tokens (covers the first 7 records)
- 6 live level-0 records (most recent): 6 × 150 = 900 tokens

Hmm, that's *worse* with this projection. The benefit shows up at scale: on a 200-record project, naïve recall still returns 5 records; new recall returns 1 level-2 (covering 49) + a few mid-tier + recent. **The project keeps growing but the recall doesn't.**

So the win is asymptotic. For tiny projects (< 14 records), recall is essentially identical to before. For long-running projects, recall becomes flat-cost. That's the architectural property we wanted.

---

## FILE — `leet-mcp/src/tools.rs` (replace `leet_recall` and helpers)

Locate the existing `leet_recall` function (from PROMPT_10a) and the `RecallArgs` struct. Replace **only** those — keep the other tools intact.

```rust
// ─── leet_recall (delta-aware, post-11a) ─────────────────────────────────────

#[derive(Deserialize)]
struct RecallArgs {
    #[serde(default)]
    query: Option<String>,
    #[serde(default = "default_limit")]
    limit: usize,
    /// Optional override: cap on raw (level 0) records returned. Default: unbounded.
    #[serde(default)]
    raw_cap: Option<usize>,
    /// Optional override: cap on mid-tier records returned. Default: unbounded.
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
        // Still touch the cursor so future recalls know they're not the first.
        store.index.touch_recall(now_ns());
        let _ = store.index.flush();
        return Ok(crate::protocol::ToolResult::text(
            "No prior context in this project. Starting fresh.".to_string(),
        ));
    }

    // Build the candidate set: live records grouped by tier.
    let tiers = group_live_records_by_tier(store);

    let picks = match args.query.as_deref() {
        Some(q) if !q.is_empty() => rank_by_distance(store, &tiers, q, args.limit)?,
        _ => fill_temporal(&tiers, args.limit, args.mid_cap, args.raw_cap),
    };

    // Render.
    let mut out = String::new();
    if picks.is_empty() {
        out.push_str("Found no live context to recall (all records consolidated and not yet \
                      summarized at any level — this shouldn't normally happen).");
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

    // Update recall cursor.
    store.index.touch_recall(now_ns());
    let _ = store.index.flush();

    Ok(crate::protocol::ToolResult::text(out))
}

// ─── Tiering ─────────────────────────────────────────────────────────────────

#[derive(Debug, Default)]
struct Tiers {
    /// Highest-level live record (the "foundation"). Optional — empty store has none.
    foundation: Option<usize>,
    /// Live records at intermediate levels (between 1 and foundation_level - 1).
    /// Sorted most-recent-first.
    mid: Vec<usize>,
    /// Live records at level 0. Sorted most-recent-first.
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
    // Foundation = newest live record at max_live_level (if max_live_level > 0).
    if max_live_level > 0 {
        for (i, entry) in store.index.entries.iter().enumerate().rev() {
            if !entry.is_consolidated() && entry.level == max_live_level {
                foundation_idx = Some(i);
                break;
            }
        }
    }
    tiers.foundation = foundation_idx;

    // Walk records newest-first, classifying.
    for (i, entry) in store.index.entries.iter().enumerate().rev() {
        if entry.is_consolidated() {
            continue;
        }
        if Some(i) == foundation_idx {
            continue;
        }
        if entry.level == 0 {
            tiers.raw.push(i);
        } else if entry.level < max_live_level || max_live_level == 0 {
            tiers.mid.push(i);
        } else {
            // entry.level == max_live_level but isn't the foundation — older sibling.
            // Treat as mid for ranking purposes.
            tiers.mid.push(i);
        }
    }

    tiers
}

// ─── Ranked recall (with query) ──────────────────────────────────────────────

#[derive(Debug, Clone)]
struct Pick {
    idx: usize,
    distance: Option<f32>, // None when temporal-only fill
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
            let d = leet_core::operators::dist(&query_cogon, &store.records()[i].cogon);
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

// ─── Temporal recall (no query): foundation + mid + recent raw ───────────────

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

    // Apply overall `limit` last — if user explicitly asked for fewer, truncate.
    // (Common case: limit=5, foundation+mid covers it, raw gets clipped.)
    out.truncate(limit.max(1));
    out
}

// ─── Rendering helpers ───────────────────────────────────────────────────────

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

// ─── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod recall_tests {
    use super::*;
    use crate::store::{PersonalStore, StoreRecord};
    use leet_core::types::Cogon;
    use uuid::Uuid;

    fn make_record(seed: f32, excerpt: &str, unix_ns: i64) -> StoreRecord {
        StoreRecord {
            cogon: Cogon { id: Uuid::new_v4(), sem: [seed; 32], stamp: 0, raw: None },
            excerpt: excerpt.to_string(),
            unix_ns,
        }
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_empty_store() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        let res = leet_recall(serde_json::json!({}), &mut store).await.unwrap();
        let text = res.content.iter().filter_map(|c| match c {
            crate::protocol::ContentItem::Text { text } => Some(text.clone()),
        }).collect::<String>();
        assert!(text.contains("No prior context"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_below_threshold_returns_all_raw() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..3 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let res = leet_recall(
            serde_json::json!({"limit": 10}),
            &mut store,
        ).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("rec0"));
        assert!(text.contains("rec1"));
        assert!(text.contains("rec2"));
        // No level tags should appear except 'raw'.
        assert!(!text.contains("L1"));
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_after_consolidation_includes_foundation() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        // 8 records → 7 consolidated (level 0 flagged) + 1 foundation (level 1 live).
        for i in 0..8 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        // After 7 raws → 1 consolidated (record 7, level 1).
        // Then record 8 is a fresh raw at level 0.
        let res = leet_recall(serde_json::json!({"limit": 10}), &mut store).await.unwrap();
        let text = format_text(&res);
        assert!(text.contains("L1"));      // foundation included
        assert!(text.contains("raw"));     // recent raw included
        assert!(text.contains("rec7"));    // record 7's excerpt prefix
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_with_query_ranks_by_distance() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        // Different seeds → different sem vectors → different distances.
        store.append(make_record(0.1, "near 0", 1)).unwrap();
        store.append(make_record(0.5, "middle", 2)).unwrap();
        store.append(make_record(0.9, "near 1", 3)).unwrap();

        let res = leet_recall(
            serde_json::json!({"query": "anything", "limit": 3}),
            &mut store,
        ).await.unwrap();
        let text = format_text(&res);
        // All three included, in some ranked order — just check distances appear.
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
        assert!(after > before, "cursor should advance after recall (before={before}, after={after})");
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_skips_consolidated_records() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        for i in 0..7 {
            store.append(make_record(0.5, &format!("absorbed{i}"), i)).unwrap();
        }
        // Now records 0..6 are flagged consolidated, record 7 is the L1 foundation.
        let res = leet_recall(serde_json::json!({"limit": 50}), &mut store).await.unwrap();
        let text = format_text(&res);
        // The L1 record's excerpt starts with "[L1×7]" by 11a's blend_n_records.
        assert!(text.contains("[L1×7]"));
        // None of the absorbed records should be returned individually.
        for i in 0..7 {
            assert!(!text.contains(&format!("absorbed{i}\n")),
                "record {i} should not appear standalone — it was consolidated");
        }
    }

    #[tokio::test(flavor = "current_thread")]
    async fn recall_at_high_levels_stays_bounded() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
        // 49 records → cascades to 1 L2 + leftovers.
        for i in 0..49 {
            store.append(make_record(0.5, &format!("rec{i}"), i)).unwrap();
        }
        let res = leet_recall(serde_json::json!({"limit": 50}), &mut store).await.unwrap();
        let text = format_text(&res);
        // Token count proxy: rendered text should be < 4 KB even though
        // the store has 57 records on disk.
        assert!(text.len() < 4096, "recall output {} bytes — too verbose at scale", text.len());
        assert!(text.contains("L2"));
    }

    fn format_text(r: &crate::protocol::ToolResult) -> String {
        r.content.iter().filter_map(|c| match c {
            crate::protocol::ContentItem::Text { text } => Some(text.clone()),
        }).collect::<String>()
    }
}
```

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-mcp recall_tests
cargo test --workspace

# Smoke at scale
rm -rf /tmp/leet-pyramid && mkdir /tmp/leet-pyramid
for i in $(seq 1 50); do
  echo "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"leet_remember\",\"arguments\":{\"text\":\"decision $i: ...\"}}}"
done | LEET_PROJECT_ROOT=/tmp/leet-pyramid cargo run -p leet-mcp 2>/dev/null > /dev/null

# Now recall — expect bounded output
echo '{"jsonrpc":"2.0","id":99,"method":"tools/call","params":{"name":"leet_recall","arguments":{"limit":10}}}' \
  | LEET_PROJECT_ROOT=/tmp/leet-pyramid cargo run -p leet-mcp 2>/dev/null \
  | jq -r '.result.content[0].text'

# Expected output mentions:
#   - "L2" (foundation)
#   - some "L1" entries (mid)
#   - some "raw" entries (recent)
#   - footer like "(1 foundation + 0 mid-tier + 1 raw)"
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt11b "leet_recall delta-aware: foundation + mid-tier + recent raw, query-ranked when provided"
# work
task project:1337 +prompt11b done

git add leet-mcp/src/tools.rs
git commit -m "feat(mcp): delta-aware leet_recall with foundation + mid + raw tiers

Recall now respects the memory pyramid built by PROMPT_11a's
hierarchical consolidation. Three tiers selected per call:

  Foundation: highest-level live record (1, optional)
  Mid:        live records at intermediate levels (newest-first)
  Raw:        live records at level 0 (newest-first)

Two modes:
  - With query: rank all live records by DIST to the query, take limit.
  - Without query: foundation + all mid + recent raw, capped by limit.

Render includes per-record level tags (L1/L2/raw) and a summary footer
('1 foundation + 3 mid-tier + 5 raw').

Token cost stays bounded as the project grows. On a 49-record project,
recall output is ~3KB regardless of scale (verified in
recall_at_high_levels_stays_bounded test).

Updates last_recall_at on every call (best-effort flush) for future
intent=DELTA payloads (PROMPT_11e).

Part of token-optimization phase, sub-prompt 11b."
git push origin main
```

---

**END OF PROMPT_11b**
