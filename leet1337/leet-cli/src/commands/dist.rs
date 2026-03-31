use colored::Colorize;
use leet_core::axes::CANONICAL_AXES;

use crate::commands::project_mock;

pub async fn run(text1: &str, text2: &str, _service: &str) -> anyhow::Result<()> {
    let c1 = project_mock(text1);
    let c2 = project_mock(text2);

    let sem1 = &c1.sem;
    let sem2 = &c2.sem;
    let unc1 = &c1.unc;
    let unc2 = &c2.unc;

    // Weighted cosine distance
    let mut dot = 0.0f32;
    let mut n1_sq = 0.0f32;
    let mut n2_sq = 0.0f32;
    let mut weights = vec![0.0f32; 32];

    for i in 0..32 {
        let w = (1.0 - unc1[i]) * (1.0 - unc2[i]);
        weights[i] = w;
        dot += sem1[i] * sem2[i] * w;
        n1_sq += sem1[i] * sem1[i] * w;
        n2_sq += sem2[i] * sem2[i] * w;
    }

    let n1 = n1_sq.sqrt() + 1e-8;
    let n2 = n2_sq.sqrt() + 1e-8;
    let sim = dot / (n1 * n2);
    let dist = 1.0 - sim;

    println!("{}", "COGON Distance".bold());
    println!("  Text 1 : \"{}\"", text1);
    println!("  Text 2 : \"{}\"", text2);
    println!();
    println!("  Distance   : {:.4}", dist);
    println!("  Similarity : {:.4}", sim);
    println!();

    // Top contributing axes (highest w * sem1 * sem2)
    let mut contributions: Vec<(usize, f32)> = (0..32)
        .map(|i| {
            let contrib = weights[i] * sem1[i] * sem2[i];
            (i, contrib)
        })
        .collect();
    contributions.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    println!("{}", "Top contributing axes:".bold());
    for (i, contrib) in contributions.iter().take(5) {
        let axis = &CANONICAL_AXES[*i];
        println!(
            "  [{:2}] {:<22}: contrib={:.4}  sem1={:.3}  sem2={:.3}  w={:.3}",
            i, axis.name, contrib, sem1[*i], sem2[*i], weights[*i]
        );
    }
    println!();

    // Interpretation
    println!("{}", "Interpretation:".bold());
    let interp = if dist < 0.1 {
        "Nearly identical semantic content"
    } else if dist < 0.3 {
        "Very similar — strong conceptual overlap"
    } else if dist < 0.5 {
        "Moderately similar — partial overlap"
    } else if dist < 0.7 {
        "Dissimilar — weak conceptual relation"
    } else {
        "Very dissimilar — orthogonal or opposite concepts"
    };
    println!("  {}", interp);

    Ok(())
}
