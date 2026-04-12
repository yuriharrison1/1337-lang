//! 1337 Core Library — Rust implementation
//!
//! This crate provides the core types and operators for the 1337
//! inter-agent communication language.

pub mod axes;
pub mod codec;
pub mod error;
pub mod operators;
pub mod protocol;
pub mod types;
pub mod validate;

// Re-export commonly used items
pub use axes::CANONICAL_AXES;
pub use codec::{encode_cogon, decode_cogon, binary_size, compare_sizes};
pub use error::LeetError;
pub use operators::{blend, delta, dist, focus, anomaly_score};
pub use types::{Cogon, Dag, Edge, EdgeType, Intent, Msg1337, Receiver, SemVec};
pub use validate::{validate, check_confidence};

/// Library version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Specification version
pub const SPEC_VERSION: &str = "0.4";
