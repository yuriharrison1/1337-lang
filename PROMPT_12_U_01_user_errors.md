# PROMPT 12-U-01 — MENSAGENS DE ERRO HUMANAS

Substituir o uso direto de `anyhow!()` propagado pra usuário por um enum centralizado `UserFacingError` em `leet-core/src/error.rs`. Cada erro CLI/MCP terá: mensagem orientada a ação (PT/EN), sugestão de correção, e link opcional pra docs. Erros internos continuam usando `anyhow` — só o que **chega ao usuário** muda.

**PRÉ-REQUISITOS**: `cargo test --workspace` verde após 12-T-01 e 12-T-02 executados. Workspace limpo, sem nomes errados.

**ESCOPO**: 1 arquivo novo + edits cirúrgicos em ~6 arquivos existentes. Mudança puramente de UX — não toca em lógica.

**Taskwarrior**: `+prompt12_U_01`.

---

## CONTEXTO E MOTIVAÇÃO

Hoje, quando algo dá errado em uma chamada CLI ou MCP tool, o usuário recebe stack traces de `anyhow`:

```
Error: opening /home/yuri/.claude/settings.json

Caused by:
    0: parsing /home/yuri/.claude/settings.json — this file has invalid JSON. Fix it or back it up and re-run setup.
    1: expected `,` or `}` at line 14 column 5
```

Esse output é OK pra debugging mas terrível pra usuário. v1.0 precisa que falhas comuns retornem **algo que o usuário consegue **agir** sobre**, sem ler stack trace ou googlar mensagem.

Solução: enum tipado de erros user-facing, com `Display` cuidadoso, sugestão de fix, e fallback gracioso quando `anyhow` ainda for a fonte.

**Não estamos eliminando `anyhow`** — só interceptando antes da fronteira CLI/MCP.

---

## ARQUIVO 1 (NOVO) — `leet-core/src/user_error.rs`

Novo arquivo com o enum centralizado.

```rust
//! User-facing error type. Each variant carries:
//!   - a one-line summary (what went wrong)
//!   - a suggested action (what to do)
//!   - an optional docs link
//!
//! CLI/MCP boundaries convert internal `anyhow::Error` into `UserFacingError`
//! before printing. Internal code continues to use `anyhow` freely.

use std::fmt;
use std::path::PathBuf;

/// All user-facing failure modes in v1.0.
/// New variants are additive — never remove or renumber.
#[derive(Debug)]
pub enum UserFacingError {
    // ── Setup / installation ──────────────────────────────────────────────
    ClaudeCodeNotFound {
        searched: Vec<PathBuf>,
    },
    CursorNotFound {
        searched: Vec<PathBuf>,
    },
    VsCodeContinueNotFound {
        searched: Vec<PathBuf>,
    },
    NoIdesDetected,
    BinaryNotOnPath {
        binary: String,
    },
    SettingsFileMalformed {
        path: PathBuf,
        details: String,
    },

    // ── Storage / store.bin ───────────────────────────────────────────────
    StoreCorrupted {
        path: PathBuf,
        details: String,
    },
    StoreVersionMismatch {
        path: PathBuf,
        found_version: u8,
        expected_version: u8,
    },
    IndexOutOfSync {
        store_path: PathBuf,
        index_path: PathBuf,
        store_count: usize,
        index_count: usize,
    },
    NoWritePermission {
        path: PathBuf,
    },

    // ── W matrix / calibration ────────────────────────────────────────────
    WMatrixMissing {
        expected_at: PathBuf,
    },
    WMatrixCorrupted {
        path: PathBuf,
        details: String,
    },
    EmbeddingProviderUnavailable {
        provider: String,
        reason: String,
    },

    // ── API / network ─────────────────────────────────────────────────────
    AnthropicApiKeyMissing,
    OpenAiApiKeyMissing,
    NetworkUnreachable {
        url: String,
    },

    // ── Project state ─────────────────────────────────────────────────────
    NotInProject {
        cwd: PathBuf,
    },
    ProjectAlreadyInitialized {
        leet_dir: PathBuf,
    },

    // ── Council / Mundo A ─────────────────────────────────────────────────
    CouncilNoPersonasMatched {
        query_summary: String,
        threshold: f32,
    },
    CouncilTimeout {
        elapsed_ms: u64,
        timeout_ms: u64,
    },

    // ── Generic fallback ──────────────────────────────────────────────────
    /// Used when an internal `anyhow::Error` reaches the user boundary
    /// without being mapped to a specific variant. Carries the chain.
    Unexpected {
        summary: String,
        chain: String,
    },
}

impl UserFacingError {
    /// Short one-line summary (what went wrong).
    pub fn summary(&self) -> String {
        use UserFacingError::*;
        match self {
            ClaudeCodeNotFound { .. } => "Claude Code not found on this machine.".into(),
            CursorNotFound { .. } => "Cursor not found on this machine.".into(),
            VsCodeContinueNotFound { .. } => "VS Code with Continue.dev not detected.".into(),
            NoIdesDetected => "No supported IDEs detected.".into(),
            BinaryNotOnPath { binary } => format!("`{}` is not on your PATH.", binary),
            SettingsFileMalformed { path, .. } => format!(
                "{} contains invalid JSON.",
                path.display()
            ),
            StoreCorrupted { path, .. } => format!(
                "The leet store at {} is corrupted.",
                path.display()
            ),
            StoreVersionMismatch { found_version, expected_version, .. } => format!(
                "Store version {} doesn't match expected version {}.",
                found_version, expected_version
            ),
            IndexOutOfSync { store_count, index_count, .. } => format!(
                "Store has {} records but index has {} entries — out of sync.",
                store_count, index_count
            ),
            NoWritePermission { path } => format!(
                "No permission to write to {}.",
                path.display()
            ),
            WMatrixMissing { .. } => "W matrix not available — using degraded keyword fallback.".into(),
            WMatrixCorrupted { path, .. } => format!(
                "W matrix at {} is corrupted.",
                path.display()
            ),
            EmbeddingProviderUnavailable { provider, .. } => format!(
                "Embedding provider `{}` is not available.",
                provider
            ),
            AnthropicApiKeyMissing => "ANTHROPIC_API_KEY environment variable is not set.".into(),
            OpenAiApiKeyMissing => "OPENAI_API_KEY environment variable is not set.".into(),
            NetworkUnreachable { url } => format!("Cannot reach {}.", url),
            NotInProject { .. } => "Not inside a project directory.".into(),
            ProjectAlreadyInitialized { .. } => "Project is already initialized.".into(),
            CouncilNoPersonasMatched { .. } => "No agent personas matched your query.".into(),
            CouncilTimeout { .. } => "Council timed out waiting for agent responses.".into(),
            Unexpected { summary, .. } => summary.clone(),
        }
    }

    /// Suggested next action (what to do).
    pub fn suggestion(&self) -> Option<String> {
        use UserFacingError::*;
        match self {
            ClaudeCodeNotFound { searched } => Some(format!(
                "Install Claude Code from https://claude.ai/code, or pass --claude-dir <path> if installed elsewhere.\n\
                 Searched: {}",
                searched.iter().map(|p| p.display().to_string()).collect::<Vec<_>>().join(", ")
            )),
            CursorNotFound { searched } => Some(format!(
                "Install Cursor from https://cursor.com, or pass --cursor-dir <path>.\n\
                 Searched: {}",
                searched.iter().map(|p| p.display().to_string()).collect::<Vec<_>>().join(", ")
            )),
            VsCodeContinueNotFound { .. } => Some(
                "Install VS Code from https://code.visualstudio.com and the Continue extension \
                 from https://continue.dev. Then re-run `leet setup`.".into()
            ),
            NoIdesDetected => Some(
                "Install at least one supported IDE (Claude Code, Cursor, or VS Code with \
                 Continue.dev). Then re-run `leet setup`.".into()
            ),
            BinaryNotOnPath { binary } => Some(format!(
                "Run `cargo install --path {bin}` from the workspace root, or check that \
                 ~/.cargo/bin is in your PATH.",
                bin = binary
            )),
            SettingsFileMalformed { path, details } => Some(format!(
                "Fix the JSON manually or back up the file:\n  \
                 cp {path} {path}.bak\n  \
                 Then re-run `leet setup`.\n  \
                 Parser error: {details}",
                path = path.display(),
                details = details
            )),
            StoreCorrupted { path, .. } => Some(format!(
                "Run `leet doctor --auto-fix` to attempt recovery, or back up and reset:\n  \
                 mv {path} {path}.bak\n  \
                 Recall will start fresh; .bak file preserves your data.",
                path = path.display()
            )),
            StoreVersionMismatch { found_version, .. } => Some(format!(
                "This store was created by leet v{}. Run `leet migrate` to convert, or \
                 back up and start fresh with `mv .leet/store.bin .leet/store.bin.v{}.bak`.",
                found_version, found_version
            )),
            IndexOutOfSync { .. } => Some(
                "Run `leet consolidate rebuild-index --yes` to regenerate the index from \
                 the store. (Lossy: consolidation history is lost.)".into()
            ),
            NoWritePermission { path } => Some(format!(
                "Check ownership and permissions:\n  \
                 ls -la {parent}\n  \
                 Most likely fix: chown -R $USER {parent}",
                parent = path.parent().map(|p| p.display().to_string()).unwrap_or_else(|| "<parent>".into())
            )),
            WMatrixMissing { .. } => Some(
                "For best quality, run `leet calibrate --download` to fetch the official W \
                 matrix. Until then, leet falls back to keyword heuristics (lower quality).".into()
            ),
            WMatrixCorrupted { .. } => Some(
                "Re-download with `leet calibrate --download --force`.".into()
            ),
            EmbeddingProviderUnavailable { provider, reason } => Some(format!(
                "Provider `{}` failed: {}\n  \
                 Try a different provider via LEET_EMBEDDING_PROVIDER=hash (no setup) \
                 or sentence-transformers (requires `pip install sentence-transformers`).",
                provider, reason
            )),
            AnthropicApiKeyMissing => Some(
                "Set ANTHROPIC_API_KEY in your environment:\n  \
                 export ANTHROPIC_API_KEY=sk-ant-...\n  \
                 Get a key at https://console.anthropic.com/settings/keys.".into()
            ),
            OpenAiApiKeyMissing => Some(
                "Set OPENAI_API_KEY in your environment, or switch providers via \
                 LEET_EMBEDDING_PROVIDER=sentence-transformers.".into()
            ),
            NetworkUnreachable { .. } => Some(
                "Check your internet connection. If behind a corporate firewall, ensure \
                 the relevant domains are allowed.".into()
            ),
            NotInProject { cwd } => Some(format!(
                "Either:\n  \
                 - cd into a project directory, or\n  \
                 - pass --project <path> to specify one.\n  \
                 Current directory: {}",
                cwd.display()
            )),
            ProjectAlreadyInitialized { leet_dir } => Some(format!(
                "If you want to start fresh, remove and re-create:\n  \
                 rm -rf {dir}\n  \
                 (This deletes all stored memory for this project.)",
                dir = leet_dir.display()
            )),
            CouncilNoPersonasMatched { threshold, .. } => Some(format!(
                "Try lowering --threshold (currently {:.2}, default 0.6) or rephrasing your \
                 query to be more specific.",
                threshold
            )),
            CouncilTimeout { timeout_ms, .. } => Some(format!(
                "Try a smaller council with --max-personas 3, or increase timeout via \
                 LEET_COUNCIL_TIMEOUT_MS={}",
                timeout_ms * 2
            )),
            Unexpected { .. } => Some(
                "This is likely a bug. Please report at https://github.com/leetlang/leet/issues \
                 with the full error chain below.".into()
            ),
        }
    }

    /// Optional docs URL for deeper context.
    pub fn docs_url(&self) -> Option<&'static str> {
        use UserFacingError::*;
        match self {
            ClaudeCodeNotFound { .. } | CursorNotFound { .. } | VsCodeContinueNotFound { .. }
                | NoIdesDetected => Some("https://docs.leetlang.org/integrations"),
            StoreCorrupted { .. } | StoreVersionMismatch { .. } | IndexOutOfSync { .. }
                => Some("https://docs.leetlang.org/storage"),
            WMatrixMissing { .. } | WMatrixCorrupted { .. }
                => Some("https://docs.leetlang.org/calibration"),
            CouncilNoPersonasMatched { .. } | CouncilTimeout { .. }
                => Some("https://docs.leetlang.org/council"),
            _ => None,
        }
    }

    /// Exit code for CLI use.
    /// 1 = error (caller should abort), 2 = warning (degraded but usable).
    pub fn exit_code(&self) -> i32 {
        use UserFacingError::*;
        match self {
            // Warnings — degraded operation, not fatal
            WMatrixMissing { .. } => 2,
            // Everything else: fatal
            _ => 1,
        }
    }
}

impl fmt::Display for UserFacingError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.summary())?;
        if let Some(suggestion) = self.suggestion() {
            write!(f, "\n\nWhat to do:\n  {}", suggestion.replace('\n', "\n  "))?;
        }
        if let Some(url) = self.docs_url() {
            write!(f, "\n\nMore info: {}", url)?;
        }
        if let UserFacingError::Unexpected { chain, .. } = self {
            write!(f, "\n\nError chain:\n{}", chain)?;
        }
        Ok(())
    }
}

impl std::error::Error for UserFacingError {}

/// Convert any `anyhow::Error` into `UserFacingError::Unexpected` as fallback.
/// Specific variants should be raised directly via `bail_user!` in call sites.
impl From<anyhow::Error> for UserFacingError {
    fn from(err: anyhow::Error) -> Self {
        let summary = err.to_string();
        let chain = err.chain()
            .skip(1)
            .map(|e| format!("  caused by: {}", e))
            .collect::<Vec<_>>()
            .join("\n");
        UserFacingError::Unexpected {
            summary,
            chain: if chain.is_empty() { "(no further details)".into() } else { chain },
        }
    }
}

/// Helper macro: bail with a specific UserFacingError variant.
/// Usage: `bail_user!(UserFacingError::ClaudeCodeNotFound { searched });`
#[macro_export]
macro_rules! bail_user {
    ($err:expr) => {
        return Err(::anyhow::Error::new($err))
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summary_includes_path_for_corrupted_store() {
        let err = UserFacingError::StoreCorrupted {
            path: PathBuf::from("/x/store.bin"),
            details: "magic bytes".into(),
        };
        assert!(err.summary().contains("/x/store.bin"));
    }

    #[test]
    fn suggestion_present_for_known_variants() {
        let err = UserFacingError::ClaudeCodeNotFound { searched: vec![] };
        assert!(err.suggestion().is_some());
        assert!(err.suggestion().unwrap().contains("claude.ai/code"));
    }

    #[test]
    fn unexpected_carries_chain() {
        let inner = anyhow::anyhow!("inner thing")
            .context("middle thing")
            .context("outer thing");
        let user: UserFacingError = inner.into();
        match user {
            UserFacingError::Unexpected { summary, chain } => {
                assert!(summary.contains("outer thing"));
                assert!(chain.contains("middle thing"));
                assert!(chain.contains("inner thing"));
            }
            _ => panic!("expected Unexpected variant"),
        }
    }

    #[test]
    fn display_format_has_summary_and_action() {
        let err = UserFacingError::AnthropicApiKeyMissing;
        let s = format!("{}", err);
        assert!(s.contains("ANTHROPIC_API_KEY"));
        assert!(s.contains("What to do:"));
    }

    #[test]
    fn w_matrix_missing_is_warning_not_fatal() {
        let err = UserFacingError::WMatrixMissing {
            expected_at: PathBuf::from("/foo"),
        };
        assert_eq!(err.exit_code(), 2);
    }

    #[test]
    fn most_errors_are_fatal() {
        let err = UserFacingError::ClaudeCodeNotFound { searched: vec![] };
        assert_eq!(err.exit_code(), 1);
    }
}
```

---

## ARQUIVO 2 — `leet-core/src/lib.rs` (re-export)

Adicionar:

```rust
pub mod user_error;
pub use user_error::UserFacingError;
```

---

## ARQUIVO 3 — `leet-cli/src/main.rs` (interceptar erros)

Localizar a função `main()`. Antes:

```rust
fn main() -> Result<()> {
    // ... existing setup ...
    cmd::dispatch(args)?;
    Ok(())
}
```

Depois:

```rust
fn main() {
    // ... existing setup ...
    let result = cmd::dispatch(args);

    if let Err(err) = result {
        let user_err: leet_core::UserFacingError = err.downcast::<leet_core::UserFacingError>()
            .unwrap_or_else(|anyhow_err| anyhow_err.into());

        eprintln!("\n{}\n", user_err);
        std::process::exit(user_err.exit_code());
    }
}
```

Mudança importante: `main` deixa de retornar `Result<()>` (não imprimimos mais o `Debug` automático do anyhow). Agora **a gente controla o output**.

---

## ARQUIVO 4 — `leet-cli/src/cmd/setup.rs` (usar variantes específicas)

Localizar locais onde erros são propagados ao usuário e substituir por `bail_user!`. Exemplos:

### 4.1 `detect_claude_dir()`

```rust
// ANTES
fn detect_claude_dir() -> Result<PathBuf> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let primary = home.join(".claude");
    if primary.exists() { return Ok(primary); }
    let alt = home.join(".config/claude-code");
    if alt.exists() { return Ok(alt); }
    std::fs::create_dir_all(&primary)
        .with_context(|| format!("creating {}", primary.display()))?;
    Ok(primary)
}

// DEPOIS
fn detect_claude_dir() -> Result<PathBuf> {
    let home = dirs_home().ok_or_else(|| anyhow!("no HOME directory"))?;
    let primary = home.join(".claude");
    let alt = home.join(".config/claude-code");
    let searched = vec![primary.clone(), alt.clone()];

    if primary.exists() { return Ok(primary); }
    if alt.exists() { return Ok(alt); }

    // Neither exists. Determine if we should auto-create or fail.
    // Auto-create only if `claude` binary is on PATH (heuristic for installed-but-not-run).
    if has_claude_binary() {
        std::fs::create_dir_all(&primary)
            .with_context(|| format!("creating {}", primary.display()))?;
        Ok(primary)
    } else {
        bail_user!(leet_core::UserFacingError::ClaudeCodeNotFound { searched })
    }
}

fn has_claude_binary() -> bool {
    Command::new("which").arg("claude").output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}
```

### 4.2 `register_mcp_server()` — settings file malformado

```rust
// ANTES
let mut settings: Value = if settings_path.exists() {
    let text = std::fs::read_to_string(&settings_path)?;
    if text.trim().is_empty() {
        json!({})
    } else {
        serde_json::from_str(&text).with_context(|| {
            format!("parsing {} — this file has invalid JSON. Fix it or back it up and re-run setup.",
                    settings_path.display())
        })?
    }
} else {
    json!({})
};

// DEPOIS
let mut settings: Value = if settings_path.exists() {
    let text = std::fs::read_to_string(&settings_path)?;
    if text.trim().is_empty() {
        json!({})
    } else {
        match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(e) => bail_user!(leet_core::UserFacingError::SettingsFileMalformed {
                path: settings_path.clone(),
                details: e.to_string(),
            }),
        }
    }
} else {
    json!({})
};
```

### 4.3 `locate_or_install_mcp_binary()` — binary missing

```rust
// ANTES
if !install {
    bail!(
        "leet-mcp not found on PATH. Either:\n  - run `cargo install --path leet-mcp` ...
    );
}

// DEPOIS
if !install {
    bail_user!(leet_core::UserFacingError::BinaryNotOnPath {
        binary: "leet-mcp".to_string(),
    });
}
```

---

## ARQUIVO 5 — `leet-cli/src/cmd/consolidate.rs`

```rust
// store.rs corrupt detected:
match decode_record(&data) {
    Ok(rec) => {...},
    Err(e) => {
        bail_user!(leet_core::UserFacingError::StoreCorrupted {
            path: store_path.clone(),
            details: e.to_string(),
        });
    }
}
```

E onde index está fora de sync:

```rust
if entries.len() != store_record_count {
    bail_user!(leet_core::UserFacingError::IndexOutOfSync {
        store_path: store_path.clone(),
        index_path: index_path.clone(),
        store_count: store_record_count,
        index_count: entries.len(),
    });
}
```

---

## ARQUIVO 6 — `leet-mcp/src/server.rs` (graceful degradation)

MCP tools nunca devem **abortar** o server por erro de usuário — devem retornar `ToolResult { is_error: true, ... }`. Adicionar conversão:

```rust
async fn handle_tools_call(...) -> JsonRpcResponse {
    // ... existing code ...

    match result {
        Ok(tr) => JsonRpcResponse::ok(id, serde_json::to_value(tr).unwrap()),
        Err(e) => {
            let user_err: leet_core::UserFacingError = e.downcast::<leet_core::UserFacingError>()
                .unwrap_or_else(|a| a.into());
            let tr = ToolResult::error(format!("{}", user_err));
            JsonRpcResponse::ok(id, serde_json::to_value(tr).unwrap())
        }
    }
}
```

---

## ARQUIVO 7 — `leet-bridge/src/projector.rs` (W matrix missing)

```rust
// ANTES
if !path.exists() {
    bail!("W matrix not found at {}", path.display());
}

// DEPOIS
if !path.exists() {
    bail_user!(leet_core::UserFacingError::WMatrixMissing {
        expected_at: path.clone(),
    });
}
```

---

## VERIFICATION

```bash
cargo build --workspace
# Esperado: 0 errors, 0 warnings.

cargo test --workspace
# Esperado: ainda ≥ 247 testes passando + os 6 novos do user_error.

# Smoke test: erros bonitos em situações reais
mkdir /tmp/leet-no-permission && chmod 444 /tmp/leet-no-permission
LEET_PROJECT_ROOT=/tmp/leet-no-permission ./target/debug/leet-mcp 2>&1 | head
# Esperado: mensagem humana explicando "No permission to write to..."

# Stack trace some quando erro é específico
./target/debug/leet setup claude-code 2>&1 | grep -i "stack\|backtrace"
# Esperado: nada (zero matches)

# Erros mantêm exit code correto
./target/debug/leet calibrate --download 2>&1; echo "exit=$?"
# Esperado: exit=2 (warning) se W ausente; exit=1 se erro real
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt12_U_01 "User-facing error type with actionable suggestions"
task project:1337 +prompt12_U_01 done

git add leet-core/src/user_error.rs leet-core/src/lib.rs \
        leet-cli/src/main.rs leet-cli/src/cmd/setup.rs \
        leet-cli/src/cmd/consolidate.rs \
        leet-mcp/src/server.rs leet-bridge/src/projector.rs

git commit -m "feat(ux): UserFacingError enum with actionable suggestions

Replaces direct anyhow propagation at CLI/MCP boundaries with a
typed enum carrying summary + suggestion + optional docs URL per variant.

Variants in v1.0:
  - Setup/install (4 variants)
  - Storage corruption (4 variants)
  - W matrix / calibration (3 variants)
  - API/network (3 variants)
  - Project state (2 variants)
  - Council (2 variants)
  - Unexpected (anyhow fallback, preserves chain)

Architecture:
  - Internal code keeps using anyhow freely
  - Boundaries (CLI main, MCP tool handler) intercept and convert
  - Display format: summary + 'What to do:' + optional docs link
  - Exit codes: 1 fatal, 2 warning (degraded but usable)

bail_user! macro added for ergonomic raising of specific variants.

Part of Phase 12-U (UX): humanize the developer experience.
First step toward leet doctor and other diagnostic UX in 12-U-02+."
git push origin main
```

---

**END OF PROMPT_12-U-01**
