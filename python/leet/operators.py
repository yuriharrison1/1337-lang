"""Semantic operators for 1337."""

import math
from typing import Optional
from leet.types import Cogon, FIXED_DIMS


def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    """
    Interpolated semantic fusion.

    sem = α·c1.sem + (1-α)·c2.sem
    unc = max(c1.unc, c2.unc)  # conservative uncertainty

    Args:
        c1: First COGON
        c2: Second COGON
        alpha: Interpolation weight [0.0, 1.0]

    Raises:
        ValueError: If alpha is outside the range [0, 1]
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")

    sem = [alpha * s1 + (1 - alpha) * s2
           for s1, s2 in zip(c1.sem, c2.sem)]
    unc = [max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]
    return Cogon.new(sem=sem, unc=unc)


def delta(prev: Cogon, curr: Cogon) -> list[float]:
    """Semantic difference between two states (point by point)."""
    return [c - p for p, c in zip(prev.sem, curr.sem)]


def dist(c1: Cogon, c2: Cogon) -> float:
    """
    Cosine distance weighted by (1-unc).

    Uncertain dimensions (high unc) carry less weight.
    Returns a value between 0 (identical) and 1 (orthogonal/opposite).
    """
    # Weight = 1 - max(unc_a, unc_b)
    weights = [1 - max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]

    # Weighted dot product
    dot = sum(w * s1 * s2 for w, s1, s2 in zip(weights, c1.sem, c2.sem))

    # Weighted norms
    norm1 = math.sqrt(sum(w * s * s for w, s in zip(weights, c1.sem)))
    norm2 = math.sqrt(sum(w * s * s for w, s in zip(weights, c2.sem)))

    if norm1 == 0 or norm2 == 0:
        return 1.0  # maximum distance if either is zero

    cosine = dot / (norm1 * norm2)
    # Clamp to avoid numerical errors
    cosine = max(-1.0, min(1.0, cosine))

    # Returns 1 - similarity (distance)
    return 1.0 - cosine


def focus(cogon: Cogon, dims: list[int]) -> Cogon:
    """
    Projects COGON onto a subset of dimensions.

    Selected dimensions keep their values.
    Unselected dimensions: sem=0, unc=1.0 (maximum uncertainty)
    """
    dim_set = set(dims)
    sem = [s if i in dim_set else 0.0 for i, s in enumerate(cogon.sem)]
    unc = [u if i in dim_set else 1.0 for i, u in enumerate(cogon.unc)]
    return Cogon.new(sem=sem, unc=unc)


def anomaly_score(cogon: Cogon, history: list[Cogon]) -> float:
    """
    Average distance from the historical centroid.

    Returns 0.5 (neutral value) if history is empty, since there is no
    baseline for comparison. Maximum anomaly (1.0) only makes sense
    when we have history to compare against.
    """
    if not history:
        return 0.5  # neutral: no baseline

    # Compute centroid
    n = len(history)
    centroid_sem = [sum(h.sem[i] for h in history) / n for i in range(FIXED_DIMS)]
    centroid_unc = [sum(h.unc[i] for h in history) / n for i in range(FIXED_DIMS)]

    centroid = Cogon.new(sem=centroid_sem, unc=centroid_unc)

    # Distance from the cogon to the centroid
    return dist(cogon, centroid)


def apply_patch(base: Cogon, patch: list[float]) -> Cogon:
    """
    Applies a delta patch, clamped to [0,1].

    sem_result[i] = clamp(base.sem[i] + patch[i], 0, 1)
    """
    sem = [max(0.0, min(1.0, s + p)) for s, p in zip(base.sem, patch)]
    return Cogon.new(sem=sem, unc=base.unc.copy())
