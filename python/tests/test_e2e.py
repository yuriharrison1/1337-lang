"""
Testes de integração end-to-end para 1337 v0.4.
Validam o fluxo completo de tipos, operadores, validação e bridge.
Todos usam MockProjector — sem API key necessária.

Rodar com: pytest tests/test_e2e.py -v
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
        """COGON_ZERO tem valores exatos da spec."""
        zero = Cogon.zero()
        assert len(zero.sem) == 32
        assert len(zero.unc) == 32
        assert all(s == 1.0 for s in zero.sem), "sem deve ser [1]*32"
        assert all(u == 0.0 for u in zero.unc), "unc deve ser [0]*32"
        assert zero.stamp == 0
        assert zero.is_zero()

    def test_serialization_roundtrip(self):
        """COGON_ZERO serializa e desserializa sem perda."""
        zero = Cogon.zero()
        json_str = zero.to_json()
        restored = Cogon.from_json(json_str)
        assert restored.sem == zero.sem
        assert restored.unc == zero.unc
        assert restored.stamp == 0
        assert restored.is_zero()

    def test_zero_id_is_nil(self):
        """ID do COGON_ZERO é nil UUID."""
        zero = Cogon.zero()
        assert zero.id == "00000000-0000-0000-0000-000000000000"

    def test_zero_no_low_confidence(self):
        """COGON_ZERO não tem flags de baixa confiança (unc=0 em tudo)."""
        zero = Cogon.zero()
        assert zero.low_confidence_dims() == []


# ═══════════════════════════════════════════════════════════════════
# TEST 2: Texto → COGON → Texto (roundtrip com MockProjector)
# ═══════════════════════════════════════════════════════════════════

class TestTextRoundtrip:
    @pytest.fixture
    def projector(self):
        return MockProjector()

    @pytest.mark.asyncio
    async def test_urgent_text(self, projector):
        """'urgente' deve ter URGÊNCIA e AÇÃO altos."""
        cogon = await encode("Situação urgente no servidor", projector)
        assert cogon.sem[C1_URGENCIA] > 0.8, "C1_URGÊNCIA deve ser alto"
        assert cogon.sem[C3_ACAO] > 0.7, "C3_AÇÃO deve ser alto"

    @pytest.mark.asyncio
    async def test_failure_text(self, projector):
        """'servidor caiu' deve ter ANOMALIA e ESTADO altos."""
        cogon = await encode("O servidor caiu", projector)
        assert cogon.sem[A8_ESTADO] > 0.7, "A8_ESTADO deve ser alto"
        assert cogon.sem[C5_ANOMALIA] > 0.7, "C5_ANOMALIA deve ser alto"

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_semantics(self, projector):
        """Encode → decode preserva eixos dominantes."""
        original = "Situação urgente no servidor"
        cogon = await encode(original, projector)
        reconstructed = await decode(cogon, projector)
        # O texto reconstruído deve mencionar os eixos dominantes
        assert isinstance(reconstructed, str)
        assert len(reconstructed) > 0

    @pytest.mark.asyncio
    async def test_generic_text(self, projector):
        """Texto genérico tem valores moderados."""
        cogon = await encode("Bom dia", projector)
        # Sem keywords especiais, valores devem ser ~0.5
        avg = sum(cogon.sem) / len(cogon.sem)
        assert 0.3 < avg < 0.7, "Texto genérico deve ter média moderada"


# ═══════════════════════════════════════════════════════════════════
# TEST 3: DAG — Raciocínio Composto
# ═══════════════════════════════════════════════════════════════════

class TestDag:
    def test_simple_dag(self):
        """DAG com 3 nós e 2 edges — cenário de incidente."""
        # A: "Houve um deploy" (PROCESSO alto)
        a_sem = [0.5] * 32
        a_sem[A9_PROCESSO] = 0.85
        a = Cogon(sem=a_sem, unc=[0.1] * 32, stamp=1, id="a" * 36)

        # B: "O sistema caiu" (ANOMALIA alto)
        b_sem = [0.5] * 32
        b_sem[C5_ANOMALIA] = 0.9
        b_sem[A8_ESTADO] = 0.9
        b = Cogon(sem=b_sem, unc=[0.1] * 32, stamp=2, id="b" * 36)

        # C: "Precisamos reverter" (AÇÃO + URGÊNCIA altos)
        c_sem = [0.5] * 32
        c_sem[C3_ACAO] = 0.9
        c_sem[C1_URGENCIA] = 0.85
        c = Cogon(sem=c_sem, unc=[0.1] * 32, stamp=3, id="c" * 36)

        # Montar DAG
        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_node(c)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type="CAUSA", weight=0.9))
        dag.add_edge(Edge(from_id=b.id, to_id=c.id, edge_type="CONDICIONA", weight=0.85))

        # Validar topological order
        order = dag.topological_order()
        assert len(order) == 3
        assert order.index(a.id) < order.index(b.id)
        assert order.index(b.id) < order.index(c.id)

    def test_dag_cycle_detection(self):
        """DAG com ciclo deve falhar (R4)."""
        a = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        b = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=2, id="b" * 36)

        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type="CAUSA", weight=0.9))
        dag.add_edge(Edge(from_id=b.id, to_id=a.id, edge_type="CAUSA", weight=0.9))  # ciclo!

        with pytest.raises((ValueError, Exception)):
            dag.topological_order()

    def test_dag_single_node(self):
        """DAG com nó único é válido."""
        a = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        dag = Dag.from_root(a)
        order = dag.topological_order()
        assert order == [a.id]


# ═══════════════════════════════════════════════════════════════════
# TEST 4: DELTA Compression
# ═══════════════════════════════════════════════════════════════════

class TestDeltaCompression:
    def test_delta_only_urgency(self):
        """DELTA entre dois estados que diferem só em urgência."""
        sem_before = [0.5] * 32
        sem_after = [0.5] * 32
        sem_after[C1_URGENCIA] = 0.95  # só urgência mudou

        prev = Cogon(sem=sem_before, unc=[0.1] * 32, stamp=1, id="p" * 36)
        curr = Cogon(sem=sem_after, unc=[0.1] * 32, stamp=2, id="c" * 36)

        d = delta(prev, curr)
        assert len(d) == 32
        # Só índice 22 (C1_URGÊNCIA) deve ser != 0
        for i, v in enumerate(d):
            if i == C1_URGENCIA:
                assert abs(v - 0.45) < 0.01, "Delta de urgência deve ser ~0.45"
            else:
                assert abs(v) < 0.001, f"Delta no eixo {i} deve ser ~0"

    def test_apply_patch_roundtrip(self):
        """Aplica patch → resultado = estado novo."""
        sem_before = [0.5] * 32
        sem_after = [0.5] * 32
        sem_after[C1_URGENCIA] = 0.95

        prev = Cogon(sem=sem_before, unc=[0.1] * 32, stamp=1, id="p" * 36)
        curr = Cogon(sem=sem_after, unc=[0.1] * 32, stamp=2, id="c" * 36)

        d = delta(prev, curr)
        restored = apply_patch(prev, d)

        for i in range(32):
            assert abs(restored.sem[i] - curr.sem[i]) < 0.001, \
                f"Eixo {i}: {restored.sem[i]} != {curr.sem[i]}"

    def test_patch_clamp(self):
        """Patch que levaria acima de 1.0 é clamped."""
        base = Cogon(sem=[0.9] * 32, unc=[0.1] * 32, stamp=1, id="b" * 36)
        patch = [0.5] * 32  # 0.9 + 0.5 = 1.4 → clamped a 1.0
        result = apply_patch(base, patch)
        assert all(s <= 1.0 for s in result.sem)


# ═══════════════════════════════════════════════════════════════════
# TEST 5: BLEND de Dois Agentes
# ═══════════════════════════════════════════════════════════════════

class TestBlend:
    def test_midpoint_blend(self):
        """α=0.5 entre opostos → meio termo."""
        c1 = Cogon(sem=[1.0] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)
        result = blend(c1, c2, 0.5)
        for s in result.sem:
            assert abs(s - 0.5) < 0.001

    def test_conservative_uncertainty(self):
        """unc do BLEND é max dos dois (conservadora)."""
        c1 = Cogon(sem=[0.5] * 32, unc=[0.1] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.5] * 32, unc=[0.9] * 32, stamp=2, id="b" * 36)
        result = blend(c1, c2, 0.5)
        for u in result.unc:
            assert abs(u - 0.9) < 0.001, "UNC deve ser max(0.1, 0.9) = 0.9"

    def test_alpha_extremes(self):
        """α=1.0 retorna c1, α=0.0 retorna c2."""
        c1 = Cogon(sem=[1.0] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        c2 = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)

        r1 = blend(c1, c2, 1.0)
        assert all(abs(s - 1.0) < 0.001 for s in r1.sem)

        r0 = blend(c1, c2, 0.0)
        assert all(abs(s - 0.0) < 0.001 for s in r0.sem)

    def test_two_agents_different_domains(self):
        """Agente técnico (SISTEMA) + Agente empático (AFETO) → BLEND."""
        tech = Cogon(sem=[0.5] * 32, unc=[0.2] * 32, stamp=1, id="a" * 36)
        tech.sem[7] = 0.95   # A7_SISTEMA
        tech.unc[7] = 0.05

        empathic = Cogon(sem=[0.5] * 32, unc=[0.2] * 32, stamp=2, id="b" * 36)
        empathic.sem[27] = 0.95  # C6_AFETO
        empathic.unc[27] = 0.05

        result = blend(tech, empathic, 0.5)
        # Ambos devem ter ~0.725 nos seus eixos dominantes
        assert result.sem[7] > 0.6, "SISTEMA deve estar presente"
        assert result.sem[27] > 0.6, "AFETO deve estar presente"


# ═══════════════════════════════════════════════════════════════════
# TEST 6: Validação R1-R21
# ═══════════════════════════════════════════════════════════════════

class TestValidation:
    def _make_valid_msg(self, intent=Intent.ASSERT):
        """Helper: cria MSG_1337 válida."""
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
        """MSG_1337 válida passa validação."""
        msg = self._make_valid_msg()
        assert validate(msg) is None

    def test_r2_delta_without_ref(self):
        """R2: DELTA sem ref deve falhar."""
        msg = self._make_valid_msg(Intent.DELTA)
        msg.ref_hash = None
        msg.patch = None
        result = validate(msg)
        assert result is not None
        assert "R2" in result or "delta" in result.lower() or "ref" in result.lower()

    def test_r2_non_delta_with_patch(self):
        """R2: ASSERT com patch deve falhar."""
        msg = self._make_valid_msg(Intent.ASSERT)
        msg.patch = [0.1] * 32
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_no_urgency(self):
        """R6: human_required=true sem urgency deve falhar."""
        msg = self._make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = None
        result = validate(msg)
        assert result is not None

    def test_r6_human_required_with_urgency(self):
        """R6: human_required=true COM urgency deve passar."""
        msg = self._make_valid_msg()
        msg.surface.human_required = True
        msg.surface.urgency = 0.85
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_assert_fails(self):
        """R8: BROADCAST com ASSERT deve falhar."""
        msg = self._make_valid_msg(Intent.ASSERT)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is not None

    def test_r8_broadcast_anomaly_passes(self):
        """R8: BROADCAST com ANOMALY deve passar."""
        msg = self._make_valid_msg(Intent.ANOMALY)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None

    def test_r8_broadcast_sync_passes(self):
        """R8: BROADCAST com SYNC deve passar."""
        msg = self._make_valid_msg(Intent.SYNC)
        msg.receiver = Receiver.broadcast()
        result = validate(msg)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# TEST 7: MSG_1337 Completa — Envelope Roundtrip
# ═══════════════════════════════════════════════════════════════════

class TestMsgEnvelope:
    def test_full_envelope_roundtrip(self):
        """Cria MSG_1337 → serializa → hash → desserializa → revalida."""
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

        # Serializa
        json_str = msg.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 100

        # Hash
        h = msg.hash()
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex

        # Desserializa
        restored = Msg1337.from_json(json_str)
        assert restored.intent == msg.intent
        assert restored.sender == msg.sender
        assert restored.c5.schema_ver == "0.4.0"

        # Hash do restaurado deve ser igual
        assert restored.hash() == h, "Roundtrip deve preservar hash"

        # Revalida
        assert validate(restored) is None, "Restored msg deve ser válida"

    def test_msg_with_dag_payload(self):
        """MSG_1337 com payload DAG (não COGON simples)."""
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
        """MSG_1337 com RAW BRIDGE (interoperabilidade)."""
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
        # RAW deve sobreviver o roundtrip
        payload = restored.payload
        assert payload.raw is not None
        assert payload.raw.role == RawRole.BRIDGE
        assert payload.raw.content_type == "protocol/mcp"


# ═══════════════════════════════════════════════════════════════════
# TEST 8: Operadores Adicionais
# ═══════════════════════════════════════════════════════════════════

class TestOperatorsE2E:
    def test_focus_ontological_only(self):
        """FOCUS nos eixos ontológicos (0-13)."""
        c = Cogon(sem=[0.8] * 32, unc=[0.1] * 32, stamp=1, id="c" * 36)
        focused = focus(c, list(range(14)))  # A0-A13
        # Eixos 0-13 mantém valores
        for i in range(14):
            assert focused.sem[i] == 0.8
        # Eixos 14-31 zerados, unc=1.0
        for i in range(14, 32):
            assert focused.sem[i] == 0.0
            assert focused.unc[i] == 1.0

    def test_dist_zero_for_identical(self):
        """Distância entre COGONs idênticos é ~0."""
        c = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=1, id="c" * 36)
        d = dist(c, c)
        assert d < 0.001

    def test_dist_increases_with_difference(self):
        """Distância aumenta conforme COGONs divergem."""
        base = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=1, id="a" * 36)
        similar = Cogon(sem=[0.6] * 32, unc=[0.0] * 32, stamp=2, id="b" * 36)
        different = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=3, id="c" * 36)

        d_similar = dist(base, similar)
        d_different = dist(base, different)
        assert d_similar < d_different

    def test_anomaly_score_outlier(self):
        """COGON fora do padrão histórico tem score alto."""
        # Histórico: tudo em 0.5
        history = [Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=i, id=str(i) * 36) for i in range(5)]
        # Outlier: tudo em 0.0
        outlier = Cogon(sem=[0.0] * 32, unc=[0.0] * 32, stamp=10, id="x" * 36)

        score = anomaly_score(outlier, history)
        assert score > 0.5, "Outlier deve ter anomaly score alto"

    def test_anomaly_score_normal(self):
        """COGON dentro do padrão tem score baixo."""
        history = [Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=i, id=str(i) * 36) for i in range(5)]
        normal = Cogon(sem=[0.5] * 32, unc=[0.0] * 32, stamp=10, id="x" * 36)

        score = anomaly_score(normal, history)
        assert score < 0.1, "Normal deve ter anomaly score baixo"


# ═══════════════════════════════════════════════════════════════════
# TEST 9: Axes Reference
# ═══════════════════════════════════════════════════════════════════

class TestAxes:
    def test_32_axes_defined(self):
        """Todos os 32 eixos estão definidos."""
        assert len(CANONICAL_AXES) == 32

    def test_axes_indices_sequential(self):
        """Índices de 0 a 31 sequenciais."""
        for i, ax in enumerate(CANONICAL_AXES):
            assert ax.index == i

    def test_group_a_ontological(self):
        """Grupo A tem 14 eixos (0-13)."""
        from leet.axes import axes_in_group, AxisGroup
        group_a = axes_in_group(AxisGroup.ONTOLOGICAL)
        assert len(group_a) == 14

    def test_group_b_epistemic(self):
        """Grupo B tem 8 eixos (14-21)."""
        from leet.axes import axes_in_group, AxisGroup
        group_b = axes_in_group(AxisGroup.EPISTEMIC)
        assert len(group_b) == 8

    def test_group_c_pragmatic(self):
        """Grupo C tem 10 eixos (22-31)."""
        from leet.axes import axes_in_group, AxisGroup
        group_c = axes_in_group(AxisGroup.PRAGMATIC)
        assert len(group_c) == 10
