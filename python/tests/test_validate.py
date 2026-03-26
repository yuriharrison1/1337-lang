"""Tests for leet.validate module."""

import pytest
from leet import (
    Cogon, Msg1337, Intent, Receiver, Surface, CanonicalSpace,
    Raw, RawRole
)
from leet.validate import validate


def _make_valid_msg(intent=Intent.ASSERT):
    """Helper: cria MSG_1337 válida."""
    cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
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


class TestValidation:
    def test_valid_msg_passes(self):
        """MSG_1337 válida passa validação."""
        msg = _make_valid_msg()
        assert validate(msg) is None

    def test_r2_delta_without_ref(self):
        """R2: DELTA sem ref deve falhar."""
        msg = _make_valid_msg(Intent.DELTA)
        msg.ref_hash = None
        msg.patch = None
        result = validate(msg)
        assert result is not None
        assert "R2" in result or "delta" in result.lower() or "ref" in result.lower()

    def test_r2_non_delta_with_patch(self):
        """R2: ASSERT com patch deve falhar."""
        msg = _make_valid_msg(Intent.ASSERT)
        msg.patch = [0.1] * 32
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_no_urgency(self):
        """R6: human_required=true sem urgency deve falhar."""
        msg = _make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = None
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_with_urgency(self):
        """R6: human_required=true COM urgency deve passar."""
        msg = _make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = 0.85
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_assert_fails(self):
        """R8: BROADCAST com ASSERT deve falhar."""
        msg = _make_valid_msg(Intent.ASSERT)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is not None

    def test_r8_broadcast_anomaly_passes(self):
        """R8: BROADCAST com ANOMALY deve passar."""
        msg = _make_valid_msg(Intent.ANOMALY)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_sync_passes(self):
        """R8: BROADCAST com SYNC deve passar."""
        msg = _make_valid_msg(Intent.SYNC)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None
