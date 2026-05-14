//! leet decode — reconstruct text from a COGON JSON.

use leet_bridge::{BridgeProjector as _, MockProjector};
use leet_core::types::Cogon;

pub fn run(json_input: &str, top: usize) {
    let cogon: Cogon = match serde_json::from_str(json_input) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Error parsing COGON JSON: {}", e);
            std::process::exit(1);
        }
    };

    let proj = MockProjector;
    let result = proj.reconstruct(&cogon);
    // Show text summary then top-N axis breakdown.
    if let Ok(text) = result {
        println!("{}", text);
    }
    use leet_core::axes::CANONICAL_AXES;
    let n = if top > 0 { top } else { 5 };
    let mut axes: Vec<(usize, f32)> = cogon.sem.iter().enumerate()
        .map(|(i, &v)| (i, (v - 0.5).abs()))
        .collect();
    axes.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    println!("\nTop-{} most-deviated axes:", n);
    for (i, _) in axes.iter().take(n) {
        let axis = &CANONICAL_AXES[*i];
        println!("  {}_{}: {:.3}", axis.code, axis.name, cogon.sem[*i]);
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_decode_valid_cogon_json() {
        use leet_core::types::Cogon;
        let cogon = Cogon::zero();
        let json = serde_json::to_string(&cogon).unwrap();
        // Should parse without error
        let parsed: Cogon = serde_json::from_str(&json).unwrap();
        assert!(parsed.is_zero());
    }
}
