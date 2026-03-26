#![cfg(feature = "python")]
/// PyO3 Python bindings for leet_core.
/// All functions accept/return JSON strings for simple interop.
///
/// Example usage:
///   import leet_core
///   zero = leet_core.cogon_zero()        # JSON string
///   blended = leet_core.blend(c1, c2, 0.5)
///   err = leet_core.validate(msg_json)   # None=ok, str=error
use pyo3::prelude::*;

use crate::operators;
use crate::types::Cogon;
use crate::validate::Validator;

fn parse<T: serde::de::DeserializeOwned>(s: &str) -> PyResult<T> {
    serde_json::from_str(s).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("JSON parse error: {e}"))
    })
}

fn to_json<T: serde::Serialize>(val: &T) -> PyResult<String> {
    serde_json::to_string(val).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {e}"))
    })
}

/// Returns COGON_ZERO as a JSON string.
/// Example: leet_core.cogon_zero()
#[pyfunction]
fn cogon_zero() -> PyResult<String> {
    to_json(&Cogon::zero())
}

/// Create a new COGON with auto UUID and timestamp.
/// sem and unc must each be lists of 32 floats.
/// Example: leet_core.cogon_new([0.5]*32, [0.1]*32)
#[pyfunction]
fn cogon_new(sem: Vec<f32>, unc: Vec<f32>) -> PyResult<String> {
    if sem.len() != crate::FIXED_DIMS || unc.len() != crate::FIXED_DIMS {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("sem and unc must each have {} elements", crate::FIXED_DIMS),
        ));
    }
    to_json(&Cogon::new(sem, unc))
}

/// Create a COGON with a RAW field.
/// raw_role: "EVIDENCE" | "ARTIFACT" | "TRACE" | "BRIDGE"
/// Example: leet_core.cogon_with_raw([0.5]*32, [0.1]*32, "application/json", "{}", "BRIDGE")
#[pyfunction]
fn cogon_with_raw(
    sem: Vec<f32>,
    unc: Vec<f32>,
    raw_content_type: &str,
    raw_content_json: &str,
    raw_role: &str,
) -> PyResult<String> {
    let content: serde_json::Value = serde_json::from_str(raw_content_json).unwrap_or(
        serde_json::Value::String(raw_content_json.to_string()),
    );
    let role: crate::types::RawRole = serde_json::from_value(
        serde_json::Value::String(raw_role.to_string()),
    )
    .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid raw_role"))?;

    let raw = crate::types::Raw {
        content_type: raw_content_type.to_string(),
        content,
        role,
    };
    let cogon = Cogon::new(sem, unc).with_raw(raw);
    to_json(&cogon)
}

/// BLEND two COGONs (JSON strings).
/// Returns blended COGON as JSON.
/// Example: leet_core.blend(c1_json, c2_json, 0.5)
#[pyfunction]
fn blend(c1_json: &str, c2_json: &str, alpha: f32) -> PyResult<String> {
    let c1: Cogon = parse(c1_json)?;
    let c2: Cogon = parse(c2_json)?;
    let result = operators::blend(&c1, &c2, alpha)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    to_json(&result)
}

/// DELTA between two COGONs. Returns list of 32 floats.
/// Example: leet_core.delta(prev_json, curr_json)
#[pyfunction]
fn delta(prev_json: &str, curr_json: &str) -> PyResult<Vec<f32>> {
    let prev: Cogon = parse(prev_json)?;
    let curr: Cogon = parse(curr_json)?;
    operators::delta(&prev, &curr)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// DIST between two COGONs. Returns float.
/// Example: leet_core.dist(c1_json, c2_json)
#[pyfunction]
fn dist(c1_json: &str, c2_json: &str) -> PyResult<f32> {
    let c1: Cogon = parse(c1_json)?;
    let c2: Cogon = parse(c2_json)?;
    operators::dist(&c1, &c2)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// FOCUS — project COGON onto dimension subset. Returns JSON.
/// dims: list of dimension indices to keep.
/// Example: leet_core.focus(cogon_json, list(range(14)))
#[pyfunction]
fn focus(cogon_json: &str, dims: Vec<usize>) -> PyResult<String> {
    let cogon: Cogon = parse(cogon_json)?;
    let result = operators::focus(&cogon, &dims)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    to_json(&result)
}

/// ANOMALY_SCORE. Returns float. Empty history → 1.0.
/// history_json: list of COGON JSON strings.
/// Example: leet_core.anomaly_score(cogon_json, [c1_json, c2_json])
#[pyfunction]
fn anomaly_score(cogon_json: &str, history_json: Vec<String>) -> PyResult<f32> {
    let cogon: Cogon = parse(cogon_json)?;
    let history: Vec<Cogon> = history_json
        .iter()
        .map(|s| parse(s))
        .collect::<PyResult<Vec<_>>>()?;
    operators::anomaly_score(&cogon, &history)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// apply_patch — add delta to base COGON, clamped [0,1]. Returns JSON.
/// patch: list of 32 floats.
/// Example: leet_core.apply_patch(base_json, [0.1]*32)
#[pyfunction]
fn apply_patch(base_json: &str, patch: Vec<f32>) -> PyResult<String> {
    let base: Cogon = parse(base_json)?;
    let result = operators::apply_patch(&base, &patch)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    to_json(&result)
}

/// Validate MSG_1337 JSON. Returns None if valid, error string if invalid.
/// Example: err = leet_core.validate(msg_json); assert err is None
#[pyfunction]
fn validate(msg_json: &str) -> PyResult<Option<String>> {
    let msg: crate::types::Msg1337 = parse(msg_json)?;
    match Validator::validate(&msg) {
        Ok(()) => Ok(None),
        Err(e) => Ok(Some(e.to_string())),
    }
}

/// check_confidence — returns list of (cogon_id, dim_index, unc_value) soft warnings.
/// Example: warnings = leet_core.check_confidence(msg_json)
#[pyfunction]
fn check_confidence(msg_json: &str) -> PyResult<Vec<(String, usize, f32)>> {
    let msg: crate::types::Msg1337 = parse(msg_json)?;
    Ok(Validator::check_confidence(&msg)
        .into_iter()
        .map(|(id, dim, unc)| (id.to_string(), dim, unc))
        .collect())
}

/// Re-serialize MSG_1337 in canonical field order.
/// Example: canonical = leet_core.serialize_msg(msg_json)
#[pyfunction]
fn serialize_msg(msg_json: &str) -> PyResult<String> {
    let msg: crate::types::Msg1337 = parse(msg_json)?;
    to_json(&msg)
}

/// Returns the library version string.
/// Example: leet_core.version()  → "0.4.0"
#[pyfunction]
fn version() -> &'static str {
    "0.4.0"
}

#[pymodule]
pub fn leet_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cogon_zero, m)?)?;
    m.add_function(wrap_pyfunction!(cogon_new, m)?)?;
    m.add_function(wrap_pyfunction!(cogon_with_raw, m)?)?;
    m.add_function(wrap_pyfunction!(blend, m)?)?;
    m.add_function(wrap_pyfunction!(delta, m)?)?;
    m.add_function(wrap_pyfunction!(dist, m)?)?;
    m.add_function(wrap_pyfunction!(focus, m)?)?;
    m.add_function(wrap_pyfunction!(anomaly_score, m)?)?;
    m.add_function(wrap_pyfunction!(apply_patch, m)?)?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(check_confidence, m)?)?;
    m.add_function(wrap_pyfunction!(serialize_msg, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
