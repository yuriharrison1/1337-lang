//! leet dist — compute cosine distance between two texts.

use colored::Colorize;
use leet_bridge::{BridgeProjector, MockProjector};
use leet_core::operators::dist as cogon_dist;
use leet_core::axes::CANONICAL_AXES;

pub fn run(text_a: &str, text_b: &str) {
    let proj = MockProjector;
    let ca = proj.project(text_a).unwrap();
    let cb = proj.project(text_b).unwrap();

    let d = cogon_dist(&ca, &cb);
    println!("Distance: {:.4}", d);

    // Top-5 axes most discordant
    let mut diffs: Vec<(usize, f32)> = ca
        .sem
        .iter()
        .zip(cb.sem.iter())
        .enumerate()
        .map(|(i, (a, b))| (i, (a - b).abs()))
        .collect();
    diffs.sort_by(|x, y| y.1.partial_cmp(&x.1).unwrap());

    println!("\nTop-5 most discordant axes:");
    for (i, diff) in diffs.iter().take(5) {
        let axis = &CANONICAL_AXES[*i];
        let label = format!("{}_{}", axis.code, axis.name);
        let line = format!("  {:25} diff={:.4}  ({:.2} vs {:.2})", label, diff, ca.sem[*i], cb.sem[*i]);
        if *diff > 0.3 {
            println!("{}", line.yellow());
        } else {
            println!("{}", line);
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_dist_same_text_is_small() {
        use leet_bridge::{BridgeProjector, MockProjector};
        use leet_core::operators::dist;
        let proj = MockProjector;
        let c = proj.project("urgente agora").unwrap();
        let d = dist(&c, &c);
        assert!(d < 1e-5);
    }
}
