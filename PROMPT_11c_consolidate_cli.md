# PROMPT 11c — `leet consolidate` MANUAL CLI (debug + force consolidation)

Add a `leet consolidate` subcommand for inspecting the memory pyramid and forcing consolidations manually. Three subcommands: `inspect` (read-only diagnostic), `force` (consolidate even below threshold), `rebuild-index` (regenerate `.leet/index.bin` from scratch — recovery tool).

**PRE-REQUISITES**: 11a + 11b landed. `cargo test --workspace` green.

**SCOPE**: `leet-cli/src/cmd/consolidate.rs` (new) + register in `cmd/mod.rs`. No changes to leet-mcp.

**Taskwarrior**: `+prompt11c`.

---

## WHY THIS EXISTS

Most users never run this. It exists for three real situations:

1. **Debugging**: "did consolidation actually run? what level am I at?" → `leet consolidate inspect` shows the pyramid shape.
2. **Manual nudge**: "I want a clean recall right now, even though I only have 4 records" → `leet consolidate force --level 0` collapses what's there.
3. **Recovery**: "I deleted .leet/index.bin by accident" → `leet consolidate rebuild-index` reconstructs from store.bin.

This is a CLI command (not an MCP tool) because:
- It's diagnostic/operational, not part of the conversation flow
- The user runs it consciously, not via Claude
- Output is for humans, not for compression

---

## SUBCOMMANDS

```bash
leet consolidate inspect              # show pyramid, levels, live counts
leet consolidate inspect --json       # machine-readable
leet consolidate force                # force one consolidation pass at all levels
leet consolidate force --level 0      # only at level 0
leet consolidate rebuild-index        # delete index.bin, regenerate fresh
```

`leet consolidate inspect` output (typical):

```
Project: /home/yuri/some-project
Store:   .leet/store.bin (15 records, 5416 bytes)
Index:   .leet/index.bin (32 + 360 bytes)

Pyramid:
  L2: 1 live  (1 total, 0 consolidated)
  L1: 2 live  (3 total, 1 consolidated)
  L0: 5 live  (11 total, 6 consolidated)

Cursors:
  last_recall_at: 2026-04-26 12:34:56  (3 hours ago)

Next consolidation: needs 2 more L0 records (5/7) before triggering.
```

---

## FILE 1 — `leet-cli/src/cmd/consolidate.rs` (new)

The CLI re-implements the same binary format readers as PROMPT_10b/11a — we don't depend on `leet-mcp` from `leet-cli` to avoid circular deps. The format is fully specified, so duplicating the reader (read-only here, for inspect; write paths reuse the same writers) is acceptable.

For `force` we need to write back to the same `.leet/store.bin` and `.leet/index.bin` — this means reproducing the consolidation logic from 11a here. To keep this manageable we expose the consolidation function from `leet-mcp` as a library function and call it.

**Step 1**: in `leet-mcp/Cargo.toml`, add `[lib]` so this crate is also a library:

```toml
[lib]
name = "leet_mcp"
path = "src/lib.rs"

[[bin]]
name = "leet-mcp"
path = "src/main.rs"
```

Create `leet-mcp/src/lib.rs`:

```rust
//! leet-mcp as a library: exposes PersonalStore and consolidation primitives
//! for use by leet-cli and other in-workspace consumers.

pub mod index;
pub mod store;
// tools/protocol/server intentionally not re-exported — they're MCP-specific.
```

In `leet-mcp/src/main.rs`, replace `mod index; mod store; mod tools; mod protocol; mod server;` with:

```rust
use leet_mcp::store;
use leet_mcp::index;
mod tools;
mod protocol;
mod server;
```

(`tools.rs` and `server.rs` continue to refer to `crate::store::PersonalStore` etc. — adjust their imports if they previously assumed the modules were in the binary crate. Likely the only change needed is `use crate::store::PersonalStore;` → `use leet_mcp::store::PersonalStore;` in `tools.rs` and `server.rs`.)

**Step 2**: add `leet-mcp` as a dependency of `leet-cli`. In `leet-cli/Cargo.toml`:

```toml
[dependencies]
leet-mcp = { path = "../leet-mcp" }
# ... existing deps stay
```

**Step 3**: now write the actual subcommand.

```rust
//! `leet consolidate` — diagnose and manually trigger consolidation.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use clap::{Args, Subcommand};
use serde_json::json;

use leet_mcp::store::PersonalStore;
use leet_mcp::index::{Index, IndexEntry};

#[derive(Debug, Args)]
pub struct ConsolidateArgs {
    #[command(subcommand)]
    pub command: ConsolidateCommand,
}

#[derive(Debug, Subcommand)]
pub enum ConsolidateCommand {
    /// Show the pyramid shape — read-only.
    Inspect {
        /// Output JSON instead of human-readable text.
        #[arg(long)]
        json: bool,

        /// Path to project root (default: cwd).
        #[arg(long)]
        project: Option<PathBuf>,
    },

    /// Force consolidation. Useful when the trigger threshold (7) hasn't been hit
    /// yet but you want a clean recall now.
    Force {
        /// Restrict to a specific level. Without this flag, all levels cascade.
        #[arg(long)]
        level: Option<u8>,

        /// Minimum live records required at the level (default 2 — won't merge a single record).
        #[arg(long, default_value = "2")]
        min: usize,

        /// Path to project root (default: cwd).
        #[arg(long)]
        project: Option<PathBuf>,
    },

    /// Delete and rebuild .leet/index.bin from .leet/store.bin.
    /// Lossy: all records degrade to level 0 (consolidation history is lost).
    RebuildIndex {
        /// Skip confirmation prompt.
        #[arg(long)]
        yes: bool,

        /// Path to project root (default: cwd).
        #[arg(long)]
        project: Option<PathBuf>,
    },
}

pub fn run(args: ConsolidateArgs) -> Result<()> {
    match args.command {
        ConsolidateCommand::Inspect { json, project } => {
            inspect(project_or_cwd(project)?, json)
        }
        ConsolidateCommand::Force { level, min, project } => {
            force(project_or_cwd(project)?, level, min)
        }
        ConsolidateCommand::RebuildIndex { yes, project } => {
            rebuild_index(project_or_cwd(project)?, yes)
        }
    }
}

fn project_or_cwd(p: Option<PathBuf>) -> Result<PathBuf> {
    match p {
        Some(path) => Ok(path.canonicalize()?),
        None => Ok(std::env::current_dir()?),
    }
}

// ─── inspect ──────────────────────────────────────────────────────────────────

fn inspect(project_root: PathBuf, as_json: bool) -> Result<()> {
    let store = PersonalStore::open_or_create(&project_root)
        .with_context(|| format!("opening store at {}", project_root.display()))?;

    // Group entries by level.
    let mut by_level: std::collections::BTreeMap<u8, (usize, usize)> =
        std::collections::BTreeMap::new(); // (live, consolidated)
    for entry in &store.index.entries {
        let slot = by_level.entry(entry.level).or_default();
        if entry.is_consolidated() {
            slot.1 += 1;
        } else {
            slot.0 += 1;
        }
    }

    let store_path = project_root.join(".leet/store.bin");
    let index_path = project_root.join(".leet/index.bin");
    let store_size = std::fs::metadata(&store_path).map(|m| m.len()).unwrap_or(0);
    let index_size = std::fs::metadata(&index_path).map(|m| m.len()).unwrap_or(0);

    if as_json {
        let pyramid: Vec<_> = by_level
            .iter()
            .rev()
            .map(|(level, (live, consol))| {
                json!({
                    "level": level,
                    "live": live,
                    "consolidated": consol,
                    "total": live + consol,
                })
            })
            .collect();

        let out = json!({
            "project": project_root.display().to_string(),
            "store": {
                "path": store_path.display().to_string(),
                "records": store.len(),
                "bytes": store_size,
            },
            "index": {
                "path": index_path.display().to_string(),
                "bytes": index_size,
                "last_recall_at": store.index.last_recall_at,
            },
            "pyramid": pyramid,
            "next_consolidation": next_consolidation_hint(&by_level),
        });
        println!("{}", serde_json::to_string_pretty(&out)?);
        return Ok(());
    }

    // Human-readable.
    println!("Project: {}", project_root.display());
    println!("Store:   {} ({} records, {} bytes)", store_path.display(), store.len(), store_size);
    println!("Index:   {} ({} bytes)", index_path.display(), index_size);
    println!();
    println!("Pyramid:");
    for (level, (live, consol)) in by_level.iter().rev() {
        let total = live + consol;
        println!(
            "  L{level}: {live} live  ({total} total, {consol} consolidated)"
        );
    }
    println!();

    if store.index.last_recall_at > 0 {
        let ts = format_unix_ns(store.index.last_recall_at);
        let ago = humanize_age(store.index.last_recall_at);
        println!("Cursors:");
        println!("  last_recall_at: {ts}  ({ago})");
        println!();
    }

    println!("Next consolidation: {}", next_consolidation_hint(&by_level));
    Ok(())
}

fn next_consolidation_hint(
    by_level: &std::collections::BTreeMap<u8, (usize, usize)>,
) -> String {
    const THRESHOLD: usize = 7;
    for (level, (live, _)) in by_level {
        if *live >= THRESHOLD {
            return format!("ready at L{level} ({live} live)");
        }
    }
    // Find the highest level with any live records and show progress.
    if let Some((level, (live, _))) = by_level.iter().rev().find(|(_, (live, _))| *live > 0) {
        let needed = THRESHOLD.saturating_sub(*live);
        if needed == 0 {
            format!("ready at L{level}")
        } else {
            format!("needs {needed} more L{level} records ({live}/{THRESHOLD}) before triggering")
        }
    } else {
        "no live records yet".to_string()
    }
}

// ─── force ────────────────────────────────────────────────────────────────────

fn force(project_root: PathBuf, level_filter: Option<u8>, min: usize) -> Result<()> {
    if min < 2 {
        anyhow::bail!("--min must be ≥ 2 (cannot consolidate fewer than 2 records)");
    }

    let mut store = PersonalStore::open_or_create(&project_root)?;

    let mut total_consolidations = 0usize;
    let max_iterations = 20; // safety bound

    for _ in 0..max_iterations {
        let consolidated_this_pass = match level_filter {
            Some(level) => {
                store.force_consolidate_at(level, min, leet_mcp::store::CONSOLIDATE_THRESHOLD)?
            }
            None => {
                let mut any = false;
                for level in 0u8..=10 {
                    if store.force_consolidate_at(
                        level,
                        min,
                        leet_mcp::store::CONSOLIDATE_THRESHOLD,
                    )? {
                        any = true;
                    }
                }
                any
            }
        };
        if !consolidated_this_pass {
            break;
        }
        total_consolidations += 1;
    }

    println!("Forced {total_consolidations} consolidation(s).");
    Ok(())
}

// ─── rebuild-index ────────────────────────────────────────────────────────────

fn rebuild_index(project_root: PathBuf, skip_confirm: bool) -> Result<()> {
    let leet_dir = project_root.join(".leet");
    let store_path = leet_dir.join("store.bin");
    let index_path = leet_dir.join("index.bin");

    if !store_path.exists() {
        anyhow::bail!("no store at {}", store_path.display());
    }

    if !skip_confirm {
        println!("This will delete {}", index_path.display());
        println!("Records will all be marked as level 0 — consolidation history is lost.");
        println!("Type 'yes' to continue:");
        let mut buf = String::new();
        std::io::stdin().read_line(&mut buf)?;
        if buf.trim() != "yes" {
            println!("Aborted.");
            return Ok(());
        }
    }

    if index_path.exists() {
        std::fs::remove_file(&index_path)
            .with_context(|| format!("removing {}", index_path.display()))?;
    }

    // Reopen will rebuild fresh.
    let store = PersonalStore::open_or_create(&project_root)?;
    println!(
        "Rebuilt index for {} records. All marked level 0 (lossy).",
        store.len()
    );
    Ok(())
}

// ─── helpers (no chrono dep) ──────────────────────────────────────────────────

fn format_unix_ns(unix_ns: i64) -> String {
    let secs = unix_ns / 1_000_000_000;
    let days = secs / 86400;
    let rem = secs % 86400;
    let (y, m, d) = civil_from_days(days);
    format!("{y:04}-{m:02}-{d:02} {:02}:{:02}:{:02}", rem / 3600, (rem % 3600) / 60, rem % 60)
}

fn humanize_age(unix_ns: i64) -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos() as i64)
        .unwrap_or(0);
    let age_secs = (now - unix_ns) / 1_000_000_000;
    if age_secs < 60 {
        format!("{age_secs} seconds ago")
    } else if age_secs < 3600 {
        format!("{} minutes ago", age_secs / 60)
    } else if age_secs < 86400 {
        format!("{} hours ago", age_secs / 3600)
    } else {
        format!("{} days ago", age_secs / 86400)
    }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn humanize_age_buckets() {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as i64)
            .unwrap_or(0);
        assert!(humanize_age(now - 30 * 1_000_000_000).contains("seconds"));
        assert!(humanize_age(now - 600 * 1_000_000_000).contains("minutes"));
        assert!(humanize_age(now - 7200 * 1_000_000_000).contains("hours"));
        assert!(humanize_age(now - 200_000 * 1_000_000_000).contains("days"));
    }

    #[test]
    fn next_consolidation_hint_progress() {
        let mut m = std::collections::BTreeMap::new();
        m.insert(0u8, (3usize, 0usize));
        let hint = next_consolidation_hint(&m);
        assert!(hint.contains("4 more") && hint.contains("3/7"));
    }

    #[test]
    fn next_consolidation_hint_ready() {
        let mut m = std::collections::BTreeMap::new();
        m.insert(0u8, (7usize, 0usize));
        let hint = next_consolidation_hint(&m);
        assert!(hint.contains("ready"));
    }

    #[test]
    fn next_consolidation_hint_empty() {
        let m = std::collections::BTreeMap::new();
        let hint = next_consolidation_hint(&m);
        assert!(hint.contains("no live"));
    }
}
```

---

## FILE 2 — `leet-mcp/src/store.rs` (expose `force_consolidate_at` and `CONSOLIDATE_THRESHOLD`)

The CLI calls these. Expose them via `pub`:

```rust
// Change visibility:
pub const CONSOLIDATE_THRESHOLD: usize = 7;

impl PersonalStore {
    // ... existing methods ...

    /// Public wrapper for `force` CLI: consolidates at `level` if at least `min`
    /// live records exist there. Honors the same threshold cap (max 7 per pass).
    /// Returns true if consolidation happened.
    pub fn force_consolidate_at(
        &mut self,
        level: u8,
        min: usize,
        cap: usize,
    ) -> Result<bool> {
        let live = self.index.live_indices_at_level(level);
        if live.len() < min {
            return Ok(false);
        }

        let take = live.len().min(cap);
        let to_merge: Vec<usize> = live.into_iter().take(take).collect();

        let merged = blend_n_records(
            &to_merge.iter().map(|&i| &self.records[i]).collect::<Vec<_>>(),
            level,
        );

        let header_size = 16u64;
        let first_offset = header_size + (to_merge[0] as u64) * (RECORD_SIZE as u64);
        let last_offset =
            header_size + (*to_merge.last().unwrap() as u64) * (RECORD_SIZE as u64);

        let entry = IndexEntry {
            level: level + 1,
            flags: 0,
            consolidates_from_first: first_offset,
            consolidates_from_last: last_offset,
        };
        self.append_at_level(merged, level + 1, entry)?;
        self.index.mark_consolidated(&to_merge);
        self.index.flush()?;

        tracing::info!(
            "force_consolidate_at: merged {} records at level {level} → 1 record at level {}",
            to_merge.len(),
            level + 1
        );
        Ok(true)
    }
}
```

Also make `blend_n_records`, `append_at_level`, `RECORD_SIZE`, and `IndexEntry` accessible at crate level (they may already be `pub(crate)` — promote to `pub` if cli reaches them through the lib boundary). Concretely:

- `blend_n_records` → keep private (only used internally)
- `append_at_level` → keep private
- `RECORD_SIZE` → `pub const RECORD_SIZE: usize = 360;`
- `StoreRecord`, `PersonalStore` → already `pub`
- `IndexEntry` → already `pub` (from `index.rs`)

---

## FILE 3 — `leet-cli/src/cmd/mod.rs` (register subcommand)

```rust
pub mod consolidate;

// In Command enum:
/// Inspect, force, or rebuild the consolidation pyramid for a project.
Consolidate(cmd::consolidate::ConsolidateArgs),

// In dispatcher:
Command::Consolidate(args) => cmd::consolidate::run(args),
```

---

## VERIFICATION

```bash
cargo build --workspace
cargo test --workspace

# Inspect on an empty project
mkdir /tmp/leet-c && cd /tmp/leet-c
cargo run -p leet-cli -- consolidate inspect
# Expected: "no live records yet" type output

# Force on a small store
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"a"}}}' \
  | cargo run -p leet-mcp 2>/dev/null > /dev/null
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"leet_remember","arguments":{"text":"b"}}}' \
  | cargo run -p leet-mcp 2>/dev/null > /dev/null

cargo run -p leet-cli -- consolidate inspect
# Expected: L0: 2 live (2 total, 0 consolidated)

cargo run -p leet-cli -- consolidate force --min 2
# Expected: "Forced 1 consolidation(s)."

cargo run -p leet-cli -- consolidate inspect
# Expected: L1: 1 live, L0: 0 live (2 consolidated)

cargo run -p leet-cli -- consolidate inspect --json | jq .pyramid
# Expected: array of {level, live, consolidated, total}

# Rebuild
cargo run -p leet-cli -- consolidate rebuild-index --yes
cargo run -p leet-cli -- consolidate inspect
# Expected: all records back to L0
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt11c "leet consolidate CLI: inspect, force, rebuild-index"
task project:1337 +prompt11c done

git add leet-mcp/Cargo.toml leet-mcp/src/lib.rs leet-mcp/src/main.rs \
        leet-mcp/src/store.rs \
        leet-cli/Cargo.toml leet-cli/src/cmd/consolidate.rs leet-cli/src/cmd/mod.rs

git commit -m "feat(cli): leet consolidate — diagnose and force the memory pyramid

Three subcommands:

  leet consolidate inspect [--json]
      Show pyramid shape, level-by-level breakdown, last-recall cursor,
      and a hint for when the next auto-consolidation will fire.

  leet consolidate force [--level N] [--min K]
      Trigger consolidation manually at one or all levels, even below
      the auto-trigger threshold (7). --min defaults to 2.

  leet consolidate rebuild-index [--yes]
      Delete and regenerate .leet/index.bin. Lossy — all records degrade
      to level 0. Recovery tool for corrupted or accidentally-deleted index.

Required restructuring:
  - leet-mcp now exposes a [lib] crate alongside its bin
    (lib.rs publishes store + index; main.rs uses them via leet_mcp::*)
  - leet-cli depends on leet-mcp as a library to reuse PersonalStore
    rather than reimplementing the binary format.
  - PersonalStore::force_consolidate_at and CONSOLIDATE_THRESHOLD made pub.

Part of token-optimization phase, sub-prompt 11c."
git push origin main
```

---

**END OF PROMPT_11c**
