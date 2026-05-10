//! `leet setup <target>` — zero-friction installer for Claude Code and others.

use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, bail, Context, Result};
use clap::{Args, Subcommand};
use serde_json::{json, Value};

use super::setup_skill_content;

// ─── CLI shape ────────────────────────────────────────────────────────────────

#[derive(Debug, Args)]
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

    /// Remove leet configuration from a target. .leet/ directories are kept.
    Uninstall {
        /// Target to uninstall: "claude-code".
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

    Ok(())
}

// ─── uninstall ────────────────────────────────────────────────────────────────

fn uninstall(target: &str) -> Result<()> {
    if target != "claude-code" {
        bail!("unknown target `{target}` — only `claude-code` is supported");
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

    println!();
    println!("  Your per-project .leet/ directories are untouched.");
    println!("  To wipe a project's store, run: rm -rf <project>/.leet");

    Ok(())
}

// ─── helpers ──────────────────────────────────────────────────────────────────

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
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
}
