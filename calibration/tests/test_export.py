"""Tests for export_w.py — binary format and verify round-trip."""
import sys
import os
import struct
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Helpers matching train_w.py's export format ─────────────────────────────

def _write_w_bin(W: np.ndarray, path: str) -> None:
    """Write W as flat float32 LE (format used by train_w.py: rows*cols*4 bytes)."""
    w_f32 = W.astype(np.float32)
    w_f32.tofile(path)


def _read_w_bin(path: str, rows: int = 128, cols: int = 32) -> np.ndarray:
    """Read W from flat float32 binary."""
    data = np.fromfile(path, dtype=np.float32)
    assert len(data) == rows * cols, f"Expected {rows*cols} floats, got {len(data)}"
    return data.reshape(rows, cols)


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_export_file_created():
    W = np.random.rand(128, 32).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        assert os.path.exists(path)
    finally:
        os.unlink(path)


def test_export_file_size():
    W = np.ones((128, 32), dtype=np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        expected_bytes = 128 * 32 * 4  # 16384
        assert os.path.getsize(path) == expected_bytes, (
            f"Expected {expected_bytes} bytes, got {os.path.getsize(path)}"
        )
    finally:
        os.unlink(path)


def test_export_round_trip_shape():
    W = np.random.rand(128, 32).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        W2 = _read_w_bin(path)
        assert W2.shape == (128, 32)
    finally:
        os.unlink(path)


def test_export_round_trip_values():
    W = np.random.rand(128, 32).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        W2 = _read_w_bin(path)
        np.testing.assert_array_almost_equal(W, W2, decimal=6)
    finally:
        os.unlink(path)


def test_export_endianness_float32():
    """Verify first element matches expected little-endian bytes."""
    W = np.array([[0.5] + [0.0] * 31] + [[0.0] * 32] * 127, dtype=np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        with open(path, "rb") as f:
            raw = f.read(4)
        val = struct.unpack("<f", raw)[0]
        assert abs(val - 0.5) < 1e-6, f"First float should be 0.5, got {val}"
    finally:
        os.unlink(path)


def test_export_zeros_matrix():
    W = np.zeros((128, 32), dtype=np.float32)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = f.name
    try:
        _write_w_bin(W, path)
        W2 = _read_w_bin(path)
        assert np.all(W2 == 0.0)
    finally:
        os.unlink(path)
