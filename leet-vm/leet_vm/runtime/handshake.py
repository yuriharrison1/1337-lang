import hashlib
from leet_vm.types import Cogon, DAG, Edge

# 5 anchor COGONs — immutable per spec
def _make_sem(overrides: dict[int, float]) -> list[float]:
    base = [0.5] * 32
    for idx, val in overrides.items():
        base[idx] = val
    return base

ANCORA_1_PRESENCA  = Cogon(sem=_make_sem({0: 1.0, 2: 0.0}), unc=[0.1]*32, id="ancora-1")
ANCORA_2_AUSENCIA  = Cogon(sem=_make_sem({0: 0.0, 1: 0.0, 2: 0.0}), unc=[0.1]*32, id="ancora-2")
ANCORA_3_MUDANCA   = Cogon(sem=_make_sem({2: 1.0}), unc=[0.2]*32, id="ancora-3")
ANCORA_4_AGENCIA   = Cogon(sem=_make_sem({0: 0.8, 2: 0.7}), unc=[0.2]*32, id="ancora-4")
ANCORA_5_INCERTEZA = Cogon(sem=[0.5]*32, unc=[0.8]*32, id="ancora-5")

ANCHORS = [
    ANCORA_1_PRESENCA,
    ANCORA_2_AUSENCIA,
    ANCORA_3_MUDANCA,
    ANCORA_4_AGENCIA,
    ANCORA_5_INCERTEZA,
]

def build_anchor_dag() -> DAG:
    """Returns a DAG of 5 anchor COGONs for C5 handshake (intent=SYNC)."""
    edges = [
        Edge(from_id="ancora-1", to_id="ancora-2", type="CONTRADIZ", weight=1.0),
        Edge(from_id="ancora-1", to_id="ancora-3", type="CONDICIONA", weight=0.8),
        Edge(from_id="ancora-3", to_id="ancora-4", type="REFINA", weight=0.7),
        Edge(from_id="ancora-5", to_id="ancora-1", type="EMERGE", weight=0.5),
    ]
    return DAG(root="ancora-1", nodes=list(ANCHORS), edges=edges)

def align_hash(agent_id: str) -> str:
    """
    Returns SHA256-based alignment hash for the given agent_id.
    Scaffolding: full matrix computation is future work.
    Returns deterministic hash of agent_id + protocol version.
    """
    data = (agent_id + "v0.4").encode()
    return hashlib.sha256(data).hexdigest()
