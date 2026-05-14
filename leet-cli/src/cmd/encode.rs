//! leet encode — project text and display colored axis bars.

use colored::Colorize;
use leet_bridge::MockProjector;
use leet_core::axes::CANONICAL_AXES;

/// Render a single axis bar with colored output.
pub fn render_bar(name: &str, value: f32, width: usize) -> String {
    let filled = (value * width as f32).round() as usize;
    let empty = width.saturating_sub(filled);
    let bar: String = format!(
        "[{}{}]",
        "█".repeat(filled),
        "░".repeat(empty)
    );

    let bar_colored = if value > 0.8 {
        bar.red().to_string()
    } else if value >= 0.5 {
        bar.yellow().to_string()
    } else {
        bar.green().to_string()
    };

    format!("  {:20} {} {:.2}", name, bar_colored, value)
}

pub fn run(text: &str, json: bool, top: usize) {
    use leet_bridge::BridgeProjector;
    let proj = MockProjector;
    let cogon = match proj.project(text) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    };

    if json {
        println!("{}", serde_json::to_string(&cogon).unwrap());
        return;
    }

    println!("COGON {}", cogon.id);
    let mut axes_with_vals: Vec<(usize, f32)> = cogon.sem
        .iter()
        .enumerate()
        .filter(|(_, &v)| v > 0.3)
        .map(|(i, &v)| (i, v))
        .collect();
    axes_with_vals.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    let to_show = if top > 0 { top } else { axes_with_vals.len() };
    let mut any_printed = false;
    for (i, v) in axes_with_vals.iter().take(to_show) {
        let axis = &CANONICAL_AXES[*i];
        let label = format!("{}_{}", axis.code, axis.name);
        println!("{}", render_bar(&label, *v, 10));
        any_printed = true;
    }
    if !any_printed {
        println!("  (all axes at or below 0.3 — neutral)");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_bar_high_value_has_full_fill() {
        let bar = render_bar("TEST", 1.0, 10);
        assert!(bar.contains("██████████"));
    }

    #[test]
    fn test_render_bar_zero_value_has_empty() {
        let bar = render_bar("TEST", 0.0, 10);
        assert!(bar.contains("░░░░░░░░░░"));
    }

    #[test]
    fn test_render_bar_half_value() {
        let bar = render_bar("TEST", 0.5, 10);
        assert!(bar.contains("█████"));
    }

    #[test]
    fn test_render_bar_contains_name() {
        let bar = render_bar("MY_AXIS", 0.7, 10);
        assert!(bar.contains("MY_AXIS"));
    }

    #[test]
    fn test_render_bar_contains_value() {
        let bar = render_bar("X", 0.75, 10);
        assert!(bar.contains("0.75"));
    }
}
