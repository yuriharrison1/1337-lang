//! leet-service — gRPC server entry point.

use std::sync::Arc;
use tonic::transport::Server;
use tracing::info;

use leet_service::config::Config;
use leet_service::projection::Engine;
use leet_service::server::{proto::leet_service_server::LeetServiceServer, LeetServiceImpl};
use leet_service::store::{MemoryStore, SqliteStore, Store};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cfg = Config::from_env();

    // Init tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(&cfg.log)),
        )
        .init();

    let addr = format!("0.0.0.0:{}", cfg.port).parse()?;

    let engine = Arc::new(Engine::new());

    let store: Arc<dyn Store> = match cfg.store.as_str() {
        "sqlite" => {
            info!("using sqlite store at {}", cfg.sqlite_path);
            SqliteStore::new(&cfg.sqlite_path)?
        }
        _ => {
            info!("using memory store");
            MemoryStore::new()
        }
    };

    let svc = LeetServiceImpl::new(engine, store, cfg.clone());

    info!("leet-service listening on 0.0.0.0:{}", cfg.port);

    Server::builder()
        .add_service(LeetServiceServer::new(svc))
        .serve_with_shutdown(addr, async {
            tokio::signal::ctrl_c()
                .await
                .expect("failed to listen for ctrl_c");
            info!("shutdown signal received");
        })
        .await?;

    Ok(())
}
