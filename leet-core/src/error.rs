use thiserror::Error;
use uuid::Uuid;

/// One error variant per rule R1–R21 plus general errors.
#[derive(Debug, Error, Clone, PartialEq)]
pub enum LeetError {
    // R1: Every MSG_1337 has exactly one intent.
    #[error("R1: message is missing an intent")]
    R1MissingIntent,

    // R2: intent=DELTA requires ref+patch; non-DELTA prohibits patch.
    #[error("R2: DELTA intent requires both ref and patch fields")]
    R2DeltaRefMismatch,

    #[error("R2: non-DELTA intent must not include patch field")]
    R2NonDeltaPatch,

    // R3: Every COGON referenced in DAG must be declared in nodes.
    #[error("R3: DAG references unknown node {0}")]
    R3MissingNode(Uuid),

    // R4: DAG cannot have cycles.
    #[error("R4: DAG contains a cycle")]
    R4Cycle,

    // R5: P6_CONFIANCA (sem[29]) < 0.1 triggers low-confidence flag.
    #[error("R5: low confidence — P6_TEMPORAL_VECTOR at dim {dim} = {value:.3} (threshold 0.1)")]
    R5LowConfidence { dim: usize, value: f32 },

    // R6: surface.human_required=true requires urgency declared.
    #[error("R6: human_required=true but urgency is not set")]
    R6MissingUrgency,

    // R7: zone_emergent only references IDs registered in C5 handshake.
    #[error("R7: zone_emergent references unregistered emergent ID {0}")]
    R7UnregisteredEmergent(Uuid),

    // R8: BROADCAST only for ANOMALY or SYNC.
    #[error("R8: BROADCAST receiver only allowed for ANOMALY or SYNC intent")]
    R8InvalidBroadcast,

    // R9: RAW role=EVIDENCE must have coherent sem (non-zero).
    #[error("R9: RAW role=EVIDENCE has incoherent sem (all zeros)")]
    R9IncoherentEvidence,

    // R10: VECTOR[32] indexed by position.
    #[error("R10: vector has wrong dimensionality: expected 32, got {0}")]
    R10WrongDimension(usize),

    // R14: No DAG node processed before all parents absorbed.
    #[error("R14: DAG node {0} has unabsorbed parent")]
    R14ParentNotAbsorbed(Uuid),

    // R16: FOCUS always before BLEND.
    #[error("R16: FOCUS operator must precede BLEND")]
    R16FocusAfterBlend,

    // R19: Max inheritance chain 4 levels.
    #[error("R19: inheritance chain exceeds maximum depth of 4")]
    R19InheritanceTooDeep,

    // R20: Every agent transmits COGON_ZERO before any other message.
    #[error("R20: agent must transmit COGON_ZERO before any other message")]
    R20MissingCogonZero,

    // R21: BRIDGE agent never exposes 1337 internals to external system.
    #[error("R21: BRIDGE agent attempted to expose 1337 internals")]
    R21BridgeExposure,

    // R22: All sem values must be in [0.0, 1.0].
    #[error("R22: sem[{dim}] = {value:.4} is out of [0.0, 1.0] range")]
    R22SemOutOfRange { dim: usize, value: f32 },

    // R23: stamp must be >= 0 (nanoseconds since epoch).
    #[error("R23: stamp = {0} is negative (must be >= 0)")]
    R23NegativeStamp(i64),

    // General errors
    #[error("dimension mismatch: expected {expected}, got {got}")]
    DimensionMismatch { expected: usize, got: usize },

    #[error("scalar out of range [0,1]: {0}")]
    ScalarOutOfRange(f32),

    #[error("alignment mismatch: emergent index {0} not aligned")]
    AlignmentMismatch(usize),

    #[error("serialization error: {0}")]
    SerializationError(String),
}

impl LeetError {
    pub fn rule_code(&self) -> &'static str {
        match self {
            Self::R1MissingIntent => "R1",
            Self::R2DeltaRefMismatch | Self::R2NonDeltaPatch => "R2",
            Self::R3MissingNode(_) => "R3",
            Self::R4Cycle => "R4",
            Self::R5LowConfidence { .. } => "R5",
            Self::R6MissingUrgency => "R6",
            Self::R7UnregisteredEmergent(_) => "R7",
            Self::R8InvalidBroadcast => "R8",
            Self::R9IncoherentEvidence => "R9",
            Self::R10WrongDimension(_) => "R10",
            Self::R14ParentNotAbsorbed(_) => "R14",
            Self::R16FocusAfterBlend => "R16",
            Self::R19InheritanceTooDeep => "R19",
            Self::R20MissingCogonZero => "R20",
            Self::R21BridgeExposure => "R21",
            Self::R22SemOutOfRange { .. } => "R22",
            Self::R23NegativeStamp(_) => "R23",
            _ => "ERR",
        }
    }
}
