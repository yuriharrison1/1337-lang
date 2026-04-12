//! leet-bridge — Human text ↔ 1337 semantic vector translation.
//!
//! This crate implements R21: BRIDGE agents never expose 1337 internals
//! to external systems. Text in, text out. COGONs never leave the bridge.
//!
//! # Architecture
//!
//! ```text
//! External System
//!      │ (plain text)
//!      ▼
//! ┌─────────────┐
//! │  BridgeIn   │  encode(text) → Cogon
//! │  BridgeOut  │  decode(Cogon) → text
//! └─────────────┘
//!      │ (COGON / DAG — internal only)
//!      ▼
//!  leet-core network
//! ```

pub mod anthropic_client;
pub mod claude_1337_prompt;
pub mod heuristics;
pub mod nl_translator;
pub mod projector;

pub use projector::{BridgeProjector, MockProjector};
pub use nl_translator::{nl_to_cogon, cogon_to_nl, infer_intent};

use leet_core::{Cogon, LeetError};

/// Encode human text into a COGON semantic vector.
///
/// Enforces R21: the resulting COGON must never be forwarded verbatim to
/// external systems — only the reconstructed text from `decode()` may be.
pub fn encode(text: &str, projector: &dyn BridgeProjector) -> Result<Cogon, LeetError> {
    projector.project(text)
}

/// Decode a COGON back into human-readable text.
///
/// Enforces R21: this is the only surface exposed to external systems.
pub fn decode(cogon: &Cogon, projector: &dyn BridgeProjector) -> Result<String, LeetError> {
    projector.reconstruct(cogon)
}
