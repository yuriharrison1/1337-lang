//! leet version — print version info.

pub fn run() {
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
