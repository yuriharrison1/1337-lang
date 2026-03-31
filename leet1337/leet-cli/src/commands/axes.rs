use colored::Colorize;
use leet_core::axes::{AxisGroup, CANONICAL_AXES};

pub fn run() -> anyhow::Result<()> {
    println!("{}", "Canonical Axes — 1337 Protocol".bold());
    println!();

    let mut current_group: Option<&AxisGroup> = None;

    for axis in CANONICAL_AXES.iter() {
        // Print group header when group changes
        let print_header = match current_group {
            None => true,
            Some(g) => g != &axis.group,
        };

        if print_header {
            let header = match axis.group {
                AxisGroup::Ontological => "Group A — Ontological (indices 0–13)".blue().bold().to_string(),
                AxisGroup::Epistemic => "Group B — Epistemic (indices 14–21)".cyan().bold().to_string(),
                AxisGroup::Pragmatic => "Group C — Pragmatic (indices 22–31)".green().bold().to_string(),
            };
            if current_group.is_some() {
                println!();
            }
            println!("{}", header);
            current_group = Some(&axis.group);
        }

        let line = format!(
            "  [{:2}] {:<5} {:<26} {}",
            axis.index, axis.code, axis.name, axis.description
        );
        let colored_line = match axis.group {
            AxisGroup::Ontological => line.blue().to_string(),
            AxisGroup::Epistemic => line.cyan().to_string(),
            AxisGroup::Pragmatic => line.green().to_string(),
        };
        println!("{}", colored_line);
    }

    println!();
    println!("Total: {} axes", CANONICAL_AXES.len());

    Ok(())
}
