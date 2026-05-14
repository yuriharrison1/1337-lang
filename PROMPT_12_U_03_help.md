# PROMPT 12-U-03 — `--help` DECENTE EM TODOS OS SUBCOMANDOS

Auditar e melhorar `--help` dos 17 subcomandos da CLI. Cada um terá: descrição em 1 linha, descrição longa explicando quando usar, pelo menos 2 exemplos de uso, e notas de cuidados/alternativas. Tudo via clap derives — sem mecanismo paralelo. Adicionar `leet help` interativo que lista categorias.

**PRÉ-REQUISITOS**: 12-U-01 e 12-U-02 executados.

**ESCOPO**: edits em ~17 arquivos `cmd/*.rs` (atualizar doc strings dos `Args`), 1 arquivo novo (`cmd/help.rs`), 1 edit no `cmd/mod.rs` pra registrar.

**Taskwarrior**: `+prompt12_U_03`.

---

## INVENTÁRIO ATUAL (auditado no zip)

17 subcomandos existentes em `leet-cli/src/cmd/`:

| Categoria | Subcomando |
|---|---|
| **Setup & diagnóstico** | `setup`, `doctor` (novo em 12-U-02), `version`, `health` |
| **Operações de memória** | `absorb`, `consolidate` |
| **Inspeção** | `axes`, `zero`, `inspect` |
| **Álgebra** | `encode`, `decode`, `dist`, `blend`, `validate` |
| **Calibração** | `bench` |
| **Outros** | `chat` |

Faltam (entram nas próximas fases): `recall`, `remember`, `calibrate`. **Não inventar agora** — só estes 17.

---

## ANATOMIA DE UM `--help` BOM

Pra cada subcomando, o que `--help` deve mostrar:

```
$ leet encode --help

Project natural-language text into a 32-axis canonical sem vector.

Use this when you want to inspect how leet sees a piece of text — useful
for debugging projection quality, or feeding raw COGONs to other tools.
For routine memory operations, use leet_remember via MCP instead.

Usage: leet encode [OPTIONS] <TEXT>

Arguments:
  <TEXT>  Text to encode. Use '-' to read from stdin.

Options:
      --json           Output as JSON instead of human-readable
      --top <N>        Show only the top N most-deviated axes (default: 5)
  -h, --help           Print help

Examples:
  # Inspect a single sentence
  leet encode "Decided to use Postgres"

  # Pipe from another command
  echo "rolling back to commit abc123" | leet encode -

  # Get the full sem[32] as JSON
  leet encode --json "ATLAS thinks we should pivot"

See also:
  leet decode  — reverse a sem vector back to top-axis narrative
  leet dist    — compute distance between two encoded vectors
```

Quatro elementos essenciais:
1. **Linha 1**: descrição short (mostra em `leet --help`)
2. **Parágrafo about**: quando usar / quando não usar
3. **Examples**: 2-3 casos reais, copiáveis
4. **See also**: comandos relacionados pra discoverability

clap suporta tudo isso via attribute macros — `#[command(about, long_about)]` + `#[command(after_help)]`.

---

## TEMPLATE DE EDIT POR SUBCOMANDO

Cada arquivo `cmd/<nome>.rs` tem hoje algo como:

```rust
#[derive(Debug, Args)]
pub struct EncodeArgs {
    pub text: String,
    #[arg(long)]
    pub json: bool,
}
```

Vira:

```rust
#[derive(Debug, Args)]
#[command(
    about = "Project natural-language text into a 32-axis canonical sem vector",
    long_about = "Project natural-language text into a 32-axis canonical sem vector.\n\
\n\
Use this when you want to inspect how leet sees a piece of text — useful\n\
for debugging projection quality, or feeding raw COGONs to other tools.\n\
For routine memory operations, use leet_remember via MCP instead.",
    after_help = "Examples:\n  \
  # Inspect a single sentence\n  \
  leet encode \"Decided to use Postgres\"\n\
\n  \
  # Pipe from another command\n  \
  echo \"rolling back to commit abc123\" | leet encode -\n\
\n  \
  # Get the full sem[32] as JSON\n  \
  leet encode --json \"ATLAS thinks we should pivot\"\n\
\n\
See also:\n  \
  leet decode  — reverse a sem vector back to top-axis narrative\n  \
  leet dist    — compute distance between two encoded vectors"
)]
pub struct EncodeArgs {
    /// Text to encode. Use '-' to read from stdin.
    pub text: String,

    /// Output as JSON instead of human-readable
    #[arg(long)]
    pub json: bool,

    /// Show only the top N most-deviated axes (default: 5)
    #[arg(long, default_value = "5")]
    pub top: usize,
}
```

**Observações importantes**:
- `about` é a linha curta (vai pro `leet --help`)
- `long_about` é o parágrafo (vai pro `leet encode --help`)
- `after_help` traz examples + see also
- Cada field com `///` doc comment vira descrição na seção Options/Arguments
- **`-h, --help` é gerado automaticamente pelo clap derive**, não inventar

---

## CONTEÚDO POR SUBCOMANDO

Pra cada um dos 17, segue o `about` + `long_about` + `after_help`. **Os Args structs ficam idênticos em estrutura** — só adiciona os attributes do `#[command(...)]`.

### 1. `setup`

```
about: Configure leet for one or more IDEs (Claude Code, Cursor, VS Code+Continue)

long_about:
Configure leet for one or more IDEs (Claude Code, Cursor, VS Code+Continue).

Without arguments, auto-detects installed IDEs and configures them all.
With a target argument, configures only that IDE. Idempotent — running
twice doesn't duplicate entries.

after_help:
Examples:
  # Auto-detect and configure all installed IDEs
  leet setup

  # Configure only Claude Code
  leet setup claude-code

  # See what's currently configured
  leet setup status

  # Reverse a configuration
  leet setup uninstall cursor

See also:
  leet doctor  — verify configuration health
```

### 2. `doctor`

```
about: Run a system health check across binaries, IDEs, store, network

long_about:
Run a system health check across binaries, IDEs, store, network.

Verifies that everything leet needs is in place: binaries on PATH,
IDE configs valid, skill installed, project store readable, network
reachable. Outputs human-readable by default, JSON for automation.

Exit codes: 0 all OK, 1 errors present, 2 warnings only.

after_help:
Examples:
  # Run all checks
  leet doctor

  # Skip network checks (offline mode)
  leet doctor --offline

  # Attempt automatic fixes for known issues
  leet doctor --auto-fix

  # Output for CI / scripts
  leet doctor --json | jq .status

See also:
  leet setup     — configure missing IDEs
  leet calibrate — download W matrix if missing
```

### 3. `version`

```
about: Print version information for all installed leet components

long_about:
Print version information for all installed leet components.

Useful for bug reports — paste the output to confirm exactly which
versions are running. Shows leet, leet-mcp, leet-server, and the
spec version implemented.

after_help:
Examples:
  leet version
  leet version --json

See also:
  leet doctor  — full health check including version mismatches
```

### 4. `health`

```
about: Quick liveness check for the running leet-service (deprecated, use doctor)

long_about:
Quick liveness check for the running leet-service (deprecated, use doctor).

Originally intended for systemd. Most users should use 'leet doctor' instead,
which covers both static health and service-level health. This subcommand
will be removed in v2.0.

after_help:
Examples:
  leet health

See also:
  leet doctor  — preferred replacement
```

### 5. `absorb`

```
about: Bulk-import past Claude Code sessions into the leet store

long_about:
Bulk-import past Claude Code sessions into the leet store.

Reads conversation history from ~/.claude/projects/<hash>/, summarizes
each session into one COGON, and appends to the current project's store.
Useful for bootstrapping leet on an existing project that has prior
Claude Code history.

Idempotent — won't double-import the same session.

after_help:
Examples:
  # Import sessions from the past 7 days
  leet absorb --since 7d

  # Import all available sessions
  leet absorb --all

  # Dry run (show what would be imported)
  leet absorb --dry-run

See also:
  leet remember  — manually append a single memory
  leet inspect   — see store contents after import
```

### 6. `consolidate`

```
about: Inspect, force, or rebuild the consolidation pyramid

long_about:
Inspect, force, or rebuild the consolidation pyramid.

leet auto-consolidates memories every 7 entries. This subcommand exposes
the pyramid for manual inspection, forcing consolidation below threshold,
or recovering after index corruption.

after_help:
Examples:
  # Show pyramid shape (how many entries at each level)
  leet consolidate inspect

  # Force a consolidation pass at all levels (--min 2 to merge fewer)
  leet consolidate force --min 2

  # Regenerate index.bin from store.bin (lossy: levels reset to 0)
  leet consolidate rebuild-index --yes

See also:
  leet doctor  — detects index/store sync issues
  leet inspect — store statistics
```

### 7. `axes`

```
about: List the 32 canonical axes of the 1337 protocol

long_about:
List the 32 canonical axes of the 1337 protocol.

Shows code (S1..P8), name, block, range semantics, and bipolar marker.
Useful as a reference while reading sem vectors or designing prompts
that target specific axes.

after_help:
Examples:
  # Human-readable table
  leet axes

  # Machine-readable JSON
  leet axes --json

  # Filter by block
  leet axes --block S

See also:
  leet zero   — print COGON_ZERO with axis values
  leet decode — interpret a sem[32] in terms of these axes
```

### 8. `zero`

```
about: Print COGON_ZERO — the canonical boot vector

long_about:
Print COGON_ZERO — the canonical boot vector.

COGON_ZERO encodes "I exist with full presence and zero history". Every
agent transmits this on joining a network (R20). The values follow
Pillar 4 defaults: most axes at 0.5, with specific exceptions.

after_help:
Examples:
  # Show all 32 values with axis labels
  leet zero

  # JSON for piping to other tools
  leet zero --json

See also:
  leet axes  — full axis reference
  leet encode — project arbitrary text into the same space
```

### 9. `inspect`

```
about: Show storage statistics for a leet project

long_about:
Show storage statistics for a leet project.

Reports record count, store size, index status, top-recall cursor,
consolidation depth, and last-modified time. Read-only — never
modifies state.

after_help:
Examples:
  # Inspect current directory
  leet inspect

  # Inspect another project explicitly
  leet inspect --project ~/code/some-other-project

See also:
  leet doctor               — full health check including project state
  leet consolidate inspect  — pyramid-specific view
```

### 10. `encode`

```
about: Project natural-language text into a 32-axis canonical sem vector

long_about:
Project natural-language text into a 32-axis canonical sem vector.

Use this when you want to inspect how leet sees a piece of text — useful
for debugging projection quality or feeding raw COGONs to other tools.
For routine memory operations, use leet_remember via MCP instead.

after_help:
Examples:
  # Inspect a single sentence
  leet encode "Decided to use Postgres"

  # Pipe from another command
  echo "rolling back to commit abc123" | leet encode -

  # Get the full sem[32] as JSON
  leet encode --json "ATLAS thinks we should pivot"

See also:
  leet decode  — reverse a sem vector back to top-axis narrative
  leet dist    — compute distance between two encoded vectors
```

### 11. `decode`

```
about: Interpret a sem[32] vector as a top-axis narrative

long_about:
Interpret a sem[32] vector as a top-axis narrative.

Takes a 32-float sem vector (as JSON or comma-separated) and produces
a human-readable description focused on the most-deviated axes. Inverse
of 'leet encode' (lossy — encode/decode round-trip is approximate).

after_help:
Examples:
  # Decode COGON_ZERO
  leet decode "$(leet zero --json | jq -c .sem)"

  # Decode from comma-separated
  leet decode "0.5,0.2,..."

  # Top 3 axes only (default 5)
  leet decode --top 3 "$(leet zero --json | jq -c .sem)"

See also:
  leet encode  — forward direction
  leet axes    — axis reference
```

### 12. `dist`

```
about: Compute cosine distance between two sem vectors

long_about:
Compute cosine distance between two sem vectors.

Returns a value in [0, 2]: 0 = identical, 1 = orthogonal, 2 = opposite.
Weighted by P6 CONFIDENCE — uncertain vectors contribute less to the
final distance.

after_help:
Examples:
  # Distance between two encoded texts
  A=$(leet encode --json "FastAPI is fast" | jq -c .sem)
  B=$(leet encode --json "Flask is simple" | jq -c .sem)
  leet dist "$A" "$B"

  # Distance from COGON_ZERO
  Z=$(leet zero --json | jq -c .sem)
  leet dist "$Z" "$(leet encode --json 'something else' | jq -c .sem)"

See also:
  leet encode  — produce sem vectors to compare
```

### 13. `blend`

```
about: Blend two COGONs into one (BLEND operator)

long_about:
Blend two COGONs into one (BLEND operator).

Per-block rules:
  D4 STABILITY    — min over inputs
  G1 MASS         — clamp(sum, 0, 1) (saturating)
  G7 K_INTERACTION — max
  P6 CONFIDENCE   — min
All other axes: linear interpolation by alpha (default 0.5).

after_help:
Examples:
  # 50/50 blend
  A=$(leet encode --json "..." | jq -c .sem)
  B=$(leet encode --json "..." | jq -c .sem)
  leet blend "$A" "$B"

  # Weighted toward A
  leet blend --alpha 0.8 "$A" "$B"

  # Show how MASS accumulates
  leet blend --json "$A" "$B" | jq .sem[16]

See also:
  leet consolidate force  — N-ary blend used for memory hierarchy
```

### 14. `validate`

```
about: Validate a 1337 message against R1–R25 structural rules

long_about:
Validate a 1337 message against R1–R25 structural rules.

Reads a JSON-encoded MSG_1337 from stdin or argument, runs all
structural checks, and reports first violation (if any). Use for
debugging integrations and for CI checks.

after_help:
Examples:
  # Validate from file
  leet validate < message.json

  # Validate inline
  leet validate '{"intent":"ASSERT", ...}'

  # Strict mode (also warns about deprecated patterns)
  leet validate --strict < message.json

See also:
  leet axes      — axis index reference
  leet encode    — produce well-formed COGONs
```

### 15. `bench`

```
about: Run benchmarks on operators and storage

long_about:
Run benchmarks on operators and storage.

Measures throughput of BLEND, DIST, encode/decode round-trip, and
storage append/recall. Useful for regression testing and for
documenting performance numbers.

after_help:
Examples:
  # Run all benchmarks
  leet bench

  # Only operator benches (skip storage)
  leet bench --operators

  # Output JSON for tracking
  leet bench --json > benchmarks-$(date +%F).json

See also:
  cargo bench  — full criterion-based benchmarks (developer-only)
```

### 16. `chat`

```
about: Interactive REPL for conversing in 1337 (developer/demo only)

long_about:
Interactive REPL for conversing in 1337 (developer/demo only).

Spawns a local agent that translates your natural-language input into
COGONs, optionally calls Anthropic API, and reconstructs responses
as natural language. Useful for demos and protocol exploration.

NOT the production path — production uses MCP integrations
(leet setup claude-code/cursor/vscode).

after_help:
Examples:
  # Start REPL
  leet chat

  # Use a specific model
  leet chat --model claude-3-5-sonnet-latest

  # Demo mode (no API key needed; uses canned responses)
  leet chat --demo

See also:
  leet setup  — production path via MCP
```

### 17. (futuro) `calibrate`

Não existe ainda — entra na Fase 12-W. **Não criar agora.** Quando 12-W aterrissar, segue o mesmo template.

---

## ARQUIVO NOVO — `leet-cli/src/cmd/help.rs`

Subcomando interativo `leet help` que lista categorias. Pra usuário que esqueceu o nome do subcomando.

```rust
//! `leet help` — show categorized command overview.

use clap::Args;

#[derive(Debug, Args)]
#[command(
    about = "Show command overview grouped by category",
    long_about = "Show command overview grouped by category.\n\
\n\
Lists all subcommands grouped by what they do. Useful when you forgot\n\
which command does what. For details on a specific command, use\n\
'leet <command> --help'.",
    after_help = "Examples:\n  \
  # Show all commands grouped\n  \
  leet help\n\
\n  \
  # Search by keyword\n  \
  leet help --search store"
)]
pub struct HelpArgs {
    /// Filter commands by keyword (matches name or description)
    #[arg(long)]
    pub search: Option<String>,
}

pub fn run(args: HelpArgs) -> anyhow::Result<()> {
    let categories = build_categories();

    println!();
    println!("leet — semantic memory layer for coding agents");
    println!("════════════════════════════════════════════════════");
    println!();

    for (cat_name, commands) in &categories {
        let filtered: Vec<&CommandInfo> = if let Some(q) = &args.search {
            let q = q.to_lowercase();
            commands.iter().filter(|c|
                c.name.to_lowercase().contains(&q) || c.about.to_lowercase().contains(&q)
            ).collect()
        } else {
            commands.iter().collect()
        };

        if filtered.is_empty() {
            continue;
        }

        println!("{}", cat_name);
        for cmd in filtered {
            println!("  {:<20} {}", cmd.name, cmd.about);
        }
        println!();
    }

    println!("For details on a specific command:");
    println!("  leet <command> --help");
    println!();
    println!("Tab-completion installation:");
    println!("  leet --generate-completion bash > /etc/bash_completion.d/leet");
    println!();

    Ok(())
}

struct CommandInfo {
    name: &'static str,
    about: &'static str,
}

fn build_categories() -> Vec<(&'static str, Vec<CommandInfo>)> {
    vec![
        ("Setup & diagnóstico", vec![
            CommandInfo { name: "setup",      about: "Configure leet for IDEs" },
            CommandInfo { name: "doctor",     about: "Health check across binaries, IDEs, store, network" },
            CommandInfo { name: "version",    about: "Print version information" },
            CommandInfo { name: "health",     about: "[deprecated] Use 'doctor' instead" },
        ]),
        ("Memória do projeto", vec![
            CommandInfo { name: "absorb",       about: "Bulk-import past Claude Code sessions" },
            CommandInfo { name: "consolidate",  about: "Inspect/force/rebuild the consolidation pyramid" },
            CommandInfo { name: "inspect",      about: "Show storage statistics for a project" },
        ]),
        ("Inspeção do protocolo", vec![
            CommandInfo { name: "axes",   about: "List the 32 canonical axes" },
            CommandInfo { name: "zero",   about: "Print COGON_ZERO (boot vector)" },
        ]),
        ("Álgebra de COGONs", vec![
            CommandInfo { name: "encode",   about: "Text → sem[32]" },
            CommandInfo { name: "decode",   about: "sem[32] → top-axis narrative" },
            CommandInfo { name: "dist",     about: "Cosine distance between two vectors" },
            CommandInfo { name: "blend",    about: "Blend two COGONs (BLEND operator)" },
            CommandInfo { name: "validate", about: "Validate a 1337 message against R1–R25" },
        ]),
        ("Avançado", vec![
            CommandInfo { name: "bench",    about: "Run benchmarks on operators and storage" },
            CommandInfo { name: "chat",     about: "Interactive REPL (demo / development)" },
        ]),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn categories_have_no_duplicates() {
        let cats = build_categories();
        let mut seen = std::collections::HashSet::new();
        for (_, cmds) in cats {
            for cmd in cmds {
                assert!(seen.insert(cmd.name), "duplicate command: {}", cmd.name);
            }
        }
    }

    #[test]
    fn every_command_has_about() {
        let cats = build_categories();
        for (_, cmds) in cats {
            for cmd in cmds {
                assert!(!cmd.about.is_empty(), "{} missing about", cmd.name);
                assert!(cmd.about.len() < 80, "{} about too long: '{}'", cmd.name, cmd.about);
            }
        }
    }
}
```

---

## ARQUIVO `cmd/mod.rs` — registrar `help`

```rust
pub mod help;

// Em Command enum:
/// Show command overview grouped by category.
Help(cmd::help::HelpArgs),

// No dispatcher:
Command::Help(args) => cmd::help::run(args),
```

---

## ESTRATÉGIA DE EXECUÇÃO

Como são 17 arquivos, sugestão de ordem ao Claude Code que executar este prompt:

1. Adicionar attributes em **um** arquivo (ex: `encode.rs`) — confirmar build verde
2. Aplicar mesmo padrão nos outros 16
3. Criar `help.rs` novo
4. Registrar `help` em `mod.rs`
5. Rodar `cargo test --workspace`
6. Manual smoke: `leet --help` mostra todos; `leet encode --help` traz examples; `leet help` agrupa categorias

**Não testar cada subcomando interativamente** — o test é estrutural (compila, clap não reclama, doc strings não vazias). Validação de qualidade do help fica pro humano que ler.

---

## VERIFICATION

```bash
cargo build --workspace
cargo test --workspace

# Cada subcomando tem about não-vazio?
for cmd in setup doctor version health absorb consolidate axes zero inspect encode decode dist blend validate bench chat help; do
  out=$(./target/debug/leet $cmd --help 2>&1 | head -1)
  if [ -z "$out" ]; then
    echo "FAIL: $cmd has empty help"
    exit 1
  fi
done
echo "OK"

# Examples aparecem?
./target/debug/leet encode --help | grep -c "Examples:"
# Esperado: 1

# leet help mostra categorias?
./target/debug/leet help | head -30
# Esperado: hierarquia "Setup & diagnóstico", "Memória do projeto", etc

# Search funciona?
./target/debug/leet help --search "store" | grep -c "inspect\|absorb\|consolidate"
# Esperado: ≥ 1

# leet --help global tá decente?
./target/debug/leet --help | wc -l
# Esperado: ≥ 25 linhas (hoje provavelmente é 12-15)
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt12_U_03 "Decent --help on all 17 subcommands + leet help interactive"
task project:1337 +prompt12_U_03 done

git add leet-cli/src/cmd/

git commit -m "docs(cli): proper --help on all 17 subcommands

Each subcommand now has:
  - 1-line 'about' (visible in 'leet --help')
  - Multi-line 'long_about' explaining when to use vs alternatives
  - 'after_help' with 2-3 copy-pasteable examples
  - 'See also' pointing to related commands

Implementation: pure clap derive macros, no parallel mechanism.

New 'leet help' subcommand: categorized overview for users who forgot
which command does what. Supports --search to filter by keyword.

Categories: Setup & diagnóstico, Memória do projeto, Inspeção do
protocolo, Álgebra de COGONs, Avançado.

Part of Phase 12-U (UX): discoverability matters as much as features."
git push origin main
```

---

**END OF PROMPT_12-U-03**
