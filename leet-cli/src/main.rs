//! leet — CLI for the 1337 inter-agent language.

mod cmd;

use clap::{Parser, Subcommand};
use std::io::Read;

#[derive(Parser)]
#[command(
    name = "leet",
    about = "1337 language CLI toolkit",
    long_about = "leet — semantic memory layer and algebraic toolkit for coding agents.\n\
\n\
Encodes natural language into 32-axis sem vectors (COGONs), stores project\n\
memory across sessions, and exposes it to Claude Code, Cursor, and VS Code\n\
via MCP. Algebra tools (encode, decode, dist, blend) let you inspect and\n\
manipulate the semantic space directly.",
    version = env!("CARGO_PKG_VERSION"),
    after_help = "Run 'leet help' for a categorized command overview.\n\
Run 'leet <command> --help' for details on a specific command.",
    disable_help_subcommand = true,
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Project natural-language text into a 32-axis canonical sem vector
    #[command(
        long_about = "Project natural-language text into a 32-axis canonical sem vector.\n\
\n\
Use this when you want to inspect how leet sees a piece of text — useful\n\
for debugging projection quality or feeding raw COGONs to other tools.\n\
For routine memory operations, use leet_remember via MCP instead.",
        after_help = "Examples:\n  \
  # Inspect a single sentence\n  \
  leet encode \"Decided to use Postgres\"\n\
\n  \
  # Pipe from another command\n  \
  echo \"rolling back to commit abc123\" | leet encode -\n\
\n\
See also:\n  \
  leet decode  — reverse a sem vector back to top-axis narrative\n  \
  leet dist    — compute distance between two encoded vectors"
    )]
    Encode {
        /// Text to encode. Use '-' to read from stdin.
        text: String,
    },
    /// Interpret a sem[32] vector as a top-axis narrative
    #[command(
        long_about = "Interpret a sem[32] vector as a top-axis narrative.\n\
\n\
Takes a 32-float sem vector (as JSON or comma-separated) and produces a\n\
human-readable description focused on the most-deviated axes. Inverse of\n\
'leet encode' (lossy — encode/decode round-trip is approximate).",
        after_help = "Examples:\n  \
  # Decode COGON_ZERO\n  \
  leet decode \"$(leet zero --json | jq -c .sem)\"\n\
\n  \
  # Decode from comma-separated\n  \
  leet decode \"0.5,0.2,...\"\n\
\n\
See also:\n  \
  leet encode  — forward direction\n  \
  leet axes    — axis reference"
    )]
    Decode {
        /// COGON JSON string or path (use '-' for stdin)
        json: Option<String>,
    },
    /// Compute cosine distance between two sem vectors
    #[command(
        long_about = "Compute cosine distance between two sem vectors.\n\
\n\
Returns a value in [0, 2]: 0 = identical, 1 = orthogonal, 2 = opposite.\n\
Weighted by P6 CONFIDENCE — uncertain vectors contribute less.",
        after_help = "Examples:\n  \
  # Distance between two encoded texts\n  \
  A=$(leet encode --json \"FastAPI is fast\" | jq -c .sem)\n  \
  B=$(leet encode --json \"Flask is simple\" | jq -c .sem)\n  \
  leet dist \"$A\" \"$B\"\n\
\n\
See also:\n  \
  leet encode  — produce sem vectors to compare\n  \
  leet blend   — combine two vectors"
    )]
    Dist {
        /// First text
        text_a: String,
        /// Second text
        text_b: String,
    },
    /// Blend two COGONs into one (BLEND operator)
    #[command(
        long_about = "Blend two COGONs into one (BLEND operator).\n\
\n\
Per-block rules:\n  \
  D4 STABILITY    — min over inputs\n  \
  G1 MASS         — clamp(sum, 0, 1) (saturating)\n  \
  G7 K_INTERACTION — max\n  \
  P6 CONFIDENCE   — min\n\
All other axes: linear interpolation by alpha (default 0.5).",
        after_help = "Examples:\n  \
  # 50/50 blend\n  \
  A=$(leet encode --json \"...\" | jq -c .sem)\n  \
  B=$(leet encode --json \"...\" | jq -c .sem)\n  \
  leet blend \"$A\" \"$B\"\n\
\n  \
  # Weighted toward A\n  \
  leet blend --alpha 0.8 \"$A\" \"$B\"\n\
\n\
See also:\n  \
  leet consolidate force  — N-ary blend used for memory hierarchy"
    )]
    Blend {
        /// First text
        text_a: String,
        /// Second text
        text_b: String,
        /// Blend weight for text_a (0.0 to 1.0, default: 0.5)
        #[arg(long, default_value = "0.5")]
        alpha: f32,
    },
    /// List the 32 canonical axes of the 1337 protocol
    #[command(
        long_about = "List the 32 canonical axes of the 1337 protocol.\n\
\n\
Shows code (S1..P8), name, block, range semantics, and bipolar marker.\n\
Useful as a reference while reading sem vectors or designing prompts\n\
that target specific axes.",
        after_help = "Examples:\n  \
  # Human-readable table\n  \
  leet axes\n\
\n  \
  # Machine-readable JSON\n  \
  leet axes --json\n\
\n\
See also:\n  \
  leet zero   — print COGON_ZERO with axis values\n  \
  leet decode — interpret a sem[32] in terms of these axes"
    )]
    Axes,
    /// Print COGON_ZERO — the canonical boot vector
    #[command(
        long_about = "Print COGON_ZERO — the canonical boot vector.\n\
\n\
COGON_ZERO encodes \"I exist with full presence and zero history\". Every\n\
agent transmits this on joining a network (R20). The values follow Pillar 4\n\
defaults: most axes at 0.5, with specific exceptions.",
        after_help = "Examples:\n  \
  # Show all 32 values with axis labels\n  \
  leet zero\n\
\n  \
  # JSON for piping to other tools\n  \
  leet zero --json\n\
\n\
See also:\n  \
  leet axes    — full axis reference\n  \
  leet encode  — project arbitrary text into the same space"
    )]
    Zero,
    /// Validate a 1337 message against R1–R25 structural rules
    #[command(
        long_about = "Validate a 1337 message against R1–R25 structural rules.\n\
\n\
Reads a JSON-encoded MSG_1337 from stdin or argument, runs all structural\n\
checks, and reports the first violation (if any). Use for debugging\n\
integrations and CI checks.",
        after_help = "Examples:\n  \
  # Validate from file\n  \
  leet validate < message.json\n\
\n  \
  # Validate inline\n  \
  leet validate '{\"intent\":\"ASSERT\", ...}'\n\
\n\
See also:\n  \
  leet axes    — axis index reference\n  \
  leet encode  — produce well-formed COGONs"
    )]
    Validate {
        /// MSG_1337 JSON string (use '-' for stdin)
        json: Option<String>,
    },
    /// Run benchmarks on operators and storage
    #[command(
        long_about = "Run benchmarks on operators and storage.\n\
\n\
Measures throughput of BLEND, DIST, encode/decode round-trip, and storage\n\
append/recall. Useful for regression testing and documenting performance.",
        after_help = "Examples:\n  \
  # Run N encode iterations (default: 1000)\n  \
  leet bench\n  \
  leet bench --n 5000\n\
\n\
See also:\n  \
  cargo bench  — full criterion-based benchmarks (developer-only)"
    )]
    Bench {
        /// Number of encodes to run
        #[arg(long, short, default_value = "1000")]
        n: usize,
    },
    /// Show storage statistics for a leet project
    #[command(
        long_about = "Show storage statistics for a leet project.\n\
\n\
Reports record count, store size, index status, top-recall cursor,\n\
consolidation depth, and last-modified time. Read-only — never modifies\n\
state.",
        after_help = "Examples:\n  \
  # Inspect current directory\n  \
  leet inspect\n\
\n  \
  # Inspect another project\n  \
  leet inspect /path/to/other-project/some.json\n\
\n\
See also:\n  \
  leet doctor               — full health check including project state\n  \
  leet consolidate inspect  — pyramid-specific view"
    )]
    Inspect {
        /// COGON JSON string (use '-' for stdin)
        json: Option<String>,
    },
    /// Quick liveness check for the running leet-service (deprecated, use doctor)
    #[command(
        long_about = "Quick liveness check for the running leet-service (deprecated, use doctor).\n\
\n\
Originally intended for systemd health probes. Most users should use\n\
'leet doctor' instead, which covers both static health and service-level\n\
health. This subcommand will be removed in v2.0.",
        after_help = "Examples:\n  \
  leet health\n  \
  leet health --url localhost:50051\n\
\n\
See also:\n  \
  leet doctor  — preferred replacement (comprehensive)"
    )]
    Health {
        /// Address to check
        #[arg(long, default_value = "localhost:50051")]
        url: String,
    },
    /// Print version information for all installed leet components
    #[command(
        long_about = "Print version information for all installed leet components.\n\
\n\
Useful for bug reports — paste the output to confirm exactly which\n\
versions are running. Shows leet, leet-mcp, leet-server, and the spec\n\
version implemented.",
        after_help = "Examples:\n  \
  leet version\n\
\n\
See also:\n  \
  leet doctor  — full health check including version mismatches"
    )]
    Version,
    /// Interactive REPL for conversing in 1337 (developer/demo only)
    #[command(
        long_about = "Interactive REPL for conversing in 1337 (developer/demo only).\n\
\n\
Spawns a local agent that translates natural-language input into COGONs,\n\
optionally calls Anthropic API, and reconstructs responses as natural\n\
language. Useful for demos and protocol exploration.\n\
\n\
NOT the production path — production uses MCP integrations\n\
(leet setup claude-code/cursor/vscode).",
        after_help = "Examples:\n  \
  # Start REPL in Portuguese (default)\n  \
  leet chat\n\
\n  \
  # English output with COGON summaries shown\n  \
  leet chat --lang en --show-cogon\n\
\n\
See also:\n  \
  leet setup  — production path via MCP"
    )]
    Chat {
        /// Output language: pt (default) or en
        #[arg(long, default_value = "pt")]
        lang: String,
        /// Show COGON summaries inline with each message
        #[arg(long)]
        show_cogon: bool,
        /// Maximum number of agents to engage per round (1-6)
        #[arg(long, default_value = "3")]
        agents: usize,
        /// Connect to a running leet-server instead of calling the API directly
        /// (e.g. "127.0.0.1:1337" or "/run/leet/leet.sock")
        #[arg(long)]
        connect: Option<String>,
    },
    /// Download and manage the W matrix for high-quality NL→COGON projection
    Calibrate(cmd::calibrate::CalibrateArgs),
    /// Run system health check across binaries, IDEs, store, network
    Doctor(cmd::doctor::DoctorArgs),
    /// Configure leet for one or more IDEs (Claude Code, Cursor, VS Code+Continue)
    Setup(cmd::setup::SetupArgs),
    /// Bulk-import Claude Code session history into the project's .leet store
    Absorb(cmd::absorb::AbsorbArgs),
    /// Inspect, force, or rebuild the consolidation pyramid for a project
    Consolidate(cmd::consolidate::ConsolidateArgs),
    /// Show command overview grouped by category
    Help(cmd::help::HelpArgs),
}

fn read_input(maybe_json: Option<String>) -> String {
    match maybe_json {
        Some(ref s) if s == "-" => {
            let mut buf = String::new();
            std::io::stdin().read_to_string(&mut buf).unwrap();
            buf
        }
        Some(s) => s,
        None => {
            let mut buf = String::new();
            std::io::stdin().read_to_string(&mut buf).unwrap();
            buf
        }
    }
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Encode { text } => cmd::encode::run(&text),
        Commands::Decode { json } => {
            let input = read_input(json);
            cmd::decode::run(&input);
        }
        Commands::Dist { text_a, text_b } => cmd::dist::run(&text_a, &text_b),
        Commands::Blend { text_a, text_b, alpha } => cmd::blend::run(&text_a, &text_b, alpha),
        Commands::Axes => cmd::axes::run(),
        Commands::Zero => cmd::zero::run(),
        Commands::Validate { json } => {
            let input = read_input(json);
            cmd::validate::run(&input);
        }
        Commands::Bench { n } => cmd::bench::run(n),
        Commands::Inspect { json } => {
            let input = read_input(json);
            cmd::inspect::run(&input);
        }
        Commands::Health { url } => cmd::health::run(&url),
        Commands::Version => cmd::version::run(),
        Commands::Chat { lang, show_cogon, agents, connect } => {
            let rt = tokio::runtime::Runtime::new().expect("failed to create tokio runtime");
            if let Some(ref addr) = connect {
                rt.block_on(cmd::chat::run_connected(addr, &lang, show_cogon));
            } else {
                rt.block_on(cmd::chat::run(&lang, show_cogon, agents));
            }
        }
        Commands::Calibrate(args) => exit_on_err(cmd::calibrate::run(args)),
        Commands::Doctor(args) => exit_on_err(cmd::doctor::run(args)),
        Commands::Setup(args) => exit_on_err(cmd::setup::run(args)),
        Commands::Absorb(args) => exit_on_err(cmd::absorb::run(args)),
        Commands::Consolidate(args) => exit_on_err(cmd::consolidate::run(args)),
        Commands::Help(args) => exit_on_err(cmd::help::run(args)),
    }
}

fn exit_on_err(result: anyhow::Result<()>) {
    if let Err(err) = result {
        let user_err = err
            .downcast::<leet_core::UserFacingError>()
            .unwrap_or_else(|anyhow_err| anyhow_err.into());
        eprintln!("\n{}\n", user_err);
        std::process::exit(user_err.exit_code());
    }
}
