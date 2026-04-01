"""Tests for generate_dataset.py — embedding and scoring functions."""
import sys
import os

# Make calibration/ importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate_dataset import mock_embed, mock_score, clamp


# ─── mock_embed ──────────────────────────────────────────────────────────────

def test_mock_embed_length():
    emb = mock_embed("hello world")
    assert len(emb) == 128, f"Expected 128-dim embedding, got {len(emb)}"


def test_mock_embed_values_in_range():
    emb = mock_embed("urgência crítica no sistema")
    for i, v in enumerate(emb):
        assert 0.0 <= v <= 1.0, f"emb[{i}] = {v} not in [0,1]"


def test_mock_embed_deterministic():
    e1 = mock_embed("same text")
    e2 = mock_embed("same text")
    assert e1 == e2, "mock_embed must be deterministic"


def test_mock_embed_distinct_texts_differ():
    e1 = mock_embed("amor eterno")
    e2 = mock_embed("sistema crítico falhou")
    assert e1 != e2, "different texts must produce different embeddings"


# ─── mock_score ──────────────────────────────────────────────────────────────

def test_mock_score_length():
    sem, unc = mock_score("test scoring")
    assert len(sem) == 32, f"sem must have 32 dims, got {len(sem)}"
    assert len(unc) == 32, f"unc must have 32 dims, got {len(unc)}"


def test_mock_score_sem_in_range():
    sem, _ = mock_score("some arbitrary text to score")
    for i, v in enumerate(sem):
        assert 0.0 <= v <= 1.0, f"sem[{i}] = {v} not in [0,1]"


def test_mock_score_unc_in_range():
    _, unc = mock_score("another piece of text")
    for i, v in enumerate(unc):
        assert 0.0 <= v <= 1.0, f"unc[{i}] = {v} not in [0,1]"


def test_mock_score_unc_formula():
    """unc[i] must follow: unc = 1 - |sem - 0.5| * 2"""
    sem, unc = mock_score("formula verification")
    for i in range(32):
        expected = 1.0 - abs(sem[i] - 0.5) * 2.0
        assert abs(unc[i] - expected) < 1e-6, (
            f"unc[{i}]={unc[i]:.6f} != formula {expected:.6f}"
        )


def test_mock_score_deterministic():
    s1, u1 = mock_score("determinism check")
    s2, u2 = mock_score("determinism check")
    assert s1 == s2, "sem must be deterministic"
    assert u1 == u2, "unc must be deterministic"


# ─── clamp ───────────────────────────────────────────────────────────────────

def test_clamp_within_range():
    assert clamp(0.5) == 0.5


def test_clamp_above_one():
    assert clamp(1.5) == 1.0


def test_clamp_below_zero():
    assert clamp(-0.3) == 0.0
