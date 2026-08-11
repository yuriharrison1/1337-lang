"""
Compact binary encoding for 1337.

Ultra-compact binary format with no repeated metadata.
Axes are identified by implicit order (0-31).

COGON format (96 fixed bytes):
    [HEADER][PAYLOAD][CHECKSUM]

    HEADER (4 bytes):
        - magic: 2 bytes (0x1337)
        - version_flags: 1 byte (version 4 bits + flags 4 bits)
        - reserved: 1 byte

    PAYLOAD (88 bytes):
        - id: 16 bytes (UUID)
        - sem: 32 bytes (32 uint8 values, fixed order A0-C10)
        - unc: 32 bytes (32 uint8 values, fixed order A0-C10)
        - stamp: 8 bytes (uint64, nanoseconds)

    CHECKSUM (4 bytes):
        - CRC32 of header + payload for integrity

Quantization:
    - Float [0.0, 1.0] → uint8: int(value * 255)
    - uint8 → Float: value / 255.0
    - Precision: ~0.4%

Compression vs JSON: ~5:1
Integrity: CRC32 verifies data corruption
"""

from __future__ import annotations

import struct
import zlib
from typing import Optional
from uuid import UUID

from leet.types import Cogon, Dag, Msg1337, Intent, Receiver, Surface, CanonicalSpace, Edge

# Constants
MAGIC = 0x1337
VERSION = 0x02  # Version 2 (with checksum)

# Header format: magic (2) + version_flags (1) + reserved (1)
HEADER_FORMAT = "!HBB"
HEADER_SIZE = 4

# Cogon format: id (16) + sem (32) + unc (32) + stamp (8)
COGON_FORMAT = "!16s32B32BQ"
COGON_SIZE = 88  # 16 + 32 + 32 + 8

# Checksum size
CHECKSUM_SIZE = 4

# Total binary size
TOTAL_BINARY_SIZE = HEADER_SIZE + COGON_SIZE + CHECKSUM_SIZE  # 96 bytes


def _compute_crc32(data: bytes) -> int:
    """Computes the CRC32 of the payload (unsigned)."""
    return zlib.crc32(data) & 0xFFFFFFFF


def _float_to_uint8(value: float) -> int:
    """Quantizes a float [0,1] to uint8 [0,255]."""
    return max(0, min(255, int(value * 255)))


def _uint8_to_float(value: int) -> float:
    """De-quantizes a uint8 [0,255] to float [0,1]."""
    return value / 255.0


def encode_cogon(cogon: Cogon) -> bytes:
    """
    Encodes a COGON to bytes (compact binary format with checksum).

    Returns:
        96 bytes (4 header + 88 payload + 4 checksum)
    """
    # Header
    version_flags = (VERSION << 4) | 0x00  # version 2, flags 0
    header = struct.pack(HEADER_FORMAT, MAGIC, version_flags, 0)

    # Payload
    uuid_bytes = UUID(cogon.id).bytes
    sem_bytes = [_float_to_uint8(v) for v in cogon.sem]
    unc_bytes = [_float_to_uint8(v) for v in cogon.unc]

    payload = struct.pack(COGON_FORMAT, uuid_bytes, *sem_bytes, *unc_bytes, cogon.stamp)

    # Compute CRC32 of header + payload
    crc = _compute_crc32(header + payload)
    checksum = struct.pack("!I", crc)

    return header + payload + checksum


def decode_cogon(data: bytes) -> Cogon:
    """
    Decodes bytes to a COGON with checksum validation.

    Args:
        data: 96 bytes in the binary format

    Raises:
        ValueError: If the format is invalid or the checksum fails
    """
    if len(data) < TOTAL_BINARY_SIZE:
        raise ValueError(
            f"Invalid data size: {len(data)} bytes, expected {TOTAL_BINARY_SIZE}"
        )

    # Split components
    header_data = data[:HEADER_SIZE]
    payload_data = data[HEADER_SIZE:HEADER_SIZE + COGON_SIZE]
    checksum_data = data[HEADER_SIZE + COGON_SIZE:HEADER_SIZE + COGON_SIZE + CHECKSUM_SIZE]

    # Parse header
    magic, version_flags, _ = struct.unpack(HEADER_FORMAT, header_data)

    if magic != MAGIC:
        raise ValueError(f"Invalid magic: 0x{magic:04x}, expected 0x{MAGIC:04x}")

    version = version_flags >> 4
    if version != VERSION:
        raise ValueError(f"Unsupported version: {version}, expected {VERSION}")

    # Verify checksum
    stored_crc = struct.unpack("!I", checksum_data)[0]
    computed_crc = _compute_crc32(header_data + payload_data)

    if stored_crc != computed_crc:
        raise ValueError(
            f"Checksum mismatch: stored=0x{stored_crc:08x}, computed=0x{computed_crc:08x}. "
            "Data may be corrupted."
        )

    # Parse payload
    unpacked = struct.unpack(COGON_FORMAT, payload_data)

    uuid_bytes = unpacked[0]
    sem_bytes = unpacked[1:33]  # 32 bytes
    unc_bytes = unpacked[33:65]  # 32 bytes
    stamp = unpacked[65]

    # Convert back
    cogon_id = str(UUID(bytes=uuid_bytes))
    sem = [_uint8_to_float(v) for v in sem_bytes]
    unc = [_uint8_to_float(v) for v in unc_bytes]

    return Cogon(
        id=cogon_id,
        sem=sem,
        unc=unc,
        stamp=stamp,
        raw=None  # RAW is not supported in the compact binary format
    )


def encode_msg(msg: Msg1337) -> bytes:
    """
    Encodes a MSG_1337 to bytes.

    Format:
        [HEADER][COGON PAYLOAD][MSG EXTENSION]

    MSG EXTENSION:
        - sender_len: 1 byte
        - sender: N bytes
        - receiver_len: 1 byte (0 = broadcast)
        - receiver: N bytes (omitted if broadcast)
        - intent: 1 byte
        - has_patch: 1 byte (0 or 1)
        - patch: 32 bytes * 4 (if has_patch=1, 32 floats)
    """
    # Encode base Cogon payload
    base = encode_cogon(msg.payload if hasattr(msg.payload, 'sem') else msg.payload.nodes[0])

    # MSG extension
    sender_bytes = msg.sender.encode('utf-8')
    sender_len = len(sender_bytes)

    receiver_id = msg.receiver.agent_id if msg.receiver.agent_id else ""
    receiver_bytes = receiver_id.encode('utf-8')
    receiver_len = len(receiver_bytes)

    intent_value = Intent(msg.intent).value if isinstance(msg.intent, str) else msg.intent.value
    intent_code = {
        "ASSERT": 0, "QUERY": 1, "DELTA": 2, "SYNC": 3, "ANOMALY": 4, "ACK": 5
    }.get(intent_value, 0)

    has_patch = 1 if msg.patch else 0

    # Build extension
    ext = struct.pack("!B", sender_len)
    ext += sender_bytes
    ext += struct.pack("!B", receiver_len)
    ext += receiver_bytes
    ext += struct.pack("!BB", intent_code, has_patch)

    if msg.patch:
        # Pack 32 floats as 32 uint8 (quantized)
        patch_bytes = [_float_to_uint8(v) for v in msg.patch]
        ext += struct.pack("!32B", *patch_bytes)

    return base + ext


def decode_msg(data: bytes) -> Msg1337:
    """Decodes bytes to a MSG_1337."""
    # First decode the Cogon part
    cogon = decode_cogon(data)

    # Parse extension
    offset = HEADER_SIZE + COGON_SIZE

    sender_len = data[offset]
    offset += 1
    sender = data[offset:offset + sender_len].decode('utf-8')
    offset += sender_len

    receiver_len = data[offset]
    offset += 1
    receiver_id = data[offset:offset + receiver_len].decode('utf-8') if receiver_len > 0 else None
    offset += receiver_len

    intent_code, has_patch = struct.unpack("!BB", data[offset:offset + 2])
    offset += 2

    intent_map = {0: "ASSERT", 1: "QUERY", 2: "DELTA", 3: "SYNC", 4: "ANOMALY", 5: "ACK"}
    intent = intent_map.get(intent_code, "ASSERT")

    patch = None
    if has_patch:
        patch_bytes = struct.unpack("!32B", data[offset:offset + 32])
        patch = [_uint8_to_float(v) for v in patch_bytes]

    return Msg1337(
        id=cogon.id,  # Reuse cogon ID for message
        sender=sender,
        receiver=Receiver(agent_id=receiver_id),
        intent=intent,
        payload=cogon,
        c5=CanonicalSpace(
            zone_fixed=[0.5] * 32,
            zone_emergent={},
            schema_ver="0.4",
            align_hash=""
        ),
        surface=Surface(
            human_required=False,
            urgency=None,
            reconstruct_depth=0,
            lang="pt"
        ),
        patch=patch
    )


def get_binary_size(cogon: Cogon) -> int:
    """Returns the size in bytes of the binary encoding."""
    return TOTAL_BINARY_SIZE


def compare_sizes(cogon: Cogon) -> dict:
    """Compares sizes between JSON and binary."""
    json_size = len(cogon.to_json().encode('utf-8'))
    binary_size = get_binary_size(cogon)

    return {
        "json_bytes": json_size,
        "binary_bytes": binary_size,
        "compression_ratio": json_size / binary_size,
        "space_saved_percent": (1 - binary_size / json_size) * 100
    }


# Add methods to Cogon for convenience
def _cogon_to_bytes(self) -> bytes:
    """Export COGON to binary format."""
    return encode_cogon(self)


def _cogon_from_bytes(cls, data: bytes) -> Cogon:
    """Import COGON from binary format."""
    return decode_cogon(data)


# Monkey-patch Cogon
Cogon.to_bytes = _cogon_to_bytes
Cogon.from_bytes = classmethod(_cogon_from_bytes)


__all__ = [
    'encode_cogon',
    'decode_cogon',
    'encode_msg',
    'decode_msg',
    'get_binary_size',
    'compare_sizes',
]
