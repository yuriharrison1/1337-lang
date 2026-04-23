use thiserror::Error;

#[derive(Debug, Error)]
pub enum BridgeError {
    #[error(
        "W matrix not available — not found at LEET_W_PATH or default locations \
         (./calibration/data/W.bin, /usr/share/leetlang/W.bin); \
         enable feature `keyword-fallback` for degraded mode"
    )]
    WMatrixNotAvailable,

    #[error("W matrix load error: {0}")]
    WLoadError(String),

    #[error("dimension mismatch: expected {expected}, got {got}")]
    DimensionMismatch { expected: usize, got: usize },

    #[error("projection error: {0}")]
    ProjectionError(String),
}
