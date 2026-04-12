//! Configuration from environment variables.

/// Runtime configuration for leet-service.
#[derive(Debug, Clone)]
pub struct Config {
    /// Port to listen on (LEET_PORT, default: 50051)
    pub port: u16,
    /// Store backend ("memory" or "sqlite") (LEET_STORE, default: "memory")
    pub store: String,
    /// Path to SQLite DB (LEET_SQLITE_PATH, default: ".leet_store.db")
    pub sqlite_path: String,
    /// Log level (LEET_LOG, default: "info")
    pub log: String,
}

impl Config {
    /// Load configuration from environment variables with sensible defaults.
    pub fn from_env() -> Self {
        let port = std::env::var("LEET_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(50051u16);

        let store = std::env::var("LEET_STORE")
            .unwrap_or_else(|_| "memory".to_string());

        let sqlite_path = std::env::var("LEET_SQLITE_PATH")
            .unwrap_or_else(|_| ".leet_store.db".to_string());

        let log = std::env::var("LEET_LOG")
            .unwrap_or_else(|_| "info".to_string());

        Self {
            port,
            store,
            sqlite_path,
            log,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        // Clear env vars to test defaults
        std::env::remove_var("LEET_PORT");
        std::env::remove_var("LEET_STORE");
        std::env::remove_var("LEET_SQLITE_PATH");
        std::env::remove_var("LEET_LOG");

        let cfg = Config::from_env();
        assert_eq!(cfg.port, 50051);
        assert_eq!(cfg.store, "memory");
        assert_eq!(cfg.sqlite_path, ".leet_store.db");
        assert_eq!(cfg.log, "info");
    }
}
