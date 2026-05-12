//! `leet consolidate` — diagnose and manually trigger consolidation.

use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Args, Subcommand};
use serde_json::json;

use leet_mcp::store::{PersonalStore, CONSOLIDATE_THRESHOLD};

#[derive(Debug, Args)]
#[command(
    about = "Inspect, force, or rebuild the consolidation pyramid",
    long_about = "Inspect, force, or rebuild the consolidation pyramid.\n\
\n\
leet auto-consolidates memories every 7 entries. This subcommand exposes\n\
the pyramid for manual inspection, forcing consolidation below threshold,\n\
or recovering after index corruption.",
    after_help = "Examples:\n  \
  # Show pyramid shape (how many entries at each level)\n  \
  leet consolidate inspect\n\
\n  \
  # Force a consolidation pass\n  \
  leet consolidate force\n\
\n  \
  # Regenerate index.bin from store.bin (lossy: levels reset to 0)\n  \
  leet consolidate rebuild-index --yes\n\
\n\
See also:\n  \
  leet doctor  — detects index/store sync issues"
)]
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

        /// Minimum live records required at the level (default 2).
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

    let mut by_level: std::collections::BTreeMap<u8, (usize, usize)> =
        std::collections::BTreeMap::new();
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

    println!("Project: {}", project_root.display());
    println!(
        "Store:   {} ({} records, {} bytes)",
        store_path.display(),
        store.len(),
        store_size
    );
    println!("Index:   {} ({} bytes)", index_path.display(), index_size);
    println!();
    println!("Pyramid:");
    for (level, (live, consol)) in by_level.iter().rev() {
        let total = live + consol;
        println!("  L{level}: {live} live  ({total} total, {consol} consolidated)");
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
    for (level, (live, _)) in by_level {
        if *live >= CONSOLIDATE_THRESHOLD {
            return format!("ready at L{level} ({live} live)");
        }
    }
    if let Some((level, (live, _))) = by_level.iter().find(|(_, (live, _))| *live > 0) {
        let needed = CONSOLIDATE_THRESHOLD.saturating_sub(*live);
        if needed == 0 {
            format!("ready at L{level}")
        } else {
            format!(
                "needs {needed} more L{level} records ({live}/{CONSOLIDATE_THRESHOLD}) before triggering"
            )
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
    let max_iterations = 20;

    for _ in 0..max_iterations {
        let consolidated_this_pass = match level_filter {
            Some(level) => store.force_consolidate_at(level, min, CONSOLIDATE_THRESHOLD)?,
            None => {
                let mut any = false;
                for level in 0u8..=10 {
                    if store.force_consolidate_at(level, min, CONSOLIDATE_THRESHOLD)? {
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
    format!(
        "{y:04}-{m:02}-{d:02} {:02}:{:02}:{:02}",
        rem / 3600,
        (rem % 3600) / 60,
        rem % 60
    )
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
