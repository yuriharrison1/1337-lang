//! leet bench — benchmark encode performance.

use std::time::{Duration, Instant};
use leet_bridge::{BridgeProjector, MockProjector};

static BENCH_TEXTS: &[&str] = &[
    "urgente agora",
    "erro no sistema",
    "deploy do pipeline",
    "reverter rollback",
    "hello world",
    "processo em andamento",
    "caiu o servidor",
    "status crítico",
    "tudo ok",
    "alerta de anomalia",
];

pub fn run(n: usize) {
    let proj = MockProjector;
    let mut durations: Vec<Duration> = Vec::with_capacity(n);

    for i in 0..n {
        let text = BENCH_TEXTS[i % BENCH_TEXTS.len()];
        let start = Instant::now();
        let _ = proj.project(text);
        durations.push(start.elapsed());
    }

    durations.sort();

    let p50 = percentile(&durations, 0.50);
    let p95 = percentile(&durations, 0.95);
    let p99 = percentile(&durations, 0.99);

    println!("Bench: {} encodes", n);
    println!("  P50: {:?}", p50);
    println!("  P95: {:?}", p95);
    println!("  P99: {:?}", p99);
}

fn percentile(sorted: &[Duration], p: f64) -> Duration {
    if sorted.is_empty() {
        return Duration::ZERO;
    }
    let idx = ((sorted.len() as f64 - 1.0) * p).round() as usize;
    sorted[idx.min(sorted.len() - 1)]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_percentile_sorted() {
        let durations: Vec<Duration> = (1..=100).map(|i| Duration::from_nanos(i)).collect();
        let p50 = percentile(&durations, 0.50);
        let p99 = percentile(&durations, 0.99);
        assert!(p50 < p99);
    }

    #[test]
    fn test_percentile_empty() {
        let d = percentile(&[], 0.5);
        assert_eq!(d, Duration::ZERO);
    }
}
