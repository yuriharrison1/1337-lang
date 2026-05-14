//! leet blend — blend two sem vectors or texts with alpha weight.

use leet_core::operators::blend as cogon_blend;
use leet_core::types::Cogon;

fn parse_or_project(input: &str) -> Cogon {
    if let Ok(arr) = serde_json::from_str::<Vec<f32>>(input) {
        if arr.len() == 32 {
            let mut cogon = Cogon::zero();
            cogon.sem.copy_from_slice(&arr);
            return cogon;
        }
    }
    let parts: Vec<f32> = input.split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();
    if parts.len() == 32 {
        let mut cogon = Cogon::zero();
        cogon.sem.copy_from_slice(&parts);
        return cogon;
    }
    leet_bridge::projector::project_text_simple(input).unwrap_or_else(|_| Cogon::zero())
}

pub fn run(text_a: &str, text_b: &str, alpha: f32, json: bool) {
    let ca = parse_or_project(text_a);
    let cb = parse_or_project(text_b);
    let blended = cogon_blend(&ca, &cb, alpha);

    if json {
        println!("{}", serde_json::to_string(&blended).unwrap());
        return;
    }

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
        use leet_bridge::projector::project_text_simple;
        use leet_core::operators::blend;
        let c1 = project_text_simple("urgente").unwrap();
        let c2 = project_text_simple("hello").unwrap();
        let result = blend(&c1, &c2, 0.5);
        // Result should be clamped in [0, 1]
        assert!(result.sem.iter().all(|&v| v >= 0.0 && v <= 1.0));
    }
}
