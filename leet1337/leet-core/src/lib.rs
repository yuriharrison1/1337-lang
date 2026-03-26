pub mod axes;
pub mod error;
pub mod ffi;
pub mod operators;
pub mod types;
pub mod validate;

#[cfg(feature = "python")]
pub mod python;

pub use error::{LeetError, LeetResult};
pub use types::{
    Anchor, CanonicalSpace, Cogon, Dag, Edge, EdgeType, EmergentRegistration, Hash, Id, Intent,
    Msg1337, Payload, Raw, RawRole, Receiver, Scalar, SemanticVector, Surface,
};
pub use operators::{anomaly_score, apply_patch, blend, delta, dist, focus};
pub use validate::Validator;

pub const FIXED_DIMS: usize = 32;
pub const MAX_INHERITANCE_DEPTH: usize = 4;
pub const LOW_CONFIDENCE_THRESHOLD: f32 = 0.9;

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn leet_core_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    python::leet_core(m)
}
