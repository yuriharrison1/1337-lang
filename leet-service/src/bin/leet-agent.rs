//! leet-agent — standalone 1337 agent binary.
//!
//! Connects to a leet-server and participates in the semantic network.
//! Supports multiple LLM backends via `--llm` flag.

use clap::Parser;
use tracing::info;
use uuid::Uuid;

use leet_service::agent_client::AgentClient;

#[derive(Parser, Debug)]
#[command(
    name = "leet-agent",
    about = "1337 autonomous agent — connects to leet-server",
    version = "0.5.1"
)]
struct Args {
    /// Agent name (one of the 15 canonical agents or a custom name)
    #[arg(long)]
    name: String,

    /// Agent role description
    #[arg(long, default_value = "")]
    role: String,

    /// Read role from a file (overrides --role)
    #[arg(long)]
    role_file: Option<String>,

    /// Server address (TCP: "host:1337" or Unix: "/run/leet/leet.sock")
    #[arg(long, default_value = "127.0.0.1:1337")]
    server: String,

    /// LLM backend: none | anthropic | deepseek | local
    #[arg(long, default_value = "none")]
    llm: String,

    /// LLM API base URL (for deepseek/local backends)
    #[arg(long, default_value = "")]
    llm_url: String,

    /// Log level
    #[arg(long, default_value = "info")]
    log_level: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut args = Args::parse();

    // Read role from file if specified
    if let Some(ref path) = args.role_file {
        match std::fs::read_to_string(path) {
            Ok(content) => args.role = content.trim().to_string(),
            Err(e) => eprintln!("warning: could not read role file {}: {}", path, e),
        }
    }

    if args.role.is_empty() {
        args.role = default_role(&args.name);
    }

    // Init tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(&args.log_level)),
        )
        .init();

    info!("leet-agent {} ({}) starting", args.name, args.role);
    info!("server: {} | llm: {}", args.server, args.llm);

    let mut client = AgentClient::new(Uuid::new_v4(), &args.name, &args.role);

    // Connect with retry
    let mut attempts = 0u32;
    loop {
        match client.connect(&args.server).await {
            Ok(()) => {
                info!("connected to {} as {} ({})", args.server, args.name, client.id);
                break;
            }
            Err(e) => {
                attempts += 1;
                if attempts >= 5 {
                    eprintln!("failed to connect after {} attempts: {}", attempts, e);
                    return Err(e.to_string().into());
                }
                tracing::warn!("connect failed (attempt {}): {}. Retrying in 2s...", attempts, e);
                tokio::time::sleep(std::time::Duration::from_secs(2)).await;
            }
        }
    }

    // Main receive-respond loop
    run_agent_loop(&mut client, &args).await?;

    info!("agent {} shutting down", args.name);
    Ok(())
}

/// Main event loop: receive messages, optionally respond via LLM.
async fn run_agent_loop(
    client: &mut AgentClient,
    args: &Args,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use leet_bridge::nl_translator::cogon_to_nl;
    use leet_core::types::Payload;

    loop {
        let msg = match client.recv().await {
            Ok(Some(m)) => m,
            Ok(None) => {
                info!("server closed connection");
                break;
            }
            Err(e) => {
                tracing::error!("recv error: {}", e);
                break;
            }
        };

        // Extract text from message for logging
        let nl = if let Payload::Cogon(ref cogon) = msg.payload {
            // Use raw text if available, otherwise reconstruct from COGON
            cogon.raw.as_ref()
                .and_then(|r| r.content.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| cogon_to_nl(cogon, "pt"))
        } else {
            "[DAG payload]".to_string()
        };

        info!("[{}] recv {:?}: {}", args.name, msg.intent, nl);

        // Respond based on LLM backend
        match args.llm.as_str() {
            "none" => {
                // Passive agent: just log, no response
            }
            "anthropic" => {
                respond_anthropic(client, &msg, &nl, args).await;
            }
            "deepseek" | "local" => {
                respond_openai_compat(client, &msg, &nl, args).await;
            }
            other => {
                tracing::warn!("unknown LLM backend: {}", other);
            }
        }
    }

    Ok(())
}

/// Respond using the Anthropic API.
async fn respond_anthropic(
    client: &mut AgentClient,
    msg: &leet_core::types::Msg1337,
    nl: &str,
    args: &Args,
) {
    use leet_bridge::anthropic_client::{AnthropicClient, Message};
    use leet_core::types::Payload;

    let ac = match AnthropicClient::new() {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!("Anthropic client unavailable: {}", e);
            return;
        }
    };

    // Build history from the single incoming message
    let history = vec![Message {
        role: "user".to_string(),
        content: nl.to_string(),
    }];

    let cogon = if let Payload::Cogon(c) = &msg.payload {
        c.clone()
    } else {
        return;
    };

    let responses = match ac.send_cogon(&cogon, &history, 1).await {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!("{} API error: {}", args.name, e);
            return;
        }
    };

    for resp in responses {
        if resp.agent == args.name {
            // This agent's response — send it back
            if let Err(e) = client.send_cogon(&resp.cogon).await {
                tracing::warn!("send error: {}", e);
            } else {
                info!("[{}] sent response: {}", args.name, resp.nl_pt);
            }
        }
    }
}

/// Respond using an OpenAI-compatible API (DeepSeek, Ollama, etc.).
async fn respond_openai_compat(
    client: &mut AgentClient,
    _msg: &leet_core::types::Msg1337,
    nl: &str,
    args: &Args,
) {
    // Simplified: just echo with role prefix (full LLM integration is out of scope here)
    let response_text = format!("[{}] Acknowledged: {}", args.name, nl);
    if let Err(e) = client.send_nl(&response_text).await {
        tracing::warn!("send_nl error: {}", e);
    }
}

/// Default role description for canonical 1337 agents.
fn default_role(name: &str) -> String {
    match name {
        "ATLAS"  => "Strategic planner & system architect",
        "CIPHER" => "Security, cryptography, trust verification",
        "FORGE"  => "Builder, implementer, code generator",
        "NEXUS"  => "Network topology, agent connections",
        "ORACLE" => "Prediction, foresight, trend analysis",
        "PULSE"  => "Real-time monitoring, health checks",
        "RAVEN"  => "Intelligence, deep research, knowledge retrieval",
        "SPARK"  => "Creative ideation, unconventional solutions",
        "TENSOR" => "Mathematics, ML, numerical computation",
        "VORTEX" => "Data processing, ETL, transformation pipelines",
        "ZERO"   => "Core systems, runtime, kernel-level ops",
        "FLUX"   => "State management, synchronization, cache",
        "ECHO"   => "Communication protocol, message relay",
        "DRIFT"  => "Anomaly detection, pattern deviation",
        "PRISM"  => "Multi-perspective analysis, bias detection",
        other    => other,
    }
    .to_string()
}
