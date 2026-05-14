# PROMPT 12-P-02 — SHELL COMPLETIONS + MAN PAGES

Adicionar `leet completions <shell>` (bash/zsh/fish/elvish) e gerar man pages via `build.rs` + `clap_mangen`. Completions são geradas em runtime pelo binário; man pages são geradas em build time e instaladas junto com o binário.

**PRÉ-REQUISITOS**: 12-P-01 executado. `cargo build --workspace` verde.

**ESCOPO**: `leet-cli/Cargo.toml` + `leet-cli/build.rs` (novo) + `leet-cli/src/cmd/completions.rs` (novo) + registro em `mod.rs` e `main.rs`.

**Taskwarrior**: `+prompt12_P_02`.

---

## EXPERIÊNCIA QUE O USUÁRIO TEM

```
$ leet completions bash >> ~/.bash_completion.d/leet
$ leet completions zsh > ~/.zsh/completions/_leet
$ leet completions fish > ~/.config/fish/completions/leet.fish
$ leet completions elvish > ~/.config/elvish/completions/leet.elv

$ leet completions --help

Generate shell completion scripts for leet.

The completion script should be sourced or placed in your shell's completions
directory. This enables tab-completion for leet commands and flags.

Usage: leet completions <SHELL>

Arguments:
  <SHELL>  Shell to generate completions for [possible values: bash, zsh, fish, elvish]

Examples:
  # Bash
  leet completions bash >> ~/.bash_completion.d/leet
  echo 'source ~/.bash_completion.d/leet' >> ~/.bashrc

  # Zsh
  leet completions zsh > ~/.zsh/completions/_leet
  # Make sure ~/.zsh/completions is in fpath

  # Fish
  leet completions fish > ~/.config/fish/completions/leet.fish

See also:
  leet setup  — configure IDE integrations
```

Man pages:

```
$ man leet
$ man leet-encode
$ man leet-doctor
```

---

## IMPLEMENTAÇÃO

### `leet-cli/Cargo.toml` — adicionar deps

```toml
[dependencies]
# ...existing...
clap_complete = "4"

[build-dependencies]
clap = { version = "4", features = ["derive"] }
clap_mangen = "0.2"
```

### `leet-cli/src/cmd/completions.rs`

```rust
use clap::CommandFactory;
use clap_complete::{generate, Shell};
use std::str::FromStr;

use anyhow::{bail, Result};

pub fn run(shell_name: &str) -> Result<()> {
    let shell = Shell::from_str(shell_name).map_err(|_| {
        anyhow::anyhow!(
            "Unknown shell '{}'. Valid options: bash, zsh, fish, elvish",
            shell_name
        )
    })?;

    let mut cmd = crate::Cli::command();
    let bin_name = cmd.get_name().to_string();
    generate(shell, &mut cmd, &bin_name, &mut std::io::stdout());
    Ok(())
}
```

### `leet-cli/src/main.rs` — adicionar variant

No enum `Commands`:
```rust
/// Generate shell completion scripts
#[command(
    long_about = "Generate shell completion scripts for leet.\n\
\n\
The completion script should be sourced or placed in your shell's completions\n\
directory. This enables tab-completion for leet commands and flags.",
    after_help = "Examples:\n  \
  # Bash\n  \
  leet completions bash >> ~/.bash_completion.d/leet\n\
  echo 'source ~/.bash_completion.d/leet' >> ~/.bashrc\n\
\n  \
  # Zsh\n  \
  leet completions zsh > ~/.zsh/completions/_leet\n\
\n  \
  # Fish\n  \
  leet completions fish > ~/.config/fish/completions/leet.fish\n\
\n\
See also:\n  \
  leet setup  — configure IDE integrations"
)]
Completions {
    /// Shell to generate completions for
    #[arg(value_enum)]
    shell: String,
},
```

No match:
```rust
Commands::Completions { shell } => exit_on_err(cmd::completions::run(&shell)),
```

### `leet-cli/src/cmd/mod.rs`

```rust
pub mod completions;
```

### `leet-cli/build.rs` (novo arquivo)

```rust
use std::path::PathBuf;

fn main() {
    let out_dir = match std::env::var("CARGO_MANIFEST_DIR") {
        Ok(d) => PathBuf::from(d).join("../../target/man"),
        Err(_) => return,
    };

    std::fs::create_dir_all(&out_dir).ok();

    // We need to build the CLI struct without the actual binary.
    // clap_mangen works on the Command object directly.
    // Unfortunately, build.rs can't import the binary crate's types.
    // Strategy: duplicate the top-level command definition in build.rs,
    // or use a shared crate. Simplest: generate a stub command tree here.

    // NOTE: This requires manually keeping the command list in sync.
    // A cleaner approach uses a workspace crate that exposes cli_command().
    // For now, generate only the top-level man page from a stub.

    let cmd = build_stub_command();
    let man = clap_mangen::Man::new(cmd.clone());
    let mut buf = vec![];
    man.render(&mut buf).ok();
    std::fs::write(out_dir.join("leet.1"), buf).ok();

    // Generate subcommand man pages
    for sub in cmd.get_subcommands() {
        let sub_man = clap_mangen::Man::new(sub.clone());
        let mut buf = vec![];
        sub_man.render(&mut buf).ok();
        let name = format!("leet-{}.1", sub.get_name());
        std::fs::write(out_dir.join(&name), buf).ok();
    }
}

fn build_stub_command() -> clap::Command {
    use clap::{Arg, Command};
    Command::new("leet")
        .version(env!("CARGO_PKG_VERSION"))
        .about("1337 language CLI toolkit")
        .subcommand(Command::new("encode").about("Project text to sem[32]"))
        .subcommand(Command::new("decode").about("Interpret sem[32] as narrative"))
        .subcommand(Command::new("dist").about("Cosine distance between two COGONs"))
        .subcommand(Command::new("blend").about("Blend two COGONs"))
        .subcommand(Command::new("axes").about("List the 32 canonical axes"))
        .subcommand(Command::new("zero").about("Print COGON_ZERO"))
        .subcommand(Command::new("validate").about("Validate a 1337 message"))
        .subcommand(Command::new("bench").about("Run benchmarks"))
        .subcommand(Command::new("inspect").about("Storage statistics"))
        .subcommand(Command::new("health").about("Quick liveness check (deprecated, use doctor)"))
        .subcommand(Command::new("version").about("Print version information"))
        .subcommand(Command::new("chat").about("Interactive REPL (developer/demo only)"))
        .subcommand(Command::new("doctor").about("System health check"))
        .subcommand(Command::new("setup").about("Configure IDE integrations"))
        .subcommand(Command::new("absorb").about("Import session history"))
        .subcommand(Command::new("consolidate").about("Manage consolidation pyramid"))
        .subcommand(Command::new("calibrate").about("Download and manage W matrix"))
        .subcommand(Command::new("completions").about("Generate shell completion scripts"))
        .subcommand(Command::new("help").about("Show command overview by category"))
}
```

**Nota sobre build.rs**: A abordagem "stub" é simples mas pode desincronizar. Alternativa melhor: criar um crate `leet-cli-def` que expõe `build_cli() -> clap::Command` e tanto `main.rs` quanto `build.rs` usam. Isso é refactor adicional — deixar para depois ou implementar direto se o dev preferir.

---

## ATUALIZAR `leet help` PARA INCLUIR `completions`

Em `leet-cli/src/cmd/help.rs`, adicionar `completions` na categoria "Setup & diagnostics":

```rust
// Na função build_categories():
("Setup & diagnostics", vec![
    CommandInfo { name: "doctor",      about: "System health check" },
    CommandInfo { name: "setup",       about: "Configure IDE integrations (Claude Code, Cursor, VS Code)" },
    CommandInfo { name: "calibrate",   about: "Download and manage W matrix" },
    CommandInfo { name: "completions", about: "Generate shell completion scripts" },
    CommandInfo { name: "version",     about: "Print version information" },
    CommandInfo { name: "health",      about: "Quick liveness check (deprecated, use doctor)" },
]),
```

---

## TESTES

Em `leet-cli/src/cmd/completions.rs`:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bash_completion_produces_output() {
        // Capture stdout
        let result = run("bash");
        assert!(result.is_ok());
    }

    #[test]
    fn unknown_shell_errors() {
        let result = run("powershell");
        assert!(result.is_err());
        let msg = result.unwrap_err().to_string();
        assert!(msg.contains("powershell") || msg.contains("Unknown"));
    }

    #[test]
    fn all_valid_shells_accepted() {
        for shell in &["bash", "zsh", "fish", "elvish"] {
            // We only check it doesn't fail with "Unknown shell"
            // Stdout capture not needed — we just check no error
            // (full output test would require capturing stdout)
            let s = clap_complete::Shell::from_str(shell);
            assert!(s.is_ok(), "shell '{}' should be valid", shell);
        }
    }
}
```

---

## GATES

```bash
# Build com novas deps
cargo build -p leet-cli
# Esperado: 0 errors, 0 warnings

# Completions command existe
./target/debug/leet completions --help
# Esperado: output com shells disponíveis

# Bash completions geram output
./target/debug/leet completions bash | wc -l
# Esperado: > 10 linhas

# Zsh completions começam corretamente
./target/debug/leet completions zsh | head -1
# Esperado: linha começando com '#compdef'

# Fish completions têm 'complete -c leet'
./target/debug/leet completions fish | grep -c "complete -c leet"
# Esperado: > 0

# Shell inválido dá erro claro
./target/debug/leet completions powershell 2>&1 | grep -q -i "unknown\|invalid\|possible"
# Esperado: mensagem de erro com shells válidos

# Man pages gerados em build
ls target/man/leet*.1 2>/dev/null | wc -l
# Esperado: > 5 (pelo menos main + 5 subcomandos)

# Testes verdes
cargo test --workspace
# Esperado: todos OK
```
