//! leet blend — blend two texts with alpha weight.

use leet_bridge::{BridgeProjector, MockProjector};
use leet_core::operators::blend as cogon_blend;

pub fn run(text_a: &str, text_b: &str, alpha: f32) {
    let proj = MockProjector;
    let ca = proj.project(text_a).unwrap();
    let cb = proj.project(text_b).unwrap();

    let blended = cogon_blend(&ca, &cb, alpha);

    println!("COGON blend(alpha={:.2}): {}", alpha, blended.id);
    println!("Semantic vector (top activated):");
    let mut indexed: Vec<(usize, f32)> = blended.sem.iter().enumerate().map(|(i, &v)| (i, v)).collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    for (i, v) in indexed.iter().take(5) {
        let axis = &leet_core::axes::CANONICAL_AXES[*i];
        println!("  {}_{}: {:.3}", axis.code, axis.name, v);
    }
    println!("\nJSON: {}", serde_json::to_string(&blended).unwrap());
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_blend_alpha_half() {
        use leet_bridge::{BridgeProjector, MockProjector};
        use leet_core::operators::blend;
        let proj = MockProjector;
        let c1 = proj.project("urgente").unwrap();
        let c2 = proj.project("hello").unwrap();
        let result = blend(&c1, &c2, 0.5);
        // C1_URGENCIA should be between hello's 0.5 and urgente's 0.95
        assert!(result.sem[22] > 0.5 && result.sem[22] < 0.95 + 0.01);
    }
}
