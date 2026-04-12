//! leet inspect — show top-10 activated axes in a COGON.

use colored::Colorize;
use leet_core::axes::CANONICAL_AXES;
use leet_core::types::Cogon;

pub fn run(json_input: &str) {
    let cogon: Cogon = match serde_json::from_str(json_input) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Error parsing COGON JSON: {}", e);
            std::process::exit(1);
        }
    };

    println!("Inspecting COGON: {}", cogon.id);
    println!("Top-10 activated axes:");

    let mut indexed: Vec<(usize, f32)> = cogon
        .sem
        .iter()
        .enumerate()
        .map(|(i, &v)| (i, v))
        .collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    for (rank, (i, v)) in indexed.iter().take(10).enumerate() {
        let axis = &CANONICAL_AXES[*i];
        let label = format!("{}_{}", axis.code, axis.name);
        let line = format!("  {:2}. {:28} = {:.4}  (unc={:.4})", rank + 1, label, v, cogon.unc[*i]);
        if *v > 0.8 {
            println!("{}", line.red());
        } else if *v >= 0.5 {
            println!("{}", line.yellow());
        } else {
            println!("{}", line.dimmed());
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_inspect_parses_cogon_json() {
        use leet_core::types::Cogon;
        let mut c = Cogon::zero();
        c.sem[22] = 0.95;
        let json = serde_json::to_string(&c).unwrap();
        let parsed: Cogon = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.sem[22], 0.95);
    }
}
