"""Tests for leet.operators module."""

import pytest
from leet import Cogon, blend, delta, dist, focus, anomaly_score, apply_patch


class TestBlend:
    def test_midpoint_blend(self):
        """α=0.5 entre opostos → meio termo."""
        c1 = Cogon.new(sem=[1.0] * 32, unc=[0.0] * 32)
        c2 = Cogon.new(sem=[0.0] * 32, unc=[0.0] * 32)
        result = blend(c1, c2, 0.5)
        for s in result.sem:
            assert abs(s - 0.5) < 0.001

    def test_conservative_uncertainty(self):
        """unc do BLEND é max dos dois (conservadora)."""
        c1 = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        c2 = Cogon.new(sem=[0.5] * 32, unc=[0.9] * 32)
        result = blend(c1, c2, 0.5)
        for u in result.unc:
            assert abs(u - 0.9) < 0.001, "UNC deve ser max(0.1, 0.9) = 0.9"

    def test_alpha_extremes(self):
        """α=1.0 retorna c1, α=0.0 retorna c2."""
        c1 = Cogon.new(sem=[1.0] * 32, unc=[0.0] * 32)
        c2 = Cogon.new(sem=[0.0] * 32, unc=[0.0] * 32)

        r1 = blend(c1, c2, 1.0)
        assert all(abs(s - 1.0) < 0.001 for s in r1.sem)

        r0 = blend(c1, c2, 0.0)
        assert all(abs(s - 0.0) < 0.001 for s in r0.sem)


class TestDelta:
    def test_delta_computation(self):
        """Diferença correta."""
        prev = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        curr = Cogon.new(sem=[0.7] * 32, unc=[0.1] * 32)
        d = delta(prev, curr)
        assert len(d) == 32
        assert all(abs(v - 0.2) < 0.001 for v in d)


class TestDist:
    def test_dist_identical(self):
        """Distância entre COGONs idênticos é ~0."""
        c = Cogon.new(sem=[0.5] * 32, unc=[0.0] * 32)
        d = dist(c, c)
        assert d < 0.001

    def test_dist_orthogonal(self):
        """Distância entre opostos é alta."""
        c1 = Cogon.new(sem=[1.0] * 32, unc=[0.0] * 32)
        c2 = Cogon.new(sem=[0.0] * 32, unc=[0.0] * 32)
        d = dist(c1, c2)
        assert d > 0.9


class TestFocus:
    def test_focus_subset(self):
        """Dims selecionadas mantêm, resto zera com unc=1."""
        c = Cogon.new(sem=[0.8] * 32, unc=[0.1] * 32)
        focused = focus(c, [0, 1, 2])  # Só 3 primeiras dims
        
        for i in range(3):
            assert focused.sem[i] == 0.8
        for i in range(3, 32):
            assert focused.sem[i] == 0.0
            assert focused.unc[i] == 1.0


class TestAnomalyScore:
    def test_anomaly_score_empty(self):
        """Histórico vazio retorna 1.0."""
        c = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        score = anomaly_score(c, [])
        assert score == 1.0

    def test_anomaly_score_normal(self):
        """COGON igual ao histórico tem score baixo."""
        history = [Cogon.new(sem=[0.5] * 32, unc=[0.0] * 32) for _ in range(5)]
        normal = Cogon.new(sem=[0.5] * 32, unc=[0.0] * 32)
        score = anomaly_score(normal, history)
        assert score < 0.1


class TestApplyPatch:
    def test_apply_patch_clamp(self):
        """Patch que levaria acima de 1.0 é clamped."""
        base = Cogon.new(sem=[0.9] * 32, unc=[0.1] * 32)
        patch = [0.5] * 32  # 0.9 + 0.5 = 1.4 → clamped a 1.0
        result = apply_patch(base, patch)
        assert all(s <= 1.0 for s in result.sem)
        assert all(s == 1.0 for s in result.sem)  # clamped at 1.0
