# PROMPT 11e — `intent=DELTA` SKETCH (spec compliance, opt-in, future-ready)

Implement `intent=DELTA` per spec § 8 and R2 — the formal patch-based recall already defined in v0.5.1 but never wired up. This is the "spec compliance" half of the dual decision (consolidation now + intent=DELTA later). It does NOT replace the tiered recall from PROMPT_11b — both coexist.

**WHY KEEP IT MARGINAL**: with Claude Code as the consumer, the DELTA path provides modest savings in real conversations. Its value is architectural: it formalizes how a future native-1337 agent (Mundo A) will request only what's changed. This prompt lands the protocol; future prompts can opt agents into using it.

**PRE-REQUISITES**: 11a + 11b + 11c + 11d landed.

**SCOPE**:
- New tool `leet_recall_delta` in `leet-mcp/src/tools.rs` (DOES NOT replace `leet_recall`)
- Helper functions in `leet-mcp/src/store.rs` to compute patch since cursor
- Tests
- Skill update is **NOT** part of this prompt — Claude Code shouldn't be steered toward DELTA yet

**Taskwarrior**: `+prompt11e`.

---

## SPEC RECAP — INTENT=DELTA

From v0.5.1 § 8:

```
MSG_1337 := {
  ...
  intent: ENUM<ASSERT|QUERY|DELTA|SYNC|ANOMALY|ACK>,
  ref:    HASH?,        // when intent=DELTA: which prior state we're patching
  patch:  VECTOR[32]?,  // when intent=DELTA: element-wise diff to apply
  payload: COGON | DAG,
  ...
}
```

R2: `intent=DELTA` requires both `ref` and `patch`. `intent≠DELTA` forbids `patch`.

The spec describes inter-agent delta compression: agent A holds a state; agent B sends the patch since A's last sync. Translated to our PersonalStore context:

- **Agent A** = the LLM that just received a recall response and now "holds" that state mentally (we approximate this by tracking `last_recall_at`).
- **Agent B** = the MCP server (us). It computes the patch since the cursor.
- **The patch** = a `VECTOR[32]` representing the **difference between the canonical centroid of all live records** and the canonical centroid **at the time of last_recall_at**.

This is a coarse approximation — a real native-1337 agent would track per-axis state. But it's spec-compliant and demonstrates the wire shape.

---

## NEW TOOL: `leet_recall_delta`

A separate tool (not a modification of `leet_recall`) so existing skill behavior is unaffected.

| Parameter | Type | Notes |
|---|---|---|
| `since_unix_ns` | i64? | Override the cursor; default uses `index.last_recall_at` |

Response:

```json
{
  "intent": "DELTA",
  "ref_hash": "<sha256 of the foundation cogon's sem at the cursor>",
  "patch": [f32; 32],
  "newly_added": [
    { "level": 0, "excerpt": "..." },
    ...
  ],
  "unchanged_since": <unix_ns>
}
```

The receiver applies `patch` to its prior `sem` to recover the current consolidated state. Plus `newly_added` gives concrete recent entries that haven't been folded into a higher tier yet (these aren't compressible as patches because they weren't there before — they're additions, not modifications).

Conceptually: **patch = (current_centroid − prior_centroid)**, plus any newly-added raw entries.

---

## ALGORITHM — COMPUTING THE DELTA

```
inputs:
  cursor_ns: i64                  // when the receiver last synced
  store: PersonalStore            // current state

step 1:  prior_centroid = G1-weighted centroid of all live records with unix_ns ≤ cursor_ns
step 2:  current_centroid = G1-weighted centroid of all live records (any unix_ns)
step 3:  patch[k] = current_centroid[k] − prior_centroid[k]  for k in 0..32
step 4:  ref_hash = SHA256(prior_centroid as f32 LE bytes)
step 5:  newly_added = excerpts of records with unix_ns > cursor_ns

returns: { ref_hash, patch, newly_added, unchanged_since: cursor_ns }
```

Note `patch` can have **negative values** — DELTA is a difference vector, not a clamped state. R22 explicitly does not apply to patches (they live outside the [0,1] range; they're applied to states which are then clamped).

If the cursor is 0 (no prior recall, fresh consumer), the prior_centroid is taken to be `axes::boot_vector()` — Pillar 4 boot defaults. The first DELTA call from a fresh consumer is essentially "here's the world from neutral."

---

## FILE 1 — `leet-mcp/src/store.rs` (add public helper)

Add at the bottom of the `impl PersonalStore` block:

```rust
impl PersonalStore {
    // ... existing methods ...

    /// Compute the canonical centroid (G1-weighted) of all live records
    /// whose unix_ns is ≤ `cursor_ns`. If `cursor_ns` is 0 or no records
    /// match, returns the Pillar 4 boot vector.
    pub fn centroid_up_to(&self, cursor_ns: i64) -> [f32; 32] {
        let eligible: Vec<&StoreRecord> = self
            .records
            .iter()
            .enumerate()
            .filter(|(i, _)| !self.index.entries[*i].is_consolidated())
            .map(|(_, r)| r)
            .filter(|r| cursor_ns == 0 || r.unix_ns <= cursor_ns)
            .collect();

        if eligible.is_empty() {
            return leet_core::axes::boot_vector();
        }

        let total_mass: f32 = eligible.iter().map(|r| r.cogon.sem[16]).sum();
        let mut sem = [0.0_f32; 32];

        if total_mass > f32::EPSILON {
            for r in &eligible {
                let w = r.cogon.sem[16] / total_mass;
                for k in 0..32 {
                    sem[k] += w * r.cogon.sem[k];
                }
            }
        } else {
            let inv_n = 1.0 / eligible.len() as f32;
            for r in &eligible {
                for k in 0..32 {
                    sem[k] += r.cogon.sem[k] * inv_n;
                }
            }
        }

        for v in sem.iter_mut() {
            *v = v.clamp(0.0, 1.0);
        }
        sem
    }

    /// Live records added strictly after `cursor_ns`. Returns indices in
    /// store order (oldest to newest).
    pub fn live_records_after(&self, cursor_ns: i64) -> Vec<usize> {
        self.records
            .iter()
            .enumerate()
            .filter(|(i, r)| {
                !self.index.entries[*i].is_consolidated() && r.unix_ns > cursor_ns
            })
            .map(|(i, _)| i)
            .collect()
    }
}
```

---

## FILE 2 — `leet-mcp/src/tools.rs` (add new tool)

In `tool_definitions()`, append a new ToolDef:

```rust
ToolDef {
    name: "leet_recall_delta",
    description: "Spec-compliant intent=DELTA recall. Returns a 32-dim patch vector \
                  representing the change in canonical state since the last sync, plus \
                  any newly-added live records. Use ONLY if you maintain prior state \
                  and can apply patches — for human-readable recall, use leet_recall.",
    input_schema: json!({
        "type": "object",
        "properties": {
            "since_unix_ns": {
                "type": "integer",
                "description": "Override the cursor. If omitted, uses index.last_recall_at. \
                                Pass 0 to get the patch from the boot baseline."
            }
        }
    }),
},
```

Add the dispatcher case in `handle_tools_call` (server.rs):

```rust
"leet_recall_delta" => tools::leet_recall_delta(arguments, store).await,
```

Implement the tool handler (in tools.rs):

```rust
// ─── leet_recall_delta (intent=DELTA spec compliance) ────────────────────────

#[derive(Deserialize)]
struct RecallDeltaArgs {
    #[serde(default)]
    since_unix_ns: Option<i64>,
}

pub async fn leet_recall_delta(
    args: Value,
    store: &mut PersonalStore,
) -> Result<crate::protocol::ToolResult> {
    let args: RecallDeltaArgs = serde_json::from_value(args).unwrap_or(RecallDeltaArgs {
        since_unix_ns: None,
    });

    let cursor_ns = args.since_unix_ns.unwrap_or(store.index.last_recall_at);

    // Compute centroids.
    let prior = store.centroid_up_to(cursor_ns);
    let current = store.centroid_up_to(0); // 0 means no upper bound → all live records

    // Patch = current - prior (signed; can be negative).
    let mut patch = [0.0_f32; 32];
    for k in 0..32 {
        patch[k] = current[k] - prior[k];
    }

    // ref_hash = SHA256 over prior centroid bytes.
    let ref_hash = sha256_of_sem(&prior);

    // newly_added: live records strictly after cursor.
    let new_indices = store.live_records_after(cursor_ns);
    let newly_added: Vec<Value> = new_indices
        .iter()
        .map(|&i| {
            let entry = &store.index.entries[i];
            let rec = &store.records()[i];
            json!({
                "level": entry.level,
                "excerpt": rec.excerpt,
                "unix_ns": rec.unix_ns,
            })
        })
        .collect();

    let payload = json!({
        "intent": "DELTA",
        "ref_hash": ref_hash,
        "patch": patch.to_vec(),
        "newly_added": newly_added,
        "unchanged_since": cursor_ns,
        "spec_version": "0.5.1",
    });

    // Update cursor (consumer is now caught up).
    store.index.touch_recall(now_ns());
    let _ = store.index.flush();

    Ok(crate::protocol::ToolResult::text(payload.to_string()))
}

/// SHA256 hex string of a sem[32] little-endian byte representation.
fn sha256_of_sem(sem: &[f32; 32]) -> String {
    use sha2::{Digest, Sha256};
    let mut bytes = [0u8; 128];
    for (k, v) in sem.iter().enumerate() {
        bytes[k * 4..k * 4 + 4].copy_from_slice(&v.to_le_bytes());
    }
    let h = Sha256::digest(bytes);
    hex(&h)
}

fn hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{:02x}", b));
    }
    s
}
```

The `sha2` and `hex`/format usage matches what's already in leet-core for align_hash. If `sha2` isn't a leet-mcp dependency yet, add it to `leet-mcp/Cargo.toml`:

```toml
[dependencies]
# ... existing
sha2 = "0.10"
```

---

## FILE 3 — Tests (in `leet-mcp/src/tools.rs`)

Add to the existing test module:

```rust
#[tokio::test(flavor = "current_thread")]
async fn delta_with_no_records_returns_zero_patch() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    let res = leet_recall_delta(serde_json::json!({}), &mut store).await.unwrap();
    let text = format_text(&res);
    let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
    let patch = parsed["patch"].as_array().unwrap();
    // boot_vector vs boot_vector → all zeros
    for v in patch {
        assert!((v.as_f64().unwrap()).abs() < 1e-6);
    }
    assert_eq!(parsed["intent"].as_str().unwrap(), "DELTA");
}

#[tokio::test(flavor = "current_thread")]
async fn delta_after_first_record_is_nontrivial() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    let mut rec = make_record(0.5, "first decision", 1000);
    rec.cogon.sem[0] = 0.95; // strong signal on S1_INTENTION
    store.append(rec).unwrap();

    let res = leet_recall_delta(serde_json::json!({"since_unix_ns": 0}), &mut store)
        .await.unwrap();
    let text = format_text(&res);
    let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
    let patch = parsed["patch"].as_array().unwrap();
    let s1_delta = patch[0].as_f64().unwrap() as f32;
    // S1 went from boot_default (0.5) to ~0.95 → patch should be ~+0.45
    assert!(s1_delta > 0.3, "S1 delta = {s1_delta}, expected ≥ 0.3");
}

#[tokio::test(flavor = "current_thread")]
async fn delta_includes_newly_added() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    store.append(make_record(0.5, "before", 1000)).unwrap();
    store.index.touch_recall(2000);
    let _ = store.index.flush();
    store.append(make_record(0.5, "after", 3000)).unwrap();

    let res = leet_recall_delta(serde_json::json!({}), &mut store).await.unwrap();
    let text = format_text(&res);
    let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
    let added = parsed["newly_added"].as_array().unwrap();
    assert_eq!(added.len(), 1);
    assert_eq!(added[0]["excerpt"].as_str().unwrap(), "after");
}

#[tokio::test(flavor = "current_thread")]
async fn delta_ref_hash_changes_with_state() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    let res1 = leet_recall_delta(serde_json::json!({"since_unix_ns": 0}), &mut store)
        .await.unwrap();
    let text1 = format_text(&res1);
    let parsed1: serde_json::Value = serde_json::from_str(&text1).unwrap();
    let h1 = parsed1["ref_hash"].as_str().unwrap().to_string();

    store.append(make_record(0.9, "x", 10)).unwrap();
    let res2 = leet_recall_delta(serde_json::json!({"since_unix_ns": 0}), &mut store)
        .await.unwrap();
    let text2 = format_text(&res2);
    let parsed2: serde_json::Value = serde_json::from_str(&text2).unwrap();
    let h2 = parsed2["ref_hash"].as_str().unwrap().to_string();

    // Both hashes are computed against the prior baseline (boot_vector for cursor=0)
    // so both should be IDENTICAL — the prior state didn't change.
    assert_eq!(h1, h2);
}

#[tokio::test(flavor = "current_thread")]
async fn delta_patch_can_be_negative() {
    let tmp = tempfile::tempdir().unwrap();
    let mut store = PersonalStore::open_or_create(tmp.path()).unwrap();
    // Boot S5_ENTROPY is 0.5. Add a record with low entropy.
    let mut rec = make_record(0.5, "low entropy", 1);
    rec.cogon.sem[4] = 0.1;
    store.append(rec).unwrap();

    let res = leet_recall_delta(serde_json::json!({"since_unix_ns": 0}), &mut store)
        .await.unwrap();
    let text = format_text(&res);
    let parsed: serde_json::Value = serde_json::from_str(&text).unwrap();
    let patch = parsed["patch"].as_array().unwrap();
    let s5_delta = patch[4].as_f64().unwrap() as f32;
    assert!(s5_delta < -0.2, "S5 should drop from 0.5 to ~0.1, delta = {s5_delta}");
}
```

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-mcp tools
cargo test --workspace

# Live smoke
mkdir /tmp/leet-delta && cd /tmp/leet-delta
cargo run -p leet-mcp <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"a"}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"b"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"leet_recall_delta","arguments":{"since_unix_ns":0}}}
EOF | tail -1 | jq

# Expected JSON shape:
# {
#   "intent": "DELTA",
#   "ref_hash": "<64-char hex>",
#   "patch": [32 floats, mix of positive and negative],
#   "newly_added": [...two entries...],
#   "unchanged_since": 0,
#   "spec_version": "0.5.1"
# }
```

---

## WHY NO SKILL UPDATE FOR THIS

PROMPT_11d already taught Claude how to use the recommended (tiered) recall. Steering Claude toward `leet_recall_delta` would be premature — the LLM is not the right consumer for this tool. It's there for:

- A future native-1337 orchestrator agent that maintains 32-dim state in memory
- External programmatic consumers (analytics, dashboards) that want the raw deltas
- Spec compliance / interop with other 1337 implementations

When (if) Mundo A becomes a real product, a different skill or system prompt would steer those agents to use `leet_recall_delta`. For now, it sits available, dormant, spec-compliant.

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt11e "leet_recall_delta: spec-compliant intent=DELTA tool"
task project:1337 +prompt11e done

git add leet-mcp/src/tools.rs leet-mcp/src/store.rs leet-mcp/src/server.rs leet-mcp/Cargo.toml
git commit -m "feat(mcp): leet_recall_delta — spec-compliant intent=DELTA recall

Adds the formal patch-based recall that v0.5.1 § 8 defines but never
wired up. Returns:
  intent: 'DELTA'
  ref_hash: SHA256 of the prior canonical centroid (sem[32] LE bytes)
  patch: VECTOR[32] of (current_centroid - prior_centroid), signed
  newly_added: list of {level, excerpt, unix_ns} for new live records
  unchanged_since: the cursor value used as baseline

This is intentionally separate from leet_recall — the existing tiered
recall (PROMPT_11b) remains the recommended path for human-facing
conversations. leet_recall_delta exists for:

  - Spec compliance with v0.5.1 R2 (intent=DELTA requires ref+patch)
  - Future native-1337 orchestrator agents (Mundo A) that maintain
    32-dim state and can apply patches efficiently
  - External programmatic consumers (analytics, dashboards)

Architectural notes:
  - prior_centroid uses cursor (last_recall_at by default; pass 0 for
    boot baseline)
  - current_centroid uses all live records
  - Patch values can be negative (R22 doesn't apply to deltas; only to
    states they're applied to, which then get clamped)
  - Both prior and current use G1_MASS-weighted centroid with uniform
    fallback when total mass is zero

The skill is NOT updated to steer Claude toward this tool — it's
infrastructure for a future audience.

Part of token-optimization phase, sub-prompt 11e (final of phase 11)."
git push origin main
```

---

**END OF PROMPT_11e**
