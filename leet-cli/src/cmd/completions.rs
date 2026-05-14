//! `leet completions` — generate shell completion scripts.

use anyhow::Result;
use clap::CommandFactory;
use clap_complete::{generate, Shell};

pub fn run(shell_name: &str) -> Result<()> {
    let shell: Shell = shell_name.parse().map_err(|_| {
        anyhow::anyhow!(
            "Unknown shell '{}'. Valid options: bash, zsh, fish, elvish, powershell",
            shell_name
        )
    })?;

    let mut cmd = crate::Cli::command();
    let bin_name = cmd.get_name().to_string();
    generate(shell, &mut cmd, &bin_name, &mut std::io::stdout());
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_shell_errors() {
        let result = run("nushell");
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("nushell") || msg.contains("Unknown") || msg.contains("invalid"));
    }

    #[test]
    fn all_valid_shells_parse() {
        for shell in &["bash", "zsh", "fish", "elvish", "powershell"] {
            let parsed: Result<Shell, _> = shell.parse();
            assert!(parsed.is_ok(), "shell '{}' should be valid", shell);
        }
    }
}
