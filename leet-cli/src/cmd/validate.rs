//! leet validate — validate a MSG_1337 JSON file.

use leet_core::types::Msg1337;
use leet_core::validate::validate;

pub fn run(json_input: &str) {
    let msg: Msg1337 = match serde_json::from_str(json_input) {
        Ok(m) => m,
        Err(e) => {
            eprintln!("Error parsing MSG_1337 JSON: {}", e);
            std::process::exit(1);
        }
    };

    match validate(&msg) {
        Ok(()) => {
            println!("\u{2713} Message is valid (all rules passed)");
        }
        Err(e) => {
            println!("\u{2717} Validation failed: {}", e);
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use leet_core::types::*;
    use uuid::Uuid;

    fn make_valid_msg_json() -> String {
        let msg = Msg1337 {
            id: Uuid::new_v4(),
            sender: Uuid::new_v4(),
            receiver: Receiver::Agent(Uuid::new_v4()),
            intent: Intent::Assert,
            ref_hash: None,
            patch: None,
            payload: Payload::Cogon(Cogon {
                id: Uuid::new_v4(),
                sem: [0.5_f32; 32],
                unc: [0.1_f32; 32],
                stamp: 1000000,
                raw: None,
            }),
            c5: C5Block {
                zone_fixed: [0.5_f32; 32],
                zone_emergent: std::collections::HashMap::new(),
                schema_ver: "0.4.0".to_string(),
                align_hash: [0u8; 32],
            },
            surface: SurfaceBlock {
                human_required: false,
                urgency: None,
                reconstruct_depth: 1,
                lang: "pt".to_string(),
            },
        };
        serde_json::to_string(&msg).unwrap()
    }

    #[test]
    fn test_validate_valid_message() {
        let json = make_valid_msg_json();
        let msg: Msg1337 = serde_json::from_str(&json).unwrap();
        assert!(validate(&msg).is_ok());
    }
}
