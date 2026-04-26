//! `leet absorb` — bulk-import Claude Code session history into .leet/store.bin.

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use anyhow::{anyhow, bail, Context, Result};
use clap::Args;
use serde::Deserialize;

use leet_core::codec::encode_cogon;
use leet_core::types::Cogon;
use leet_bridge::projector::project_text_simple;

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

    let claude_project_dir = find_claude_project_dir(&project_root)?.ok_or_else(|| {
        anyhow!(
            "could not locate Claude Code project history for {}. \
             Has this project ever been opened in Claude Code?",
            project_root.display()
        )
    })?;

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
                eprintln!("  ! skipping {}: embedding failed: {e}", session.path.display());
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
            append_record(&project_root, &cogon, &session.excerpt, session.unix_ns)?;
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
        if e.chars().count() <= 80 {
            e.clone()
        } else {
            format!("{}…", e.chars().take(79).collect::<String>())
        }
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

    // Probe metadata.json for a matching project_path.
    for entry in std::fs::read_dir(&projects_root)? {
        let entry = entry?;
        if !entry.file_type()?.is_dir() {
            continue;
        }
        let meta_path = entry.path().join("metadata.json");
        if !meta_path.exists() {
            continue;
        }
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

    // Fallback: directory name contains the project basename.
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

    // Prefer sessions.jsonl (canonical format).
    let jsonl = claude_dir.join("sessions.jsonl");
    if jsonl.exists() {
        out.extend(read_sessions_jsonl(&jsonl, cutoff_ns)?);
    }

    // Fallback: rendered conversation_*.md files.
    if let Ok(entries) = std::fs::read_dir(claude_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().to_string();
            if !name.starts_with("conversation_") || !name.ends_with(".md") {
                continue;
            }
            let meta = entry.metadata()?;
            let mtime = meta.modified()?.duration_since(UNIX_EPOCH).unwrap_or_default();
            let unix_ns = mtime.as_nanos() as i64;
            if let Some(cutoff) = cutoff_ns {
                if unix_ns < cutoff {
                    continue;
                }
            }
            let text = std::fs::read_to_string(&path).unwrap_or_default();
            if text.is_empty() {
                continue;
            }
            out.push(DiscoveredSession {
                path,
                signal_text: extract_signal(&text),
                excerpt: extract_excerpt(&text),
                unix_ns,
            });
        }
    }

    Ok(out)
}

#[derive(Deserialize)]
struct JsonlTurn {
    #[serde(default)]
    role: String,
    #[serde(default)]
    content: serde_json::Value,
    #[serde(default)]
    timestamp: String,
    #[serde(default)]
    session_id: String,
}

fn turn_content_text(content: &serde_json::Value) -> String {
    match content {
        serde_json::Value::String(s) => s.clone(),
        serde_json::Value::Array(arr) => arr
            .iter()
            .filter_map(|item| item.get("text").and_then(|t| t.as_str()).map(str::to_string))
            .collect::<Vec<_>>()
            .join(" "),
        _ => String::new(),
    }
}

fn read_sessions_jsonl(
    path: &Path,
    cutoff_ns: Option<i64>,
) -> Result<Vec<DiscoveredSession>> {
    let text = std::fs::read_to_string(path)?;

    use std::collections::BTreeMap;
    // session_id → (turns, latest_ns)
    let mut by_session: BTreeMap<String, (Vec<(String, String)>, i64)> = BTreeMap::new();

    for line in text.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let turn: JsonlTurn = match serde_json::from_str(line) {
            Ok(t) => t,
            Err(_) => continue,
        };
        let content_text = turn_content_text(&turn.content);
        let ns = iso_to_ns(&turn.timestamp).unwrap_or(0);
        let entry = by_session.entry(turn.session_id.clone()).or_default();
        entry.1 = entry.1.max(ns);
        entry.0.push((turn.role, content_text));
    }

    let mut out = Vec::new();
    for (sid, (turns, latest_ns)) in by_session {
        if sid.is_empty() {
            continue;
        }
        if let Some(cutoff) = cutoff_ns {
            if latest_ns < cutoff {
                continue;
            }
        }

        let mut signal_parts = Vec::new();
        let mut first_user: Option<String> = None;

        for (role, content) in &turns {
            if first_user.is_none() && role == "user" && !content.trim().is_empty() {
                first_user = Some(content.clone());
            }
            if role == "user" {
                let lower = content.to_lowercase();
                if lower.contains("decision:")
                    || lower.starts_with("let's")
                    || lower.starts_with("vamos")
                {
                    signal_parts.push(content.clone());
                }
            }
            if role == "assistant" {
                signal_parts.push(content.clone());
            }
        }

        let signal_text = if signal_parts.is_empty() {
            let all: String = turns.iter().map(|(_, c)| c.as_str()).collect::<Vec<_>>().join("\n");
            tail_chars(&all, 2000)
        } else {
            tail_chars(&signal_parts.join("\n\n"), 4000)
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
    let mut out = Vec::new();
    let mut current_role = "";
    let mut current_buf = String::new();

    for line in text.lines() {
        let new_role = if line.starts_with("**User:**") || line.starts_with("## User") {
            Some("user")
        } else if line.starts_with("**Claude:**")
            || line.starts_with("## Claude")
            || line.starts_with("## Assistant")
        {
            Some("assistant")
        } else {
            None
        };

        if let Some(role) = new_role {
            if !current_buf.trim().is_empty() {
                if current_role == "user" {
                    let lower = current_buf.to_lowercase();
                    if lower.contains("decision:")
                        || lower.contains("let's")
                        || lower.contains("vamos")
                    {
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
    truncate(text.trim(), 256)
}

// ─── Writing to store ────────────────────────────────────────────────────────

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
        std::fs::write(
            &gitignore,
            "# Auto-created by leet. Remove this line to commit the store.\nstore.bin\n",
        )?;
    }

    let store_path = leet_dir.join("store.bin");
    let is_new = !store_path.exists();

    if is_new {
        let mut header = [0u8; 16];
        header[0..4].copy_from_slice(b"LEET");
        header[4] = 0x01;
        std::fs::write(&store_path, &header)?;
    }

    let frame = encode_cogon(cogon);
    if frame.len() != 96 {
        bail!("encode_cogon returned {} bytes (expected 96)", frame.len());
    }

    let mut record = [0u8; 360];
    record[0..96].copy_from_slice(&frame);
    record[96..104].copy_from_slice(&unix_ns.to_le_bytes());

    let excerpt_bytes = excerpt.as_bytes();
    let len = excerpt_bytes.len().min(256);
    record[104..104 + len].copy_from_slice(&excerpt_bytes[..len]);

    let mut f = OpenOptions::new().append(true).open(&store_path)?;
    f.write_all(&record)?;
    f.sync_all()?;
    Ok(())
}

fn load_existing_timestamps(project_root: &Path) -> Result<std::collections::HashSet<i64>> {
    let mut out = std::collections::HashSet::new();
    let store_path = project_root.join(".leet/store.bin");
    if !store_path.exists() {
        return Ok(out);
    }
    let bytes = std::fs::read(&store_path)?;
    if bytes.len() < 16 {
        return Ok(out);
    }
    for chunk in bytes[16..].chunks_exact(360) {
        let mut ts = [0u8; 8];
        ts.copy_from_slice(&chunk[96..104]);
        out.insert(i64::from_le_bytes(ts));
    }
    Ok(out)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        return s.to_string();
    }
    let mut out: String = s.chars().take(max - 1).collect();
    out.push('…');
    out
}

fn tail_chars(s: &str, n: usize) -> String {
    let chars: Vec<char> = s.chars().collect();
    if chars.len() <= n {
        return s.to_string();
    }
    chars[chars.len() - n..].iter().collect()
}

fn iso_to_ns(iso: &str) -> Option<i64> {
    if iso.is_empty() {
        return None;
    }
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
    let yoe = y - era * 400;
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
            if other.len() == 10 && other.as_bytes().get(4) == Some(&b'-') && other.as_bytes().get(7) == Some(&b'-') {
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
    use uuid::Uuid;

    #[test]
    fn truncate_ascii() {
        assert_eq!(truncate("hello world", 5), "hell…");
        assert_eq!(truncate("short", 20), "short");
    }

    #[test]
    fn tail_chars_basic() {
        assert_eq!(tail_chars("abcdefghij", 3), "hij");
        assert_eq!(tail_chars("abcdefghij", 100), "abcdefghij");
    }

    #[test]
    fn iso_to_ns_basic() {
        let ns = iso_to_ns("2026-01-01T00:00:00Z").unwrap();
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
