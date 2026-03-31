use colored::Colorize;
use leet_core::axes::{AxisGroup, CANONICAL_AXES};

use crate::commands::project_mock;

pub async fn run(text: &str, json: bool, _service: &str) -> anyhow::Result<()> {
    let cogon = project_mock(text);

    if json {
        let j = serde_json::to_string_pretty(&cogon)?;
        println!("{}", j);
        return Ok(());
    }

    println!("{}", format!("COGON encode: \"{}\"", text).bold());
    println!();

    // Group A — Ontological (indices 0–13)
    println!("{}", "Group A — Ontological".blue().bold());
    for axis in CANONICAL_AXES.iter().filter(|a| a.group == AxisGroup::Ontological) {
        let i = axis.index;
        let s = cogon.sem[i];
        let u = cogon.unc[i];
        let bar = make_bar(s, 10);
        println!(
            "  [{:2}]  {:<22}: {:.3}  unc: {:.3}  {}",
            i,
            axis.name.to_lowercase(),
            s,
            u,
            bar.blue()
        );
    }
    println!();

    // Group B — Epistemic (indices 14–21)
    println!("{}", "Group B — Epistemic".cyan().bold());
    for axis in CANONICAL_AXES.iter().filter(|a| a.group == AxisGroup::Epistemic) {
        let i = axis.index;
        let s = cogon.sem[i];
        let u = cogon.unc[i];
        let bar = make_bar(s, 10);
        println!(
            "  [{:2}]  {:<22}: {:.3}  unc: {:.3}  {}",
            i,
            axis.name.to_lowercase(),
            s,
            u,
            bar.cyan()
        );
    }
    println!();

    // Group C — Pragmatic (indices 22–31)
    println!("{}", "Group C — Pragmatic".green().bold());
    for axis in CANONICAL_AXES.iter().filter(|a| a.group == AxisGroup::Pragmatic) {
        let i = axis.index;
        let s = cogon.sem[i];
        let u = cogon.unc[i];
        let bar = make_bar(s, 10);
        println!(
            "  [{:2}]  {:<22}: {:.3}  unc: {:.3}  {}",
            i,
            axis.name.to_lowercase(),
            s,
            u,
            bar.green()
        );
    }
    println!();

    println!("COGON ID : {}", cogon.id);
    println!("Stamp    : {}", cogon.stamp);

    Ok(())
}

fn make_bar(val: f32, width: usize) -> String {
    let filled = (val * width as f32).round() as usize;
    let filled = filled.min(width);
    let empty = width - filled;
    format!("{}{}", "█".repeat(filled), "░".repeat(empty))
}
