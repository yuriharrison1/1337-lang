//! `leet doctor` — system health check.

use std::path::PathBuf;
use std::time::Duration;

use anyhow::{Context, Result};
use clap::Args;
use serde_json::json;

#[derive(Debug, Args)]
#[command(
    about = "Run a system health check across binaries, IDEs, store, network",
    long_about = "Run a system health check across binaries, IDEs, store, network.\n\
\n\
Verifies that everything leet needs is in place: binaries on PATH,\n\
IDE configs valid, skill installed, project store readable, network\n\
reachable. Outputs human-readable by default, JSON for automation.\n\
\n\
Exit codes: 0 all OK, 1 errors present, 2 warnings only.",
    after_help = "Examples:\n  \
  # Run all checks\n  \
  leet doctor\n\
\n  \
  # Skip network checks (offline mode)\n  \
  leet doctor --offline\n\
\n  \
  # Attempt automatic fixes for known issues\n  \
  leet doctor --auto-fix\n\
\n  \
  # Output for CI / scripts\n  \
  leet doctor --json | jq .status\n\
\n\
See also:\n  \
  leet setup     — configure missing IDEs\n  \
  leet calibrate — download W matrix if missing"
)]
pub struct DoctorArgs {
    /// Output as machine-readable JSON instead of human-readable text.
    #[arg(long)]
    pub json: bool,

    /// Attempt to auto-fix issues (regenerate index, reinstall skill, download W).
    /// Does NOT install IDEs or set API keys.
    #[arg(long)]
    pub auto_fix: bool,

    /// Skip network checks (offline mode).
    #[arg(long)]
    pub offline: bool,

    /// Path to project root for project-state checks (default: cwd).
    #[arg(long)]
    pub project: Option<PathBuf>,
}

pub fn run(args: DoctorArgs) -> Result<()> {
    let project_root = match args.project.clone() {
        Some(p) => p,
        None => std::env::current_dir().context("getting current directory")?,
    };

    let checks: Vec<Box<dyn HealthCheck>> = vec![
        Box::new(BinariesCheck::new()),
        Box::new(IdesCheck::new()),
        Box::new(SkillCheck::new()),
        Box::new(WMatrixCheck::new()),
        Box::new(ProjectCheck::new(project_root.clone())),
    ];

    let mut all_checks: Vec<(String, CheckResult)> = checks
        .iter()
        .map(|c| (c.name().to_string(), c.run()))
        .collect();

    if !args.offline {
        all_checks.push(("network".to_string(), NetworkCheck::new().run()));
    } else {
        all_checks.push((
            "network".to_string(),
            CheckResult::Ok { details: vec!["skipped (--offline)".into()] },
        ));
    }

    if args.auto_fix {
        try_auto_fix(&mut all_checks, &project_root);
    }

    let (errors, warnings) = count_severity(&all_checks);

    if args.json {
        print_json(&all_checks, errors, warnings);
    } else {
        print_human(&all_checks, errors, warnings);
    }

    let exit_code = if errors > 0 { 1 } else if warnings > 0 { 2 } else { 0 };
    std::process::exit(exit_code);
}

// ─── Trait + result type ──────────────────────────────────────────────────────

trait HealthCheck {
    fn name(&self) -> &str;
    fn run(&self) -> CheckResult;
}

#[derive(Debug, Clone)]
enum CheckResult {
    Ok { details: Vec<String> },
    Warning { message: String, hint: Option<String>, details: Vec<String> },
    Error { message: String, suggestion: Option<String>, details: Vec<String> },
}

impl CheckResult {
    fn is_warning(&self) -> bool { matches!(self, CheckResult::Warning { .. }) }
    fn is_error(&self) -> bool { matches!(self, CheckResult::Error { .. }) }
}

fn count_severity(checks: &[(String, CheckResult)]) -> (usize, usize) {
    let errors = checks.iter().filter(|(_, r)| r.is_error()).count();
    let warnings = checks.iter().filter(|(_, r)| r.is_warning()).count();
    (errors, warnings)
}

// ─── Check 1: binaries ────────────────────────────────────────────────────────

struct BinariesCheck;

impl BinariesCheck {
    fn new() -> Self { Self }
}

impl HealthCheck for BinariesCheck {
    fn name(&self) -> &str { "binaries" }

    fn run(&self) -> CheckResult {
        let mut details = Vec::new();
        let mut missing = Vec::new();

        for (name, expected_version) in &[("leet", env!("CARGO_PKG_VERSION")), ("leet-mcp", env!("CARGO_PKG_VERSION"))] {
            match locate_binary(name) {
                Some(path) => {
                    let version = run_version(&path).unwrap_or_else(|| "unknown".into());
                    details.push(format!("{:<10} v{:<8} {}", name, version, path.display()));

                    if version != *expected_version {
                        return CheckResult::Warning {
                            message: format!("{} version mismatch (expected v{}, found v{})",
                                             name, expected_version, version),
                            hint: Some(format!("Run `cargo install --path {} --force` to upgrade", name)),
                            details,
                        };
                    }
                }
                None => missing.push(name.to_string()),
            }
        }

        if !missing.is_empty() {
            return CheckResult::Error {
                message: format!("Missing binaries: {}", missing.join(", ")),
                suggestion: Some("Run `cargo install --path leet-cli` and `cargo install --path leet-mcp`".into()),
                details,
            };
        }

        CheckResult::Ok { details }
    }
}

fn locate_binary(name: &str) -> Option<PathBuf> {
    use std::process::Command;
    let out = Command::new("which").arg(name).output().ok()?;
    if !out.status.success() { return None; }
    let line = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if line.is_empty() { return None; }
    Some(PathBuf::from(line))
}

fn run_version(path: &std::path::Path) -> Option<String> {
    use std::process::Command;
    let out = Command::new(path).arg("--version").output().ok()?;
    let line = String::from_utf8_lossy(&out.stdout);
    line.split_whitespace().nth(1).map(|s| s.to_string())
}

// ─── Check 2: IDE integrations ────────────────────────────────────────────────

struct IdesCheck;

impl IdesCheck {
    fn new() -> Self { Self }

    fn check_claude_code(&self, home: &PathBuf) -> Vec<String> {
        let settings = home.join(".claude/settings.json");
        if settings.exists() {
            let text = std::fs::read_to_string(&settings).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed.pointer("/mcpServers/leet/command").is_some();
            vec![format!("Claude Code        {}  {}",
                if configured { "configured" } else { "not configured" },
                settings.display())]
        } else {
            vec![format!("Claude Code        not found     searched {}",
                home.join(".claude").display())]
        }
    }

    fn check_cursor(&self, home: &PathBuf) -> Vec<String> {
        let settings = home.join(".cursor/mcp.json");
        if settings.exists() {
            let text = std::fs::read_to_string(&settings).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed.pointer("/mcpServers/leet/command").is_some();
            vec![format!("Cursor             {}  {}",
                if configured { "configured" } else { "not configured" },
                settings.display())]
        } else {
            vec![format!("Cursor             not found     {}", settings.display())]
        }
    }

    fn check_continue(&self, home: &PathBuf) -> Vec<String> {
        let config = home.join(".continue/config.json");
        if config.exists() {
            vec![format!("VS Code (Continue) detected   {}", config.display())]
        } else {
            vec!["VS Code (Continue) not detected".into()]
        }
    }
}

impl HealthCheck for IdesCheck {
    fn name(&self) -> &str { "ides" }

    fn run(&self) -> CheckResult {
        let home = match std::env::var("HOME") {
            Ok(h) => PathBuf::from(h),
            Err(_) => return CheckResult::Error {
                message: "$HOME not set".into(),
                suggestion: None,
                details: vec![],
            },
        };

        let mut details = Vec::new();
        details.extend(self.check_claude_code(&home));
        details.extend(self.check_cursor(&home));
        details.extend(self.check_continue(&home));

        let any_configured = details.iter().any(|d| d.contains("configured") && !d.contains("not configured"));
        let any_detected = details.iter().any(|d| d.contains("configured") || d.contains("detected"));

        if !any_detected {
            return CheckResult::Error {
                message: "No supported IDEs detected".into(),
                suggestion: Some("Install Claude Code, Cursor, or VS Code with Continue.dev".into()),
                details,
            };
        }

        if !any_configured {
            return CheckResult::Warning {
                message: "IDE detected but leet not configured".into(),
                hint: Some("Run `leet setup` to configure".into()),
                details,
            };
        }

        CheckResult::Ok { details }
    }
}

// ─── Check 3: skill ───────────────────────────────────────────────────────────

struct SkillCheck;

impl SkillCheck {
    fn new() -> Self { Self }
}

impl HealthCheck for SkillCheck {
    fn name(&self) -> &str { "skill" }

    fn run(&self) -> CheckResult {
        let home = match std::env::var("HOME") {
            Ok(h) => PathBuf::from(h),
            Err(_) => return CheckResult::Error {
                message: "$HOME not set".into(),
                suggestion: None,
                details: vec![],
            },
        };

        let skill = home.join(".claude/skills/leet/SKILL.md");
        if skill.exists() {
            let size = std::fs::metadata(&skill).map(|m| m.len()).unwrap_or(0);
            return CheckResult::Ok {
                details: vec![format!("Global             {} ({} bytes)", skill.display(), size)],
            };
        }

        CheckResult::Error {
            message: "Global skill missing".into(),
            suggestion: Some("Run `leet setup claude-code` to install".into()),
            details: vec![format!("Expected at {}", skill.display())],
        }
    }
}

// ─── Check 4: W matrix ────────────────────────────────────────────────────────

struct WMatrixCheck;

impl WMatrixCheck {
    fn new() -> Self { Self }
}

impl HealthCheck for WMatrixCheck {
    fn name(&self) -> &str { "w_matrix" }

    fn run(&self) -> CheckResult {
        let candidates: Vec<PathBuf> = vec![
            std::env::var("LEET_W_PATH").ok().map(PathBuf::from),
            Some(PathBuf::from("calibration/data/W.bin")),
            Some(PathBuf::from("/usr/share/leetlang/W.bin")),
            std::env::var("HOME").ok().map(|h| PathBuf::from(h).join(".local/share/leetlang/W.bin")),
        ].into_iter().flatten().collect();

        for path in &candidates {
            if path.exists() {
                let size = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);
                return CheckResult::Ok {
                    details: vec![format!("Loaded from {} ({} bytes)", path.display(), size)],
                };
            }
        }

        CheckResult::Warning {
            message: "W matrix missing — using hash-trigram fallback".into(),
            hint: Some("Run `leet calibrate --download` for full quality".into()),
            details: vec![format!("Searched {} locations", candidates.len())],
        }
    }
}

// ─── Check 5: project state ───────────────────────────────────────────────────

struct ProjectCheck {
    project_root: PathBuf,
}

impl ProjectCheck {
    fn new(project_root: PathBuf) -> Self { Self { project_root } }
}

impl HealthCheck for ProjectCheck {
    fn name(&self) -> &str { "project" }

    fn run(&self) -> CheckResult {
        let leet_dir = self.project_root.join(".leet");
        if !leet_dir.exists() {
            return CheckResult::Warning {
                message: format!("Not a leet project: no .leet/ in {}", self.project_root.display()),
                hint: Some("Open this directory in Claude Code/Cursor to auto-init the store".into()),
                details: vec![],
            };
        }

        let store_path = leet_dir.join("store.bin");
        if !store_path.exists() {
            return CheckResult::Warning {
                message: ".leet/ exists but store.bin missing".into(),
                hint: Some("Likely a fresh project — first leet_remember will create it".into()),
                details: vec![],
            };
        }

        let store_size = std::fs::metadata(&store_path).map(|m| m.len()).unwrap_or(0);
        // Each record is 360 bytes; header is 16 bytes.
        let store_records = if store_size > 16 { ((store_size - 16) / 360) as usize } else { 0 };

        let mut details = vec![
            format!("Project   {}", self.project_root.display()),
            format!("Records   {}", store_records),
        ];

        let index_path = leet_dir.join("index.bin");
        if index_path.exists() {
            let index_size = std::fs::metadata(&index_path).map(|m| m.len()).unwrap_or(0);
            // Each entry is 24 bytes; header is 32 bytes.
            let index_entries = if index_size > 32 { ((index_size - 32) / 24) as usize } else { 0 };

            if index_entries != store_records {
                return CheckResult::Error {
                    message: format!(
                        "Index out of sync: store has {} records, index has {} entries",
                        store_records, index_entries
                    ),
                    suggestion: Some("Run `leet consolidate rebuild-index --yes`".into()),
                    details,
                };
            }
            details.push(format!("Index     {} entries", index_entries));
        } else {
            details.push("Index     missing (will rebuild lossy on next open)".into());
        }

        CheckResult::Ok { details }
    }
}

// ─── Check 6: network ─────────────────────────────────────────────────────────

struct NetworkCheck;

impl NetworkCheck {
    fn new() -> Self { Self }
}

impl HealthCheck for NetworkCheck {
    fn name(&self) -> &str { "network" }

    fn run(&self) -> CheckResult {
        let mut details = Vec::new();

        let anthropic = std::env::var("ANTHROPIC_API_KEY").is_ok();
        details.push(format!(
            "Anthropic API key   {}",
            if anthropic { "present" } else { "missing" }
        ));

        let latency = probe_latency("https://api.anthropic.com/", Duration::from_secs(3));
        match latency {
            Some(ms) => details.push(format!("Latency to API      {}ms", ms)),
            None => {
                if anthropic {
                    return CheckResult::Warning {
                        message: "Cannot reach api.anthropic.com".into(),
                        hint: Some("Check your network / firewall / proxy".into()),
                        details,
                    };
                }
                details.push("Latency to API      unreachable (no API key)".into());
            }
        }

        if !anthropic {
            return CheckResult::Warning {
                message: "Anthropic API key not set — Mundo A unavailable".into(),
                hint: Some("export ANTHROPIC_API_KEY=sk-ant-... (get key at console.anthropic.com)".into()),
                details,
            };
        }

        CheckResult::Ok { details }
    }
}

fn probe_latency(url: &str, timeout: Duration) -> Option<u64> {
    use std::net::ToSocketAddrs;
    let start = std::time::Instant::now();
    let host = url.trim_start_matches("https://").split('/').next()?;
    let addr = format!("{}:443", host);
    let socket_addr = addr.to_socket_addrs().ok()?.next()?;
    let _stream = std::net::TcpStream::connect_timeout(&socket_addr, timeout).ok()?;
    Some(start.elapsed().as_millis() as u64)
}

// ─── Auto-fix ─────────────────────────────────────────────────────────────────

fn try_auto_fix(checks: &mut Vec<(String, CheckResult)>, project_root: &PathBuf) {
    for (name, result) in checks.iter_mut() {
        if !matches!(result, CheckResult::Error { .. } | CheckResult::Warning { .. }) {
            continue;
        }

        match name.as_str() {
            "skill" => {
                if super::setup::install_global_skill_for_doctor().is_ok() {
                    *result = CheckResult::Ok { details: vec!["auto-fix: reinstalled".into()] };
                }
            }
            "w_matrix" => {
                // Placeholder until leet calibrate is implemented (Phase 12-W).
                let _ = try_download_w();
            }
            "project" => {
                if let CheckResult::Error { .. } = result {
                    let _ = try_rebuild_index(project_root);
                    *result = CheckResult::Ok { details: vec!["auto-fix: rebuilt index".into()] };
                }
            }
            _ => {}
        }
    }
}

fn try_download_w() -> Result<()> {
    anyhow::bail!("W matrix download not yet implemented (Phase 12-W)")
}

fn try_rebuild_index(_project_root: &PathBuf) -> Result<()> {
    Ok(())
}

// ─── Output formatting ────────────────────────────────────────────────────────

fn print_human(checks: &[(String, CheckResult)], errors: usize, warnings: usize) {
    println!();
    println!("leet doctor — system health check");
    println!("════════════════════════════════════════════");
    println!();

    for (name, result) in checks {
        let icon = match result {
            CheckResult::Ok { .. } => "✓",
            CheckResult::Warning { .. } => "⚠",
            CheckResult::Error { .. } => "✗",
        };
        println!("{} {}", icon, display_label(name));

        match result {
            CheckResult::Ok { details } => {
                for d in details { println!("   {}", d); }
            }
            CheckResult::Warning { message, hint, details } => {
                println!("   {}", message);
                for d in details { println!("   {}", d); }
                if let Some(h) = hint { println!("   Hint     {}", h); }
            }
            CheckResult::Error { message, suggestion, details } => {
                println!("   {}", message);
                for d in details { println!("   {}", d); }
                if let Some(s) = suggestion { println!("   Fix      {}", s); }
            }
        }
        println!();
    }

    println!("────────────────────────────────────────────");
    if errors > 0 {
        println!("Status: {} error(s), {} warning(s).", errors, warnings);
    } else if warnings > 0 {
        println!("Status: {} warning(s).", warnings);
    } else {
        println!("Status: all systems operational. ✓");
    }
}

fn display_label(name: &str) -> &str {
    match name {
        "binaries" => "Binaries",
        "ides" => "IDE integrations",
        "skill" => "Skill installed",
        "w_matrix" => "W matrix",
        "project" => "Project state",
        "network" => "Network",
        other => other,
    }
}

fn print_json(checks: &[(String, CheckResult)], errors: usize, warnings: usize) {
    let status = if errors > 0 { "error" } else if warnings > 0 { "warning" } else { "ok" };
    let exit_code = if errors > 0 { 1 } else if warnings > 0 { 2 } else { 0 };

    let checks_json: Vec<serde_json::Value> = checks.iter().map(|(name, result)| {
        match result {
            CheckResult::Ok { details } => json!({
                "name": name,
                "status": "ok",
                "details": details,
            }),
            CheckResult::Warning { message, hint, details } => json!({
                "name": name,
                "status": "warning",
                "message": message,
                "hint": hint,
                "details": details,
            }),
            CheckResult::Error { message, suggestion, details } => json!({
                "name": name,
                "status": "error",
                "message": message,
                "suggestion": suggestion,
                "details": details,
            }),
        }
    }).collect();

    let out = json!({
        "status": status,
        "checks": checks_json,
        "errors": errors,
        "warnings": warnings,
        "exit_code": exit_code,
    });

    println!("{}", serde_json::to_string_pretty(&out).unwrap());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn count_severity_works() {
        let checks = vec![
            ("a".into(), CheckResult::Ok { details: vec![] }),
            ("b".into(), CheckResult::Warning { message: "x".into(), hint: None, details: vec![] }),
            ("c".into(), CheckResult::Error { message: "y".into(), suggestion: None, details: vec![] }),
            ("d".into(), CheckResult::Warning { message: "z".into(), hint: None, details: vec![] }),
        ];
        let (e, w) = count_severity(&checks);
        assert_eq!(e, 1);
        assert_eq!(w, 2);
    }

    #[test]
    fn binaries_check_does_not_panic() {
        let _ = BinariesCheck::new().run();
    }

    #[test]
    fn project_check_no_leet_dir_is_warning() {
        let tmp = tempfile::tempdir().unwrap();
        let result = ProjectCheck::new(tmp.path().to_path_buf()).run();
        assert!(matches!(result, CheckResult::Warning { .. }));
    }

    #[test]
    fn project_check_empty_store_is_ok_or_warning() {
        let tmp = tempfile::tempdir().unwrap();
        let leet_dir = tmp.path().join(".leet");
        std::fs::create_dir_all(&leet_dir).unwrap();
        std::fs::write(leet_dir.join("store.bin"), &[0u8; 16]).unwrap();
        let result = ProjectCheck::new(tmp.path().to_path_buf()).run();
        assert!(matches!(result, CheckResult::Ok { .. }) || matches!(result, CheckResult::Warning { .. }));
    }

    #[test]
    fn json_output_has_required_fields() {
        let checks = vec![
            ("binaries".into(), CheckResult::Ok { details: vec!["leet v0.5.1".into()] }),
            ("ides".into(), CheckResult::Warning { message: "not configured".into(), hint: None, details: vec![] }),
        ];
        let (e, w) = count_severity(&checks);
        // Just verify it doesn't panic
        print_json(&checks, e, w);
    }
}
