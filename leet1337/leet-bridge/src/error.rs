use thiserror::Error;

#[derive(Debug, Error)]
pub enum BridgeError {
    #[error("Projection failed: {0}")]
    ProjectionFailed(String),

    #[error("Reconstruction failed: {0}")]
    ReconstructionFailed(String),

    #[error("Validation failed: {0}")]
    ValidationFailed(#[from] leet_core::LeetError),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Backend error: {0}")]
    Backend(String),
}
