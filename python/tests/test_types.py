"""Tests for leet.types module."""

import pytest
from leet import (
    Cogon, Edge, Dag, Msg1337, Raw, RawRole, Intent, Receiver, 
    Surface, CanonicalSpace, EdgeType
)


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


class TestCogonCreation:
    def test_cogon_creation(self):
        """Cogon creation with 32 dims."""
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        assert len(cogon.sem) == 32
        assert len(cogon.unc) == 32
        assert not cogon.is_zero()
        assert cogon.stamp > 0

    def test_cogon_to_json_roundtrip(self):
        """Serializa → desserializa = igual."""
        cogon = Cogon.new(sem=[0.7] * 32, unc=[0.2] * 32)
        json_str = cogon.to_json()
        restored = Cogon.from_json(json_str)
        assert restored.sem == cogon.sem
        assert restored.unc == cogon.unc
        assert restored.id == cogon.id


class TestDag:
    def test_dag_from_root(self):
        """DAG com 1 nó."""
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        dag = Dag.from_root(cogon)
        assert dag.root == cogon.id
        assert len(dag.nodes) == 1
        assert len(dag.edges) == 0

    def test_dag_topological_order(self):
        """Ordem topológica correta."""
        a = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        b = Cogon.new(sem=[0.6] * 32, unc=[0.1] * 32)
        
        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type=EdgeType.CAUSA, weight=0.9))
        
        order = dag.topological_order()
        assert len(order) == 2
        assert order.index(a.id) < order.index(b.id)

    def test_dag_cycle_detection(self):
        """Levanta ValueError se ciclo (R4)."""
        a = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        b = Cogon.new(sem=[0.6] * 32, unc=[0.1] * 32)
        
        dag = Dag.from_root(a)
        dag.add_node(b)
        dag.add_edge(Edge(from_id=a.id, to_id=b.id, edge_type=EdgeType.CAUSA, weight=0.9))
        dag.add_edge(Edge(from_id=b.id, to_id=a.id, edge_type=EdgeType.CAUSA, weight=0.9))  # ciclo!
        
        with pytest.raises(ValueError):
            dag.topological_order()

    def test_dag_single_node(self):
        """DAG com nó único é válido."""
        a = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
        dag = Dag.from_root(a)
        order = dag.topological_order()
        assert order == [a.id]


class TestEdgeTypes:
    def test_all_edge_types(self):
        """Todos os 5 tipos de edge."""
        types = [EdgeType.CAUSA, EdgeType.CONDICIONA, EdgeType.CONTRADIZ, 
                 EdgeType.REFINA, EdgeType.EMERGE]
        assert len(types) == 5


class TestMsgCreation:
    def test_msg_creation(self):
        """Envelope MSG_1337 completo."""
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
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
                align_hash="abc123",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=3,
                lang="pt",
            ),
        )
        assert msg.intent == Intent.ASSERT
        assert msg.c5.schema_ver == "0.4.0"

    def test_msg_hash(self):
        """Hash determinístico."""
        cogon = Cogon.new(sem=[0.5] * 32, unc=[0.1] * 32)
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
                align_hash="abc123",
            ),
            surface=Surface(
                human_required=False,
                urgency=None,
                reconstruct_depth=3,
                lang="pt",
            ),
        )
        h1 = msg.hash()
        h2 = msg.hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex
