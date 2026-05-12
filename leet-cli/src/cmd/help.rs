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
  # Filter by keyword\n  \
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
            println!("  {:<22} {}", cmd.name, cmd.about);
        }
        println!();
    }

    println!("For details on a specific command:");
    println!("  leet <command> --help");
    println!();

    Ok(())
}

struct CommandInfo {
    name: &'static str,
    about: &'static str,
}

fn build_categories() -> Vec<(&'static str, Vec<CommandInfo>)> {
    vec![
        ("Setup & diagnostics", vec![
            CommandInfo { name: "setup",       about: "Configure leet for IDEs (Claude Code, Cursor, VS Code)" },
            CommandInfo { name: "doctor",      about: "Health check: binaries, IDEs, store, network" },
            CommandInfo { name: "calibrate",   about: "Download and manage the W matrix" },
            CommandInfo { name: "version",     about: "Print version information for all components" },
            CommandInfo { name: "health",      about: "[deprecated] Use 'leet doctor' instead" },
        ]),
        ("Project memory", vec![
            CommandInfo { name: "absorb",       about: "Bulk-import past Claude Code sessions into the store" },
            CommandInfo { name: "consolidate",  about: "Inspect/force/rebuild the consolidation pyramid" },
        ]),
        ("Protocol inspection", vec![
            CommandInfo { name: "axes",   about: "List the 32 canonical axes" },
            CommandInfo { name: "zero",   about: "Print COGON_ZERO (canonical boot vector)" },
        ]),
        ("COGON algebra", vec![
            CommandInfo { name: "encode",   about: "Text → sem[32] vector" },
            CommandInfo { name: "decode",   about: "sem[32] → top-axis narrative" },
            CommandInfo { name: "dist",     about: "Cosine distance between two vectors" },
            CommandInfo { name: "blend",    about: "Blend two COGONs (BLEND operator)" },
            CommandInfo { name: "validate", about: "Validate a 1337 message against R1–R25" },
            CommandInfo { name: "inspect",  about: "Show storage statistics for a project" },
        ]),
        ("Advanced", vec![
            CommandInfo { name: "bench",    about: "Run benchmarks on operators and storage" },
            CommandInfo { name: "chat",     about: "Interactive REPL (demo / development only)" },
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
    fn every_command_has_nonempty_about() {
        let cats = build_categories();
        for (_, cmds) in cats {
            for cmd in cmds {
                assert!(!cmd.about.is_empty(), "{} missing about", cmd.name);
                assert!(cmd.about.len() < 80, "{} about too long: '{}'", cmd.name, cmd.about);
            }
        }
    }

    #[test]
    fn search_filter_works() {
        let cats = build_categories();
        let q = "store".to_lowercase();
        let matches: Vec<&str> = cats.iter()
            .flat_map(|(_, cmds)| cmds.iter())
            .filter(|c| c.name.contains(&q) || c.about.to_lowercase().contains(&q))
            .map(|c| c.name)
            .collect();
        assert!(!matches.is_empty(), "expected some commands matching 'store'");
    }
}
