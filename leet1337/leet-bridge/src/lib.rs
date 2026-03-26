pub mod error;
pub mod projector;
pub mod human_to_1337;
pub mod leet_to_human;

pub use error::BridgeError;
pub use projector::{SemanticProjector, MockProjector};
pub use human_to_1337::HumanBridge;
pub use leet_to_human::{cogon_to_text, dag_to_text, msg_to_text};

// Re-export leet_core para conveniência
pub use leet_core;
