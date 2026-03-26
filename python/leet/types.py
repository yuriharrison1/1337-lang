"""Types for 1337 — mirroring Rust structures."""

from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

# Payload é Union[Cogon, Dag] — definido para type hints
Payload = Union['Cogon', 'Dag']

FIXED_DIMS = 32


class RawRole(Enum):
    EVIDENCE = "EVIDENCE"
    ARTIFACT = "ARTIFACT"
    TRACE = "TRACE"
    BRIDGE = "BRIDGE"


class EdgeType(Enum):
    CAUSA = "CAUSA"
    CONDICIONA = "CONDICIONA"
    CONTRADIZ = "CONTRADIZ"
    REFINA = "REFINA"
    EMERGE = "EMERGE"


class Intent(Enum):
    ASSERT = "ASSERT"
    QUERY = "QUERY"
    DELTA = "DELTA"
    SYNC = "SYNC"
    ANOMALY = "ANOMALY"
    ACK = "ACK"


@dataclass
class Raw:
    content_type: str
    content: Any
    role: RawRole

    def to_dict(self) -> dict:
        return {
            "content_type": self.content_type,
            "content": self.content,
            "role": self.role.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Raw:
        return cls(
            content_type=d["content_type"],
            content=d["content"],
            role=RawRole(d["role"]),
        )


@dataclass
class Cogon:
    id: str
    sem: list[float]
    unc: list[float]
    stamp: int
    raw: Optional[Raw] = None

    def __post_init__(self):
        if len(self.sem) != FIXED_DIMS:
            raise ValueError(f"sem must have {FIXED_DIMS} dimensions, got {len(self.sem)}")
        if len(self.unc) != FIXED_DIMS:
            raise ValueError(f"unc must have {FIXED_DIMS} dimensions, got {len(self.unc)}")

    @classmethod
    def new(cls, sem: list[float], unc: list[float]) -> Cogon:
        """Create a new COGON with auto-generated UUID and timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            sem=sem,
            unc=unc,
            stamp=int(datetime.now().timestamp() * 1e9),  # nanoseconds
        )

    @classmethod
    def zero(cls) -> Cogon:
        """COGON_ZERO — 'I AM' — primordial utterance."""
        return cls(
            id="00000000-0000-0000-0000-000000000000",
            sem=[1.0] * FIXED_DIMS,
            unc=[0.0] * FIXED_DIMS,
            stamp=0,
        )

    def is_zero(self) -> bool:
        """Returns True if this is COGON_ZERO."""
        return self.id == "00000000-0000-0000-0000-000000000000" and self.stamp == 0

    def low_confidence_dims(self) -> list[int]:
        """Returns indices where unc > 0.9 (R5)."""
        return [i for i, u in enumerate(self.unc) if u > 0.9]

    def with_raw(self, raw: Raw) -> Cogon:
        """Returns a copy with RAW field set."""
        return Cogon(
            id=self.id,
            sem=self.sem.copy(),
            unc=self.unc.copy(),
            stamp=self.stamp,
            raw=raw,
        )

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "sem": self.sem,
            "unc": self.unc,
            "stamp": self.stamp,
        }
        if self.raw is not None:
            d["raw"] = self.raw.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Cogon:
        raw = None
        if "raw" in d and d["raw"] is not None:
            raw = Raw.from_dict(d["raw"])
        return cls(
            id=d["id"],
            sem=d["sem"],
            unc=d["unc"],
            stamp=d["stamp"],
            raw=raw,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> Cogon:
        return cls.from_dict(json.loads(json_str))


@dataclass
class Edge:
    from_id: str
    to_id: str
    edge_type: Union[EdgeType, str]
    weight: float

    def __post_init__(self):
        if isinstance(self.edge_type, str):
            self.edge_type = EdgeType(self.edge_type)

    def to_dict(self) -> dict:
        et = self.edge_type.value if isinstance(self.edge_type, EdgeType) else self.edge_type
        return {
            "from": self.from_id,
            "to": self.to_id,
            "type": et,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Edge:
        return cls(
            from_id=d["from"],
            to_id=d["to"],
            edge_type=d["type"],
            weight=d["weight"],
        )


@dataclass
class Dag:
    root: str
    nodes: list[Cogon] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    @classmethod
    def from_root(cls, cogon: Cogon) -> Dag:
        return cls(root=cogon.id, nodes=[cogon])

    def add_node(self, cogon: Cogon):
        self.nodes.append(cogon)

    def add_edge(self, edge: Edge):
        self.edges.append(edge)

    def node_ids(self) -> list[str]:
        return [n.id for n in self.nodes]

    def parents_of(self, node_id: str) -> list[str]:
        """Returns IDs of parent nodes (nodes with edges TO node_id)."""
        return [e.from_id for e in self.edges if e.to_id == node_id]

    def topological_order(self) -> list[str]:
        """Returns nodes in topological order. Raises ValueError if cycle detected (R4)."""
        # Kahn's algorithm
        in_degree = {n.id: 0 for n in self.nodes}
        adj = {n.id: [] for n in self.nodes}
        
        for edge in self.edges:
            adj[edge.from_id].append(edge.to_id)
            in_degree[edge.to_id] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in DAG (R4 violation)")

        return result

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Dag:
        return cls(
            root=d["root"],
            nodes=[Cogon.from_dict(n) for n in d["nodes"]],
            edges=[Edge.from_dict(e) for e in d["edges"]],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> Dag:
        return cls.from_dict(json.loads(json_str))


@dataclass
class Receiver:
    agent_id: Optional[str] = None

    @classmethod
    def broadcast(cls) -> Receiver:
        return cls(agent_id=None)

    def is_broadcast(self) -> bool:
        return self.agent_id is None

    def to_dict(self) -> Optional[str]:
        return self.agent_id

    @classmethod
    def from_dict(cls, d: Optional[str]) -> Receiver:
        return cls(agent_id=d)


@dataclass
class CanonicalSpace:
    zone_fixed: list[float]
    zone_emergent: dict[str, float]
    schema_ver: str
    align_hash: str

    def __post_init__(self):
        if len(self.zone_fixed) != FIXED_DIMS:
            raise ValueError(f"zone_fixed must have {FIXED_DIMS} dimensions")

    def to_dict(self) -> dict:
        return {
            "zone_fixed": self.zone_fixed,
            "zone_emergent": self.zone_emergent,
            "schema_ver": self.schema_ver,
            "align_hash": self.align_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CanonicalSpace:
        return cls(
            zone_fixed=d["zone_fixed"],
            zone_emergent=d.get("zone_emergent", {}),
            schema_ver=d["schema_ver"],
            align_hash=d["align_hash"],
        )


@dataclass
class Surface:
    human_required: bool
    urgency: Optional[float]
    reconstruct_depth: int
    lang: str

    def to_dict(self) -> dict:
        d = {
            "human_required": self.human_required,
            "reconstruct_depth": self.reconstruct_depth,
            "lang": self.lang,
        }
        if self.urgency is not None:
            d["urgency"] = self.urgency
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Surface:
        return cls(
            human_required=d["human_required"],
            urgency=d.get("urgency"),
            reconstruct_depth=d["reconstruct_depth"],
            lang=d["lang"],
        )


@dataclass
class Msg1337:
    id: str
    sender: str
    receiver: Receiver
    intent: Union[Intent, str]
    payload: Union[Cogon, Dag]
    c5: CanonicalSpace
    surface: Surface
    ref_hash: Optional[str] = None
    patch: Optional[list[float]] = None

    def __post_init__(self):
        if isinstance(self.intent, str):
            self.intent = Intent(self.intent)

    def hash(self) -> str:
        """SHA256 hash of canonical JSON serialization."""
        # Sort keys for deterministic output
        json_str = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver.to_dict(),
            "intent": self.intent.value if isinstance(self.intent, Intent) else self.intent,
            "payload": self.payload.to_dict(),
            "c5": self.c5.to_dict(),
            "surface": self.surface.to_dict(),
        }
        if self.ref_hash is not None:
            d["ref"] = self.ref_hash
        if self.patch is not None:
            d["patch"] = self.patch
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Msg1337:
        # Determine payload type
        payload_dict = d["payload"]
        if "root" in payload_dict:
            payload = Dag.from_dict(payload_dict)
        else:
            payload = Cogon.from_dict(payload_dict)

        return cls(
            id=d["id"],
            sender=d["sender"],
            receiver=Receiver.from_dict(d["receiver"]),
            intent=d["intent"],
            payload=payload,
            ref_hash=d.get("ref"),
            patch=d.get("patch"),
            c5=CanonicalSpace.from_dict(d["c5"]),
            surface=Surface.from_dict(d["surface"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> Msg1337:
        return cls.from_dict(json.loads(json_str))
