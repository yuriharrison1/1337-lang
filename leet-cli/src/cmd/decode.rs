//! leet decode — reconstruct text from a COGON JSON.

use leet_bridge::{BridgeProjector, MockProjector};
use leet_core::types::Cogon;

pub fn run(json_input: &str) {
    let cogon: Cogon = match serde_json::from_str(json_input) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Error parsing COGON JSON: {}", e);
            std::process::exit(1);
        }
    };

    let proj = MockProjector;
    match proj.reconstruct(&cogon) {
        Ok(text) => println!("{}", text),
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
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
