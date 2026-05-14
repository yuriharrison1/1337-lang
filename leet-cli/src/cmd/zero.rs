//! leet zero — display COGON_ZERO.

use leet_core::types::Cogon;

pub fn run(json: bool) {
    let zero = Cogon::zero();

    if json {
        println!("{}", serde_json::to_string(&zero).unwrap());
        return;
    }

    println!("COGON_ZERO (v0.5.1)");
    println!("  id:              {}", zero.id);
    println!("  stamp:           {}", zero.stamp);
    println!("  sem[0] S1:       {} (INTENTION — directional purpose)", zero.sem[0]);
    println!("  sem[13] D6:      {} (PROPAGATION — maximum influence)", zero.sem[13]);
    println!("  sem[29] P6:      {} (CONFIDENCE — full certainty)", zero.sem[29]);
    println!("  raw:             None");
    println!();
    println!("JSON:");
    println!("{}", serde_json::to_string_pretty(&zero).unwrap());
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_cogon_zero_is_zero() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert!(z.is_zero());
    }

    #[test]
    fn test_cogon_zero_s1_intention() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert_eq!(z.sem[0], 1.0, "S1_INTENTION should be 1.0 in COGON_ZERO");
    }

    #[test]
    fn test_cogon_zero_p6_confidence() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert_eq!(z.sem[29], 1.0, "P6_CONFIDENCE should be 1.0 in COGON_ZERO");
    }
}
