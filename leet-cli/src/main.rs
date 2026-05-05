//! leet — CLI for the 1337 inter-agent language.

mod cmd;

use clap::{Parser, Subcommand};
use std::io::Read;

#[derive(Parser)]
#[command(
    name = "leet",
    about = "1337 language CLI toolkit",
    version = "0.5.0"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Project text into a COGON and display axis bars
    Encode {
        /// Text to encode
        text: String,
    },
    /// Reconstruct text from a COGON JSON (reads from arg or stdin)
    Decode {
        /// COGON JSON string or path (use '-' for stdin)
        json: Option<String>,
    },
    /// Compute cosine distance between two texts
    Dist {
        /// First text
        text_a: String,
        /// Second text
        text_b: String,
    },
    /// Blend two texts with alpha weight
    Blend {
        /// First text
        text_a: String,
        /// Second text
        text_b: String,
        /// Blend weight for text_a (0.0 to 1.0, default: 0.5)
        #[arg(long, default_value = "0.5")]
        alpha: f32,
    },
    /// List all 32 canonical axes
    Axes,
    /// Print COGON_ZERO
    Zero,
    /// Validate a MSG_1337 JSON file
    Validate {
        /// MSG_1337 JSON string (use '-' for stdin)
        json: Option<String>,
    },
    /// Benchmark encode performance
    Bench {
        /// Number of encodes to run
        #[arg(long, short, default_value = "1000")]
        n: usize,
    },
    /// Inspect a COGON JSON and show semantic interpretation
    Inspect {
        /// COGON JSON string (use '-' for stdin)
        json: Option<String>,
    },
    /// Check if leet-service is reachable
    Health {
        /// Address to check (default: localhost:50051)
        #[arg(long, default_value = "localhost:50051")]
        url: String,
    },
    /// Print version information
    Version,
    /// Interactive 1337 multi-agent chat (requires LEET_API_KEY or --connect)
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
    /// Install or configure leet integration with external tools
    Setup(cmd::setup::SetupArgs),
    /// Bulk-import Claude Code session history into the project's .leet store
    Absorb(cmd::absorb::AbsorbArgs),
    /// Inspect, force, or rebuild the consolidation pyramid for a project
    Consolidate(cmd::consolidate::ConsolidateArgs),
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
        Commands::Setup(args) => {
            if let Err(e) = cmd::setup::run(args) {
                eprintln!("error: {e}");
                std::process::exit(1);
            }
        }
        Commands::Absorb(args) => {
            if let Err(e) = cmd::absorb::run(args) {
                eprintln!("error: {e}");
                std::process::exit(1);
            }
        }
        Commands::Consolidate(args) => {
            if let Err(e) = cmd::consolidate::run(args) {
                eprintln!("error: {e}");
                std::process::exit(1);
            }
        }
    }
}
