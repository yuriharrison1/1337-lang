//! Binary codec for 1337 — compact binary encoding with checksum.
//!
//! Format COGON (96 bytes fixed):
//! ```text
//! [HEADER: 4 bytes][PAYLOAD: 88 bytes][CHECKSUM: 4 bytes]
//!
//! Header:
//!   - magic: 2 bytes (0x1337)
//!   - version_flags: 1 byte
//!   - reserved: 1 byte
//!
//! Payload:
//!   - id: 16 bytes (UUID)
//!   - sem: 32 bytes (32 uint8, quantized)
//!   - reserved: 32 bytes (zeros; was unc in v0.4)  // TODO(07c): rename to reserved
//!   - stamp: 8 bytes (u64 nanoseconds)
//!
//! Checksum:
//!   - CRC32 of header + payload for integrity verification
//! ```
//!
//! Quantization: float [0.0, 1.0] <-> uint8 [0, 255]
//! Compression vs JSON: ~4-5:1
//! Integrity: CRC32 detects data corruption

use crate::types::{Cogon, SemVec};
use uuid::Uuid;

/// Magic number for binary format
pub const MAGIC: u16 = 0x1337;
/// Version 2 (with checksum)
pub const VERSION: u8 = 0x02;
/// Header size in bytes
pub const HEADER_SIZE: usize = 4;
/// Payload size in bytes
pub const PAYLOAD_SIZE: usize = 88;
/// Checksum size in bytes
pub const CHECKSUM_SIZE: usize = 4;
/// Total binary size
pub const TOTAL_SIZE: usize = HEADER_SIZE + PAYLOAD_SIZE + CHECKSUM_SIZE; // 96 bytes

/// Compute CRC32 of data
#[inline]
pub fn compute_crc32(data: &[u8]) -> u32 {
    crc32fast::hash(data)
}

/// Quantize float [0.0, 1.0] to uint8 [0, 255]
#[inline]
pub fn float_to_u8(v: f32) -> u8 {
    (v.clamp(0.0, 1.0) * 255.0).round() as u8
}

/// De-quantize uint8 [0, 255] to float [0.0, 1.0]
#[inline]
pub fn u8_to_float(v: u8) -> f32 {
    v as f32 / 255.0
}

/// Encode a Cogon to binary format (96 bytes with checksum)
pub fn encode_cogon(cogon: &Cogon) -> Vec<u8> {
    let mut buf = Vec::with_capacity(TOTAL_SIZE);

    // Header
    buf.extend_from_slice(&MAGIC.to_be_bytes());
    buf.push((VERSION << 4) | 0x00); // version + flags
    buf.push(0x00); // reserved

    // Payload: UUID (16 bytes)
    buf.extend_from_slice(cogon.id.as_bytes());

    // Payload: sem (32 bytes)
    for &v in &cogon.sem {
        buf.push(float_to_u8(v));
    }

    // Payload: reserved 32 bytes (zeros; was unc in v0.4 — kept for wire compat)
    buf.extend_from_slice(&[0u8; 32]);

    // Payload: stamp (8 bytes, big-endian u64)
    buf.extend_from_slice(&cogon.stamp.to_be_bytes());

    // Checksum: CRC32 of header + payload
    let crc = compute_crc32(&buf);
    buf.extend_from_slice(&crc.to_be_bytes());

    buf
}

/// Decode a Cogon from binary format with checksum verification
pub fn decode_cogon(data: &[u8]) -> Result<Cogon, crate::error::LeetError> {
    if data.len() < TOTAL_SIZE {
        return Err(crate::error::LeetError::SerializationError(
            format!("Invalid data size: {} bytes, expected {}", data.len(), TOTAL_SIZE)
        ));
    }

    // Split components
    let header_data = &data[..HEADER_SIZE];
    let payload_data = &data[HEADER_SIZE..HEADER_SIZE + PAYLOAD_SIZE];
    let checksum_data = &data[HEADER_SIZE + PAYLOAD_SIZE..HEADER_SIZE + PAYLOAD_SIZE + CHECKSUM_SIZE];

    // Parse header
    let magic = u16::from_be_bytes([header_data[0], header_data[1]]);
    if magic != MAGIC {
        return Err(crate::error::LeetError::SerializationError(
            format!("Invalid magic: 0x{:04x}, expected 0x{:04x}", magic, MAGIC)
        ));
    }

    let version = header_data[2] >> 4;
    if version != VERSION {
        return Err(crate::error::LeetError::SerializationError(
            format!("Unsupported version: {}, expected {}", version, VERSION)
        ));
    }

    // Verify checksum
    let stored_crc = u32::from_be_bytes([
        checksum_data[0], checksum_data[1],
        checksum_data[2], checksum_data[3]
    ]);
    let computed_crc = compute_crc32(&data[..HEADER_SIZE + PAYLOAD_SIZE]);

    if stored_crc != computed_crc {
        return Err(crate::error::LeetError::SerializationError(
            format!(
                "Checksum mismatch: stored=0x{:08x}, computed=0x{:08x}. Data may be corrupted.",
                stored_crc, computed_crc
            )
        ));
    }

    // Parse payload
    let id = Uuid::from_bytes([
        payload_data[0], payload_data[1], payload_data[2], payload_data[3],
        payload_data[4], payload_data[5], payload_data[6], payload_data[7],
        payload_data[8], payload_data[9], payload_data[10], payload_data[11],
        payload_data[12], payload_data[13], payload_data[14], payload_data[15],
    ]);

    // sem (32 bytes at offset 16)
    let mut sem: SemVec = [0.0; 32];
    for i in 0..32 {
        sem[i] = u8_to_float(payload_data[16 + i]);
    }

    // reserved 32 bytes (offset 48–79) — ignored

    // stamp (8 bytes at offset 80)
    let stamp = i64::from_be_bytes([
        payload_data[80], payload_data[81], payload_data[82], payload_data[83],
        payload_data[84], payload_data[85], payload_data[86], payload_data[87],
    ]);

    Ok(Cogon {
        id,
        sem,
        stamp,
        raw: None,
    })
}

/// Get the size of binary encoding for a Cogon
pub fn binary_size(_cogon: &Cogon) -> usize {
    TOTAL_SIZE
}

/// Compare sizes between JSON (approximate) and binary
pub fn compare_sizes(cogon: &Cogon) -> SizeComparison {
    let binary_bytes = binary_size(cogon);
    let json_bytes = estimate_json_size(cogon);

    SizeComparison {
        json_bytes,
        binary_bytes,
        compression_ratio: json_bytes as f32 / binary_bytes as f32,
        space_saved_percent: (1.0 - binary_bytes as f32 / json_bytes as f32) * 100.0,
    }
}

/// Estimate JSON serialization size
fn estimate_json_size(_cogon: &Cogon) -> usize {
    // Rough estimate: UUID (~36) + sem array (~200) + metadata
    36 + 32 * 6 + 100
}

/// Size comparison result
#[derive(Debug, Clone, Copy)]
pub struct SizeComparison {
    pub json_bytes: usize,
    pub binary_bytes: usize,
    pub compression_ratio: f32,
    pub space_saved_percent: f32,
}

impl Cogon {
    /// Export COGON to binary format
    pub fn to_bytes(&self) -> Vec<u8> {
        encode_cogon(self)
    }

    /// Import COGON from binary format
    pub fn from_bytes(data: &[u8]) -> Result<Self, crate::error::LeetError> {
        decode_cogon(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_cogon(sem_val: f32) -> Cogon {
        Cogon {
            id: Uuid::new_v4(),
            sem: [sem_val; 32],
            stamp: 0,
            raw: None,
        }
    }

    #[test]
    fn test_quantization_roundtrip() {
        let original = 0.734;
        let quantized = float_to_u8(original);
        let recovered = u8_to_float(quantized);
        assert!((original - recovered).abs() < 0.004);
    }

    #[test]
    fn test_encode_decode_roundtrip() {
        let original = make_cogon(0.5);
        let encoded = encode_cogon(&original);
        let decoded = decode_cogon(&encoded).unwrap();

        assert_eq!(original.id, decoded.id);
        for i in 0..32 {
            assert!((original.sem[i] - decoded.sem[i]).abs() < 0.004);
        }
    }

    #[test]
    fn test_cogon_zero_roundtrip() {
        let zero = Cogon::zero();
        let encoded = encode_cogon(&zero);
        let decoded = decode_cogon(&encoded).unwrap();
        assert_eq!(zero.id, decoded.id);
        // Quantization tolerance: 1/255 ≈ 0.004
        for i in 0..32 {
            assert!((zero.sem[i] - decoded.sem[i]).abs() < 0.004,
                "sem[{}]: {} vs {}", i, zero.sem[i], decoded.sem[i]);
        }
    }

    #[test]
    fn test_binary_size_constant() {
        let c1 = make_cogon(0.1);
        let c2 = make_cogon(0.9);
        assert_eq!(binary_size(&c1), TOTAL_SIZE);
        assert_eq!(binary_size(&c2), TOTAL_SIZE);
    }

    #[test]
    fn test_invalid_magic() {
        let mut data = encode_cogon(&make_cogon(0.5));
        data[0] = 0x00;
        data[1] = 0x00;
        assert!(decode_cogon(&data).is_err());
    }

    #[test]
    fn test_invalid_size() {
        let data = vec![0x13, 0x37, 0x20, 0x00]; // Too small
        assert!(decode_cogon(&data).is_err());
    }

    #[test]
    fn test_checksum_mismatch() {
        let mut data = encode_cogon(&make_cogon(0.5));
        data[10] ^= 0xFF;
        let result = decode_cogon(&data);
        assert!(result.is_err());
        let err_msg = format!("{}", result.unwrap_err());
        assert!(err_msg.contains("Checksum mismatch"));
    }

    #[test]
    fn test_compression_ratio() {
        let cogon = make_cogon(0.5);
        let comparison = compare_sizes(&cogon);
        assert!(comparison.compression_ratio > 3.0);
        assert!(comparison.space_saved_percent > 60.0);
    }

    #[test]
    fn test_cogon_to_bytes_method() {
        let cogon = make_cogon(0.5);
        let data = cogon.to_bytes();
        assert_eq!(data.len(), TOTAL_SIZE);
    }

    #[test]
    fn test_cogon_from_bytes_method() {
        let original = make_cogon(0.5);
        let data = original.to_bytes();
        let recovered = Cogon::from_bytes(&data).unwrap();
        assert_eq!(original.id, recovered.id);
    }
}
