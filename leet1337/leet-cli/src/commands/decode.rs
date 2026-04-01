use colored::Colorize;
use leet_core::axes::CANONICAL_AXES;

pub fn run(sem_json: &str) -> anyhow::Result<()> {
    let sem: Vec<f32> = serde_json::from_str(sem_json)?;
    if sem.len() != 32 {
        anyhow::bail!("Expected 32 floats, got {}", sem.len());
    }
    let unc = vec![0.5f32; 32];

    println!("{}", "COGON decode".bold());
    println!();

    // High confidence signals (unc < 0.4, which here means sem far from 0.5)
    println!("{}", "High confidence signals (unc < 0.4):".bold());
    let mut found = false;
    for axis in CANONICAL_AXES.iter() {
        let i = axis.index;
        let s = sem[i];
        let u = unc[i];
        if u < 0.4 {
            let level = describe_level(s);
            println!("  [{:2}] {:<22} : {:.3}  — {}", i, axis.name, s, level);
            found = true;
        }
    }
    if !found {
        println!("  (none — all uncertainty = 0.5 since unc vector not provided)");
    }
    println!();

    // Key axes
    println!("{}", "Key axis positions:".bold());
    let key_indices = [
        leet_core::axes::C9_NATUREZA,
        leet_core::axes::C8_VETOR_TEMPORAL,
        leet_core::axes::C10_VALENCIA_ACAO,
    ];
    for &i in &key_indices {
        let axis = &CANONICAL_AXES[i];
        let s = sem[i];
        let interp = interpret_key_axis(axis.code, s);
        println!("  [{:2}] {:<22} : {:.3}  — {}", i, axis.name, s, interp);
    }
    println!();

    // All axes summary
    println!("{}", "Full vector:".bold());
    for axis in CANONICAL_AXES.iter() {
        let i = axis.index;
        let s = sem[i];
        println!("  [{:2}] {:<22} : {:.3}", i, axis.name, s);
    }

    Ok(())
}

fn describe_level(val: f32) -> &'static str {
    if val > 0.8 {
        "very high"
    } else if val > 0.6 {
        "high"
    } else if val > 0.4 {
        "medium"
    } else if val > 0.2 {
        "low"
    } else {
        "very low"
    }
}

fn interpret_key_axis(code: &str, val: f32) -> String {
    match code {
        "C9" => {
            if val < 0.33 {
                "substantive (noun-like)".to_string()
            } else if val < 0.67 {
                "mixed (noun/verb)".to_string()
            } else {
                "verbal (verb-like)".to_string()
            }
        }
        "C8" => {
            if val < 0.33 {
                "past-oriented".to_string()
            } else if val < 0.67 {
                "present-focused".to_string()
            } else {
                "future-oriented".to_string()
            }
        }
        "C10" => {
            if val < 0.33 {
                "negative / alert / contractive".to_string()
            } else if val < 0.67 {
                "neutral / query".to_string()
            } else {
                "positive / confirmation / expansive".to_string()
            }
        }
        _ => format!("{:.3}", val),
    }
}

#[cfg(test)]
mod tests {
    use super::run;

    fn sem_json_32(val: f32) -> String {
        let v: Vec<f32> = vec![val; 32];
        serde_json::to_string(&v).unwrap()
    }

    #[test]
    fn test_decode_valid_32_floats() {
        let json = sem_json_32(0.5);
        assert!(run(&json).is_ok(), "decode should succeed with 32 floats");
    }

    #[test]
    fn test_decode_wrong_dim_fails() {
        let small: Vec<f32> = vec![0.5; 16];
        let json = serde_json::to_string(&small).unwrap();
        assert!(run(&json).is_err(), "decode should fail with 16 floats");
    }

    #[test]
    fn test_decode_empty_array_fails() {
        assert!(run("[]").is_err(), "decode should fail with empty array");
    }

    #[test]
    fn test_decode_invalid_json_fails() {
        assert!(run("not json at all").is_err(), "decode should fail with invalid JSON");
    }

    #[test]
    fn test_decode_extreme_values_accepted() {
        let vals: Vec<f32> = (0..32).map(|i| if i % 2 == 0 { 0.0 } else { 1.0 }).collect();
        let json = serde_json::to_string(&vals).unwrap();
        assert!(run(&json).is_ok(), "decode should accept values at extremes");
    }
}
