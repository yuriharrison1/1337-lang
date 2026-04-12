//! leet axes — list all 32 canonical axes.

use colored::Colorize;
use leet_core::axes::{AxisGroup, CANONICAL_AXES};

pub fn run() {
    println!("{}", "32 Canonical 1337 Axes".bold());
    println!("{}", "─".repeat(70));

    let mut current_group: Option<&AxisGroup> = None;

    for axis in CANONICAL_AXES.iter() {
        let group_changed = current_group.map_or(true, |g| g != &axis.group);
        if group_changed {
            current_group = Some(&axis.group);
            let group_label = match axis.group {
                AxisGroup::Ontological => "Group A — Ontological",
                AxisGroup::Epistemic   => "Group B — Epistemic",
                AxisGroup::Pragmatic   => "Group C — Pragmatic",
            };
            println!("\n{}", group_label.bold().underline());
        }

        let code_colored = match axis.group {
            AxisGroup::Ontological => axis.code.cyan().to_string(),
            AxisGroup::Epistemic   => axis.code.yellow().to_string(),
            AxisGroup::Pragmatic   => axis.code.magenta().to_string(),
        };

        println!(
            "  {:>3}  {:5}  {:28}  {}",
            format!("[{}]", axis.index),
            code_colored,
            axis.name,
            axis.description.dimmed()
        );
    }
    println!();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_32_axes_present() {
        assert_eq!(CANONICAL_AXES.len(), 32);
    }

    #[test]
    fn test_axes_have_valid_groups() {
        for axis in CANONICAL_AXES.iter() {
            // Just ensure we can match each group
            let _ = match axis.group {
                AxisGroup::Ontological => "A",
                AxisGroup::Epistemic => "B",
                AxisGroup::Pragmatic => "C",
            };
        }
    }
}
