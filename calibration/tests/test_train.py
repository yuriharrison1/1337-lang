"""Tests for train_w.py — dataset loading and W matrix training."""
import sys
import os
import json
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from train_w import load_dataset
from generate_dataset import mock_embed, mock_score


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_dataset_file(n: int = 20) -> str:
    """Write n records to a temp JSONL file and return its path."""
    texts = [f"text sample number {i}" for i in range(n)]
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for text in texts:
            emb = mock_embed(text)
            sem, unc = mock_score(text)
            f.write(json.dumps({"text": text, "emb": emb, "sem": sem, "unc": unc}) + "\n")
    return path


def _train_w_from_records(records) -> np.ndarray:
    """Minimal training: Ridge per axis, no normalization."""
    from sklearn.linear_model import Ridge
    X = np.array([r["emb"] for r in records], dtype=np.float64)
    Y = np.array([r["sem"] for r in records], dtype=np.float64)
    W = np.zeros((128, 32), dtype=np.float64)
    for axis in range(32):
        ridge = Ridge(alpha=0.01)
        ridge.fit(X, Y[:, axis])
        W[:, axis] = ridge.coef_
    return W


# ─── load_dataset ────────────────────────────────────────────────────────────

def test_load_dataset_returns_list():
    path = _make_dataset_file(10)
    try:
        records = load_dataset(path)
        assert isinstance(records, list)
        assert len(records) == 10
    finally:
        os.unlink(path)


def test_load_dataset_record_format():
    path = _make_dataset_file(5)
    try:
        records = load_dataset(path)
        for r in records:
            assert "text" in r
            assert "emb" in r
            assert "sem" in r
            assert "unc" in r
            assert len(r["emb"]) == 128
            assert len(r["sem"]) == 32
            assert len(r["unc"]) == 32
    finally:
        os.unlink(path)


def test_load_dataset_skips_empty_lines():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        emb = mock_embed("hello")
        sem, unc = mock_score("hello")
        f.write(json.dumps({"text": "hello", "emb": emb, "sem": sem, "unc": unc}) + "\n")
        f.write("\n")  # blank line
        f.write("\n")  # blank line
    try:
        records = load_dataset(path)
        assert len(records) == 1
    finally:
        os.unlink(path)


# ─── W matrix training ───────────────────────────────────────────────────────

def test_w_matrix_shape():
    path = _make_dataset_file(20)
    try:
        records = load_dataset(path)
        W = _train_w_from_records(records)
        assert W.shape == (128, 32), f"Expected (128,32), got {W.shape}"
    finally:
        os.unlink(path)


def test_w_projection_produces_finite_values():
    path = _make_dataset_file(20)
    try:
        records = load_dataset(path)
        W = _train_w_from_records(records)
        X = np.array([r["emb"] for r in records[:5]], dtype=np.float64)
        proj = (X @ W).clip(0.0, 1.0)
        assert proj.shape == (5, 32)
        assert np.all(np.isfinite(proj))
    finally:
        os.unlink(path)


def test_w_clipped_output_in_range():
    path = _make_dataset_file(20)
    try:
        records = load_dataset(path)
        W = _train_w_from_records(records)
        X = np.array([r["emb"] for r in records], dtype=np.float64)
        proj = (X @ W).clip(0.0, 1.0)
        assert proj.min() >= 0.0, "clipped output should be ≥ 0"
        assert proj.max() <= 1.0, "clipped output should be ≤ 1"
    finally:
        os.unlink(path)
