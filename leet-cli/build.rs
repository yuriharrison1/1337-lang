use std::path::PathBuf;

fn main() {
    // OUT_DIR is inside target/; go up to workspace target/man
    let out_dir = match std::env::var("OUT_DIR") {
        Ok(d) => {
            // OUT_DIR = <workspace>/target/debug/build/<crate>/out
            // Go up 4 levels to reach <workspace>/target, then add "man"
            let p = PathBuf::from(d);
            match p.ancestors().nth(4) {
                Some(target) => target.join("man"),
                None => return,
            }
        }
        Err(_) => return,
    };

    if std::fs::create_dir_all(&out_dir).is_err() {
        return; // Non-fatal: man pages are optional build artifacts.
    }

    let cmd = build_cmd();

    let man = clap_mangen::Man::new(cmd.clone());
    let mut buf = vec![];
    if man.render(&mut buf).is_ok() {
        let _ = std::fs::write(out_dir.join("leet.1"), &buf);
    }

    for sub in cmd.get_subcommands() {
        let sub_man = clap_mangen::Man::new(sub.clone());
        let mut buf = vec![];
        if sub_man.render(&mut buf).is_ok() {
            // Rename "leet-leet-help" workaround → "leet-help"
            let raw_name = sub.get_name();
            let page_name = if raw_name == "leet-help" {
                "leet-help.1".to_string()
            } else {
                format!("leet-{}.1", raw_name)
            };
            let _ = std::fs::write(out_dir.join(&page_name), &buf);
        }
    }
}

fn build_cmd() -> clap::Command {
    use clap::Command;
    Command::new("leet")
        .version(env!("CARGO_PKG_VERSION"))
        .about("1337 language CLI toolkit — semantic memory layer for coding agents")
        .subcommand(Command::new("encode").about("Project natural-language text into a 32-axis sem vector"))
        .subcommand(Command::new("decode").about("Interpret a sem[32] vector as a top-axis narrative"))
        .subcommand(Command::new("dist").about("Compute cosine distance between two sem vectors"))
        .subcommand(Command::new("blend").about("Blend two COGONs into one (BLEND operator)"))
        .subcommand(Command::new("axes").about("List the 32 canonical axes of the 1337 protocol"))
        .subcommand(Command::new("zero").about("Print COGON_ZERO — the canonical boot vector"))
        .subcommand(Command::new("validate").about("Validate a 1337 message against R1–R25 structural rules"))
        .subcommand(Command::new("bench").about("Run benchmarks on operators and storage"))
        .subcommand(Command::new("inspect").about("Show storage statistics for a leet project"))
        .subcommand(Command::new("health").about("Quick liveness check (deprecated, use doctor)"))
        .subcommand(Command::new("version").about("Print version information for all installed leet components"))
        .subcommand(Command::new("chat").about("Interactive REPL for conversing in 1337 (developer/demo only)"))
        .subcommand(Command::new("calibrate").about("Download and manage the W matrix for high-quality NL→COGON projection"))
        .subcommand(Command::new("doctor").about("Run system health check across binaries, IDEs, store, network"))
        .subcommand(Command::new("setup").about("Configure leet for one or more IDEs"))
        .subcommand(Command::new("absorb").about("Bulk-import Claude Code session history into the project's .leet store"))
        .subcommand(Command::new("consolidate").about("Inspect, force, or rebuild the consolidation pyramid for a project"))
        .subcommand(Command::new("completions").about("Generate shell completion scripts (bash, zsh, fish, elvish)"))
        // "help" is renamed here because a plain clap Command still has the built-in help
        // subcommand; adding "help" would cause a duplicate name panic. The generated man
        // page is renamed from leet-leet-help.1 to leet-help.1 below.
        .subcommand(Command::new("leet-help").about("Show command overview grouped by category")
            .override_usage("leet help [--search <KEYWORD>]"))
}
