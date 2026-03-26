"""Tests for leet.bridge module."""

import pytest
import asyncio
from leet import Cogon
from leet.bridge import MockProjector, encode, decode


@pytest.fixture
def projector():
    return MockProjector()


@pytest.mark.asyncio
class TestMockEncode:
    async def test_mock_encode_basic(self):
        """Texto → COGON."""
        projector = MockProjector()
        sem, unc = await projector.project("olá mundo")
        assert len(sem) == 32
        assert len(unc) == 32

    async def test_mock_encode_urgent(self):
        """Urgência alta quando texto contém 'urgente'."""
        from leet.axes import C1_URGENCIA, C3_ACAO
        cogon = await encode("situação urgente no servidor")
        assert cogon.sem[C1_URGENCIA] > 0.8
        assert cogon.sem[C3_ACAO] > 0.7

    async def test_mock_encode_failure(self):
        """Anomalia alta quando texto contém erro."""
        from leet.axes import A8_ESTADO, C5_ANOMALIA
        cogon = await encode("o servidor caiu")
        assert cogon.sem[A8_ESTADO] > 0.7
        assert cogon.sem[C5_ANOMALIA] > 0.7


@pytest.mark.asyncio
class TestMockDecode:
    async def test_mock_decode(self):
        """COGON → texto com eixos dominantes."""
        projector = MockProjector()
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        cogon.sem[22] = 0.95  # URGÊNCIA
        cogon.sem[24] = 0.9   # AÇÃO
        
        text = await decode(cogon, projector)
        assert isinstance(text, str)
        assert "URGÊNCIA=0.95" in text or "AÇÃO=0.90" in text


@pytest.mark.asyncio
class TestRoundtrip:
    async def test_roundtrip(self):
        """Encode → decode preserva semântica."""
        projector = MockProjector()
        original = "situação urgente"
        cogon = await encode(original, projector)
        reconstructed = await decode(cogon, projector)
        
        assert isinstance(reconstructed, str)
        assert len(reconstructed) > 0
        # Verifica que urgência foi preservada
        assert cogon.sem[22] > 0.8


class TestAnthropicProjector:
    def test_anthropic_projector_init_fails_without_key(self):
        """Falha sem api_key (mas não crasha)."""
        import os
        # Remove key if exists
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError):
                from leet.bridge import AnthropicProjector
                AnthropicProjector(api_key=None)
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key
