"""
Step 3: Evaluate W projection quality.
Loads data/W.npy and runs coherence tests.

Usage:
    python evaluate_w.py
"""

import hashlib
import sys

import numpy as np


W_NPY_PATH = "data/W.npy"


# ---------------------------------------------------------------------------
# Helpers (mirror of generate_dataset.py — standalone so no import needed)
# ---------------------------------------------------------------------------

def mock_embed(text: str) -> np.ndarray:
    """128-dim SHA256 expansion."""
    h = hashlib.sha256(text.encode()).digest()
    emb = []
    for i in range(128):
        b1 = h[i % 32]
        b2 = h[(i + 1) % 32]
        b3 = h[(i + 2) % 32]
        val = ((b1 << 16 | b2 << 8 | b3) & 0xFFFFFF) / 16777215.0
        emb.append(val)
    return np.array(emb, dtype=np.float32)


def mock_unc(text: str) -> np.ndarray:
    """32-dim uncertainty from mock_score."""
    h = hashlib.sha256(text.encode()).digest()
    unc = []
    for i in range(32):
        b1 = h[i % 32]
        b2 = h[(i + 1) % 32]
        val = ((b1 << 8 | b2) & 0xFFFF) / 65535.0
        unc.append(1.0 - abs(val - 0.5) * 2.0)
    return np.array(unc, dtype=np.float32)


def project(text: str, W: np.ndarray) -> np.ndarray:
    """Project text → 32-dim semantic vector via W."""
    X = mock_embed(text).reshape(1, 128)
    sem = (X @ W).clip(0.0, 1.0).reshape(32)
    return sem


def dist(sem1: np.ndarray, unc1: np.ndarray, sem2: np.ndarray, unc2: np.ndarray) -> float:
    """Weighted cosine distance in [0, 2]."""
    w = (1 - unc1) * (1 - unc2)
    dot = np.sum(sem1 * sem2 * w)
    n1 = np.sqrt(np.sum(sem1 ** 2 * w)) + 1e-8
    n2 = np.sqrt(np.sum(sem2 ** 2 * w)) + 1e-8
    return float(1.0 - dot / (n1 * n2))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_axis_coherence(W: np.ndarray) -> list[tuple[str, bool, float]]:
    """Similar texts should be close in semantic space."""
    pairs = [
        ("hello world", "greetings universe"),
        ("MPC control system", "model predictive control"),
        ("the server crashed unexpectedly", "fatal error: process terminated"),
        ("machine learning model training", "neural network optimization loop"),
        ("the temperature is rising slowly", "gradual increase in thermal energy"),
    ]
    results = []
    for a, b in pairs:
        sem_a = project(a, W)
        sem_b = project(b, W)
        unc_a = mock_unc(a)
        unc_b = mock_unc(b)
        d = dist(sem_a, unc_a, sem_b, unc_b)
        passed = d < 0.5
        results.append((f'dist("{a[:30]}", "{b[:30]}")', passed, d))
    return results


def test_axis_extremity(W: np.ndarray) -> list[tuple[str, bool, float]]:
    """Specific texts should activate expected axes."""
    checks = [
        # (text, axis_index, direction, threshold, description)
        ("CRITICAL: database connection pool exhausted — all new requests are failing immediately.",
         22, "high", 0.4, "urgency axis > 0.4 for critical alert"),
        ("The documentation has been updated to reflect the latest API changes.",
         22, "low", 0.6, "urgency axis < 0.6 for informational text"),
        ("Water evaporates from the ocean surface, rises as vapor, condenses into clouds, and returns as rain.",
         9, "high", 0.3, "processo axis > 0.3 for process description"),
        ("A photon is an elementary particle and quantum of the electromagnetic field.",
         8, "high", 0.3, "estado axis > 0.3 for state/entity description"),
    ]
    results = []
    for text, axis, direction, threshold, desc in checks:
        sem = project(text, W)
        val = float(sem[axis])
        if direction == "high":
            passed = val > threshold
            label = f"axis[{axis}]={val:.3f} > {threshold}"
        else:
            passed = val < threshold
            label = f"axis[{axis}]={val:.3f} < {threshold}"
        results.append((f"{desc} ({label})", passed, val))
    return results


def test_unc_calibration(W: np.ndarray) -> list[tuple[str, bool, float]]:
    """Definitive statements should have lower average uncertainty than vague questions."""
    definitive = "The TCP/IP protocol was standardized in 1983 and has been widely used since."
    vague = "Could this behavior possibly be caused by some kind of memory leak?"

    unc_def = mock_unc(definitive)
    unc_vague = mock_unc(vague)

    avg_def = float(unc_def.mean())
    avg_vague = float(unc_vague.mean())

    passed = avg_def < avg_vague
    label = f"unc(definitive)={avg_def:.3f} < unc(vague)={avg_vague:.3f}"
    return [(f"Definitive < vague uncertainty ({label})", passed, avg_def - avg_vague)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        W = np.load(W_NPY_PATH)
    except FileNotFoundError:
        print(f"ERROR: {W_NPY_PATH} not found. Run train_w.py first.", file=sys.stderr)
        sys.exit(1)

    assert W.shape == (128, 32), f"Expected W shape (128, 32), got {W.shape}"
    print(f"Loaded W: shape={W.shape}, dtype={W.dtype}")
    print(f"  W stats: min={W.min():.4f}, max={W.max():.4f}, mean={W.mean():.4f}\n")

    all_results = []

    print("=" * 60)
    print("TEST 1: Axis Coherence (similar texts → low distance)")
    print("=" * 60)
    coherence = test_axis_coherence(W)
    for name, passed, val in coherence:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}  d={val:.4f}")
        all_results.append(passed)

    print()
    print("=" * 60)
    print("TEST 2: Axis Extremity (expected axis activations)")
    print("=" * 60)
    extremity = test_axis_extremity(W)
    for name, passed, val in extremity:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        all_results.append(passed)

    print()
    print("=" * 60)
    print("TEST 3: Uncertainty Calibration")
    print("=" * 60)
    calib = test_unc_calibration(W)
    for name, passed, val in calib:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        all_results.append(passed)

    print()
    n_pass = sum(all_results)
    n_total = len(all_results)
    print("=" * 60)
    print(f"SUMMARY: {n_pass}/{n_total} tests passed")
    print("=" * 60)

    if n_pass < n_total:
        print("\nNOTE: Some tests failed. This may be expected with mock data.")
        print("The mock scorer uses SHA256 hashing which does not preserve semantic similarity.")
        print("Run with --provider anthropic or --provider openai for semantically accurate W.")


if __name__ == "__main__":
    main()
