//! leet dist — compute cosine distance between two sem vectors or texts.

use colored::Colorize;
use leet_core::operators::dist as cogon_dist;
use leet_core::axes::CANONICAL_AXES;
use leet_core::types::Cogon;

/// Parse input as a sem vector (JSON array or comma-separated floats).
/// Falls back to projecting as text.
fn parse_or_project(input: &str) -> Cogon {
    // Try JSON array: [f32; 32]
    if let Ok(arr) = serde_json::from_str::<Vec<f32>>(input) {
        if arr.len() == 32 {
            let mut cogon = Cogon::zero();
            cogon.sem.copy_from_slice(&arr);
            return cogon;
        }
    }
    // Try comma-separated
    let parts: Vec<f32> = input.split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();
    if parts.len() == 32 {
        let mut cogon = Cogon::zero();
        cogon.sem.copy_from_slice(&parts);
        return cogon;
    }
    // Fall back to text projection
    leet_bridge::projector::project_text_simple(input).unwrap_or_else(|_| Cogon::zero())
}

pub fn run(text_a: &str, text_b: &str, json: bool) {
    let ca = parse_or_project(text_a);
    let cb = parse_or_project(text_b);

    let d = cogon_dist(&ca, &cb);

    if json {
        println!("{}", serde_json::json!({ "distance": d }));
        return;
    }

    println!("Distance: {:.4}", d);

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
        use leet_bridge::projector::project_text_simple;
        use leet_core::operators::dist;
        let c = project_text_simple("urgente agora").unwrap();
        let d = dist(&c, &c);
        assert!(d < 1e-5);
    }
}
