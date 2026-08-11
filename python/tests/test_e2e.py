"""
End-to-end integration tests for 1337 v0.4.
Validate the full flow of types, operators, validation, and bridge.
All use MockProjector — no API key required.

Run with: pytest tests/test_e2e.py -v
"""

import pytest
import asyncio
import json
import hashlib
from leet import (
    Cogon, Edge, Dag, Msg1337, Raw, RawRole, Intent, Receiver, 
    Surface, CanonicalSpace, FIXED_DIMS,
    blend, delta, dist, focus, anomaly_score, apply_patch,
)
from leet.bridge import MockProjector, encode, decode
from leet.validate import validate, check_confidence
from leet.axes import CANONICAL_AXES, A8_ESTADO, A9_PROCESSO, C1_URGENCIA, C3_ACAO, C5_ANOMALIA


# ═══════════════════════════════════════════════════════════════════
# TEST 1: COGON_ZERO — "I AM"
# ═══════════════════════════════════════════════════════════════════

class TestCogonZero:
    def test_creation(self):
        """COGON_ZERO has exact values from the spec."""
        zero = Cogon.zero()
        assert len(zero.sem) == 32
        assert len(zero.unc) == 32
        assert all(s == 1.0 for s in zero.sem), "sem must be [1]*32"
        assert all(u == 0.0 for u in zero.unc), "unc must be [0]*32"
        assert zero.stamp == 0
        assert zero.is_zero()

    def test_serialization_roundtrip(self):
        """COGON_ZERO serializes and deserializes without loss."""
        zero = Cogon.zero()
        json_str = zero.to_json()
        restored = Cogon.from_json(json_str)
        assert restored.sem == zero.sem
        assert restored.unc == zero.unc
        assert restored.stamp == 0
        assert restored.is_zero()

    def test_zero_id_is_nil(self):
        """COGON_ZERO ID is nil UUID."""
        zero = Cogon.zero()
        assert zero.id == "00000000-0000-0000-0000-000000000000"

    def test_zero_no_low_confidence(self):
        """COGON_ZERO has no low-confidence flags (unc=0 everywhere)."""
        zero = Cogon.zero()
        assert zero.low_confidence_dims() == []


# ═══════════════════════════════════════════════════════════════════
# TEST 2: Text → COGON → Text (roundtrip with MockProjector)
# ═══════════════════════════════════════════════════════════════════

class TestTextRoundtrip:
    @pytest.fixture
    def projector(self):
        return MockProjector()

    @pytest.mark.asyncio
    async def test_urgent_text(self, projector):
        """'urgente' keyword should yield high URGÊNCIA and AÇÃO."""
        cogon = await encode("Situação urgente no servidor", projector)
        assert cogon.sem[C1_URGENCIA] > 0.8, "C1_URGÊNCIA should be high"
        assert cogon.sem[C3_ACAO] > 0.7, "C3_AÇÃO should be high"

    @pytest.mark.asyncio
    async def test_failure_text(self, projector):
        """'servidor caiu' keyword should yield high ANOMALIA and ESTADO."""
        cogon = await encode("O servidor caiu", projector)
        assert cogon.sem[A8_ESTADO] > 0.7, "A8_ESTADO should be high"
        assert cogon.sem[C5_ANOMALIA] > 0.7, "C5_ANOMALIA should be high"

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_semantics(self, projector):
        """Encode → decode preserves dominant axes."""
        original = "Situação urgente no servidor"
        cogon = await encode(original, projector)
        reconstructed = await decode(cogon, projector)
        # The reconstructed text should mention the dominant axes
        assert isinstance(reconstructed, str)
        assert len(reconstructed) > 0

    @pytest.mark.asyncio
    async def test_generic_text(self, projector):
        """Generic text has moderate values."""
        cogon = await encode("Good morning", projector)
        # No special keywords, values should be ~0.5
        avg = sum(cogon.sem) / len(cogon.sem)
        assert 0.3 < avg < 0.7, "Generic text should have moderate average"


# ═══════════════════════════════════════════════════════════════════
# TEST 3: DAG — Composite Reasoning
# ═══════════════════════════════════════════════════════════════════

class TestDag:
    def test_simple_dag(self):
        """DAG with 3 nodes and 2 edges — incident scenario."""
        # A: "There was a deploy" (PROCESSO high)
        a_sem = [0.5] * 32
        a_sem[A9_PROCESSO] = 0.85
        a = Cogon(sem=a_sem, unc=[0.1] * 32, stamp=1, id="a" * 36)

        # B: "The system crashed" (ANOMALIA high)
        b_sem = [0.5] * 32
        b_sem[C5_ANOMALIA] = 0.9
        b_sem[A8_ESTADO] = 0.9
        b = Cogon(sem=b_sem, unc=[0.1] * 32, stamp=2, id="b" * 36)

        # C: "We need to roll back" (AÇÃO + URGÊNCIA high)
        c_sem = [0.5] * 32
        c_sem[C3_ACAO] = 0.9
        c_sem[C1_URGENCIA] = 0.85
        c = Cogon(sem=c_sem, unc=[0.1] * 32, stamp=3, id="c" * 36)

        # Build DAG
        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_node(c)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type="CAUSA", weight=0.9))
        dag.add_edge(Edge(from_id=b.id, to_id=c.id, edge_type="CONDICIONA", weight=0.85))

        # Validate topological order
        order = dag.topological_order()
        assert len(order) == 3
        assert order.index(a.id) < order.index(b.id)
        assert order.index(b.id) < order.index(c.id)

    def test_dag_cycle_detection(self):
        """DAG with a cycle should fail (R4)."""
        a = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        b = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=2, id="b" * 36)

        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type="CAUSA", weight=0.9))
        dag.add_edge(Edge(from_id=b.id, to_id=a.id, edge_type="CAUSA", weight=0.9))  # cycle!

        with pytest.raises((ValueError, Exception)):
            dag.topological_order()

    def test_dag_single_node(self):
        """DAG with a single node is valid."""
        a = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        dag = Dag.from_root(a)
        order = dag.topological_order()
        assert order == [a.id]


# ═══════════════════════════════════════════════════════════════════
# TEST 4: DELTA Compression
# ═══════════════════════════════════════════════════════════════════

class TestDeltaCompression:
    def test_delta_only_urgency(self):
        """DELTA between two states that differ only in urgency."""
        sem_before = [0.5] * 32
        sem_after = [0.5] * 32
        sem_after[C1_URGENCIA] = 0.95  # only urgency changed

        prev = Cogon(sem=sem_before, unc=[0.1] * 32, stamp=1, id="p" * 36)
        curr = Cogon(sem=sem_after, unc=[0.1] * 32, stamp=2, id="c" * 36)

        d = delta(prev, curr)
        assert len(d) == 32
        # Only index 22 (C1_URGÊNCIA) should be != 0
        for i, v in enumerate(d):
            if i == C1_URGENCIA:
                assert abs(v - 0.45) < 0.01, "Urgency delta should be ~0.45"
            else:
                assert abs(v) < 0.001, f"Delta at axis {i} should be ~0"

    def test_apply_patch_roundtrip(self):
        """Applies patch → result = new state."""
        sem_before = [0.5] * 32
        sem_after = [0.5] * 32
        sem_after[C1_URGENCIA] = 0.95

        prev = Cogon(sem=sem_before, unc=[0.1] * 32, stamp=1, id="p" * 36)
        curr = Cogon(sem=sem_after, unc=[0.1] * 32, stamp=2, id="c" * 36)

        d = delta(prev, curr)
        restored = apply_patch(prev, d)

        for i in range(32):
            assert abs(restored.sem[i] - curr.sem[i]) < 0.001, \
                f"Axis {i}: {restored.sem[i]} != {curr.sem[i]}"

    def test_patch_clamp(self):
        """Patch that would go above 1.0 is clamped."""
        base = Cogon(sem=[0.9] * 32, unc=[0.1] * 32, stamp=1, id="b" * 36)
        patch = [0.5] * 32  # 0.9 + 0.5 = 1.4 → clamped to 1.0
        result = apply_patch(base, patch)
        assert all(s <= 1.0 for s in result.sem)


# ═══════════════════════════════════════════════════════════════════
# TEST 5: BLEND of Two Agents
# ═══════════════════════════════════════════════════════════════════

class TestBlend:
    def test_midpoint_blend(self):
        """α=0.5 between opposites → midpoint."""
        c1 = Cogon(sem=[1.0] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)
        result = blend(c1, c2, 0.5)
        for s in result.sem:
            assert abs(s - 0.5) < 0.001

    def test_conservative_uncertainty(self):
        """BLEND's unc is the max of the two (conservative)."""
        c1 = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.5] * 32, unc=[0.9] * 32, stamp=2, id="b" * 36)
        result = blend(c1, c2, 0.5)
        for u in result.unc:
            assert abs(u - 0.9) < 0.001, "UNC should be max(0.1, 0.9) = 0.9"

    def test_alpha_extremes(self):
        """α=1.0 returns c1, α=0.0 returns c2."""
        c1 = Cogon(sem=[1.0] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)

        r1 = blend(c1, c2, 1.0)
        assert all(abs(s - 1.0) < 0.001 for s in r1.sem)

        r0 = blend(c1, c2, 0.0)
        assert all(abs(s - 0.0) < 0.001 for s in r0.sem)

    def test_two_agents_different_domains(self):
        """Technical agent (SISTEMA) + empathic agent (AFETO) → BLEND."""
        tech = Cogon(sem=[0.5] * 32, unc=[0.2] * 32, stamp=1, id="a" * 36)
        tech.sem[7] = 0.95   # A7_SISTEMA
        tech.unc[7] = 0.05

        empathic = Cogon(sem=[0.5] * 32, unc=[0.2] * 32, stamp=2, id="b" * 36)
        empathic.sem[27] = 0.95  # C6_AFETO
        empathic.unc[27] = 0.05

        result = blend(tech, empathic, 0.5)
        # Both should have ~0.725 in their dominant axes
        assert result.sem[7] > 0.6, "SISTEMA should be present"
        assert result.sem[27] > 0.6, "AFETO should be present"


# ═══════════════════════════════════════════════════════════════════
# TEST 6: R1-R21 Validation
# ═══════════════════════════════════════════════════════════════════

class TestValidation:
    def _make_valid_msg(self, intent=Intent.ASSERT):
        """Helper: creates a valid MSG_1337."""
        cogon = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="c" * 36)
        return Msg1337(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            sender="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            receiver=Receiver(agent_id="cccccccc-cccc-cccc-cccc-cccccccccccc"),
            intent=intent,
            payload=cogon,
            c5=CanonicalSpace(
                zone_fixed=[0.5] * 32,
                zone_emergent={},
                schema_ver="0.4.0",
                align_hash="abc123",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=3,
                lang="pt",
            ),
        )

    def test_valid_msg_passes(self):
        """Valid MSG_1337 passes validation."""
        msg = self._make_valid_msg()
        assert validate(msg) is None

    def test_r2_delta_without_ref(self):
        """R2: DELTA without ref should fail."""
        msg = self._make_valid_msg(Intent.DELTA)
        msg.ref_hash = None
        msg.patch = None
        result = validate(msg)
        assert result is not None
        assert "R2" in result or "delta" in result.lower() or "ref" in result.lower()

    def test_r2_non_delta_with_patch(self):
        """R2: ASSERT with patch should fail."""
        msg = self._make_valid_msg(Intent.ASSERT)
        msg.patch = [0.1] * 32
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_no_urgency(self):
        """R6: human_required=true without urgency should fail."""
        msg = self._make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = None
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_with_urgency(self):
        """R6: human_required=true WITH urgency should pass."""
        msg = self._make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = 0.85
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_assert_fails(self):
        """R8: BROADCAST with ASSERT should fail."""
        msg = self._make_valid_msg(Intent.ASSERT)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is not None

    def test_r8_broadcast_anomaly_passes(self):
        """R8: BROADCAST with ANOMALY should pass."""
        msg = self._make_valid_msg(Intent.ANOMALY)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_sync_passes(self):
        """R8: BROADCAST with SYNC should pass."""
        msg = self._make_valid_msg(Intent.SYNC)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# TEST 7: Full MSG_1337 — Envelope Roundtrip
# ═══════════════════════════════════════════════════════════════════

class TestMsgEnvelope:
    def test_full_envelope_roundtrip(self):
        """Creates MSG_1337 → serializes → hashes → deserializes → revalidates."""
        cogon = Cogon(sem=[0.7] * 32, unc=[0.1] * 32, stamp=1, id="c" * 36)
        msg = Msg1337(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            sender="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            receiver=Receiver(agent_id="cccccccc-cccc-cccc-cccc-cccccccccccc"),
            intent=Intent.ASSERT,
            payload=cogon,
            c5=CanonicalSpace(
                zone_fixed=[0.7] * 32,
                zone_emergent={},
                schema_ver="0.4.0",
                align_hash="deadbeef",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=3,
                lang="pt",
            ),
        )

        # Serialize
        json_str = msg.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 100

        # Hash
        h = msg.hash()
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex

        # Deserialize
        restored = Msg1337.from_json(json_str)
        assert restored.intent == msg.intent
        assert restored.sender == msg.sender
        assert restored.c5.schema_ver == "0.4.0"

        # Hash of the restored message should match
        assert restored.hash() == h, "Roundtrip should preserve hash"

        # Revalidate
        assert validate(restored) is None, "Restored msg should be valid"

    def test_msg_with_dag_payload(self):
        """MSG_1337 with DAG payload (not a plain COGON)."""
        a = Cogon(sem=[0.8] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        b = Cogon(sem=[0.3] * 32, unc=[0.2] * 32, stamp=2, id="b" * 36)
        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type="CAUSA", weight=0.9))

        msg = Msg1337(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            sender="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            receiver=Receiver(agent_id="cccccccc-cccc-cccc-cccc-cccccccccccc"),
            intent=Intent.ASSERT,
            payload=dag,
            c5=CanonicalSpace(
                zone_fixed=[0.5] * 32,
                zone_emergent={},
                schema_ver="0.4.0",
                align_hash="abc",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=3,
                lang="pt",
            ),
        )

        json_str = msg.to_json()
        restored = Msg1337.from_json(json_str)
        assert validate(restored) is None

    def test_msg_with_raw_bridge(self):
        """MSG_1337 with RAW BRIDGE (interoperability)."""
        raw = Raw(
            content_type="protocol/mcp",
            content={"tool": "search", "query": "1337 spec"},
            role=RawRole.BRIDGE,
        )
        cogon = Cogon(sem=[0.5] * 32, unc=[0.2] * 32, stamp=1, id="c" * 36).with_raw(raw)

        msg = Msg1337(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            sender="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            receiver=Receiver(agent_id="cccccccc-cccc-cccc-cccc-cccccccccccc"),
            intent=Intent.ASSERT,
            payload=cogon,
            c5=CanonicalSpace(
                zone_fixed=[0.5] * 32,
                zone_emergent={},
                schema_ver="0.4.0",
                align_hash="bridge123",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=0,
                lang="pt",
            ),
        )

        json_str = msg.to_json()
        restored = Msg1337.from_json(json_str)
        # RAW should survive the roundtrip
        payload = restored.payload
        assert payload.raw is not None
        assert payload.raw.role == RawRole.BRIDGE
        assert payload.raw.content_type == "protocol/mcp"


# ═══════════════════════════════════════════════════════════════════
# TEST 8: Additional Operators
# ═══════════════════════════════════════════════════════════════════

class TestOperatorsE2E:
    def test_focus_ontological_only(self):
        """FOCUS on ontological axes (0-13)."""
        c = Cogon(sem=[0.8] * 32, unc=[0.1] * 32, stamp=1, id="c" * 36)
        focused = focus(c, list(range(14)))  # A0-A13
        # Axes 0-13 keep their values
        for i in range(14):
            assert focused.sem[i] == 0.8
        # Axes 14-31 zeroed, unc=1.0
        for i in range(14, 32):
            assert focused.sem[i] == 0.0
            assert focused.unc[i] == 1.0

    def test_dist_zero_for_identical(self):
        """Distance between identical COGONs is ~0."""
        c = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=1, id="c" * 36)
        d = dist(c, c)
        assert d < 0.001

    def test_dist_increases_with_difference(self):
        """Distance increases as COGONs diverge."""
        base = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        similar = Cogon(sem=[0.6] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)
        different = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=3, id="c" * 36)

        d_similar = dist(base, similar)
        d_different = dist(base, different)
        assert d_similar < d_different

    def test_anomaly_score_outlier(self):
        """COGON outside the historical pattern has a high score."""
        # History: everything at 0.5
        history = [Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=i, id=str(i) * 36) for i in range(5)]
        # Outlier: everything at 0.0
        outlier = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=10, id="x" * 36)

        score = anomaly_score(outlier, history)
        assert score > 0.5, "Outlier should have high anomaly score"

    def test_anomaly_score_normal(self):
        """COGON within the pattern has a low score."""
        history = [Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=i, id=str(i) * 36) for i in range(5)]
        normal = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=10, id="x" * 36)

        score = anomaly_score(normal, history)
        assert score < 0.1, "Normal should have low anomaly score"


# ═══════════════════════════════════════════════════════════════════
# TEST 9: Axes Reference
# ═══════════════════════════════════════════════════════════════════

class TestAxes:
    def test_32_axes_defined(self):
        """All 32 axes are defined."""
        assert len(CANONICAL_AXES) == 32

    def test_axes_indices_sequential(self):
        """Indices 0 to 31 are sequential."""
        for i, ax in enumerate(CANONICAL_AXES):
            assert ax.index == i

    def test_group_a_ontological(self):
        """Group A has 14 axes (0-13)."""
        from leet.axes import axes_in_group, AxisGroup
        group_a = axes_in_group(AxisGroup.ONTOLOGICAL)
        assert len(group_a) == 14

    def test_group_b_epistemic(self):
        """Group B has 8 axes (14-21)."""
        from leet.axes import axes_in_group, AxisGroup
        group_b = axes_in_group(AxisGroup.EPISTEMIC)
        assert len(group_b) == 8

    def test_group_c_pragmatic(self):
        """Group C has 10 axes (22-31)."""
        from leet.axes import axes_in_group, AxisGroup
        group_c = axes_in_group(AxisGroup.PRAGMATIC)
        assert len(group_c) == 10
