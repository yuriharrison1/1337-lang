//! PyO3 bindings for `leet-core`, built with `--features python`.
//!
//! Mirrors [`crate::ffi`] one-to-one but exchanges owned Rust `String`s
//! instead of raw C pointers — PyO3 handles the memory management.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

use crate::operators::{blend as op_blend, dist as op_dist};
use crate::types::Cogon;

fn now_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

fn cogon_from_json(s: &str) -> PyResult<Cogon> {
    serde_json::from_str(s).map_err(|e| PyValueError::new_err(e.to_string()))
}

fn cogon_to_json(c: &Cogon) -> PyResult<String> {
    serde_json::to_string(c).map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Builds a new `Cogon` from a 32-element `sem` vector. Returns it as JSON.
#[pyfunction]
fn cogon_new(sem: Vec<f32>) -> PyResult<String> {
    if sem.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "sem must have 32 dimensions, got {}",
            sem.len()
        )));
    }
    let mut sem_arr = [0.0_f32; 32];
    sem_arr.copy_from_slice(&sem);
    let cogon = Cogon {
        id: Uuid::new_v4(),
        sem: sem_arr,
        stamp: now_millis(),
        raw: None,
    };
    cogon_to_json(&cogon)
}

/// Returns COGON_ZERO as JSON.
#[pyfunction]
fn cogon_zero() -> PyResult<String> {
    cogon_to_json(&Cogon::zero())
}

/// BLEND(c1, c2, alpha) — see `leet-core::operators::blend`.
#[pyfunction]
fn blend(c1_json: &str, c2_json: &str, alpha: f32) -> PyResult<String> {
    let c1 = cogon_from_json(c1_json)?;
    let c2 = cogon_from_json(c2_json)?;
    cogon_to_json(&op_blend(&c1, &c2, alpha))
}

/// DIST(c1, c2) — see `leet-core::operators::dist`.
#[pyfunction]
fn dist(c1_json: &str, c2_json: &str) -> PyResult<f32> {
    let c1 = cogon_from_json(c1_json)?;
    let c2 = cogon_from_json(c2_json)?;
    Ok(op_dist(&c1, &c2))
}

/// Returns the `leet-core` crate version.
#[pyfunction]
fn version() -> String {
    crate::VERSION.to_string()
}

#[pymodule]
fn leet_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cogon_new, m)?)?;
    m.add_function(wrap_pyfunction!(cogon_zero, m)?)?;
    m.add_function(wrap_pyfunction!(blend, m)?)?;
    m.add_function(wrap_pyfunction!(dist, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
