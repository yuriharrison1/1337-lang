//! leet-service library — gRPC service + TCP router.

// ── Existing gRPC modules (v0.4 gRPC service) ─────────────────────────────────
pub mod batch;
pub mod config;
pub mod projection;
pub mod server;
pub mod store;

// ── New TCP/Unix socket router (v0.5.1) ───────────────────────────────────────
pub mod agent_client;
pub mod tcp_server;
