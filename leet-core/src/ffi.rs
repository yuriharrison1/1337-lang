//! C ABI (`extern "C"`) bindings for `leet-core`, built as a `cdylib`.
//!
//! Every function that returns `*mut c_char` hands ownership of a `CString`
//! to the caller — the caller must pass that pointer to [`leet_free_string`]
//! exactly once to avoid leaking memory. A null pointer is returned on error
//! (e.g. malformed JSON or invalid UTF-8 input) instead of panicking across
//! the FFI boundary.

use std::ffi::{c_char, c_float, CStr, CString};
use std::slice;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::operators::{blend, dist};
use crate::types::Cogon;
use uuid::Uuid;

fn now_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

fn string_to_ptr(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// # Safety
/// `ptr` must be non-null and point to a valid, NUL-terminated C string.
unsafe fn cstr_to_str<'a>(ptr: *const c_char) -> Option<&'a str> {
    if ptr.is_null() {
        return None;
    }
    CStr::from_ptr(ptr).to_str().ok()
}

fn cogon_from_json(s: &str) -> Option<Cogon> {
    serde_json::from_str(s).ok()
}

fn cogon_to_json(c: &Cogon) -> Option<String> {
    serde_json::to_string(c).ok()
}

/// Free a string previously returned by any `leet_*` function in this module.
///
/// # Safety
/// `ptr` must have been returned by one of this module's functions, and must
/// not be freed more than once.
#[no_mangle]
pub unsafe extern "C" fn leet_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        drop(CString::from_raw(ptr));
    }
}

/// Returns the `leet-core` crate version (e.g. `"0.5.1"`).
#[no_mangle]
pub extern "C" fn leet_version() -> *mut c_char {
    string_to_ptr(crate::VERSION.to_string())
}

/// Returns COGON_ZERO as JSON.
#[no_mangle]
pub extern "C" fn leet_cogon_zero() -> *mut c_char {
    match cogon_to_json(&Cogon::zero()) {
        Some(json) => string_to_ptr(json),
        None => std::ptr::null_mut(),
    }
}

/// Builds a new `Cogon` from a 32-element `sem` array and returns it as JSON.
///
/// # Safety
/// `sem` must point to at least `len` valid, initialized `f32` values.
#[no_mangle]
pub unsafe extern "C" fn leet_cogon_new(sem: *const c_float, len: usize) -> *mut c_char {
    if sem.is_null() || len != 32 {
        return std::ptr::null_mut();
    }
    let values = slice::from_raw_parts(sem, len);
    let mut sem_arr = [0.0_f32; 32];
    sem_arr.copy_from_slice(values);

    let cogon = Cogon {
        id: Uuid::new_v4(),
        sem: sem_arr,
        stamp: now_millis(),
        raw: None,
    };
    match cogon_to_json(&cogon) {
        Some(json) => string_to_ptr(json),
        None => std::ptr::null_mut(),
    }
}

/// BLEND(c1, c2, alpha) — see `leet-core::operators::blend`.
///
/// # Safety
/// `c1_json` and `c2_json` must be non-null, valid, NUL-terminated C strings.
#[no_mangle]
pub unsafe extern "C" fn leet_blend(
    c1_json: *const c_char,
    c2_json: *const c_char,
    alpha: c_float,
) -> *mut c_char {
    let (Some(c1_str), Some(c2_str)) = (cstr_to_str(c1_json), cstr_to_str(c2_json)) else {
        return std::ptr::null_mut();
    };
    let (Some(c1), Some(c2)) = (cogon_from_json(c1_str), cogon_from_json(c2_str)) else {
        return std::ptr::null_mut();
    };
    match cogon_to_json(&blend(&c1, &c2, alpha)) {
        Some(json) => string_to_ptr(json),
        None => std::ptr::null_mut(),
    }
}

/// DIST(c1, c2) — see `leet-core::operators::dist`. Returns `-1.0` on error
/// (valid distances are always in `[0, 2]`).
///
/// # Safety
/// `c1_json` and `c2_json` must be non-null, valid, NUL-terminated C strings.
#[no_mangle]
pub unsafe extern "C" fn leet_dist(c1_json: *const c_char, c2_json: *const c_char) -> c_float {
    let (Some(c1_str), Some(c2_str)) = (cstr_to_str(c1_json), cstr_to_str(c2_json)) else {
        return -1.0;
    };
    let (Some(c1), Some(c2)) = (cogon_from_json(c1_str), cogon_from_json(c2_str)) else {
        return -1.0;
    };
    dist(&c1, &c2)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn json_from_ptr(ptr: *mut c_char) -> String {
        assert!(!ptr.is_null());
        let s = unsafe { CStr::from_ptr(ptr) }.to_str().unwrap().to_string();
        unsafe { leet_free_string(ptr) };
        s
    }

    #[test]
    fn version_roundtrip() {
        let ptr = leet_version();
        assert_eq!(json_from_ptr(ptr), crate::VERSION);
    }

    #[test]
    fn cogon_zero_roundtrip() {
        let ptr = leet_cogon_zero();
        let json = json_from_ptr(ptr);
        let c: Cogon = serde_json::from_str(&json).unwrap();
        assert!(c.is_zero());
    }

    #[test]
    fn cogon_new_roundtrip() {
        let sem = [0.5_f32; 32];
        let ptr = unsafe { leet_cogon_new(sem.as_ptr(), 32) };
        let json = json_from_ptr(ptr);
        let c: Cogon = serde_json::from_str(&json).unwrap();
        assert_eq!(c.sem, sem);
    }

    #[test]
    fn cogon_new_rejects_wrong_len() {
        let sem = [0.5_f32; 16];
        let ptr = unsafe { leet_cogon_new(sem.as_ptr(), sem.len()) };
        assert!(ptr.is_null());
    }

    #[test]
    fn blend_and_dist_roundtrip() {
        let zero_ptr = leet_cogon_zero();
        let zero_json = json_from_ptr(zero_ptr);
        let c_zero = CString::new(zero_json.clone()).unwrap();

        let sem = [0.2_f32; 32];
        let new_ptr = unsafe { leet_cogon_new(sem.as_ptr(), 32) };
        let new_json = json_from_ptr(new_ptr);
        let c_new = CString::new(new_json).unwrap();

        let blended_ptr =
            unsafe { leet_blend(c_zero.as_ptr(), c_new.as_ptr(), 0.5) };
        let blended_json = json_from_ptr(blended_ptr);
        let blended: Cogon = serde_json::from_str(&blended_json).unwrap();
        assert!(blended.sem.iter().all(|&v| (0.0..=1.0).contains(&v)));

        let c_zero_again = CString::new(zero_json).unwrap();
        let d = unsafe { leet_dist(c_zero.as_ptr(), c_zero_again.as_ptr()) };
        assert!(d >= 0.0);
    }

    #[test]
    fn dist_null_input_returns_negative_one() {
        let d = unsafe { leet_dist(std::ptr::null(), std::ptr::null()) };
        assert_eq!(d, -1.0);
    }
}
