//! Wire format for compact inter-agent transport.
//!
//! Design decisions vs full MSG_1337:
//! - `unc` is dropped: receiver recomputes via `WireCogon::recompute_unc()`
//! - Session IDs: 4 bytes (prefix of session UUID) + u32 seq — saves 28 bytes vs two UUIDs
//! - `align_hash`: only 4 bytes (first 4 of C5 SHA-256) — saves ~150 bytes vs full CanonicalSpace
//! - Serialization: MessagePack (binary) instead of JSON
//! - SparseDelta: only transmits axes that changed beyond threshold

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::types::{Cogon, Intent};
use crate::FIXED_DIMS;

// ─── Wire COGON ──────────────────────────────────────────────────────────────

/// Compact COGON for wire transmission.
/// `unc` is omitted — receiver calls `recompute_unc()` deterministically.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WireCogon {
    pub id: [u8; 16],
    pub sem: [f32; 32],
    pub stamp: i64,
}

impl WireCogon {
    pub fn from_cogon(c: &Cogon) -> Self {
        let mut id = [0u8; 16];
        id.copy_from_slice(c.id.as_bytes());
        let mut sem = [0f32; 32];
        for (i, &v) in c.sem.iter().enumerate().take(FIXED_DIMS) {
            sem[i] = v;
        }
        Self { id, sem, stamp: c.stamp }
    }

    /// Recompute unc from sem — same formula as the projection engine.
    /// `unc[i] = (1 - |sem[i] - 0.5| * 2).clamp(0, 1)`
    pub fn recompute_unc(&self) -> [f32; 32] {
        let mut unc = [0f32; 32];
        for i in 0..32 {
            let d = (self.sem[i] - 0.5).abs() * 2.0;
            unc[i] = (1.0 - d).clamp(0.0, 1.0);
        }
        unc
    }

    /// Reconstruct a full Cogon with recomputed unc.
    pub fn to_cogon(&self) -> Cogon {
        let unc = self.recompute_unc();
        let mut c = Cogon::new(self.sem.to_vec(), unc.to_vec());
        c.id = Uuid::from_bytes(self.id);
        c.stamp = self.stamp;
        c
    }
}

// ─── Sparse Delta ─────────────────────────────────────────────────────────────

/// Sparse representation of a semantic delta.
/// Only axes that changed beyond the encoding threshold are included.
/// Each entry: (axis_index: u8, new_value: f32).
/// Worst case: 32 × 5 = 160 bytes. Typical: 3–8 axes = 15–40 bytes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SparseDelta {
    /// UUID bytes of the base COGON being patched.
    pub ref_id: [u8; 16],
    /// Changed axes: (index, new absolute value after patch).
    pub changes: Vec<(u8, f32)>,
}

// ─── Session ID ───────────────────────────────────────────────────────────────

/// Compact session-scoped message identifier.
/// Replaces two full UUIDs (32 bytes) with 8 bytes total.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionId {
    /// First 4 bytes of the session UUID — unique within a network partition.
    pub prefix: [u8; 4],
    /// Monotonically increasing message sequence number within the session.
    pub seq: u32,
}

impl SessionId {
    pub fn new(session_uuid: &Uuid, seq: u32) -> Self {
        let mut prefix = [0u8; 4];
        prefix.copy_from_slice(&session_uuid.as_bytes()[..4]);
        Self { prefix, seq }
    }
}

// ─── Wire Intent ─────────────────────────────────────────────────────────────

/// Intent encoded as a single byte.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[repr(u8)]
pub enum WireIntent {
    Assert  = 0,
    Query   = 1,
    Delta   = 2,
    Sync    = 3,
    Anomaly = 4,
    Ack     = 5,
}

impl From<&Intent> for WireIntent {
    fn from(i: &Intent) -> Self {
        match i {
            Intent::Assert  => WireIntent::Assert,
            Intent::Query   => WireIntent::Query,
            Intent::Delta   => WireIntent::Delta,
            Intent::Sync    => WireIntent::Sync,
            Intent::Anomaly => WireIntent::Anomaly,
            Intent::Ack     => WireIntent::Ack,
        }
    }
}

impl From<WireIntent> for Intent {
    fn from(w: WireIntent) -> Self {
        match w {
            WireIntent::Assert  => Intent::Assert,
            WireIntent::Query   => Intent::Query,
            WireIntent::Delta   => Intent::Delta,
            WireIntent::Sync    => Intent::Sync,
            WireIntent::Anomaly => Intent::Anomaly,
            WireIntent::Ack     => Intent::Ack,
        }
    }
}

// ─── Wire Payload ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WirePayload {
    /// Single atomic COGON.
    Cogon(WireCogon),
    /// DAG as flat list of nodes (edges encoded separately if needed).
    Dag(Vec<WireCogon>),
    /// Sparse delta patch against a known base COGON.
    Delta(SparseDelta),
}

// ─── Wire Message ─────────────────────────────────────────────────────────────

/// Compact wire envelope — replaces full MSG_1337 for inter-agent transport.
///
/// Size comparison vs full MSG_1337 (JSON):
/// - MSG_1337 JSON:   ~700-900 bytes
/// - WireMsg MsgPack: ~70-120 bytes (single COGON, no delta)
/// - WireMsg MsgPack: ~15-40  bytes (sparse DELTA intent)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WireMsg {
    /// Compact session-scoped ID (8 bytes vs 32 bytes for two UUIDs).
    pub sid: SessionId,
    /// Intent as single byte.
    pub intent: WireIntent,
    /// First 4 bytes of C5 align_hash for session integrity check.
    /// Full CanonicalSpace is negotiated once during C5 handshake, not repeated.
    pub align_hash: [u8; 4],
    /// Semantic payload.
    pub payload: WirePayload,
}

// ─── Codec ────────────────────────────────────────────────────────────────────

/// Encode a WireMsg to MessagePack bytes (positional — no field names on wire).
pub fn encode(msg: &WireMsg) -> Result<Vec<u8>, rmp_serde::encode::Error> {
    rmp_serde::to_vec(msg)
}

/// Decode a WireMsg from MessagePack bytes.
pub fn decode(bytes: &[u8]) -> Result<WireMsg, rmp_serde::decode::Error> {
    rmp_serde::from_slice(bytes)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::Cogon;

    fn make_cogon(val: f32) -> Cogon {
        Cogon::new(vec![val; FIXED_DIMS], vec![0.1f32; FIXED_DIMS])
    }

    #[test]
    fn test_wire_cogon_roundtrip() {
        let c = make_cogon(0.7);
        let wc = WireCogon::from_cogon(&c);
        let back = wc.to_cogon();
        for i in 0..FIXED_DIMS {
            assert!((c.sem[i] - back.sem[i]).abs() < 1e-6);
        }
    }

    #[test]
    fn test_recompute_unc_no_unc_transmitted() {
        let c = make_cogon(0.8);
        let wc = WireCogon::from_cogon(&c);
        let unc = wc.recompute_unc();
        // sem=0.8 → distance_from_center = |0.8-0.5|*2 = 0.6 → unc = 1-0.6 = 0.4
        for u in &unc {
            assert!((*u - 0.4).abs() < 1e-5, "expected unc≈0.4, got {}", u);
        }
    }

    #[test]
    fn test_msgpack_smaller_than_json() {
        let session = Uuid::new_v4();
        let c = make_cogon(0.6);
        let wc = WireCogon::from_cogon(&c);
        let msg = WireMsg {
            sid: SessionId::new(&session, 1),
            intent: WireIntent::Assert,
            align_hash: [0xde, 0xad, 0xbe, 0xef],
            payload: WirePayload::Cogon(wc),
        };

        let mp_bytes = encode(&msg).unwrap();
        let json_bytes = serde_json::to_vec(&msg).unwrap();

        assert!(
            mp_bytes.len() < json_bytes.len(),
            "MessagePack ({} bytes) should be smaller than JSON ({} bytes)",
            mp_bytes.len(), json_bytes.len()
        );
    }

    #[test]
    fn test_wire_msg_roundtrip() {
        let session = Uuid::new_v4();
        let c = make_cogon(0.3);
        let wc = WireCogon::from_cogon(&c);
        let msg = WireMsg {
            sid: SessionId::new(&session, 42),
            intent: WireIntent::Delta,
            align_hash: [1, 2, 3, 4],
            payload: WirePayload::Cogon(wc),
        };

        let bytes = encode(&msg).unwrap();
        let decoded = decode(&bytes).unwrap();
        assert_eq!(decoded.sid.seq, 42);
        assert_eq!(decoded.intent, WireIntent::Delta);
        assert_eq!(decoded.align_hash, [1, 2, 3, 4]);
    }

    #[test]
    fn test_sparse_delta_encoding() {
        let changes: Vec<(u8, f32)> = vec![(22u8, 0.95f32), (5u8, 0.1f32)];
        let ref_id = [0u8; 16];
        let delta = SparseDelta { ref_id, changes };
        let payload = WirePayload::Delta(delta);
        let msg = WireMsg {
            sid: SessionId::new(&Uuid::nil(), 1),
            intent: WireIntent::Delta,
            align_hash: [0; 4],
            payload,
        };
        let bytes = encode(&msg).unwrap();
        // 2 changed axes × 5 bytes each + envelope overhead (positional MsgPack)
        assert!(bytes.len() < 90, "sparse delta should be small, got {} bytes", bytes.len());
    }
}
