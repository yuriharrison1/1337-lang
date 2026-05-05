# PROMPT 10e — `leet absorb` safety-net CLI (bulk-import past Claude Code sessions)

Add a CLI subcommand `leet absorb` that reads Claude Code's local session history for the current project and compresses every session into one COGON, appending to `.leet/store.bin`. This is the **safety net** for users who want to bootstrap memory from projects that existed before leet was installed — or recover if the automatic `leet_remember` path missed things.

**PRE-REQUISITES**: 10a + 10b + 10c + 10d landed. `.leet/store.bin` works end-to-end.

**SCOPE**: `leet-cli/src/cmd/absorb.rs` (new) + register in `cmd/mod.rs`.

**Taskwarrior**: `+prompt10e`.

---

## WHY THIS EXISTS

Two user scenarios:

1. **"I've been using Claude Code for months; I just installed leet. I want today's me to remember those months."** → run `leet absorb` once. It reads all past sessions and creates one COGON per session.

2. **"I realized Claude didn't call `leet_remember` during that big refactor yesterday; the decisions are nowhere in my store."** → run `leet absorb --since yesterday`. Fills the gap.

This is an **opt-in safety net** — the automatic flow (tools + skill) is the primary path. Most users will never run `leet absorb`. But when they need it, they really need it.

---

## WHERE CLAUDE CODE STORES SESSIONS

Claude Code persists conversation history under `~/.claude/projects/<hash>/` where `<hash>` is derived from the absolute path of the project directory. Layout (observed across versions):

```
~/.claude/projects/<hash>/
  ├── sessions.jsonl           # stream of user/assistant turns
  ├── conversation_<date>.md   # readable rendered transcript (newer versions)
  └── metadata.json            # project metadata
```

Not every Claude Code version uses the same layout. `leet absorb` should probe defensively and skip gracefully if paths are missing.

To find the right `<hash>` directory for the current project, Claude Code encodes the absolute project path — historically MD5, sometimes SHA256, sometimes a readable slug. We probe by:

1. Looking for a `metadata.json` under `~/.claude/projects/*/` whose `project_path` field matches our absolute cwd.
2. Fallback: ask the user which subdirectory to use if multiple candidates.
3. Fallback-fallback: read all sessions under the hash directory that came up in `ls -t` most recently.

---

## WHAT ONE ABSORBED COGON LOOKS LIKE

Per the user's decision ("one COGON per session"), each transcript becomes exactly one record:

- **text for encoding**: concatenation of the assistant's final summary turn + any user message starting with "decision:" or "let's" — the high-signal subset. If we can't identify high-signal turns, fall back to the last 2000 characters of the conversation.
- **excerpt**: auto-extracted — typically the first substantive user message of the session, truncated to 256 bytes.
- **unix_ns**: timestamp of the last turn of the session (when the session effectively "ended").

This keeps absorb's output compatible with everything else in the store.

---

## CLI SHAPE

```
leet absorb                            # absorb all sessions not yet in the store
leet absorb --since yesterday          # only sessions modified in the last day
leet absorb --since 2026-04-01         # since a specific date
leet absorb --dry-run                  # print what would be absorbed, don't write
leet absorb --project /path/to/other   # target a different project directory
leet absorb --force                    # re-absorb even if signatures match existing records
```

---

## FILE 1 — `leet-cli/src/cmd/absorb.rs` (new)

```rust
//! `leet absorb` — bulk-import Claude Code session history into .leet/store.bin.

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{anyhow, bail, Context, Result};
use clap::Args;
use serde::Deserialize;

// We reuse the store + encoding pipeline from leet-mcp. Rather than importing
// that crate (which would create a dependency cycle), we call the same public
// building blocks: leet_core (codec/types) and leet_bridge (projector).
//
// The store format is shared — see PROMPT_10b for the spec. We keep a
// minimal writer here that produces the same binary format.

use leet_core::codec::encode_cogon;
use leet_core::types::Cogon;
use leet_bridge::projector::project_text_simple;
use uuid::Uuid;

#[derive(Debug, Args)]
pub struct AbsorbArgs {
    /// Only absorb sessions modified on/after this date.
    /// Accepts: "yesterday", "last-week", or YYYY-MM-DD.
    #[arg(long)]
    pub since: Option<String>,

    /// Print what would be absorbed without writing anything.
    #[arg(long)]
    pub dry_run: bool,

    /// Path to the project directory (default: current directory).
    #[arg(long)]
    pub project: Option<PathBuf>,

    /// Re-absorb sessions even if an existing record shares the same timestamp.
    #[arg(long)]
    pub force: bool,
}

pub fn run(args: AbsorbArgs) -> Result<()> {
    let project_root = args
        .project
        .unwrap_or_else(|| std::env::current_dir().expect("cwd"))
        .canonicalize()
        .context("resolving project path")?;

    let claude_project_dir = find_claude_project_dir(&project_root)?
        .ok_or_else(|| anyhow!(
            "could not locate Claude Code project history for {}. \
             Has this project ever been opened in Claude Code?",
            project_root.display()
        ))?;

    println!("  · Project:          {}", project_root.display());
    println!("  · Claude history:   {}", claude_project_dir.display());

    let cutoff_ns = match args.since.as_deref() {
        Some(s) => Some(parse_since(s)?),
        None => None,
    };

    let sessions = discover_sessions(&claude_project_dir, cutoff_ns)?;
    if sessions.is_empty() {
        println!("  · Nothing to absorb.");
        return Ok(());
    }
    println!("  · Sessions found:   {}", sessions.len());

    // Load existing timestamps to skip duplicates (unless --force).
    let existing_stamps: std::collections::HashSet<i64> = if args.force {
        std::collections::HashSet::new()
    } else {
        load_existing_timestamps(&project_root)?
    };

    let mut absorbed = 0usize;
    let mut skipped = 0usize;

    for session in &sessions {
        if existing_stamps.contains(&session.unix_ns) {
            skipped += 1;
            continue;
        }

        let cogon = match project_text_simple(&session.signal_text) {
            Ok(c) => c,
            Err(e) => {
                tracing::warn!("skipping {}: embedding failed: {e}", session.path.display());
                continue;
            }
        };

        if args.dry_run {
            println!(
                "  [dry-run] would absorb: {} ({})",
                session.excerpt_short(),
                format_ts(session.unix_ns)
            );
        } else {
            append_record(
                &project_root,
                &cogon,
                &session.excerpt,
                session.unix_ns,
            )?;
        }
        absorbed += 1;
    }

    println!();
    if args.dry_run {
        println!("  · Would absorb:     {}", absorbed);
    } else {
        println!("  · Absorbed:         {}", absorbed);
    }
    println!("  · Skipped (dupes):  {}", skipped);
    Ok(())
}

// ─── Session discovery ───────────────────────────────────────────────────────

struct DiscoveredSession {
    path: PathBuf,
    signal_text: String,
    excerpt: String,
    unix_ns: i64,
}

impl DiscoveredSession {
    fn excerpt_short(&self) -> String {
        let e = &self.excerpt;
        if e.chars().count() <= 80 { e.clone() }
        else { format!("{}…", e.chars().take(79).collect::<String>()) }
    }
}

fn find_claude_project_dir(project_root: &Path) -> Result<Option<PathBuf>> {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .ok_or_else(|| anyhow!("HOME not set"))?;

    let projects_root = home.join(".claude/projects");
    if !projects_root.exists() {
        return Ok(None);
    }

    let project_abs = project_root
        .to_str()
        .ok_or_else(|| anyhow!("project path has non-UTF-8"))?;

    // Probe each subdirectory's metadata.json to find a matching project_path.
    for entry in std::fs::read_dir(&projects_root)? {
        let entry = entry?;
        if !entry.file_type()?.is_dir() { continue; }
        let meta_path = entry.path().join("metadata.json");
        if !meta_path.exists() { continue; }

        let text = match std::fs::read_to_string(&meta_path) {
            Ok(t) => t,
            Err(_) => continue,
        };
        let parsed: serde_json::Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(_) => continue,
        };
        let pp = parsed.get("project_path").and_then(|v| v.as_str()).unwrap_or("");
        if pp == project_abs {
            return Ok(Some(entry.path()));
        }
    }

    // Fallback: if the projects_root directory name contains a slug that
    // matches the basename, that's probably the one. (Older layouts.)
    let basename = project_root.file_name().and_then(|s| s.to_str()).unwrap_or("");
    if !basename.is_empty() {
        for entry in std::fs::read_dir(&projects_root)? {
            let entry = entry?;
            let name = entry.file_name().to_string_lossy().to_string();
            if name.contains(basename) {
                return Ok(Some(entry.path()));
            }
        }
    }

    Ok(None)
}

fn discover_sessions(
    claude_dir: &Path,
    cutoff_ns: Option<i64>,
) -> Result<Vec<DiscoveredSession>> {
    let mut out = Vec::new();

    // Prefer sessions.jsonl if present — it's the canonical format.
    let jsonl = claude_dir.join("sessions.jsonl");
    if jsonl.exists() {
        out.extend(read_sessions_jsonl(&jsonl, cutoff_ns)?);
    }

    // Fallback: rendered conversation_*.md files.
    for entry in std::fs::read_dir(claude_dir)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();
        if !name.starts_with("conversation_") || !name.ends_with(".md") { continue; }

        let meta = entry.metadata()?;
        let mtime = meta.modified()?.duration_since(UNIX_EPOCH).unwrap_or_default();
        let unix_ns = mtime.as_nanos() as i64;
        if let Some(cutoff) = cutoff_ns {
            if unix_ns < cutoff { continue; }
        }

        let text = std::fs::read_to_string(&path).unwrap_or_default();
        if text.is_empty() { continue; }

        let signal_text = extract_signal(&text);
        let excerpt = extract_excerpt(&text);

        out.push(DiscoveredSession { path, signal_text, excerpt, unix_ns });
    }

    Ok(out)
}

#[derive(Deserialize)]
struct JsonlTurn {
    #[serde(default)]
    role: String,
    #[serde(default)]
    content: String,
    #[serde(default)]
    timestamp: String,  // ISO 8601
    #[serde(default)]
    session_id: String,
}

fn read_sessions_jsonl(
    path: &Path,
    cutoff_ns: Option<i64>,
) -> Result<Vec<DiscoveredSession>> {
    let text = std::fs::read_to_string(path)?;

    // Group turns by session_id, keep the latest timestamp per session.
    use std::collections::BTreeMap;
    let mut by_session: BTreeMap<String, (Vec<JsonlTurn>, i64)> = BTreeMap::new();

    for line in text.lines() {
        if line.trim().is_empty() { continue; }
        let turn: JsonlTurn = match serde_json::from_str(line) {
            Ok(t) => t,
            Err(_) => continue,
        };
        let ns = iso_to_ns(&turn.timestamp).unwrap_or(0);
        let entry = by_session.entry(turn.session_id.clone()).or_default();
        entry.1 = entry.1.max(ns);
        entry.0.push(turn);
    }

    let mut out = Vec::new();
    for (sid, (turns, latest_ns)) in by_session {
        if sid.is_empty() { continue; }
        if let Some(cutoff) = cutoff_ns {
            if latest_ns < cutoff { continue; }
        }

        // Build signal_text and excerpt.
        let mut signal_parts = Vec::new();
        let mut first_user: Option<String> = None;

        for t in &turns {
            if first_user.is_none() && t.role == "user" && !t.content.trim().is_empty() {
                first_user = Some(t.content.clone());
            }
            if t.role == "user" {
                let lower = t.content.to_lowercase();
                if lower.contains("decision:")
                    || lower.starts_with("let's")
                    || lower.starts_with("vamos")
                {
                    signal_parts.push(t.content.clone());
                }
            }
            if t.role == "assistant" {
                // Last assistant turn is often a summary; keep the tail.
                signal_parts.push(t.content.clone());
            }
        }

        // If we got nothing signal-y, fall back to the last 2000 chars of everything.
        let signal_text = if signal_parts.is_empty() {
            let all: String = turns.iter().map(|t| t.content.as_str()).collect::<Vec<_>>().join("\n");
            tail_chars(&all, 2000)
        } else {
            let joined = signal_parts.join("\n\n");
            tail_chars(&joined, 4000)
        };

        let excerpt = first_user
            .map(|s| truncate(&s, 256))
            .unwrap_or_else(|| format!("Session {}", &sid[..sid.len().min(16)]));

        out.push(DiscoveredSession {
            path: path.to_path_buf(),
            signal_text,
            excerpt,
            unix_ns: latest_ns,
        });
    }

    Ok(out)
}

// ─── Signal extraction (markdown fallback) ───────────────────────────────────

fn extract_signal(text: &str) -> String {
    // Prefer assistant-final turn + user decisions.
    let mut out = Vec::new();
    let mut current_role = "";
    let mut current_buf = String::new();

    for line in text.lines() {
        let new_role = if line.starts_with("**User:**") || line.starts_with("## User") {
            Some("user")
        } else if line.starts_with("**Claude:**") || line.starts_with("## Claude") || line.starts_with("## Assistant") {
            Some("assistant")
        } else {
            None
        };

        if let Some(role) = new_role {
            if !current_buf.trim().is_empty() {
                if current_role == "user" {
                    let lower = current_buf.to_lowercase();
                    if lower.contains("decision:") || lower.contains("let's") || lower.contains("vamos") {
                        out.push(current_buf.clone());
                    }
                } else if current_role == "assistant" {
                    out.push(current_buf.clone());
                }
            }
            current_buf.clear();
            current_role = role;
        } else {
            current_buf.push_str(line);
            current_buf.push('\n');
        }
    }
    if !current_buf.trim().is_empty() && current_role == "assistant" {
        out.push(current_buf);
    }

    let joined = out.join("\n\n");
    if joined.trim().is_empty() {
        tail_chars(text, 2000)
    } else {
        tail_chars(&joined, 4000)
    }
}

fn extract_excerpt(text: &str) -> String {
    // First user line that has substance.
    for line in text.lines() {
        if line.starts_with("**User:**") || line.starts_with("## User") {
            // Next non-empty line(s) are the user's first message.
        }
    }
    // Simpler fallback: first 256 chars of any text.
    truncate(text.trim(), 256)
}

// ─── Writing to store ────────────────────────────────────────────────────────

/// Append one record to .leet/store.bin, matching the format from PROMPT_10b.
/// We don't import leet-mcp (would cycle) — instead we re-implement the thin
/// writer here. The format is fixed: 16-byte header on create, 360-byte records.
fn append_record(
    project_root: &Path,
    cogon: &Cogon,
    excerpt: &str,
    unix_ns: i64,
) -> Result<()> {
    use std::fs::OpenOptions;
    use std::io::Write;

    let leet_dir = project_root.join(".leet");
    std::fs::create_dir_all(&leet_dir)?;

    let gitignore = leet_dir.join(".gitignore");
    if !gitignore.exists() {
        std::fs::write(&gitignore,
            "# Auto-created by leet. Remove this line to commit the store.\nstore.bin\n")?;
    }

    let store_path = leet_dir.join("store.bin");
    let is_new = !store_path.exists();

    if is_new {
        // Write header.
        let mut header = [0u8; 16];
        header[0..4].copy_from_slice(b"LEET");
        header[4] = 0x01;
        std::fs::write(&store_path, &header)?;
    }

    // Build 360-byte record.
    let frame = encode_cogon(cogon);
    if frame.len() != 96 {
        bail!("encode_cogon returned {} bytes (expected 96)", frame.len());
    }

    let mut record = [0u8; 360];
    record[0..96].copy_from_slice(&frame);
    record[96..104].copy_from_slice(&unix_ns.to_le_bytes());

    let excerpt_bytes = truncate(excerpt, 256);
    let b = excerpt_bytes.as_bytes();
    record[104..104 + b.len().min(256)].copy_from_slice(&b[..b.len().min(256)]);

    let mut f = OpenOptions::new().append(true).open(&store_path)?;
    f.write_all(&record)?;
    f.sync_all()?;
    Ok(())
}

fn load_existing_timestamps(project_root: &Path) -> Result<std::collections::HashSet<i64>> {
    let mut out = std::collections::HashSet::new();
    let store_path = project_root.join(".leet/store.bin");
    if !store_path.exists() { return Ok(out); }

    let bytes = std::fs::read(&store_path)?;
    if bytes.len() < 16 { return Ok(out); }
    let body = &bytes[16..];
    for chunk in body.chunks_exact(360) {
        let mut ts = [0u8; 8];
        ts.copy_from_slice(&chunk[96..104]);
        out.insert(i64::from_le_bytes(ts));
    }
    Ok(out)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max { return s.to_string(); }
    let mut out: String = s.chars().take(max - 1).collect();
    out.push('…');
    out
}

fn tail_chars(s: &str, n: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() <= n { return s.to_string(); }
    chars[chars.len() - n..].iter().collect()
}

fn iso_to_ns(iso: &str) -> Option<i64> {
    // Minimal ISO 8601 parser — good enough for "YYYY-MM-DDTHH:MM:SS[.sss]Z".
    // Returns unix_ns or None if format unexpected.
    if iso.is_empty() { return None; }
    // We intentionally avoid pulling a chrono dep.
    // Accept: "YYYY-MM-DDTHH:MM:SSZ" primarily.
    let d = iso.get(0..10)?;
    let t = iso.get(11..19)?;
    let (year, month, day) = {
        let mut it = d.split('-');
        let y: i64 = it.next()?.parse().ok()?;
        let m: i64 = it.next()?.parse().ok()?;
        let d: i64 = it.next()?.parse().ok()?;
        (y, m, d)
    };
    let (hour, minute, sec) = {
        let mut it = t.split(':');
        let h: i64 = it.next()?.parse().ok()?;
        let m: i64 = it.next()?.parse().ok()?;
        let s: i64 = it.next()?.parse().ok()?;
        (h, m, s)
    };
    let days = civil_to_days(year as i32, month as u32, day as u32);
    let secs = days * 86400 + hour * 3600 + minute * 60 + sec;
    Some(secs * 1_000_000_000)
}

fn civil_to_days(y: i32, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y } as i64;
    let era = if y >= 0 { y / 400 } else { (y - 399) / 400 };
    let yoe = (y - era * 400) as i64;
    let mp = if m > 2 { m - 3 } else { m + 9 } as i64;
    let doy = (153 * mp + 2) / 5 + d as i64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

fn parse_since(s: &str) -> Result<i64> {
    let now_ns = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as i64)
        .unwrap_or(0);

    match s {
        "yesterday" => Ok(now_ns - 24 * 60 * 60 * 1_000_000_000),
        "last-week" | "lastweek" => Ok(now_ns - 7 * 24 * 60 * 60 * 1_000_000_000),
        other => {
            // Try YYYY-MM-DD.
            if other.len() == 10 && &other[4..5] == "-" && &other[7..8] == "-" {
                let iso = format!("{other}T00:00:00Z");
                iso_to_ns(&iso).ok_or_else(|| anyhow!("cannot parse date: {other}"))
            } else {
                bail!("--since must be `yesterday`, `last-week`, or YYYY-MM-DD (got: {other})")
            }
        }
    }
}

fn format_ts(unix_ns: i64) -> String {
    let secs = unix_ns / 1_000_000_000;
    let days = secs / 86400;
    let rem = secs % 86400;
    let (y, m, d) = civil_from_days(days);
    format!("{y:04}-{m:02}-{d:02} {:02}:{:02}", rem / 3600, (rem % 3600) / 60)
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

// ─── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn truncate_ascii() {
        assert_eq!(truncate("hello world", 5), "hell…");
        assert_eq!(truncate("short", 20), "short");
    }

    #[test]
    fn tail_chars_basic() {
        let s = "abcdefghij";
        assert_eq!(tail_chars(s, 3), "hij");
        assert_eq!(tail_chars(s, 100), s);
    }

    #[test]
    fn iso_to_ns_basic() {
        let ns = iso_to_ns("2026-01-01T00:00:00Z").unwrap();
        // 2026-01-01 00:00 UTC
        assert_eq!(ns / 1_000_000_000, 1767225600);
    }

    #[test]
    fn parse_since_yesterday() {
        let a = parse_since("yesterday").unwrap();
        let b = parse_since("yesterday").unwrap();
        assert!((a - b).abs() < 1_000_000_000);
    }

    #[test]
    fn parse_since_date() {
        let ns = parse_since("2026-01-01").unwrap();
        assert_eq!(ns / 1_000_000_000, 1767225600);
    }

    #[test]
    fn parse_since_bad_format() {
        assert!(parse_since("tomorrow").is_err());
        assert!(parse_since("2026/01/01").is_err());
    }

    #[test]
    fn append_record_creates_header_on_first_write() {
        let tmp = tempfile::tempdir().unwrap();
        let cogon = Cogon { id: Uuid::new_v4(), sem: [0.5; 32], stamp: 0, raw: None };
        append_record(tmp.path(), &cogon, "test excerpt", 1_000_000_000).unwrap();

        let data = std::fs::read(tmp.path().join(".leet/store.bin")).unwrap();
        assert_eq!(&data[0..4], b"LEET");
        assert_eq!(data[4], 0x01);
        assert_eq!(data.len(), 16 + 360);
    }

    #[test]
    fn append_record_dedup_via_timestamps() {
        let tmp = tempfile::tempdir().unwrap();
        let cogon = Cogon { id: Uuid::new_v4(), sem: [0.5; 32], stamp: 0, raw: None };
        append_record(tmp.path(), &cogon, "first", 111).unwrap();
        append_record(tmp.path(), &cogon, "second", 222).unwrap();

        let seen = load_existing_timestamps(tmp.path()).unwrap();
        assert!(seen.contains(&111));
        assert!(seen.contains(&222));
    }
}
```

---

## FILE 2 — `leet-cli/src/cmd/mod.rs` (register absorb)

Add:

```rust
pub mod absorb;

// In the Command enum:
/// Bulk-import Claude Code's past session history into the project's .leet store.
Absorb(cmd::absorb::AbsorbArgs),

// In the dispatcher:
Command::Absorb(args) => cmd::absorb::run(args),
```

---

## FILE 3 — no Cargo.toml changes

Existing deps are sufficient: `anyhow`, `serde`, `serde_json`, `clap`, `uuid`, `tempfile` (dev).

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-cli absorb

# Manual smoke (dry-run in a real project)
cd /path/to/any-claude-code-project
cargo run -p leet-cli -- absorb --dry-run
# Expected: prints discovered sessions, "would absorb: N"

# Real run
cargo run -p leet-cli -- absorb --since yesterday
ls -la .leet/store.bin
# File grew by N * 360 bytes.

# Idempotency (re-run same command)
cargo run -p leet-cli -- absorb --since yesterday
# Expected: "Skipped (dupes): N" for every session already absorbed.

# Force re-absorb
cargo run -p leet-cli -- absorb --since yesterday --force
# Expected: records duplicated (intended behavior under --force).
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt10e "leet absorb: bulk-import Claude Code session history as safety net"
# work
task project:1337 +prompt10e done

git add leet-cli/src/cmd/absorb.rs leet-cli/src/cmd/mod.rs
git commit -m "feat(cli): leet absorb — import past Claude Code sessions into .leet/store.bin

Safety-net command for users who install leet after accumulating
Claude Code history, or who want to recover sessions where
leet_remember wasn't called automatically.

Flags:
  --since {yesterday|last-week|YYYY-MM-DD}   time filter
  --dry-run                                  preview without writing
  --project /path                            target a different project
  --force                                    re-absorb even if duplicate timestamps

Discovery:
- Probes ~/.claude/projects/<hash>/ matching current project via
  metadata.json project_path field, with slug/basename fallback.
- Reads sessions.jsonl (canonical) or conversation_*.md (fallback).
- Groups turns by session_id; one COGON per session.

Signal extraction: assistant-final turn + user messages starting with
'decision:', 'let's', 'vamos'. Falls back to tail-2000-chars when no
signal markers found. Excerpt = first substantive user message (≤256B).

Dedup via timestamp match against existing store records.
Writes directly in PROMPT_10b binary format (no cycle with leet-mcp).

Part of Claude Code integration, sub-prompt 10e."
git push origin main
```

---

**END OF PROMPT_10e**
