/// C ABI for leet_core — callable from any language.
///
/// MEMORY CONTRACT:
/// - All returned *mut c_char strings are heap-allocated by Rust.
/// - Caller MUST free them with leet_free_string().
/// - Passing NULL input pointers is undefined behavior.
/// - leet_validate returns NULL on success; a non-null string on error.
/// - leet_version returns a static string — do NOT free it.
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

use crate::operators;
use crate::types::Cogon;
use crate::validate::Validator;

// ─── Helpers ─────────────────────────────────────────────────────────────────

unsafe fn c_str_to_str<'a>(ptr: *const c_char) -> Option<&'a str> {
    if ptr.is_null() {
        return None;
    }
    CStr::from_ptr(ptr).to_str().ok()
}

fn to_json_ptr<T: serde::Serialize>(val: &T) -> *mut c_char {
    match serde_json::to_string(val) {
        Ok(s) => match CString::new(s) {
            Ok(cs) => cs.into_raw(),
            Err(_) => std::ptr::null_mut(),
        },
        Err(_) => std::ptr::null_mut(),
    }
}

fn parse_json<T: serde::de::DeserializeOwned>(s: &str) -> Option<T> {
    serde_json::from_str(s).ok()
}

// ─── Public FFI ──────────────────────────────────────────────────────────────

/// Free a string previously returned by any leet_* function.
#[no_mangle]
pub extern "C" fn leet_free_string(s: *mut c_char) {
    unsafe {
        if !s.is_null() {
            drop(CString::from_raw(s));
        }
    }
}

/// Returns the library version as a static string. Do NOT free.
#[no_mangle]
pub extern "C" fn leet_version() -> *const c_char {
    b"0.4.0\0".as_ptr() as *const c_char
}

/// Returns COGON_ZERO as a JSON string. Caller must free with leet_free_string.
#[no_mangle]
pub extern "C" fn leet_cogon_zero() -> *mut c_char {
    to_json_ptr(&Cogon::zero())
}

/// Create a new COGON from sem and unc float arrays.
/// dims must equal 32. Returns JSON string or NULL on error.
#[no_mangle]
pub extern "C" fn leet_cogon_new(
    sem: *const f32,
    unc: *const f32,
    dims: usize,
) -> *mut c_char {
    if sem.is_null() || unc.is_null() || dims != crate::FIXED_DIMS {
        return std::ptr::null_mut();
    }
    let sem_vec: Vec<f32> = unsafe { std::slice::from_raw_parts(sem, dims).to_vec() };
    let unc_vec: Vec<f32> = unsafe { std::slice::from_raw_parts(unc, dims).to_vec() };
    let cogon = Cogon::new(sem_vec, unc_vec);
    to_json_ptr(&cogon)
}

/// BLEND two COGONs. Returns JSON string or NULL on error.
#[no_mangle]
pub extern "C" fn leet_blend(
    c1_json: *const c_char,
    c2_json: *const c_char,
    alpha: f32,
) -> *mut c_char {
    let (c1_str, c2_str) = unsafe {
        match (c_str_to_str(c1_json), c_str_to_str(c2_json)) {
            (Some(a), Some(b)) => (a, b),
            _ => return std::ptr::null_mut(),
        }
    };
    let c1: Cogon = match parse_json(c1_str) {
        Some(c) => c,
        None => return std::ptr::null_mut(),
    };
    let c2: Cogon = match parse_json(c2_str) {
        Some(c) => c,
        None => return std::ptr::null_mut(),
    };
    match operators::blend(&c1, &c2, alpha) {
        Ok(result) => to_json_ptr(&result),
        Err(_) => std::ptr::null_mut(),
    }
}

/// DIST between two COGONs. Returns -1.0 on error.
#[no_mangle]
pub extern "C" fn leet_dist(
    c1_json: *const c_char,
    c2_json: *const c_char,
) -> f32 {
    let (c1_str, c2_str) = unsafe {
        match (c_str_to_str(c1_json), c_str_to_str(c2_json)) {
            (Some(a), Some(b)) => (a, b),
            _ => return -1.0,
        }
    };
    let c1: Cogon = match parse_json(c1_str) {
        Some(c) => c,
        None => return -1.0,
    };
    let c2: Cogon = match parse_json(c2_str) {
        Some(c) => c,
        None => return -1.0,
    };
    operators::dist(&c1, &c2).unwrap_or(-1.0)
}

/// DELTA between two COGONs. Returns JSON array string or NULL on error.
#[no_mangle]
pub extern "C" fn leet_delta(
    prev_json: *const c_char,
    curr_json: *const c_char,
) -> *mut c_char {
    let (prev_str, curr_str) = unsafe {
        match (c_str_to_str(prev_json), c_str_to_str(curr_json)) {
            (Some(a), Some(b)) => (a, b),
            _ => return std::ptr::null_mut(),
        }
    };
    let prev: Cogon = match parse_json(prev_str) {
        Some(c) => c,
        None => return std::ptr::null_mut(),
    };
    let curr: Cogon = match parse_json(curr_str) {
        Some(c) => c,
        None => return std::ptr::null_mut(),
    };
    match operators::delta(&prev, &curr) {
        Ok(result) => to_json_ptr(&result),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Validate a MSG_1337 JSON. Returns NULL on success, error string on failure.
/// Caller must free non-NULL results with leet_free_string.
#[no_mangle]
pub extern "C" fn leet_validate(msg_json: *const c_char) -> *mut c_char {
    let msg_str = match unsafe { c_str_to_str(msg_json) } {
        Some(s) => s,
        None => return error_string("NULL input"),
    };
    let msg: crate::types::Msg1337 = match parse_json(msg_str) {
        Some(m) => m,
        None => return error_string("JSON parse error"),
    };
    match Validator::validate(&msg) {
        Ok(()) => std::ptr::null_mut(),
        Err(e) => error_string(&e.to_string()),
    }
}

/// Re-serialize a MSG_1337 JSON in canonical order. Returns JSON string or NULL.
#[no_mangle]
pub extern "C" fn leet_serialize(msg_json: *const c_char) -> *mut c_char {
    let msg_str = match unsafe { c_str_to_str(msg_json) } {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };
    let msg: crate::types::Msg1337 = match parse_json(msg_str) {
        Some(m) => m,
        None => return std::ptr::null_mut(),
    };
    to_json_ptr(&msg)
}

fn error_string(s: &str) -> *mut c_char {
    CString::new(s).map(|cs| cs.into_raw()).unwrap_or(std::ptr::null_mut())
}
