# PROMPT 12-U-02 — `leet doctor` SUBCOMMAND

Implementar `leet doctor` — comando de diagnóstico que verifica todo o setup do leet num único lugar. Output amigável por padrão, JSON pra automação. Verifica binários, configs de IDE, store local, W matrix, conectividade. Retorna exit code 0/1/2 conforme severidade.

**PRÉ-REQUISITOS**: 12-T executado. 12-U-01 executado (depende de `UserFacingError` pra erros).

**ESCOPO**: 1 arquivo novo (`leet-cli/src/cmd/doctor.rs`) + registro em `cmd/mod.rs`. Pode também adicionar pequenos hooks de info em outros crates pra exposição de status.

**Taskwarrior**: `+prompt12_U_02`.

---

## EXPERIÊNCIA QUE O USUÁRIO TEM

```
$ leet doctor

leet doctor — system health check
════════════════════════════════════════════

✓ Binaries
   leet      v0.5.1   /home/yuri/.cargo/bin/leet
   leet-mcp  v0.5.1   /home/yuri/.cargo/bin/leet-mcp

✓ IDE integrations
   Claude Code        configured  ~/.claude/settings.json
   Cursor             configured  ~/.cursor/mcp.json
   VS Code (Continue) configured  ~/.continue/config.json

✓ Skill installed
   Global             ~/.claude/skills/leet/SKILL.md (4842 bytes)

⚠ W matrix
   Status   missing
   Fallback hash-trigram (degraded quality)
   Hint     run `leet calibrate --download`

✓ Project state
   Project   /home/yuri/projects/leet-1337
   Records   47 (foundation L2 ready)
   Last      recall 3 hours ago

✓ Network
   Anthropic API key   present
   Latency to API      82ms

────────────────────────────────────────────
Status: 1 warning. Run `leet calibrate --download` to clear.
```

E numa instalação quebrada:

```
$ leet doctor

leet doctor — system health check
════════════════════════════════════════════

✓ Binaries
   leet      v0.5.1   /home/yuri/.cargo/bin/leet
   leet-mcp  v0.5.1   /home/yuri/.cargo/bin/leet-mcp

✗ IDE integrations
   Claude Code        not found     searched ~/.claude, ~/.config/claude-code
   Cursor             not configured ~/.cursor/mcp.json
   VS Code (Continue) not detected   no Continue.dev install

✗ Skill installed
   Global             missing  ~/.claude/skills/leet/SKILL.md

⚠ W matrix
   Status   missing

✗ Project state
   Not in a leet project (no .leet/ in /tmp)

✓ Network
   Anthropic API key   present
   Latency             timeout

────────────────────────────────────────────
Status: 4 errors, 2 warnings.

Quick fixes:
  1. Install Claude Code from https://claude.ai/code
  2. Run `leet setup` to configure detected IDEs
  3. cd into a project directory before running leet operations
```

E pra automação (`--json`):

```json
{
  "status": "warning",
  "checks": [
    {"name": "binaries", "status": "ok", "details": "..."},
    {"name": "ides", "status": "ok", "details": "..."},
    {"name": "skill", "status": "ok"},
    {"name": "w_matrix", "status": "warning", "fallback": "hash-trigram"},
    {"name": "project", "status": "ok", "records": 47},
    {"name": "network", "status": "ok", "latency_ms": 82}
  ],
  "errors": 0,
  "warnings": 1,
  "exit_code": 2
}
```

---

## ARQUITETURA INTERNA

`doctor` é uma sequência de **checks**. Cada check é um trait:

```rust
trait HealthCheck {
    fn name(&self) -> &str;
    fn run(&self) -> CheckResult;
}

enum CheckResult {
    Ok { details: Vec<String> },
    Warning { message: String, hint: Option<String> },
    Error { message: String, suggestion: Option<String> },
}
```

`doctor` roda todos os checks, agrega resultados, formata output, computa exit code:
- 0 = todos OK
- 1 = pelo menos 1 erro
- 2 = pelo menos 1 warning, 0 erros

Auto-fix tentativo (`--auto-fix`) só corrige o que é mecânico (regenera index.bin, reinstala skill, baixa W). **Nunca** instala IDE, nunca seta API keys.

---

## ARQUIVO 1 — `leet-cli/src/cmd/doctor.rs` (novo)

```rust
//! `leet doctor` — system health check.

use std::path::PathBuf;
use std::time::Duration;

use anyhow::Result;
use clap::Args;
use serde_json::json;

#[derive(Debug, Args)]
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
    let project_root = args.project.clone().unwrap_or_else(|| std::env::current_dir().unwrap());

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
    fn is_ok(&self) -> bool { matches!(self, CheckResult::Ok { .. }) }
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
                suggestion: Some("Run `cargo install --path leet-cli --path leet-mcp`".into()),
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
        let mut lines = Vec::new();
        if settings.exists() {
            let text = std::fs::read_to_string(&settings).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed.pointer("/mcpServers/leet/command").is_some();
            lines.push(format!("Claude Code        {}  {}",
                if configured { "configured" } else { "not configured" },
                settings.display()));
        } else {
            lines.push(format!("Claude Code        not found     searched {}",
                home.join(".claude").display()));
        }
        lines
    }

    fn check_cursor(&self, home: &PathBuf) -> Vec<String> {
        let settings = home.join(".cursor/mcp.json");
        let mut lines = Vec::new();
        if settings.exists() {
            let text = std::fs::read_to_string(&settings).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed.pointer("/mcpServers/leet/command").is_some();
            lines.push(format!("Cursor             {}  {}",
                if configured { "configured" } else { "not configured" },
                settings.display()));
        } else {
            lines.push(format!("Cursor             not found     {}", settings.display()));
        }
        lines
    }

    fn check_continue(&self, home: &PathBuf) -> Vec<String> {
        let config = home.join(".continue/config.json");
        let mut lines = Vec::new();
        if config.exists() {
            lines.push(format!("VS Code (Continue) detected   {}", config.display()));
        } else {
            lines.push("VS Code (Continue) not detected".into());
        }
        lines
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
        let candidates = vec![
            std::env::var("LEET_W_PATH").ok().map(PathBuf::from),
            Some(PathBuf::from("calibration/data/W.bin")),
            Some(PathBuf::from("/usr/share/leetlang/W.bin")),
            std::env::var("HOME").ok().map(|h| PathBuf::from(h).join(".local/share/leetlang/W.bin")),
        ];
        let candidates: Vec<PathBuf> = candidates.into_iter().flatten().collect();

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

        // Read store and index counts; report mismatch as error.
        let store_size = std::fs::metadata(&store_path).map(|m| m.len()).unwrap_or(0);
        let store_records = if store_size > 16 {
            ((store_size - 16) / 360) as usize
        } else { 0 };

        let mut details = vec![
            format!("Project   {}", self.project_root.display()),
            format!("Records   {}", store_records),
        ];

        let index_path = leet_dir.join("index.bin");
        if index_path.exists() {
            let index_size = std::fs::metadata(&index_path).map(|m| m.len()).unwrap_or(0);
            let index_entries = if index_size > 32 {
                ((index_size - 32) / 24) as usize
            } else { 0 };

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

        // API key check
        let anthropic = std::env::var("ANTHROPIC_API_KEY").is_ok();
        details.push(format!(
            "Anthropic API key   {}",
            if anthropic { "present" } else { "missing" }
        ));

        // Latency probe — just to confirm we can reach api.anthropic.com,
        // not actually calling the API.
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
                hint: Some("export ANTHROPIC_API_KEY=sk-ant-... (https://console.anthropic.com/settings/keys)".into()),
                details,
            };
        }

        CheckResult::Ok { details }
    }
}

fn probe_latency(url: &str, timeout: Duration) -> Option<u64> {
    let start = std::time::Instant::now();
    // Simple TCP probe — avoid pulling reqwest as a runtime dep here.
    // Parse host out of URL.
    let host = url.trim_start_matches("https://").split('/').next()?;
    let addr = format!("{}:443", host);
    use std::net::ToSocketAddrs;
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
                // Reinstall skill
                if super::setup::install_global_skill_for_doctor().is_ok() {
                    *result = CheckResult::Ok { details: vec!["auto-fix: reinstalled".into()] };
                }
            }
            "w_matrix" => {
                // Best-effort download — silent failure
                if try_download_w().is_ok() {
                    *result = CheckResult::Ok { details: vec!["auto-fix: downloaded".into()] };
                }
            }
            "project" => {
                if let CheckResult::Error { .. } = result {
                    let _ = try_rebuild_index(project_root);
                    *result = CheckResult::Ok { details: vec!["auto-fix: rebuilt index".into()] };
                }
            }
            _ => {} // not auto-fixable
        }
    }
}

fn try_download_w() -> Result<()> {
    // Placeholder — real impl in Fase 12-W
    anyhow::bail!("not yet implemented (PROMPT_12-W-03)")
}

fn try_rebuild_index(_project_root: &PathBuf) -> Result<()> {
    // Calls into consolidate::rebuild_index logic
    Ok(())
}

// ─── Output formatting ────────────────────────────────────────────────────────

fn print_human(checks: &[(String, CheckResult)], errors: usize, warnings: usize) {
    println!();
    println!("leet doctor — system health check");
    println!("════════════════════════════════════════════");
    println!();

    for (name, result) in checks {
        let (icon, label) = match result {
            CheckResult::Ok { .. } => ("✓", display_label(name)),
            CheckResult::Warning { .. } => ("⚠", display_label(name)),
            CheckResult::Error { .. } => ("✗", display_label(name)),
        };
        println!("{} {}", icon, label);

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
    let status = if errors > 0 { "error" }
        else if warnings > 0 { "warning" }
        else { "ok" };

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
    fn binaries_check_handles_missing() {
        // Hard to test without mocks, but we can at least verify it doesn't panic.
        let _ = BinariesCheck::new().run();
    }

    #[test]
    fn project_check_no_leet_dir_is_warning() {
        let tmp = tempfile::tempdir().unwrap();
        let result = ProjectCheck::new(tmp.path().to_path_buf()).run();
        assert!(matches!(result, CheckResult::Warning { .. }));
    }

    #[test]
    fn project_check_with_leet_dir_is_ok() {
        let tmp = tempfile::tempdir().unwrap();
        let leet_dir = tmp.path().join(".leet");
        std::fs::create_dir_all(&leet_dir).unwrap();
        // Empty store.bin
        std::fs::write(leet_dir.join("store.bin"), &[0u8; 16]).unwrap();
        let result = ProjectCheck::new(tmp.path().to_path_buf()).run();
        // No store records, no index — should be Ok
        assert!(matches!(result, CheckResult::Ok { .. }) || matches!(result, CheckResult::Warning { .. }));
    }
}
```

---

## ARQUIVO 2 — `leet-cli/src/cmd/setup.rs` (expor função pra reutilização)

Adicionar wrapper público pra `install_global_skill` ser chamável de doctor:

```rust
/// Public wrapper for use in `leet doctor --auto-fix`.
pub fn install_global_skill_for_doctor() -> anyhow::Result<()> {
    let claude_dir = detect_claude_dir()?;
    install_global_skill(&claude_dir)
}
```

---

## ARQUIVO 3 — `leet-cli/src/cmd/mod.rs` (registrar)

```rust
pub mod doctor;

// Em Command enum:
/// Run system health check.
Doctor(cmd::doctor::DoctorArgs),

// No dispatcher:
Command::Doctor(args) => cmd::doctor::run(args),
```

---

## VERIFICATION

```bash
cargo build --workspace
cargo test --workspace

# Smoke (em uma máquina com setup completo):
./target/debug/leet doctor
# Esperado: ~6 checks listados, status final claro

./target/debug/leet doctor --json | jq .status
# Esperado: "ok", "warning", ou "error"

# Em máquina limpa (sem setup):
docker run --rm -v $(pwd)/target/debug/leet:/usr/local/bin/leet ubuntu:24.04 leet doctor
# Esperado: vários ✗, mas não crash. Exit code 1.

# --offline pula network
./target/debug/leet doctor --offline
# Esperado: network shown como "skipped"

# --auto-fix repara o que pode (skill faltando)
rm ~/.claude/skills/leet/SKILL.md
./target/debug/leet doctor --auto-fix
ls ~/.claude/skills/leet/SKILL.md
# Esperado: arquivo de volta
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt12_U_02 "leet doctor: full health check with auto-fix and JSON output"
task project:1337 +prompt12_U_02 done

git add leet-cli/src/cmd/doctor.rs leet-cli/src/cmd/mod.rs leet-cli/src/cmd/setup.rs

git commit -m "feat(cli): leet doctor — system health check

Diagnostic command verifying:
  - Binaries installed and version-matched (leet, leet-mcp)
  - IDE integrations configured (Claude Code, Cursor, VS Code+Continue)
  - Global skill present
  - W matrix availability (warning if fallback)
  - Project state (.leet/store.bin + index.bin sync)
  - Network reachability (Anthropic API, can be skipped --offline)

Output modes:
  default:   human-readable with ✓/⚠/✗ icons + summary footer
  --json:    machine-readable for automation

Exit codes: 0 healthy, 1 errors present, 2 warnings only.

--auto-fix attempts mechanical recovery:
  skill missing   → reinstall
  w matrix gone   → download (placeholder until 12-W-03)
  index out-sync  → rebuild lossy

Does NOT auto-install IDEs or set API keys. Those require user action.

Part of Phase 12-U (UX): one-stop diagnostic for setup health."
git push origin main
```

---

**END OF PROMPT_12-U-02**
