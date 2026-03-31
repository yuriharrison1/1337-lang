use clap::{Parser, Subcommand};

mod commands;

#[derive(Parser)]
#[command(name = "leet", about = "1337 protocol developer tools", version = "0.1.0")]
struct Cli {
    #[arg(long, default_value = "localhost:50051", global = true)]
    service: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Encode {
        text: String,
        #[arg(long)]
        json: bool,
    },
    Decode {
        sem: String,
    },
    Inspect {
        cogon: String,
    },
    Dist {
        text1: String,
        text2: String,
    },
    Bench {
        #[arg(long, default_value = "1000")]
        n: usize,
        #[arg(long)]
        parallel: bool,
    },
    Health,
    Axes,
    Version,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Encode { text, json } => commands::encode::run(&text, json, &cli.service).await,
        Commands::Decode { sem } => commands::decode::run(&sem),
        Commands::Inspect { cogon } => commands::inspect::run(&cogon),
        Commands::Dist { text1, text2 } => commands::dist::run(&text1, &text2, &cli.service).await,
        Commands::Bench { n, parallel } => commands::bench::run(n, parallel, &cli.service).await,
        Commands::Health => commands::health::run(&cli.service).await,
        Commands::Axes => commands::axes::run(),
        Commands::Version => commands::version::run(),
    }
}
