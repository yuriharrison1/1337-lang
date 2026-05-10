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
                 the store.".into()
            ),
            NoWritePermission { path } => Some(format!(
                "Check ownership and permissions:\n  \
                 ls -la {parent}\n  \
                 Most likely fix: chown -R $USER {parent}",
                parent = path.parent().map(|p| p.display().to_string())
                    .unwrap_or_else(|| "<parent>".into())
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
            ClaudeCodeNotFound { .. } | CursorNotFound { .. }
                | VsCodeContinueNotFound { .. } | NoIdesDetected
                => Some("https://docs.leetlang.org/integrations"),
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
    /// 1 = error (fatal), 2 = warning (degraded but usable).
    pub fn exit_code(&self) -> i32 {
        use UserFacingError::*;
        match self {
            WMatrixMissing { .. } => 2,
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
/// Specific variants should be raised directly at call sites.
impl From<anyhow::Error> for UserFacingError {
    fn from(err: anyhow::Error) -> Self {
        let summary = err.to_string();
        let chain = err
            .chain()
            .skip(1)
            .map(|e| format!("  caused by: {}", e))
            .collect::<Vec<_>>()
            .join("\n");
        UserFacingError::Unexpected {
            summary,
            chain: if chain.is_empty() {
                "(no further details)".into()
            } else {
                chain
            },
        }
    }
}

/// Helper macro: bail with a specific `UserFacingError` variant.
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
