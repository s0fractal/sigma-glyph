//! WASM surface of the sigma-resume engine. `engine` IS impl-rs/src/main.rs: one
//! transition, one codec, delivered to JS without a second implementation.
//! ABI: the host writes a JSON request into memory from `alloc(len)`, calls
//! `resume(ptr, len)`, and reads the JSON response at `out_ptr()` / `out_len()`.
#![allow(dead_code)]

#[path = "../../src/main.rs"]
mod engine;

static mut OUT: Vec<u8> = Vec::new();

#[no_mangle]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut buf = Vec::<u8>::with_capacity(len);
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

/// # Safety
/// `ptr` must come from `alloc(len)` and hold `len` initialized bytes.
#[no_mangle]
pub unsafe extern "C" fn resume(ptr: *mut u8, len: usize) {
    let request = Vec::from_raw_parts(ptr, len, len);
    let text = match engine::resume_response(&request) {
        Ok(text) => text,
        Err(error) => format!("{{\"outcome\":\"INVALID_REQUEST\",\"detail\":{error:?}}}"),
    };
    OUT = text.into_bytes();
}

#[no_mangle]
pub extern "C" fn out_ptr() -> *const u8 {
    unsafe { (*std::ptr::addr_of!(OUT)).as_ptr() }
}

#[no_mangle]
pub extern "C" fn out_len() -> usize {
    unsafe { (*std::ptr::addr_of!(OUT)).len() }
}
