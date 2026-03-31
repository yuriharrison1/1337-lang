mod config;
mod projection;
mod store;
mod server;

use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    dotenvy::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cfg = config::Config::from_env();
    tracing::info!(
        "leet-service starting | backend={} port={}",
        cfg.backend,
        cfg.port
    );

    let store = store::build(&cfg).await?;
    let engine = projection::Engine::new(&cfg).await?;

    server::run(cfg, engine, store).await
}
