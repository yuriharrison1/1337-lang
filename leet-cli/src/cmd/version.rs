//! leet version — print version info.

pub fn run(json: bool) {
    if json {
        println!("{}", serde_json::json!({
            "leet": env!("CARGO_PKG_VERSION"),
            "leet-core": leet_core::VERSION,
            "spec": leet_core::SPEC_VERSION,
        }));
        return;
    }
    println!("leet-cli {}", env!("CARGO_PKG_VERSION"));
    println!("leet-core {}", leet_core::VERSION);
    println!("spec v{}", leet_core::SPEC_VERSION);
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_version_constants() {
        assert_eq!(leet_core::VERSION, "0.5.1");
        assert_eq!(leet_core::SPEC_VERSION, "0.5.1");
    }
}
