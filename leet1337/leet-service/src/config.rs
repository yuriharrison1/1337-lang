#[derive(Clone, Debug)]
pub struct Config {
    pub port:            u16,
    pub backend:         String,
    pub store_url:       String,
    pub w_path:          Option<String>,
    pub batch_window_ms: u64,
    pub batch_max:       usize,
    pub embed_model:     String,
    pub embed_url:       Option<String>,
    pub embed_key:       Option<String>,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            port:            env_u16("LEET_PORT", 50051),
            backend:         env_str("LEET_BACKEND", "simd"),
            store_url:       env_str("LEET_STORE", "memory"),
            w_path:          std::env::var("LEET_W_PATH").ok(),
            batch_window_ms: env_u64("LEET_BATCH_WINDOW", 10),
            batch_max:       env_usize("LEET_BATCH_MAX", 64),
            embed_model:     env_str("LEET_EMBED_MODEL", "mock"),
            embed_url:       std::env::var("LEET_EMBED_URL").ok(),
            embed_key:       std::env::var("LEET_EMBED_KEY").ok(),
        }
    }
}

fn env_str(k: &str, default: &str) -> String {
    std::env::var(k).unwrap_or_else(|_| default.to_string())
}
fn env_u16(k: &str, d: u16) -> u16 {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
fn env_u64(k: &str, d: u64) -> u64 {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
fn env_usize(k: &str, d: usize) -> usize {
    std::env::var(k).ok().and_then(|v| v.parse().ok()).unwrap_or(d)
}
