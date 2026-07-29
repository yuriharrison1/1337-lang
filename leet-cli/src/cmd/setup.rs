//! `leet setup <target>` — zero-friction installer for Claude Code and others.

use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, bail, Context, Result};
use clap::{Args, Subcommand};
use serde_json::{json, Value};

use super::setup_skill_content;

// ─── CLI shape ────────────────────────────────────────────────────────────────

#[derive(Debug, Args)]
#[command(
    about = "Configure leet for one or more IDEs (Claude Code, Cursor, VS Code+Continue)",
    long_about = "Configure leet for one or more IDEs (Claude Code, Cursor, VS Code+Continue).\n\
\n\
Without arguments, auto-detects installed IDEs and configures them all.\n\
With a target argument, configures only that IDE. Idempotent — running\n\
twice doesn't duplicate entries.",
    after_help = "Examples:\n  \
  # Auto-detect and configure all installed IDEs\n  \
  leet setup\n\
\n  \
  # Configure only Claude Code\n  \
  leet setup claude-code\n\
\n  \
  # See what's currently configured\n  \
  leet setup status\n\
\n  \
  # Reverse a configuration\n  \
  leet setup uninstall claude-code\n\
\n\
See also:\n  \
  leet doctor  — verify configuration health"
)]
pub struct SetupArgs {
    #[command(subcommand)]
    pub command: SetupCommand,
}

#[derive(Debug, Subcommand)]
pub enum SetupCommand {
    /// Configure Claude Code integration (global).
    #[command(name = "claude-code")]
    ClaudeCode {
        /// Install the leet-mcp binary via `cargo install --path` if not on PATH.
        #[arg(long)]
        install_binary: bool,

        /// Source workspace root used when --install-binary runs cargo install.
        #[arg(long, default_value = ".")]
        from: PathBuf,
    },

    /// Print current setup status for all known targets.
    Status,

    /// Configure Cursor integration (v0.42+).
    Cursor {
        /// Install the leet-mcp binary via `cargo install --path` if not on PATH.
        #[arg(long)]
        install_binary: bool,

        /// Source workspace root used when --install-binary runs cargo install.
        #[arg(long, default_value = ".")]
        from: PathBuf,
    },

    /// Configure VS Code + Continue.dev integration (experimental MCP support).
    #[command(name = "vscode-continue")]
    VscodeContinue {
        /// Install the leet-mcp binary via `cargo install --path` if not on PATH.
        #[arg(long)]
        install_binary: bool,

        /// Source workspace root used when --install-binary runs cargo install.
        #[arg(long, default_value = ".")]
        from: PathBuf,
    },

    /// Remove leet configuration from a target. .leet/ directories are kept.
    Uninstall {
        /// Target to uninstall: "claude-code", "cursor", or "vscode-continue".
        #[arg(default_value = "claude-code")]
        target: String,
    },
}

// ─── Entry point ──────────────────────────────────────────────────────────────

pub fn run(args: SetupArgs) -> Result<()> {
    match args.command {
        SetupCommand::ClaudeCode { install_binary, from } => {
            setup_claude_code(install_binary, &from)
        }
        SetupCommand::Cursor { install_binary, from } => {
            setup_cursor(install_binary, &from)
        }
        SetupCommand::VscodeContinue { install_binary, from } => {
            setup_vscode_continue(install_binary, &from)
        }
        SetupCommand::Status => status(),
        SetupCommand::Uninstall { target } => uninstall(&target),
    }
}

// ─── setup claude-code ────────────────────────────────────────────────────────

fn setup_claude_code(install_binary: bool, workspace_root: &Path) -> Result<()> {
    let binary_path = locate_or_install_mcp_binary(install_binary, workspace_root)?;
    println!("  ✓ leet-mcp binary at {}", binary_path.display());

    let claude_dir = detect_claude_dir()?;
    println!("  ✓ Detected Claude Code at {}", claude_dir.display());

    register_mcp_server(&claude_dir, &binary_path)?;
    println!("  ✓ Registered MCP server in {}/settings.json", claude_dir.display());

    install_global_skill(&claude_dir)?;
    println!("  ✓ Installed global skill at {}/skills/leet/", claude_dir.display());
    println!("  ✓ Installed /leet-stats command at {}/commands/leet-stats.md", claude_dir.display());

    println!();
    println!("  All set. Open any project with Claude Code — 1337 recall is live.");
    println!("  Per-project state lives in `.leet/store.bin` (auto-created, git-ignored).");
    println!("  Run /leet-stats inside Claude Code to see token savings.");
    Ok(())
}

// ─── Step 1: binary ───────────────────────────────────────────────────────────

fn locate_or_install_mcp_binary(install: bool, workspace_root: &Path) -> Result<PathBuf> {
    if let Ok(output) = Command::new("which").arg("leet-mcp").output() {
        if output.status.success() {
            let line = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !line.is_empty() {
                let p = PathBuf::from(line);
                if p.exists() {
                    return Ok(p);
                }
            }
        }
    }

    if let Some(home) = dirs_home() {
        let candidate = home.join(".cargo/bin/leet-mcp");
        if candidate.exists() {
            return Ok(candidate);
        }
    }

    if !install {
        leet_core::bail_user!(leet_core::UserFacingError::BinaryNotOnPath {
            binary: "leet-mcp".to_string(),
        });
    }

    println!("  → Installing leet-mcp via cargo (this may take a minute)...");
    let status = Command::new("cargo")
        .args([
            "install",
            "--path",
            workspace_root
                .join("leet-mcp")
                .to_str()
                .ok_or_else(|| anyhow!("invalid workspace path"))?,
            "--force",
        ])
        .status()
        .context("running cargo install")?;
    if !status.success() {
        bail!("cargo install failed (exit code {:?})", status.code());
    }

    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let candidate = home.join(".cargo/bin/leet-mcp");
    if !candidate.exists() {
        bail!("cargo install succeeded but leet-mcp is not at {}", candidate.display());
    }
    Ok(candidate)
}

// ─── Step 2: detect Claude Code dir ───────────────────────────────────────────

fn detect_claude_dir() -> Result<PathBuf> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;

    let primary = home.join(".claude");
    if primary.exists() {
        return Ok(primary);
    }

    let alt = home.join(".config/claude-code");
    if alt.exists() {
        return Ok(alt);
    }

    // Auto-create only if `claude` binary is on PATH (heuristic for installed-but-not-run).
    if has_claude_binary() {
        std::fs::create_dir_all(&primary)
            .with_context(|| format!("creating {}", primary.display()))?;
        Ok(primary)
    } else {
        leet_core::bail_user!(leet_core::UserFacingError::ClaudeCodeNotFound {
            searched: vec![primary, alt],
        })
    }
}

fn has_claude_binary() -> bool {
    Command::new("which")
        .arg("claude")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

// ─── Step 3: register MCP server ──────────────────────────────────────────────

fn register_mcp_server(claude_dir: &Path, binary_path: &Path) -> Result<()> {
    let settings_path = claude_dir.join("settings.json");

    let mut settings: Value = if settings_path.exists() {
        let text = std::fs::read_to_string(&settings_path)
            .with_context(|| format!("reading {}", settings_path.display()))?;
        if text.trim().is_empty() {
            json!({})
        } else {
            match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(e) => leet_core::bail_user!(leet_core::UserFacingError::SettingsFileMalformed {
                path: settings_path.clone(),
                details: e.to_string(),
            }),
        }
        }
    } else {
        json!({})
    };

    if !settings.is_object() {
        bail!("{} is not a JSON object", settings_path.display());
    }

    let servers = settings
        .as_object_mut()
        .unwrap()
        .entry("mcpServers".to_string())
        .or_insert_with(|| json!({}));

    if !servers.is_object() {
        bail!("mcpServers in {} is not an object", settings_path.display());
    }

    let binary_str = binary_path
        .to_str()
        .ok_or_else(|| anyhow!("binary path is not valid UTF-8"))?;

    servers.as_object_mut().unwrap().insert(
        "leet".to_string(),
        json!({
            "command": binary_str,
            "args": [],
            "env": {
                "LEET_PROJECT_ROOT": "${workspaceFolder}"
            }
        }),
    );

    let pretty = serde_json::to_string_pretty(&settings)?;
    let tmp_path = settings_path.with_extension("json.tmp");
    std::fs::write(&tmp_path, &pretty)?;
    std::fs::rename(&tmp_path, &settings_path)?;

    Ok(())
}

// ─── Step 4: global skill ─────────────────────────────────────────────────────

fn install_global_skill(claude_dir: &Path) -> Result<()> {
    let skill_dir = claude_dir.join("skills").join("leet");
    std::fs::create_dir_all(&skill_dir)?;

    let skill_md = skill_dir.join("SKILL.md");
    let write_now = match std::fs::read_to_string(&skill_md) {
        Ok(existing) => {
            // Upgrade if it's our stub or a prior leet version we wrote.
            existing.contains("managed by `leet setup claude-code`")
                || (existing.starts_with("---\n")
                    && existing.contains("name: leet")
                    && existing.contains("leet_recall")
                    && existing.contains("leet_remember"))
        }
        Err(_) => true,
    };

    if write_now {
        std::fs::write(&skill_md, setup_skill_content::SKILL_MD)?;
    }

    install_global_commands(claude_dir)?;

    Ok(())
}

fn install_global_commands(claude_dir: &Path) -> Result<()> {
    let cmd_dir = claude_dir.join("commands");
    std::fs::create_dir_all(&cmd_dir)?;

    let stats_md = cmd_dir.join("leet-stats.md");
    // Always write: this is a tool file we own, not user-editable content.
    std::fs::write(&stats_md, setup_skill_content::LEET_STATS_COMMAND_MD)?;

    Ok(())
}

// ─── status ──────────────────────────────────────────────────────────────────

fn status() -> Result<()> {
    println!("leet setup status");
    println!("─────────────────");

    let bin = Command::new("which").arg("leet-mcp").output();
    match bin {
        Ok(out) if out.status.success() => {
            let path = String::from_utf8_lossy(&out.stdout).trim().to_string();
            println!("  leet-mcp binary:   ✓ {}", path);
        }
        _ => println!("  leet-mcp binary:   ✗ not on PATH"),
    }

    let claude_dir = detect_claude_dir()?;
    let settings_path = claude_dir.join("settings.json");
    let configured = settings_path.exists() && {
        let text = std::fs::read_to_string(&settings_path).unwrap_or_default();
        let parsed: Value = serde_json::from_str(&text).unwrap_or(json!({}));
        parsed
            .pointer("/mcpServers/leet/command")
            .and_then(|v| v.as_str())
            .is_some()
    };
    println!(
        "  Claude Code:       {} {}",
        if configured { "✓" } else { "✗" },
        if configured {
            "configured".to_string()
        } else {
            "not configured (run `leet setup claude-code`)".to_string()
        }
    );

    let skill_md = claude_dir.join("skills/leet/SKILL.md");
    println!(
        "  Global skill:      {} {}",
        if skill_md.exists() { "✓" } else { "✗" },
        skill_md.display()
    );

    let stats_cmd = claude_dir.join("commands/leet-stats.md");
    println!(
        "  /leet-stats cmd:   {} {}",
        if stats_cmd.exists() { "✓" } else { "✗" },
        stats_cmd.display()
    );

    // Cursor status
    if let Some(home) = dirs_home() {
        let cursor_mcp = home.join(".cursor/mcp.json");
        if cursor_mcp.exists() {
            let text = std::fs::read_to_string(&cursor_mcp).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed.pointer("/mcpServers/leet/command").is_some();
            println!(
                "  Cursor:            {} {}",
                if configured { "✓" } else { "✗" },
                if configured { "configured".to_string() } else {
                    "detected but not configured (run `leet setup cursor`)".to_string()
                }
            );
        } else {
            println!("  Cursor:            · not detected");
        }

        // VS Code + Continue status
        let continue_config = home.join(".continue/config.json");
        if continue_config.exists() {
            let text = std::fs::read_to_string(&continue_config).unwrap_or_default();
            let parsed: serde_json::Value = serde_json::from_str(&text).unwrap_or(json!({}));
            let configured = parsed
                .pointer("/experimental/modelContextProtocolServers")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().any(|s| s.get("name").and_then(|n| n.as_str()) == Some("leet")))
                .unwrap_or(false);
            println!(
                "  VS Code+Continue:  {} {}",
                if configured { "✓" } else { "✗" },
                if configured { "configured".to_string() } else {
                    "detected but not configured (run `leet setup vscode-continue`)".to_string()
                }
            );
        } else {
            println!("  VS Code+Continue:  · not detected");
        }
    }

    Ok(())
}

// ─── uninstall ────────────────────────────────────────────────────────────────

fn uninstall(target: &str) -> Result<()> {
    match target {
        "cursor" => return uninstall_cursor(),
        "vscode-continue" => return uninstall_vscode_continue(),
        "claude-code" => {}
        _ => bail!("unknown target `{target}` — supported: `claude-code`, `cursor`, `vscode-continue`"),
    }

    let claude_dir = detect_claude_dir()?;
    let settings_path = claude_dir.join("settings.json");

    if settings_path.exists() {
        let text = std::fs::read_to_string(&settings_path)?;
        let mut settings: Value = serde_json::from_str(&text).unwrap_or_else(|_| json!({}));
        if let Some(servers) = settings.pointer_mut("/mcpServers").and_then(|v| v.as_object_mut()) {
            if servers.remove("leet").is_some() {
                let pretty = serde_json::to_string_pretty(&settings)?;
                let tmp_path = settings_path.with_extension("json.tmp");
                std::fs::write(&tmp_path, &pretty)?;
                std::fs::rename(&tmp_path, &settings_path)?;
                println!("  ✓ Removed mcpServers.leet from {}", settings_path.display());
            } else {
                println!("  · mcpServers.leet not present in {}", settings_path.display());
            }
        }
    }

    let skill_dir = claude_dir.join("skills/leet");
    if skill_dir.exists() {
        std::fs::remove_dir_all(&skill_dir)?;
        println!("  ✓ Removed global skill at {}", skill_dir.display());
    }

    let stats_cmd = claude_dir.join("commands/leet-stats.md");
    if stats_cmd.exists() {
        std::fs::remove_file(&stats_cmd)?;
        println!("  ✓ Removed /leet-stats command at {}", stats_cmd.display());
    }

    println!();
    println!("  Your per-project .leet/ directories are untouched.");
    println!("  To wipe a project's store, run: rm -rf <project>/.leet");

    Ok(())
}

// ─── setup cursor ────────────────────────────────────────────────────────────

fn setup_cursor(install_binary: bool, workspace_root: &Path) -> Result<()> {
    let binary_path = locate_or_install_mcp_binary(install_binary, workspace_root)?;
    println!("  ✓ leet-mcp binary at {}", binary_path.display());

    let cursor_dir = detect_cursor_dir()?;
    println!("  ✓ Detected Cursor config at {}", cursor_dir.display());

    register_cursor_mcp(&cursor_dir, &binary_path)?;
    println!("  ✓ Registered MCP server in {}/mcp.json", cursor_dir.display());

    let cwd = std::env::current_dir()?;
    match install_cursor_rules(&cwd)? {
        CursorRulesResult::Installed => {
            println!("  ✓ Added leet instructions to {}/.cursorrules", cwd.display());
        }
        CursorRulesResult::AlreadyInstalled => {
            println!("  ✓ .cursorrules already has leet instructions");
        }
        CursorRulesResult::SkippedNoProject => {
            println!("  ⚠ Current directory not detected as a project — skipping .cursorrules");
            println!("    Run `leet setup cursor` from a project root to enable per-project rules,");
            println!("    or add these instructions to Cursor Settings → Rules for AI:");
            println!();
            for line in cursor_rules_content().lines() {
                println!("    {}", line);
            }
        }
    }

    println!();
    println!("  All set. Restart Cursor for changes to take effect.");
    Ok(())
}

fn detect_cursor_dir() -> Result<PathBuf> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let primary = home.join(".cursor");
    let searched = vec![primary.clone()];

    if primary.exists() {
        return Ok(primary);
    }

    if has_cursor_binary() || is_cursor_installed_platform() {
        std::fs::create_dir_all(&primary)
            .with_context(|| format!("creating {}", primary.display()))?;
        return Ok(primary);
    }

    leet_core::bail_user!(leet_core::UserFacingError::CursorNotFound { searched })
}

fn has_cursor_binary() -> bool {
    Command::new("which")
        .arg("cursor")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn is_cursor_installed_platform() -> bool {
    #[cfg(target_os = "macos")]
    { std::path::Path::new("/Applications/Cursor.app").exists() }

    #[cfg(target_os = "linux")]
    {
        std::path::Path::new("/opt/cursor").exists()
            || std::path::Path::new("/usr/share/cursor").exists()
            || dirs_home()
                .map(|h| h.join(".local/share/applications/cursor.desktop").exists())
                .unwrap_or(false)
    }

    #[cfg(target_os = "windows")]
    {
        std::env::var("LOCALAPPDATA")
            .ok()
            .map(|p| std::path::Path::new(&p).join("Programs/cursor").exists())
            .unwrap_or(false)
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    { false }
}

fn register_cursor_mcp(cursor_dir: &Path, binary_path: &Path) -> Result<()> {
    let mcp_path = cursor_dir.join("mcp.json");

    let mut config: serde_json::Value = if mcp_path.exists() {
        let text = std::fs::read_to_string(&mcp_path)
            .with_context(|| format!("reading {}", mcp_path.display()))?;
        if text.trim().is_empty() {
            json!({})
        } else {
            match serde_json::from_str(&text) {
                Ok(v) => v,
                Err(e) => leet_core::bail_user!(leet_core::UserFacingError::SettingsFileMalformed {
                    path: mcp_path.clone(),
                    details: e.to_string(),
                }),
            }
        }
    } else {
        json!({})
    };

    let servers = config
        .as_object_mut()
        .ok_or_else(|| anyhow!("top-level of mcp.json must be an object"))?
        .entry("mcpServers")
        .or_insert_with(|| json!({}));

    let binary_str = binary_path
        .to_str()
        .ok_or_else(|| anyhow!("binary path is not valid UTF-8"))?;

    servers
        .as_object_mut()
        .ok_or_else(|| anyhow!("mcpServers must be an object"))?
        .insert("leet".to_string(), json!({
            "command": binary_str,
            "args": [],
            "env": {
                "LEET_PROJECT_ROOT": "${workspaceFolder}"
            }
        }));

    write_atomic(&mcp_path, &serde_json::to_string_pretty(&config)?)?;
    Ok(())
}

fn write_atomic(target: &Path, content: &str) -> Result<()> {
    use std::io::Write;
    let temp = target.with_extension("tmp");
    {
        let mut f = std::fs::File::create(&temp)?;
        f.write_all(content.as_bytes())?;
        f.sync_all()?;
    }
    std::fs::rename(&temp, target)?;
    Ok(())
}

enum CursorRulesResult {
    Installed,
    AlreadyInstalled,
    SkippedNoProject,
}

fn install_cursor_rules(project_root: &Path) -> Result<CursorRulesResult> {
    if !looks_like_project(project_root) {
        return Ok(CursorRulesResult::SkippedNoProject);
    }

    let rules_path = project_root.join(".cursorrules");
    let existing = std::fs::read_to_string(&rules_path).unwrap_or_default();

    if existing.contains("<!-- leet-mcp -->") {
        return Ok(CursorRulesResult::AlreadyInstalled);
    }

    let snippet = format!(
        "\n<!-- leet-mcp -->\n{}\n<!-- /leet-mcp -->\n",
        cursor_rules_content()
    );

    let new_content = if existing.trim().is_empty() {
        snippet.trim_start_matches('\n').to_string()
    } else {
        format!("{}\n{}", existing.trim_end(), snippet)
    };

    write_atomic(&rules_path, &new_content)?;
    Ok(CursorRulesResult::Installed)
}

fn cursor_rules_content() -> &'static str {
    r#"When working in this project, you have access to the `leet` MCP server with memory tools:

- `leet_recall` — retrieve project memory from past sessions. Call at session start or when context is missing.
- `leet_remember` — persist significant decisions, task completions, and architectural choices. Call silently when the user confirms task completion or a decision is made.
- `leet_encode` / `leet_decode` / `leet_dist` — advanced COGON vector tools (use only if explicitly requested).

Rules:
1. At session start, call `leet_recall` silently to load context.
2. On task completion / decision made / topic shift, call `leet_remember` with a 1-3 sentence paraphrased summary.
3. Never announce memory operations to the user. Operate silently.
4. Q&A, typos, formatting changes: do NOT call `leet_remember`."#
}

fn looks_like_project(dir: &Path) -> bool {
    if dir.join(".git").exists() { return true; }
    for marker in &["package.json", "Cargo.toml", "pyproject.toml", "go.mod", "pom.xml"] {
        if dir.join(marker).exists() { return true; }
    }
    dir.join("README.md").exists() && has_code_files(dir)
}

fn has_code_files(dir: &Path) -> bool {
    let code_exts = [".rs", ".py", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".rb"];
    std::fs::read_dir(dir).ok()
        .map(|entries| {
            entries.flatten().any(|e| {
                let name = e.file_name().to_string_lossy().to_string();
                code_exts.iter().any(|ext| name.ends_with(ext))
            })
        })
        .unwrap_or(false)
}

fn uninstall_cursor() -> Result<()> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let mcp_path = home.join(".cursor/mcp.json");

    if mcp_path.exists() {
        let text = std::fs::read_to_string(&mcp_path)?;
        if let Ok(mut config) = serde_json::from_str::<serde_json::Value>(&text) {
            if let Some(servers) = config.pointer_mut("/mcpServers").and_then(|v| v.as_object_mut()) {
                if servers.remove("leet").is_some() {
                    write_atomic(&mcp_path, &serde_json::to_string_pretty(&config)?)?;
                    println!("  ✓ Removed mcpServers.leet from {}", mcp_path.display());
                } else {
                    println!("  · mcpServers.leet not present in {}", mcp_path.display());
                }
            }
        }
    } else {
        println!("  · {} not found — nothing to remove", mcp_path.display());
    }

    let rules_path = std::env::current_dir()?.join(".cursorrules");
    if rules_path.exists() {
        let text = std::fs::read_to_string(&rules_path)?;
        if text.contains("<!-- leet-mcp -->") {
            let cleaned = remove_leet_block(&text);
            write_atomic(&rules_path, cleaned.trim_end_matches('\n'))?;
            println!("  ✓ Removed leet block from {}", rules_path.display());
        } else {
            println!("  · No leet block found in {}", rules_path.display());
        }
    }

    println!();
    println!("  Your per-project .leet/ directories are untouched.");
    Ok(())
}

// ─── setup vscode-continue ───────────────────────────────────────────────────

fn setup_vscode_continue(install_binary: bool, workspace_root: &Path) -> Result<()> {
    let binary_path = locate_or_install_mcp_binary(install_binary, workspace_root)?;
    println!("  ✓ leet-mcp binary at {}", binary_path.display());

    let continue_dir = detect_continue_dir()?;
    println!("  ✓ Detected Continue.dev config at {}", continue_dir.display());

    register_continue_mcp(&continue_dir, &binary_path)?;
    println!("  ✓ Registered MCP server in {}/config.json", continue_dir.display());

    let sm_path = install_continue_system_message(&continue_dir)?;
    println!("  ✓ Installed system message at {}", sm_path.display());

    println!();
    println!("  Note: leet uses Continue's experimental MCP support (config under 'experimental').");
    println!("        The schema may change in future Continue.dev versions.");
    println!();
    println!("  To activate the system message in Continue:");
    println!("    Settings → System Message → select 'leet'");
    println!();
    println!("  Restart VS Code for changes to take effect.");
    Ok(())
}

fn detect_continue_dir() -> Result<PathBuf> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let primary = home.join(".continue");
    let searched = vec![primary.clone()];

    if primary.exists() {
        return Ok(primary);
    }

    if has_continue_via_vscode() {
        std::fs::create_dir_all(&primary)
            .with_context(|| format!("creating {}", primary.display()))?;
        return Ok(primary);
    }

    // VS Code installed but Continue missing — different error message
    if has_vscode_binary() || is_vscode_installed_platform() {
        leet_core::bail_user!(leet_core::UserFacingError::VsCodeContinueNotFound { searched })
    }

    leet_core::bail_user!(leet_core::UserFacingError::VsCodeContinueNotFound { searched })
}

fn has_vscode_binary() -> bool {
    Command::new("which")
        .arg("code")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

fn has_continue_via_vscode() -> bool {
    let output = Command::new("code")
        .arg("--list-extensions")
        .output();
    match output {
        Ok(o) if o.status.success() => {
            let list = String::from_utf8_lossy(&o.stdout);
            list.lines().any(|l| l.trim().eq_ignore_ascii_case("continue.continue"))
        }
        _ => false,
    }
}

fn is_vscode_installed_platform() -> bool {
    #[cfg(target_os = "macos")]
    { std::path::Path::new("/Applications/Visual Studio Code.app").exists() }

    #[cfg(target_os = "linux")]
    {
        std::path::Path::new("/opt/visual-studio-code").exists()
            || std::path::Path::new("/usr/share/code").exists()
            || std::path::Path::new("/snap/code").exists()
            || dirs_home()
                .map(|h| h.join(".vscode").exists())
                .unwrap_or(false)
    }

    #[cfg(target_os = "windows")]
    {
        std::env::var("LOCALAPPDATA")
            .ok()
            .map(|p| std::path::Path::new(&p).join("Programs/Microsoft VS Code").exists())
            .unwrap_or(false)
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux", target_os = "windows")))]
    { false }
}

fn register_continue_mcp(continue_dir: &Path, binary_path: &Path) -> Result<()> {
    let config_path = continue_dir.join("config.json");

    let mut config: serde_json::Value = if config_path.exists() {
        let text = std::fs::read_to_string(&config_path)
            .with_context(|| format!("reading {}", config_path.display()))?;
        if text.trim().is_empty() {
            json!({})
        } else {
            match serde_json::from_str(&text) {
                Ok(v) => v,
                Err(e) => leet_core::bail_user!(leet_core::UserFacingError::SettingsFileMalformed {
                    path: config_path.clone(),
                    details: e.to_string(),
                }),
            }
        }
    } else {
        json!({})
    };

    let binary_str = binary_path
        .to_str()
        .ok_or_else(|| anyhow!("binary path is not valid UTF-8"))?;

    let leet_entry = json!({
        "name": "leet",
        "transport": {
            "type": "stdio",
            "command": binary_str
        }
    });

    let experimental = config
        .as_object_mut()
        .ok_or_else(|| anyhow!("top-level of config.json must be an object"))?
        .entry("experimental")
        .or_insert_with(|| json!({}));

    let servers = experimental
        .as_object_mut()
        .ok_or_else(|| anyhow!("experimental must be an object"))?
        .entry("modelContextProtocolServers")
        .or_insert_with(|| json!([]));

    let arr = servers
        .as_array_mut()
        .ok_or_else(|| anyhow!("modelContextProtocolServers must be an array"))?;

    arr.retain(|s| s.get("name").and_then(|n| n.as_str()) != Some("leet"));
    arr.push(leet_entry);

    write_atomic(&config_path, &serde_json::to_string_pretty(&config)?)?;
    Ok(())
}

fn install_continue_system_message(continue_dir: &Path) -> Result<PathBuf> {
    let sm_dir = continue_dir.join("system_messages");
    std::fs::create_dir_all(&sm_dir)
        .with_context(|| format!("creating {}", sm_dir.display()))?;
    let sm_path = sm_dir.join("leet.md");
    write_atomic(&sm_path, continue_system_message_content())?;
    Ok(sm_path)
}

fn continue_system_message_content() -> &'static str {
    r#"# leet — memory tools

You have access to the `leet` MCP server. Use it to persist project memory across sessions.

## Tools

- `leet_recall` — retrieve project memory. Call at session start or when context is missing.
- `leet_remember` — persist decisions, task completions, architectural choices. Call silently.
- `leet_encode` / `leet_decode` / `leet_dist` — advanced COGON vector tools (use only if explicitly requested).

## When to call `leet_recall`

- At session start
- When user references past work you lack context on
- When user says "continue where we left off", "back to X we discussed", etc.

## When to call `leet_remember`

DO call for: task completion confirmed, architectural decisions, significant bug fixes, release/deploy.
DO NOT call for: Q&A, formatting, typo fixes, read-only ops, exploratory questions.

## Rules

1. Never announce memory operations. Operate silently.
2. If server returns error, continue silently. Memory is best-effort.
3. 1-3 sentence summaries. Paraphrase, don't log verbatim.
"#
}

fn uninstall_vscode_continue() -> Result<()> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let continue_dir = home.join(".continue");

    let config_path = continue_dir.join("config.json");
    if config_path.exists() {
        let text = std::fs::read_to_string(&config_path)?;
        if let Ok(mut config) = serde_json::from_str::<serde_json::Value>(&text) {
            if let Some(servers) = config
                .pointer_mut("/experimental/modelContextProtocolServers")
                .and_then(|v| v.as_array_mut())
            {
                let before_len = servers.len();
                servers.retain(|s| s.get("name").and_then(|n| n.as_str()) != Some("leet"));
                if servers.len() < before_len {
                    write_atomic(&config_path, &serde_json::to_string_pretty(&config)?)?;
                    println!("  ✓ Removed leet from MCP servers in {}", config_path.display());
                } else {
                    println!("  · leet entry not present in {}", config_path.display());
                }
            }
        }
    } else {
        println!("  · {} not found — nothing to remove", config_path.display());
    }

    let sm_path = continue_dir.join("system_messages/leet.md");
    if sm_path.exists() {
        std::fs::remove_file(&sm_path)?;
        println!("  ✓ Removed system message at {}", sm_path.display());
    } else {
        println!("  · System message not found at {}", sm_path.display());
    }

    println!();
    println!("  Your per-project .leet/ directories are untouched.");
    Ok(())
}

fn remove_leet_block(content: &str) -> String {
    let mut result = String::new();
    let mut in_block = false;
    for line in content.lines() {
        if line.contains("<!-- leet-mcp -->") { in_block = true; continue; }
        if line.contains("<!-- /leet-mcp -->") { in_block = false; continue; }
        if !in_block {
            result.push_str(line);
            result.push('\n');
        }
    }
    result
}

// ─── helpers ──────────────────────────────────────────────────────────────────

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

/// Public wrapper for use in `leet doctor --auto-fix`.
pub fn install_global_skill_for_doctor() -> anyhow::Result<()> {
    let claude_dir = detect_claude_dir()?;
    install_global_skill(&claude_dir)
}

// ─── tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn register_creates_new_settings() {
        let tmp = tempfile::tempdir().unwrap();
        register_mcp_server(tmp.path(), Path::new("/usr/local/bin/leet-mcp")).unwrap();
        let text = std::fs::read_to_string(tmp.path().join("settings.json")).unwrap();
        let v: Value = serde_json::from_str(&text).unwrap();
        assert_eq!(
            v["mcpServers"]["leet"]["command"].as_str().unwrap(),
            "/usr/local/bin/leet-mcp"
        );
        assert_eq!(
            v["mcpServers"]["leet"]["env"]["LEET_PROJECT_ROOT"].as_str().unwrap(),
            "${workspaceFolder}"
        );
    }

    #[test]
    fn register_preserves_other_mcp_servers() {
        let tmp = tempfile::tempdir().unwrap();
        let settings_path = tmp.path().join("settings.json");
        std::fs::write(
            &settings_path,
            r#"{"mcpServers":{"other":{"command":"/path/to/other"}},"someOtherSetting":"keep me"}"#,
        )
        .unwrap();

        register_mcp_server(tmp.path(), Path::new("/bin/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(&settings_path).unwrap();
        let v: Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["mcpServers"]["other"]["command"].as_str().unwrap(), "/path/to/other");
        assert_eq!(v["mcpServers"]["leet"]["command"].as_str().unwrap(), "/bin/leet-mcp");
        assert_eq!(v["someOtherSetting"].as_str().unwrap(), "keep me");
    }

    #[test]
    fn register_is_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        register_mcp_server(tmp.path(), Path::new("/a")).unwrap();
        register_mcp_server(tmp.path(), Path::new("/b")).unwrap();
        let text = std::fs::read_to_string(tmp.path().join("settings.json")).unwrap();
        let v: Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["mcpServers"]["leet"]["command"].as_str().unwrap(), "/b");
    }

    #[test]
    fn install_global_skill_writes_real_content() {
        let tmp = tempfile::tempdir().unwrap();
        install_global_skill(tmp.path()).unwrap();
        let path = tmp.path().join("skills/leet/SKILL.md");
        assert!(path.exists());
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("leet_recall"));
        assert!(content.contains("leet_remember"));
        assert!(content.starts_with("---\n"));
    }

    #[test]
    fn install_global_skill_does_not_overwrite_user_edits() {
        let tmp = tempfile::tempdir().unwrap();
        let skill_dir = tmp.path().join("skills/leet");
        std::fs::create_dir_all(&skill_dir).unwrap();
        let user_content = "---\nname: custom\n---\n\n# My own skill\n";
        std::fs::write(skill_dir.join("SKILL.md"), user_content).unwrap();

        install_global_skill(tmp.path()).unwrap();
        let content = std::fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
        assert_eq!(content, user_content);
    }

    #[test]
    fn install_global_skill_upgrades_our_prior_version() {
        let tmp = tempfile::tempdir().unwrap();
        let skill_dir = tmp.path().join("skills/leet");
        std::fs::create_dir_all(&skill_dir).unwrap();
        std::fs::write(
            skill_dir.join("SKILL.md"),
            "---\nname: leet\n---\n\nOld version\nleet_recall\nleet_remember\n",
        )
        .unwrap();

        install_global_skill(tmp.path()).unwrap();
        let content = std::fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
        assert!(content.len() > 500, "should have been upgraded to real content");
    }

    // ── Cursor tests ──────────────────────────────────────────────────────────

    #[test]
    fn register_cursor_mcp_creates_file_from_scratch() {
        let tmp = tempfile::tempdir().unwrap();
        register_cursor_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();
        let text = std::fs::read_to_string(tmp.path().join("mcp.json")).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["mcpServers"]["leet"]["command"].as_str().unwrap(), "/fake/leet-mcp");
        assert_eq!(
            v["mcpServers"]["leet"]["env"]["LEET_PROJECT_ROOT"].as_str().unwrap(),
            "${workspaceFolder}"
        );
    }

    #[test]
    fn register_cursor_mcp_preserves_existing_servers() {
        let tmp = tempfile::tempdir().unwrap();
        let mcp_path = tmp.path().join("mcp.json");
        std::fs::write(&mcp_path, r#"{"mcpServers":{"other":{"command":"/x"}}}"#).unwrap();

        register_cursor_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(&mcp_path).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["mcpServers"]["other"]["command"].as_str().unwrap(), "/x");
        assert_eq!(v["mcpServers"]["leet"]["command"].as_str().unwrap(), "/fake/leet-mcp");
    }

    #[test]
    fn register_cursor_mcp_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        register_cursor_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();
        let first = std::fs::read_to_string(tmp.path().join("mcp.json")).unwrap();
        register_cursor_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();
        let second = std::fs::read_to_string(tmp.path().join("mcp.json")).unwrap();
        assert_eq!(first, second);
    }

    #[test]
    fn cursorrules_install_creates_file() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir(tmp.path().join(".git")).unwrap();

        let result = install_cursor_rules(tmp.path()).unwrap();
        assert!(matches!(result, CursorRulesResult::Installed));

        let content = std::fs::read_to_string(tmp.path().join(".cursorrules")).unwrap();
        assert!(content.contains("<!-- leet-mcp -->"));
        assert!(content.contains("leet_recall"));
        assert!(content.contains("<!-- /leet-mcp -->"));
    }

    #[test]
    fn cursorrules_preserves_user_content() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir(tmp.path().join(".git")).unwrap();
        let existing = "# My rules\nAlways use TypeScript.\n";
        std::fs::write(tmp.path().join(".cursorrules"), existing).unwrap();

        install_cursor_rules(tmp.path()).unwrap();

        let content = std::fs::read_to_string(tmp.path().join(".cursorrules")).unwrap();
        assert!(content.contains("Always use TypeScript"));
        assert!(content.contains("<!-- leet-mcp -->"));
    }

    #[test]
    fn cursorrules_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir(tmp.path().join(".git")).unwrap();

        install_cursor_rules(tmp.path()).unwrap();
        let first = std::fs::read_to_string(tmp.path().join(".cursorrules")).unwrap();

        let second_result = install_cursor_rules(tmp.path()).unwrap();
        assert!(matches!(second_result, CursorRulesResult::AlreadyInstalled));

        let second = std::fs::read_to_string(tmp.path().join(".cursorrules")).unwrap();
        assert_eq!(first, second);
    }

    #[test]
    fn cursorrules_skipped_for_non_project() {
        let tmp = tempfile::tempdir().unwrap();
        let result = install_cursor_rules(tmp.path()).unwrap();
        assert!(matches!(result, CursorRulesResult::SkippedNoProject));
    }

    #[test]
    fn remove_leet_block_preserves_surrounding_content() {
        let input = "# My rules\nAlways use TypeScript.\n\n<!-- leet-mcp -->\nleet stuff\n<!-- /leet-mcp -->\n";
        let cleaned = remove_leet_block(input);
        assert!(cleaned.contains("Always use TypeScript"));
        assert!(!cleaned.contains("leet stuff"));
        assert!(!cleaned.contains("<!-- leet-mcp -->"));
    }

    #[test]
    fn looks_like_project_detects_git() {
        let tmp = tempfile::tempdir().unwrap();
        assert!(!looks_like_project(tmp.path()));
        std::fs::create_dir(tmp.path().join(".git")).unwrap();
        assert!(looks_like_project(tmp.path()));
    }

    #[test]
    fn looks_like_project_detects_cargo_toml() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("Cargo.toml"), "[package]\n").unwrap();
        assert!(looks_like_project(tmp.path()));
    }

    // ── VS Code + Continue tests ───────────────────────────────────────────────

    #[test]
    fn register_continue_mcp_creates_config_from_scratch() {
        let tmp = tempfile::tempdir().unwrap();
        register_continue_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(tmp.path().join("config.json")).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        let servers = v.pointer("/experimental/modelContextProtocolServers").unwrap().as_array().unwrap();
        assert_eq!(servers.len(), 1);
        assert_eq!(servers[0]["name"], "leet");
        assert_eq!(servers[0]["transport"]["command"], "/fake/leet-mcp");
    }

    #[test]
    fn register_continue_mcp_preserves_existing_servers() {
        let tmp = tempfile::tempdir().unwrap();
        let config_path = tmp.path().join("config.json");
        let initial = json!({
            "experimental": {
                "modelContextProtocolServers": [
                    { "name": "other", "transport": { "type": "stdio", "command": "/x" } }
                ]
            }
        });
        std::fs::write(&config_path, serde_json::to_string(&initial).unwrap()).unwrap();

        register_continue_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(&config_path).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        let servers = v.pointer("/experimental/modelContextProtocolServers").unwrap().as_array().unwrap();
        assert_eq!(servers.len(), 2);
        let names: Vec<&str> = servers.iter().filter_map(|s| s["name"].as_str()).collect();
        assert!(names.contains(&"other"));
        assert!(names.contains(&"leet"));
    }

    #[test]
    fn register_continue_mcp_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        register_continue_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();
        register_continue_mcp(tmp.path(), Path::new("/fake/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(tmp.path().join("config.json")).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        let servers = v.pointer("/experimental/modelContextProtocolServers").unwrap().as_array().unwrap();
        assert_eq!(servers.len(), 1, "should not duplicate leet entry");
    }

    #[test]
    fn register_continue_mcp_updates_binary_path_on_reinstall() {
        let tmp = tempfile::tempdir().unwrap();
        register_continue_mcp(tmp.path(), Path::new("/old/leet-mcp")).unwrap();
        register_continue_mcp(tmp.path(), Path::new("/new/leet-mcp")).unwrap();

        let text = std::fs::read_to_string(tmp.path().join("config.json")).unwrap();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        let servers = v.pointer("/experimental/modelContextProtocolServers").unwrap().as_array().unwrap();
        assert_eq!(servers.len(), 1);
        assert_eq!(servers[0]["transport"]["command"], "/new/leet-mcp");
    }

    #[test]
    fn install_continue_system_message_creates_file() {
        let tmp = tempfile::tempdir().unwrap();
        let sm_path = install_continue_system_message(tmp.path()).unwrap();
        assert!(sm_path.exists());
        let content = std::fs::read_to_string(&sm_path).unwrap();
        assert!(content.contains("leet_recall"));
        assert!(content.contains("leet_remember"));
    }

    #[test]
    fn install_continue_system_message_overwrites_existing() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(tmp.path().join("system_messages")).unwrap();
        std::fs::write(tmp.path().join("system_messages/leet.md"), "old content").unwrap();

        install_continue_system_message(tmp.path()).unwrap();

        let content = std::fs::read_to_string(tmp.path().join("system_messages/leet.md")).unwrap();
        assert!(!content.contains("old content"));
        assert!(content.contains("leet_recall"));
    }

    #[test]
    fn continue_uninstall_removes_only_leet_entry() {
        let initial = json!({
            "experimental": {
                "modelContextProtocolServers": [
                    { "name": "other", "transport": { "type": "stdio", "command": "/x" } },
                    { "name": "leet", "transport": { "type": "stdio", "command": "/y" } }
                ]
            }
        });
        let text = serde_json::to_string(&initial).unwrap();
        let mut config: serde_json::Value = serde_json::from_str(&text).unwrap();
        if let Some(servers) = config
            .pointer_mut("/experimental/modelContextProtocolServers")
            .and_then(|v| v.as_array_mut())
        {
            servers.retain(|s| s.get("name").and_then(|n| n.as_str()) != Some("leet"));
        }
        let servers = config.pointer("/experimental/modelContextProtocolServers").unwrap().as_array().unwrap();
        assert_eq!(servers.len(), 1);
        assert_eq!(servers[0]["name"], "other");
    }
}
