use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::time::{Duration, Instant};

use crate::commands::project_mock;

const SAMPLE_TEXTS: [&str; 20] = [
    "The quick brown fox jumps over the lazy dog",
    "Quantum entanglement challenges our understanding of locality",
    "Economic inequality drives social instability",
    "Machine learning models require large training datasets",
    "The mitochondria is the powerhouse of the cell",
    "Democracy depends on an informed citizenry",
    "Entropy always increases in isolated systems",
    "Language shapes thought and perception of reality",
    "Climate change threatens biodiversity worldwide",
    "Love is the fundamental force of human connection",
    "Consciousness may emerge from complex information processing",
    "Free markets allocate resources through price signals",
    "The nervous system encodes experience as neural patterns",
    "Art communicates what language cannot express",
    "Political power corrupts without institutional checks",
    "Evolution selects for reproductive fitness not happiness",
    "Gravity curves spacetime according to general relativity",
    "Trust is the foundation of cooperative societies",
    "Uncertainty is inherent in quantum measurement",
    "History repeats as tragedy then as farce",
];

pub async fn run(n: usize, parallel: bool, _service: &str) -> anyhow::Result<()> {
    println!(
        "{} n={}, parallel={}",
        "COGON Benchmark".bold(),
        n,
        parallel
    );
    println!();

    let pb = ProgressBar::new(n as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta})")
            .unwrap_or_else(|_| ProgressStyle::default_bar())
            .progress_chars("#>-"),
    );

    let mut latencies: Vec<Duration> = Vec::with_capacity(n);

    if parallel {
        // Split work into chunks and use tokio::spawn
        let chunk_size = (n / num_cpus()).max(1);
        let mut handles = Vec::new();

        let mut remaining = n;
        while remaining > 0 {
            let count = chunk_size.min(remaining);
            remaining = remaining.saturating_sub(count);
            handles.push(tokio::spawn(async move {
                let mut lats = Vec::with_capacity(count);
                for j in 0..count {
                    let text = SAMPLE_TEXTS[j % SAMPLE_TEXTS.len()];
                    let start = Instant::now();
                    let _ = project_mock(text);
                    lats.push(start.elapsed());
                }
                lats
            }));
        }

        for handle in handles {
            let chunk_lats = handle.await?;
            for lat in chunk_lats {
                latencies.push(lat);
                pb.inc(1);
            }
        }
    } else {
        for i in 0..n {
            let text = SAMPLE_TEXTS[i % SAMPLE_TEXTS.len()];
            let start = Instant::now();
            let _ = project_mock(text);
            latencies.push(start.elapsed());
            pb.inc(1);
        }
    }

    pb.finish_with_message("done");

    // Compute stats
    latencies.sort();
    let total: Duration = latencies.iter().sum();
    let avg = total / latencies.len() as u32;
    let p50 = latencies[latencies.len() / 2];
    let p95 = latencies[(latencies.len() as f64 * 0.95) as usize];
    let p99 = latencies[((latencies.len() as f64 * 0.99) as usize).min(latencies.len() - 1)];
    let throughput = n as f64 / total.as_secs_f64();

    println!();
    println!("{}", "Results:".bold());
    println!("  Throughput : {:.0} ops/sec", throughput);
    println!("  Avg latency: {:?}", avg);
    println!("  p50 latency: {:?}", p50);
    println!("  p95 latency: {:?}", p95);
    println!("  p99 latency: {:?}", p99);
    println!("  Total ops  : {}", n);

    Ok(())
}

fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
}
