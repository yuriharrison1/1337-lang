use colored::Colorize;
use std::time::Duration;
use tokio::net::TcpStream;
use tokio::time::timeout;

pub async fn run(service: &str) -> anyhow::Result<()> {
    // Normalize the service address for TCP connect
    let addr = if service.starts_with("http://") || service.starts_with("https://") {
        service
            .trim_start_matches("http://")
            .trim_start_matches("https://")
            .to_string()
    } else {
        service.to_string()
    };

    println!("{}", "Health Check".bold());
    println!("  Service: {}", service);
    println!();

    match timeout(Duration::from_secs(3), TcpStream::connect(&addr)).await {
        Ok(Ok(_)) => {
            println!("  Status : {}", "ok".green().bold());
            println!("  The leet-service is reachable at {}", addr);
        }
        Ok(Err(e)) => {
            println!("  Status : {}", "error".red().bold());
            println!("  Could not connect to {}: {}", addr, e);
            println!();
            println!("  To start the service:");
            println!("    cd leet-service && cargo run");
            println!("  Or:");
            println!("    cargo run -p leet-service");
        }
        Err(_) => {
            println!("  Status : {}", "timeout".yellow().bold());
            println!("  Connection to {} timed out after 3 seconds.", addr);
            println!();
            println!("  To start the service:");
            println!("    cd leet-service && cargo run");
            println!("  Or:");
            println!("    cargo run -p leet-service");
        }
    }

    Ok(())
}
