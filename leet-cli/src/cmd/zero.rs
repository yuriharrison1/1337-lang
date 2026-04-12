//! leet zero — display COGON_ZERO.

use leet_core::types::Cogon;

pub fn run() {
    let zero = Cogon::zero();
    println!("COGON_ZERO");
    println!("  id:    {}", zero.id);
    println!("  stamp: {}", zero.stamp);
    println!("  sem:   [{}, ..., {}] (all 1.0, 32 dims)", zero.sem[0], zero.sem[31]);
    println!("  unc:   [{}, ..., {}] (all 0.0, 32 dims)", zero.unc[0], zero.unc[31]);
    println!("  raw:   None");
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
    fn test_cogon_zero_sem_all_ones() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert!(z.sem.iter().all(|&v| v == 1.0));
    }

    #[test]
    fn test_cogon_zero_unc_all_zeros() {
        use leet_core::types::Cogon;
        let z = Cogon::zero();
        assert!(z.unc.iter().all(|&v| v == 0.0));
    }
}
