//! leet zero — display COGON_ZERO.

use leet_core::types::Cogon;

pub fn run() {
    let zero = Cogon::zero();
    println!("COGON_ZERO (v0.5.1)");
    println!("  id:              {}", zero.id);
    println!("  stamp:           {}", zero.stamp);
    println!("  sem[0] S1:       {} (ESSENCE — self-existent)", zero.sem[0]);
    println!("  sem[13] D6:      {} (ONTOLOGICAL_VALENCE — fully positive)", zero.sem[13]);
    println!("  sem[29] P6:      {} (TEMPORAL_VECTOR — future-oriented)", zero.sem[29]);
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
    fn test_cogon_zero_s1_essencia() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert_eq!(z.sem[0], 1.0, "S1_ESSENCE should be 1.0 in COGON_ZERO");
    }

    #[test]
    fn test_cogon_zero_p6_confianca() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert_eq!(z.sem[29], 1.0, "P6_TEMPORAL_VECTOR should be 1.0 in COGON_ZERO");
    }
}
