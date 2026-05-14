//! leet axes — list all 32 canonical axes.

use colored::Colorize;
use leet_core::axes::{AxisGroup, CANONICAL_AXES};

pub fn run(json: bool, block: Option<&str>) {
    let filtered: Vec<_> = CANONICAL_AXES.iter().filter(|a| {
        match block {
            None => true,
            Some(b) => {
                let b = b.to_uppercase();
                match a.group {
                    AxisGroup::S => b == "S",
                    AxisGroup::D => b == "D",
                    AxisGroup::G => b == "G",
                    AxisGroup::P => b == "P",
                }
            }
        }
    }).collect();

    if json {
        let arr: Vec<serde_json::Value> = filtered.iter().map(|a| {
            serde_json::json!({
                "index": a.index,
                "code": a.code,
                "name": a.name,
                "group": format!("{:?}", a.group),
                "bipolar": a.bipolar,
                "description": a.description,
            })
        }).collect();
        println!("{}", serde_json::to_string(&arr).unwrap());
        return;
    }

    println!("{}", "32 Canonical 1337 Axes (v0.5.1)".bold());
    println!("{}", "─".repeat(70));

    let mut current_group: Option<&AxisGroup> = None;

    for axis in filtered.iter() {
        let group_changed = current_group != Some(&axis.group);
        if group_changed {
            current_group = Some(&axis.group);
            let group_label = match axis.group {
                AxisGroup::S => "Block S — Semantic  (0–7)",
                AxisGroup::D => "Block D — Dynamic   (8–15)",
                AxisGroup::G => "Block G — Gravity   (16–23)",
                AxisGroup::P => "Block P — Precision (24–31)",
            };
            println!("\n{}", group_label.bold().underline());
        }

        let code_colored = match axis.group {
            AxisGroup::S => axis.code.cyan().to_string(),
            AxisGroup::D => axis.code.yellow().to_string(),
            AxisGroup::G => axis.code.magenta().to_string(),
            AxisGroup::P => axis.code.green().to_string(),
        };

        let valence_marker = if axis.bipolar { " ★" } else { "" };

        println!(
            "  {:>3}  {:5}  {:22}{}  {}",
            format!("[{}]", axis.index),
            code_colored,
            axis.name,
            valence_marker,
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
            let _ = match axis.group {
                AxisGroup::S => "S",
                AxisGroup::D => "D",
                AxisGroup::G => "G",
                AxisGroup::P => "P",
            };
        }
    }
}
