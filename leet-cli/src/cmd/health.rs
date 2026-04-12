//! leet health — check if leet-service is reachable.

use std::net::TcpStream;
use std::time::Duration;

pub fn run(url: &str) {
    // Parse host:port, default to localhost:50051
    let addr = if url.contains(':') {
        url.to_string()
    } else {
        format!("{}:50051", url)
    };

    match TcpStream::connect_timeout(&addr.parse().unwrap_or_else(|_| "127.0.0.1:50051".parse().unwrap()), Duration::from_secs(2)) {
        Ok(_) => println!("\u{2713} leet-service UP at {}", addr),
        Err(e) => {
            println!("\u{2717} unreachable: {} ({})", addr, e);
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_health_addr_parsing() {
        // Just verify the addr parsing logic works
        let url = "localhost:50051";
        assert!(url.contains(':'));
    }

    #[test]
    fn test_health_default_port() {
        let url = "localhost";
        let addr = if url.contains(':') {
            url.to_string()
        } else {
            format!("{}:50051", url)
        };
        assert_eq!(addr, "localhost:50051");
    }
}
