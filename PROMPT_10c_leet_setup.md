# PROMPT 10c — `leet setup claude-code` (zero-friction installer)

Add a `leet setup` subcommand to the CLI that does every step required to wire leet-mcp into Claude Code, globally, with idempotency. The user runs it **once** and never has to think about integration again. New projects work automatically.

**PRE-REQUISITES**: 10a + 10b landed. `leet-mcp` binary builds. `cargo test --workspace` green.

**SCOPE**: `leet-cli/src/cmd/setup.rs` (new) + register in `leet-cli/src/cmd/mod.rs` + optional: `setup.py` integration note at the end.

**Taskwarrior**: `+prompt10c`.

---

## WHAT THE USER EXPERIENCES

```
$ cargo install leetlang              # one-time install from crates.io (future)
$ leet setup claude-code
  ✓ leet-mcp binary available at ~/.cargo/bin/leet-mcp
  ✓ Detected Claude Code at ~/.claude/
  ✓ Registered MCP server in ~/.claude/settings.json
  ✓ Installed global skill at ~/.claude/skills/leet/
  → All set. Open any project with Claude Code and 1337 recall is live.

$ leet setup --status
  Claude Code:       ✓ configured
  leet-mcp binary:   ✓ ~/.cargo/bin/leet-mcp (0.5.1)
  Global skill:      ✓ ~/.claude/skills/leet/
  Projects seen:     4 (.leet/store.bin found)

$ leet setup --uninstall claude-code    # clean removal
  ✓ Removed MCP entry from ~/.claude/settings.json
  ✓ Removed global skill
  Your .leet/ directories are NOT deleted (run `leet wipe` per project if needed).
```

The key property: **the only state we touch lives in `~/.claude/` and `~/.cargo/bin/`**. Projects that already have `.leet/store.bin` keep working. Running setup twice is a no-op.

---

## WHAT IT ACTUALLY DOES

Three steps, each idempotent:

### Step 1 — Verify/install the binary

`leet-mcp` must be on PATH. Detection strategy:
1. If `which leet-mcp` works → record the path, move on.
2. Else, if the caller is running from `~/.cargo/bin/leet` → check `~/.cargo/bin/leet-mcp`.
3. Else, run `cargo install --path <workspace>/leet-mcp` **only if** `--install-binary` flag is passed.
4. Else, fail with a clear message: "run `cargo install --path leet-mcp` first, or pass `--install-binary`".

We don't auto-install binaries by default because that's intrusive. User opts in.

### Step 2 — Register the MCP server

Claude Code reads two possible config files, in priority order:
1. `~/.claude/settings.json` (global user settings)
2. `<project>/.claude/settings.json` (per-project override)
3. Historical alternative paths: `~/.config/claude-code/mcp.json` (older versions)

We write to `~/.claude/settings.json` (global) by default. Shape:

```json
{
  "mcpServers": {
    "leet": {
      "command": "/home/user/.cargo/bin/leet-mcp",
      "args": [],
      "env": {
        "LEET_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

`${workspaceFolder}` is Claude Code's built-in variable for the current project directory. This is what makes zero-friction work — leet-mcp spawns with cwd set to wherever the user opened Claude Code, and our `open_or_create` in PROMPT_10a picks that up automatically.

Idempotency: if an entry named `leet` already exists, we re-write it (upgrade path for version bumps). If the file has other MCP servers configured, we preserve them.

### Step 3 — Install the global skill

Create `~/.claude/skills/leet/SKILL.md`. Content written by PROMPT_10d. For now, write a placeholder that says "see PROMPT_10d for contents".

Per-project overrides (`.claude/skills/leet/SKILL.md` inside a specific project) take precedence when Claude Code reads them. That's already handled by Claude Code; we just write the global and let the precedence work.

---

## FILE 1 — `leet-cli/src/cmd/setup.rs` (new)

```rust
//! `leet setup <target>` — zero-friction installer for Claude Code and others.

use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, bail, Context, Result};
use clap::{Args, Subcommand};
use serde_json::{json, Value};

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

    /// Remove leet configuration from a target. .leet/ directories in projects are kept.
    Uninstall {
        /// Target to uninstall: "claude-code" (currently the only option).
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
    // Step 1: locate or install the binary.
    let binary_path = locate_or_install_mcp_binary(install_binary, workspace_root)?;
    println!("  ✓ leet-mcp binary at {}", binary_path.display());

    // Step 2: detect Claude Code config directory.
    let claude_dir = detect_claude_dir()?;
    println!("  ✓ Detected Claude Code at {}", claude_dir.display());

    // Step 3: register MCP server.
    register_mcp_server(&claude_dir, &binary_path)?;
    println!("  ✓ Registered MCP server in {}/settings.json", claude_dir.display());

    // Step 4: install global skill stub (10d fills in the content).
    install_global_skill(&claude_dir)?;
    println!("  ✓ Installed global skill at {}/skills/leet/", claude_dir.display());

    println!();
    println!("  All set. Open any project with Claude Code — 1337 recall is live.");
    println!("  Per-project state lives in `.leet/store.bin` (auto-created, git-ignored).");
    Ok(())
}

// ─── Step 1: binary ───────────────────────────────────────────────────────────

fn locate_or_install_mcp_binary(
    install: bool,
    workspace_root: &Path,
) -> Result<PathBuf> {
    // Try PATH.
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

    // Try ~/.cargo/bin/leet-mcp directly.
    if let Some(home) = dirs_home() {
        let candidate = home.join(".cargo/bin/leet-mcp");
        if candidate.exists() {
            return Ok(candidate);
        }
    }

    if !install {
        bail!(
            "leet-mcp not found on PATH. Either:\n  \
             - run `cargo install --path leet-mcp` from the workspace root, or\n  \
             - re-run with --install-binary to do it automatically."
        );
    }

    // Install via cargo.
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

    // After install, locate again.
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

    // Preferred: ~/.claude (current Claude Code layout).
    let primary = home.join(".claude");
    if primary.exists() {
        return Ok(primary);
    }

    // Older / alt layout: ~/.config/claude-code
    let alt = home.join(".config/claude-code");
    if alt.exists() {
        return Ok(alt);
    }

    // Neither exists: create ~/.claude (Claude Code will also tolerate this).
    std::fs::create_dir_all(&primary)
        .with_context(|| format!("creating {}", primary.display()))?;
    Ok(primary)
}

// ─── Step 3: register MCP server ──────────────────────────────────────────────

fn register_mcp_server(claude_dir: &Path, binary_path: &Path) -> Result<()> {
    let settings_path = claude_dir.join("settings.json");

    // Load existing config, or start fresh.
    let mut settings: Value = if settings_path.exists() {
        let text = std::fs::read_to_string(&settings_path)
            .with_context(|| format!("reading {}", settings_path.display()))?;
        if text.trim().is_empty() {
            json!({})
        } else {
            serde_json::from_str(&text).with_context(|| {
                format!(
                    "parsing {} — this file has invalid JSON. \
                     Fix it or back it up and re-run setup.",
                    settings_path.display()
                )
            })?
        }
    } else {
        json!({})
    };

    // Ensure it's an object.
    if !settings.is_object() {
        bail!("{} is not a JSON object", settings_path.display());
    }

    // mcpServers.leet = { command, args, env }
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

    // Atomic write: write to tempfile, rename.
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
    // Do NOT overwrite a user-edited skill. Only write on first install,
    // or if the content exactly matches the previous stub (upgrade path).
    let write_now = match std::fs::read_to_string(&skill_md) {
        Ok(existing) => {
            // Upgrade only if the existing file is our stub or a previous version.
            existing.contains("managed by `leet setup claude-code`")
        }
        Err(_) => true, // doesn't exist yet
    };

    if write_now {
        // PROMPT_10d will replace this content with the real skill.
        // For now, write a functional placeholder so Claude Code sees something.
        std::fs::write(&skill_md, SKILL_STUB)?;
    }

    Ok(())
}

const SKILL_STUB: &str = r#"---
name: leet
description: Recall prior-session context for the current project via the leet-mcp server. Use `leet_recall` at the start of a session and `leet_remember` whenever a decision is made, a topic concludes, or the conversation shifts substantively.
---

# Leet — 1337 persistent context (v0.5.1)

This file is managed by `leet setup claude-code`. PROMPT_10d will expand
it with detailed triggering guidance. For now, call `leet_recall` at the
start of each session and `leet_remember` when you reach a natural
closing point for a topic.

The store lives in `.leet/store.bin` inside the project root. It is
append-only, crash-safe, and git-ignored by default.
"#;

// ─── status ──────────────────────────────────────────────────────────────────

fn status() -> Result<()> {
    println!("leet setup status");
    println!("─────────────────");

    // Binary.
    let bin = Command::new("which").arg("leet-mcp").output();
    match bin {
        Ok(out) if out.status.success() => {
            let path = String::from_utf8_lossy(&out.stdout).trim().to_string();
            println!("  leet-mcp binary:   ✓ {}", path);
        }
        _ => {
            println!("  leet-mcp binary:   ✗ not on PATH");
        }
    }

    // Claude dir.
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
        if configured { "configured" } else { "not configured (run `leet setup claude-code`)" }
    );

    // Global skill.
    let skill_md = claude_dir.join("skills/leet/SKILL.md");
    println!(
        "  Global skill:      {} {}",
        if skill_md.exists() { "✓" } else { "✗" },
        skill_md.display()
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

    // Remove mcpServers.leet if present.
    if settings_path.exists() {
        let text = std::fs::read_to_string(&settings_path)?;
        let mut settings: Value = serde_json::from_str(&text)
            .unwrap_or_else(|_| json!({}));
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

    // Remove global skill.
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

/// Return the user's home directory without pulling the `dirs` crate.
fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

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
            r#"{
              "mcpServers": {
                "other": {"command":"/path/to/other"}
              },
              "someOtherSetting": "keep me"
            }"#,
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
    fn uninstall_removes_only_leet_entry() {
        let tmp = tempfile::tempdir().unwrap();
        let settings_path = tmp.path().join("settings.json");
        std::fs::write(
            &settings_path,
            r#"{"mcpServers":{"leet":{"command":"/x"},"other":{"command":"/y"}}}"#,
        ).unwrap();

        // Simulate HOME = tmp so uninstall targets our fake dir.
        std::env::set_var("HOME", tmp.path());
        std::fs::create_dir_all(tmp.path().join(".claude")).unwrap();
        std::fs::rename(&settings_path, tmp.path().join(".claude/settings.json")).unwrap();

        uninstall("claude-code").unwrap();

        let text = std::fs::read_to_string(tmp.path().join(".claude/settings.json")).unwrap();
        let v: Value = serde_json::from_str(&text).unwrap();
        assert!(v["mcpServers"]["leet"].is_null());
        assert_eq!(v["mcpServers"]["other"]["command"].as_str().unwrap(), "/y");
    }
}
```

---

## FILE 2 — `leet-cli/src/cmd/mod.rs` (register subcommand)

Find the enum (or function) that lists subcommands. Add:

```rust
pub mod setup;
// ... existing modules

// In the Command enum (derive clap::Subcommand):
/// Install or configure leet integration with external tools.
Setup(cmd::setup::SetupArgs),

// In the dispatch match:
Command::Setup(args) => cmd::setup::run(args),
```

Adapt to the existing shape (some CLIs have a separate dispatcher; others inline). Whatever the pattern, make `leet setup ...` work.

---

## FILE 3 — `leet-cli/Cargo.toml` (dev dep)

Add `tempfile` under `[dev-dependencies]` if not already there:

```toml
[dev-dependencies]
tempfile = "3"
```

No other changes — `serde_json`, `anyhow`, `clap` are already present.

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-cli setup

# Manual smoke
cargo run -p leet-cli -- setup claude-code --install-binary --from .
cargo run -p leet-cli -- setup status
cat ~/.claude/settings.json | jq '.mcpServers.leet'
# Expected: command path + env with LEET_PROJECT_ROOT=${workspaceFolder}

# Re-run (idempotent)
cargo run -p leet-cli -- setup claude-code
# No duplicates, no errors.

# Uninstall
cargo run -p leet-cli -- setup uninstall claude-code
cat ~/.claude/settings.json | jq '.mcpServers'
# Expected: no `leet` key.
```

---

## NOTE ON `setup.py`

The existing `setup.py` at the repo root is for interactive `.env` configuration (unrelated to MCP). We intentionally do NOT modify it — the Rust `leet setup` subcommand is the canonical surface for Claude Code integration. Keeping `setup.py` for what it already does (env bootstrap) avoids coupling Python state to the MCP flow.

If later someone wants `pipx install leetlang` to transparently install the Rust binary too, that's a packaging concern handled in the Fase B (public distribution) phase, not here.

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt10c "CLI: leet setup claude-code (zero-friction installer, idempotent)"
# work
task project:1337 +prompt10c done

git add leet-cli/src/cmd/setup.rs leet-cli/src/cmd/mod.rs leet-cli/Cargo.toml
git commit -m "feat(cli): leet setup claude-code — zero-friction installer

One command configures the full Claude Code integration:

  leet setup claude-code [--install-binary]

Steps (all idempotent):
  1. Locate or (opt-in) cargo install the leet-mcp binary
  2. Detect Claude Code config dir (~/.claude or ~/.config/claude-code)
  3. Register leet-mcp in settings.json under mcpServers.leet with
     LEET_PROJECT_ROOT=\${workspaceFolder} for per-project store
  4. Install global skill stub at ~/.claude/skills/leet/SKILL.md
     (PROMPT_10d will replace content with the real skill)

Also:
  leet setup status                    — summary of what's configured
  leet setup uninstall claude-code     — clean removal (leaves .leet/ alone)

Settings.json edits are atomic (write-tempfile + rename) and preserve
unrelated keys. Re-running setup upgrades paths without duplication.

Part of Claude Code integration, sub-prompt 10c."
git push origin main
```

---

**END OF PROMPT_10c**
