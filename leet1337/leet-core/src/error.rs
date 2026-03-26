use thiserror::Error;
use uuid::Uuid;

#[derive(Debug, Error)]
pub enum LeetError {
    #[error("R1: message must have exactly one intent")]
    R1SingleIntent,

    #[error("R2: DELTA intent requires ref and patch")]
    R2DeltaRequiresRef,

    #[error("R2: non-DELTA intent must not include patch")]
    R2NonDeltaHasPatch,

    #[error("R3: COGON {0} referenced in DAG but not in nodes")]
    R3UndeclaredNode(String),

    #[error("R4: DAG contains a cycle — circular cognition is anomaly")]
    R4DagCycle,

    #[error("R5: COGON {0} has low-confidence dimensions: {1:?}")]
    R5LowConfidence(String, Vec<usize>),

    #[error("R6: human_required=true but urgency not declared")]
    R6UrgencyRequired,

    #[error("R7: zone_emergent references ID not in C5 handshake")]
    R7InvalidEmergentId,

    #[error("R8: BROADCAST only allowed for ANOMALY or SYNC, got {0}")]
    R8InvalidBroadcast(String),

    #[error("R9: RAW EVIDENCE must have non-zero semantic vector")]
    R9EvidenceIncoherent,

    #[error("R10: VECTOR must have exactly {0} dimensions, got {1}")]
    R10DimensionMismatch(usize, usize),

    #[error("Dimension mismatch: expected {0}, got {1}")]
    DimensionMismatch(usize, usize),

    #[error("Scalar out of range [0,1]: {0}")]
    ScalarOutOfRange(f32),

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Alignment mismatch: expected {0}, got {1}")]
    AlignmentMismatch(String, String),

    #[error("Invalid UUID: {0}")]
    InvalidUuid(String),
}

pub type LeetResult<T> = Result<T, LeetError>;

impl From<serde_json::Error> for LeetError {
    fn from(e: serde_json::Error) -> Self {
        LeetError::Serialization(e.to_string())
    }
}

impl From<uuid::Error> for LeetError {
    fn from(e: uuid::Error) -> Self {
        LeetError::InvalidUuid(e.to_string())
    }
}

// Suppress unused import warning — Uuid is used in variants above conceptually,
// but we keep it available for callers.
#[allow(dead_code)]
fn _use_uuid(_: Uuid) {}
