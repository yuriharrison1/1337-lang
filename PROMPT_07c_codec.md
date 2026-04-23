# PROMPT 07c — CODEC v0.5.1 (unc[32] → reserved[32], manter 96 bytes)

Atualizar o codec binário pra refletir a remoção de `unc` do `Cogon` (feita em 07b). Mantém **exatamente os mesmos 96 bytes de wire format** (header 4 + payload 88 + CRC32 4) trocando o bloco de 32 bytes que era `unc` por `reserved[32]` com zeros.

**PRÉ-REQUISITOS**: 07a + 07b executados. `cargo test --workspace` verde. `Cogon` já não tem mais campo `unc`.

**ESCOPO FORA**: tudo exceto `codec.rs`.

**Taskwarrior**: `+prompt07c`.

---

## POR QUE reserved[32] E NÃO REDUZIR PRA 64 BYTES

Decisão do Yuri ("opção B"):

1. Preserva compatibilidade binária com agentes v0.4 que ainda estão no ar — frames novos passam pelo decoder antigo (ele vê `reserved` como `unc`, recupera `[0]*32` que é incerteza mínima — erra pouco).
2. CRC32 continua funcionando com mesmo tamanho — não precisa coordenar bump de versão.
3. Reserva espaço pra uso futuro (Zona Emergente formalizada, 32 eixos adicionais, telemetria embarcada). Se esse espaço for ativado no futuro, bumpa `VERSION` de `0x02` pra `0x03` e interpreta os bytes.
4. Solução menos agressiva disponível. Upgrade path claro.

Em runtime o `Cogon` já não tem `unc`. No wire, os 32 bytes que antes carregavam `unc` são sempre zero na serialização e ignorados na desserialização.

---

## FILE ÚNICO — `leet-core/src/codec.rs`

### Cabeçalho do arquivo

Atualizar o doc-comment de topo:

```rust
//! Binary codec for 1337 — compact binary encoding with checksum (v0.5.1).
//!
//! Format COGON (96 bytes fixed):
//! ```text
//! [HEADER: 4 bytes][PAYLOAD: 88 bytes][CHECKSUM: 4 bytes]
//!
//! Header:
//!   - magic: 2 bytes (0x1337)
//!   - version_flags: 1 byte   (v0.5.1 keeps VERSION=0x02 for binary compat)
//!   - reserved: 1 byte
//!
//! Payload:
//!   - id: 16 bytes (UUID)                         bytes  0..16
//!   - sem: 32 bytes (32 uint8, quantized)         bytes 16..48
//!   - reserved: 32 bytes (always zero, v0.5.1)    bytes 48..80
//!   - stamp: 8 bytes (u64 nanoseconds)            bytes 80..88
//!
//! Checksum:
//!   - CRC32 of header + payload for integrity verification
//! ```
//!
//! v0.5.1 CHANGE: the 32-byte block that previously held 'unc' is now
//! 'reserved' and written as zeros. Decoders from v0.4 will see zeros
//! instead of uncertainty, which translates to "maximum confidence" in
//! the old semantic — acceptable forward-compatibility.
//!
//! Reserved bytes may be repurposed in the future; doing so requires
//! bumping VERSION to 0x03 so old decoders can reject the frame.
//!
//! Quantization: float [0.0, 1.0] <-> uint8 [0, 255]
//! Compression vs JSON: ~4-5:1
//! Integrity: CRC32 detects data corruption
```

### encode_cogon

```rust
pub fn encode_cogon(cogon: &Cogon) -> Vec<u8> {
    let mut buf = Vec::with_capacity(TOTAL_SIZE);

    // Header
    buf.extend_from_slice(&MAGIC.to_be_bytes());
    buf.push((VERSION << 4) | 0x00); // version + flags
    buf.push(0x00); // reserved (header-level)

    // Payload: UUID (16 bytes)
    buf.extend_from_slice(cogon.id.as_bytes());

    // Payload: sem (32 bytes)
    for &v in &cogon.sem {
        buf.push(float_to_u8(v));
    }

    // Payload: reserved (32 bytes, always zero in v0.5.1)
    // Previously held 'unc' in v0.4; kept for wire compatibility.
    buf.extend_from_slice(&[0u8; 32]);

    // Payload: stamp (8 bytes, big-endian u64)
    buf.extend_from_slice(&cogon.stamp.to_be_bytes());

    // Checksum: CRC32 of header + payload
    let crc = compute_crc32(&buf);
    buf.extend_from_slice(&crc.to_be_bytes());

    debug_assert_eq!(buf.len(), TOTAL_SIZE, "frame must be exactly 96 bytes");
    buf
}
```

### decode_cogon

```rust
pub fn decode_cogon(data: &[u8]) -> Result<Cogon, crate::error::LeetError> {
    if data.len() < TOTAL_SIZE {
        return Err(crate::error::LeetError::SerializationError(format!(
            "Invalid data size: {} bytes, expected {}",
            data.len(),
            TOTAL_SIZE
        )));
    }

    // Split components
    let header_data = &data[..HEADER_SIZE];
    let payload_data = &data[HEADER_SIZE..HEADER_SIZE + PAYLOAD_SIZE];
    let checksum_data = &data[HEADER_SIZE + PAYLOAD_SIZE..HEADER_SIZE + PAYLOAD_SIZE + CHECKSUM_SIZE];

    // Parse header
    let magic = u16::from_be_bytes([header_data[0], header_data[1]]);
    if magic != MAGIC {
        return Err(crate::error::LeetError::SerializationError(format!(
            "Invalid magic: 0x{:04x}, expected 0x{:04x}",
            magic, MAGIC
        )));
    }

    let version = header_data[2] >> 4;
    if version != VERSION {
        return Err(crate::error::LeetError::SerializationError(format!(
            "Unsupported version: {}, expected {}",
            version, VERSION
        )));
    }

    // Verify checksum
    let stored_crc = u32::from_be_bytes([
        checksum_data[0],
        checksum_data[1],
        checksum_data[2],
        checksum_data[3],
    ]);
    let computed_crc = compute_crc32(&data[..HEADER_SIZE + PAYLOAD_SIZE]);

    if stored_crc != computed_crc {
        return Err(crate::error::LeetError::SerializationError(format!(
            "Checksum mismatch: stored=0x{:08x}, computed=0x{:08x}. Data may be corrupted.",
            stored_crc, computed_crc
        )));
    }

    // Parse payload
    let id = Uuid::from_bytes([
        payload_data[0], payload_data[1], payload_data[2], payload_data[3],
        payload_data[4], payload_data[5], payload_data[6], payload_data[7],
        payload_data[8], payload_data[9], payload_data[10], payload_data[11],
        payload_data[12], payload_data[13], payload_data[14], payload_data[15],
    ]);

    // sem (32 bytes, indices 16..48 of payload)
    let mut sem: SemVec = [0.0; 32];
    for i in 0..32 {
        sem[i] = u8_to_float(payload_data[16 + i]);
    }

    // reserved (32 bytes, indices 48..80) — intentionally discarded in v0.5.1.
    // Future versions may interpret this region; current version requires zeros.
    // We do NOT enforce zeros on decode to stay compatible with v0.4 frames
    // carrying real unc data (which we simply drop).

    // stamp (8 bytes, indices 80..88)
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
```

### Ajustar helpers

`estimate_json_size` removar a referência a unc:
```rust
fn estimate_json_size(_cogon: &Cogon) -> usize {
    // Rough estimate: UUID (~36) + sem array (~200) + metadata
    36 + 32 * 6 + 100
}
```

`compare_sizes` continua igual — só o denominador muda (menos bytes em JSON equivalente), mas a ordem de magnitude permanece.

### Testes — reescrita completa do módulo `tests`

```rust
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
    fn test_frame_size_is_96_bytes() {
        let c = make_cogon(0.5);
        let encoded = encode_cogon(&c);
        assert_eq!(encoded.len(), TOTAL_SIZE);
        assert_eq!(encoded.len(), 96);
    }

    #[test]
    fn test_reserved_bytes_are_zero() {
        let c = make_cogon(0.9);
        let encoded = encode_cogon(&c);
        // Payload starts at byte 4 (after header). Reserved region is payload[48..80].
        let reserved = &encoded[HEADER_SIZE + 48..HEADER_SIZE + 80];
        assert_eq!(reserved, &[0u8; 32], "reserved bytes must all be zero");
    }

    #[test]
    fn test_quantization_roundtrip() {
        let original = 0.734;
        let quantized = float_to_u8(original);
        let recovered = u8_to_float(quantized);
        assert!((original - recovered).abs() < 0.004); // 1/255 tolerance
    }

    #[test]
    fn test_encode_decode_roundtrip() {
        let original = make_cogon(0.5);
        let encoded = encode_cogon(&original);
        let decoded = decode_cogon(&encoded).unwrap();

        assert_eq!(original.id, decoded.id);
        for i in 0..32 {
            assert!((original.sem[i] - decoded.sem[i]).abs() < 0.004, "dim {i}");
        }
        assert_eq!(original.stamp, decoded.stamp);
    }

    #[test]
    fn test_cogon_zero_roundtrip() {
        let zero = Cogon::zero();
        let encoded = encode_cogon(&zero);
        let decoded = decode_cogon(&encoded).unwrap();
        assert!(decoded.is_zero());
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
        let data = vec![0x13, 0x37, 0x20, 0x00];
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
    fn test_v04_frame_with_unc_still_decodes() {
        // Forward-compat: a v0.4-style frame where bytes 48..80 contain
        // non-zero unc data still decodes correctly (reserved bytes discarded).
        let c = make_cogon(0.5);
        let mut encoded = encode_cogon(&c);

        // Simulate v0.4 encoder: fill reserved region with some unc values.
        for i in 0..32 {
            encoded[HEADER_SIZE + 48 + i] = 128; // simulated unc=0.5
        }
        // Recompute checksum so the frame is still "valid" under v0.4 producer.
        let new_crc = compute_crc32(&encoded[..HEADER_SIZE + PAYLOAD_SIZE]);
        encoded[HEADER_SIZE + PAYLOAD_SIZE..HEADER_SIZE + PAYLOAD_SIZE + CHECKSUM_SIZE]
            .copy_from_slice(&new_crc.to_be_bytes());

        let decoded = decode_cogon(&encoded).expect("v0.4-style frame must decode");
        assert_eq!(decoded.id, c.id);
        for i in 0..32 {
            assert!((decoded.sem[i] - 0.5).abs() < 0.004);
        }
        // The unc data from the v0.4 frame is silently discarded — that's the contract.
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
```

Mudanças-chave no módulo `tests`:
- `make_cogon` toma só `sem_val` (não mais `unc_val`).
- Teste novo `test_reserved_bytes_are_zero` garante a invariante em encode.
- Teste novo `test_v04_frame_with_unc_still_decodes` valida forward-compat.
- Removido qualquer assert sobre `decoded.unc[i]`.

---

## VERIFICATION

```bash
cargo test -p leet-core --lib codec
cargo test -p leet-core
cargo test --workspace

# Verificar tamanho do frame via CLI (se existir subcomando):
cargo run -p leet-cli --bin leet -- encode --inspect
# ou via loopback: encode → decode → diff byte a byte deve ser zero nos reserved.
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt07c "Codec v0.5.1: unc[32] slot becomes reserved[32] zeros, 96-byte wire preserved"
# work
task project:1337 +prompt07c done

git add leet-core/src/codec.rs
git commit -m "refactor(codec): replace unc[32] with reserved[32] zeros (v0.5.1)

Wire format preserves the exact 96-byte frame to maintain forward/backward
compatibility with v0.4 agents still in the field. The 32-byte region at
payload offset 48..80 (formerly 'unc', one u8-quantized value per dim)
is now 'reserved' — always written as zeros on encode, silently discarded
on decode.

- VERSION stays at 0x02 (compat with v0.4 decoders).
- A future bump to 0x03 would signal that the reserved region carries
  new semantics (e.g., emergent zone telemetry).
- encode_cogon: writes 32 zero bytes where unc bytes used to go.
- decode_cogon: skips the 32 bytes after sem[] and before stamp.
- Added test_reserved_bytes_are_zero and test_v04_frame_with_unc_still_decodes.

Part of Fase A, sub-prompt 07c."
git push origin main
```

---

**END OF PROMPT_07c**
