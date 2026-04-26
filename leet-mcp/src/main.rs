//! leet-mcp — Model Context Protocol server for the 1337 language.
//!
//! Transport: stdio (spawned as subprocess by Claude Code).
//! All logging goes to stderr; stdout is reserved for JSON-RPC.

use anyhow::Result;
use tracing_subscriber::EnvFilter;

mod protocol;
mod server;
mod store;
mod tools;

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("leet_mcp=info")),
        )
        .init();

    tracing::info!("leet-mcp starting (v{})", env!("CARGO_PKG_VERSION"));

    let project_root = match std::env::var("LEET_PROJECT_ROOT") {
        Ok(p) => std::path::PathBuf::from(p),
        Err(_) => std::env::current_dir()?,
    };

    tracing::info!("project root: {}", project_root.display());

    let store = store::PersonalStore::open_or_create(&project_root)?;
    tracing::info!("store loaded: {} cogons", store.len());

    server::run_stdio(store).await?;

    tracing::info!("leet-mcp exiting");
    Ok(())
}
