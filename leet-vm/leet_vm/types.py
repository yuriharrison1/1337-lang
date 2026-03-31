from dataclasses import dataclass, field
from typing import Optional
import time, uuid

AXIS_NAMES = [
    # Group A — Ontological (0-13)
    "via", "correspondencia", "vibracao", "polaridade", "ritmo",
    "causa_efeito", "genero", "sistema", "estado", "processo",
    "relacao", "sinal", "estabilidade", "valencia_ontologica",
    # Group B — Epistemic (14-21)
    "verificabilidade", "temporalidade", "completude", "causalidade",
    "reversibilidade", "carga", "origem", "valencia_epistemica",
    # Group C — Pragmatic (22-31)
    "urgencia", "impacto", "acao", "valor", "anomalia", "afeto",
    "dependencia", "vetor_temporal", "natureza", "valencia_acao",
]

@dataclass
class RawField:
    type:    str                   # MIME or enum string
    content: object
    role:    str                   # EVIDENCE | ARTIFACT | TRACE | BRIDGE

@dataclass
class Cogon:
    sem:   list[float]             # 32 floats [0,1]
    unc:   list[float]             # 32 floats [0,1]
    id:    str = field(default_factory=lambda: str(uuid.uuid4()))
    stamp: int = field(default_factory=lambda: time.time_ns())
    raw:   Optional[RawField] = None

    def to_dict(self) -> dict:
        return {"id": self.id, "sem": self.sem, "unc": self.unc,
                "stamp": self.stamp}

@dataclass
class Edge:
    from_id: str
    to_id:   str
    type:    str    # CAUSA | CONDICIONA | CONTRADIZ | REFINA | EMERGE
    weight:  float

@dataclass
class DAG:
    root:  str
    nodes: list[Cogon]
    edges: list[Edge]

@dataclass
class VMResult:
    text:         str
    cogon:        Cogon
    tokens_saved: int = 0
    session_id:   str = ""
