# PROMPT 03 — leet-vm

Build a Python package called `leet-vm` that orchestrates the 1337 VM layer:
protocol adapters, semantic projector, runtime router, PersonalStore, and Surface C4.
This package is used internally by `leet-py` — users never import it directly.

## Package structure to create

```
leet-vm/
├── pyproject.toml
├── leet_vm/
│   ├── __init__.py
│   ├── vm.py               ← LeetVM main orchestrator
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py         ← AdapterFrame + Adapter protocol
│   │   ├── text.py         ← plain text (default)
│   │   ├── json_rpc.py     ← JSON-RPC 2.0
│   │   ├── mcp.py          ← MCP tool call/result
│   │   ├── rest.py         ← generic REST/JSON
│   │   └── registry.py     ← auto-detect protocol
│   ├── projector/
│   │   ├── __init__.py
│   │   ├── base.py         ← Projector protocol
│   │   ├── service.py      ← calls leet-service via gRPC
│   │   └── local.py        ← calls leet-core PyO3 directly (offline)
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── router.py       ← routes COGONs to agents
│   │   ├── surface.py      ← Surface C4: COGON → natural language
│   │   └── handshake.py    ← C5 handshake protocol
│   ├── store/
│   │   ├── __init__.py
│   │   ├── personal.py     ← PersonalStore
│   │   └── session.py      ← SessionDAG + DELTA cache
│   └── types.py            ← Python dataclasses mirroring leet-core types
└── tests/
    ├── test_adapters.py
    ├── test_projector.py
    ├── test_store.py
    └── test_vm.py
```

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "leet-vm"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "grpcio>=1.60",
    "grpcio-tools>=1.60",
    "protobuf>=4.25",
    "numpy>=1.26",
    "redis>=5.0",
    "aiohttp>=3.9",
    "pydantic>=2.5",
    "typing-extensions>=4.9",
]

[project.optional-dependencies]
core = ["leet-core"]   # PyO3 wheel — install separately
```

## leet_vm/types.py

Python dataclasses mirroring the Rust leet-core types:

```python
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
    content: any
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
```

## leet_vm/adapters/base.py

```python
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

@dataclass
class AdapterFrame:
    method:   Optional[str]    # JSON-RPC method, REST endpoint, etc.
    params:   dict             # extracted parameters
    corr_id:  Optional[str]    # request ID for round-trip correlation
    is_error: bool = False
    raw_bytes: Optional[bytes] = None   # original payload preserved

@runtime_checkable
class Adapter(Protocol):
    protocol_id: str

    def decode(self, raw: bytes | str | dict) -> AdapterFrame: ...
    def encode(self, cogon, corr_id: Optional[str] = None) -> bytes: ...
    def detect(self, raw: bytes | str | dict) -> bool: ...
```

## leet_vm/adapters/text.py

Plain text adapter (default). decode: wrap text in AdapterFrame with method=None.
encode: call Surface C4 to reconstruct text from cogon.

## leet_vm/adapters/json_rpc.py

JSON-RPC 2.0 adapter.

decode: parse JSON, extract `method`, `params` (dict or list→dict), `id` as corr_id.
If `error` key present, set is_error=True, put error in params.

encode: build JSON-RPC response `{"jsonrpc":"2.0","result":{...},"id": corr_id}`.
If cogon.raw and cogon.raw.role == "BRIDGE", use cogon.raw.content as result directly.
Otherwise build result from cogon.to_dict().

## leet_vm/adapters/mcp.py

MCP (Model Context Protocol) adapter.

MCP tool call format: `{"type":"tool_use","name":"...","input":{...},"id":"..."}`
MCP tool result format: `{"type":"tool_result","tool_use_id":"...","content":"..."}`

decode: extract name→method, input→params, id→corr_id.
encode: build tool_result with content from cogon raw or sem summary.

## leet_vm/adapters/rest.py

Generic REST/JSON adapter. decode: if dict has "path"/"method"/"body", extract those.
Otherwise treat entire dict as params with method="unknown".

## leet_vm/adapters/registry.py

Auto-detect protocol from payload:

```python
def detect_protocol(raw: bytes | str | dict) -> str:
    """Returns: 'json-rpc' | 'mcp' | 'rest' | 'text'"""
    if isinstance(raw, (bytes, str)):
        try:
            data = json.loads(raw)
        except:
            return 'text'
    else:
        data = raw
    if isinstance(data, dict):
        if 'jsonrpc' in data:             return 'json-rpc'
        if data.get('type') == 'tool_use': return 'mcp'
        if 'path' in data or 'method' in data: return 'rest'
        return 'rest'
    return 'text'
```

## leet_vm/projector/base.py

```python
from typing import Protocol
from leet_vm.types import Cogon

class Projector(Protocol):
    async def project(self, text: str, agent_id: str = "") -> Cogon: ...
    async def decode(self, cogon: Cogon) -> str: ...
```

## leet_vm/projector/service.py

Calls leet-service via gRPC. Uses the generated protobuf stubs.
If gRPC connection fails, falls back to LocalProjector automatically with a warning log.

```python
class ServiceProjector:
    def __init__(self, service_url: str = "localhost:50051"):
        self._url = service_url
        self._channel = None
        self._stub = None

    async def _connect(self):
        import grpc
        # import generated stub
        try:
            from leet_vm._proto import leet_pb2_grpc, leet_pb2
            self._channel = grpc.aio.insecure_channel(self._url)
            self._stub = leet_pb2_grpc.LeetServiceStub(self._channel)
        except Exception as e:
            raise ConnectionError(f"leet-service unavailable at {self._url}: {e}")

    async def project(self, text: str, agent_id: str = "") -> Cogon:
        if not self._stub:
            await self._connect()
        req = leet_pb2.EncodeRequest(text=text, agent_id=agent_id)
        resp = await self._stub.Encode(req)
        return Cogon(
            id=resp.cogon_id,
            sem=list(resp.sem),
            unc=list(resp.unc),
            stamp=resp.stamp,
        )

    async def decode(self, cogon: Cogon) -> str:
        if not self._stub:
            await self._connect()
        req = leet_pb2.DecodeRequest(sem=cogon.sem, unc=cogon.unc)
        resp = await self._stub.Decode(req)
        return resp.text
```

## leet_vm/projector/local.py

Offline projector — no network, no leet-service needed. Two modes:

**Mock mode** (default): deterministic projection using text hash.
Uses SHA256 of text, expands to 32 floats by cycling bytes, normalizes to [0,1].
unc is estimated as distance from 0.5 (less extreme = more uncertain).

**PyO3 mode**: tries `import leet_core` and calls the Rust projection directly.
Falls back to mock if leet_core not installed.

```python
import hashlib, struct

class LocalProjector:
    def __init__(self, mode: str = "auto"):
        # mode: "mock" | "pyO3" | "auto" (tries pyO3, falls back to mock)
        self._mode = mode
        self._core = None
        if mode in ("pyO3", "auto"):
            try:
                import leet_core
                self._core = leet_core
                self._mode = "pyO3"
            except ImportError:
                self._mode = "mock"

    async def project(self, text: str, agent_id: str = "") -> Cogon:
        if self._mode == "pyO3" and self._core:
            return self._project_core(text)
        return self._project_mock(text)

    def _project_mock(self, text: str) -> Cogon:
        h = hashlib.sha256(text.encode()).digest()
        # expand 32 bytes to 32 floats by cycling
        sem = []
        for i in range(32):
            b1 = h[i % 32]
            b2 = h[(i + 1) % 32]
            val = ((b1 << 8 | b2) & 0xFFFF) / 65535.0
            sem.append(val)
        unc = [1.0 - abs(s - 0.5) * 2.0 for s in sem]
        return Cogon(sem=sem, unc=unc)

    def _project_core(self, text: str) -> Cogon:
        # call leet_core PyO3 binding
        result = self._core.project_text(text)
        return Cogon(sem=result.sem, unc=result.unc)

    async def decode(self, cogon: Cogon) -> str:
        # reconstruct human-readable summary from sem
        parts = []
        axis_names = AXIS_NAMES
        for i, (name, val, u) in enumerate(zip(axis_names, cogon.sem, cogon.unc)):
            if val > 0.7 and u < 0.5:  # high confidence, meaningful value
                parts.append(f"{name}:{val:.2f}")
        if not parts:
            parts = [f"sem[{i}]:{v:.2f}" for i,v in enumerate(cogon.sem[:8])]
        return " ".join(parts[:8])
```

## leet_vm/store/personal.py

PersonalStore: accumulates COGONs per agent_id. Replaces RAG.

```python
import numpy as np
from typing import Optional
from leet_vm.types import Cogon, AXIS_NAMES

class PersonalStore:
    """
    Stores COGONs per agent. Provides semantic recall via DIST.
    Backend: 'memory' (default) | 'redis://...' | 'sqlite://...'
    """
    def __init__(self, backend: str = "memory"):
        self._backend = backend
        self._data: dict[str, list[dict]] = {}   # agent_id → list of records
        self._redis = None
        if backend.startswith("redis://"):
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(backend)

    async def add(self, agent_id: str, cogon: Cogon,
                  text: Optional[str] = None) -> None:
        record = {
            "cogon_id": cogon.id,
            "sem":      cogon.sem,
            "unc":      cogon.unc,
            "stamp":    cogon.stamp,
            "text":     text,
        }
        if self._redis:
            import json
            await self._redis.rpush(f"leet:store:{agent_id}", json.dumps(record))
        else:
            self._data.setdefault(agent_id, []).append(record)

    async def recall(self, agent_id: str, query: Cogon, k: int = 5) -> list[tuple[dict, float]]:
        """Returns list of (record, dist) sorted by ascending dist (closest first)."""
        records = await self._get_all(agent_id)
        if not records:
            return []
        scored = []
        for r in records:
            d = self._dist(query.sem, query.unc, r["sem"], r["unc"])
            scored.append((r, d))
        scored.sort(key=lambda x: x[1])
        return scored[:k]

    async def delta_context(self, agent_id: str, since_stamp: int) -> list[dict]:
        """Returns records added after since_stamp (DELTA — only what changed)."""
        records = await self._get_all(agent_id)
        return [r for r in records if r["stamp"] > since_stamp]

    async def count(self, agent_id: str) -> int:
        records = await self._get_all(agent_id)
        return len(records)

    async def _get_all(self, agent_id: str) -> list[dict]:
        if self._redis:
            import json
            raw = await self._redis.lrange(f"leet:store:{agent_id}", 0, -1)
            return [json.loads(r) for r in raw]
        return self._data.get(agent_id, [])

    def _dist(self, sem1: list, unc1: list, sem2: list, unc2: list) -> float:
        """Weighted cosine distance. Uncertain dims contribute less."""
        s1 = np.array(sem1, dtype=np.float32)
        s2 = np.array(sem2, dtype=np.float32)
        u1 = np.array(unc1, dtype=np.float32)
        u2 = np.array(unc2, dtype=np.float32)
        w  = (1 - u1) * (1 - u2)
        dot  = float(np.sum(s1 * s2 * w))
        n1   = float(np.sqrt(np.sum(s1**2 * w)) + 1e-8)
        n2   = float(np.sqrt(np.sum(s2**2 * w)) + 1e-8)
        sim  = dot / (n1 * n2)
        return 1.0 - sim
```

## leet_vm/store/session.py

```python
import time
from leet_vm.types import Cogon

class SessionDAG:
    """Tracks the current session's COGONs for DELTA compression."""
    def __init__(self, session_id: str):
        self.session_id   = session_id
        self.start_stamp  = time.time_ns()
        self._cogons: list[Cogon] = []

    def add(self, cogon: Cogon) -> None:
        self._cogons.append(cogon)

    def delta_since(self, stamp: int) -> list[Cogon]:
        return [c for c in self._cogons if c.stamp > stamp]

    def last_stamp(self) -> int:
        if not self._cogons:
            return self.start_stamp
        return self._cogons[-1].stamp

    def count(self) -> int:
        return len(self._cogons)
```

## leet_vm/runtime/surface.py

Surface C4: COGON → natural language. Deterministic, not generative.

```python
from leet_vm.types import Cogon, AXIS_NAMES

class SurfaceC4:
    def reconstruct(self, cogon: Cogon, depth: int = 3) -> str:
        """
        Reconstruct human-readable text from a COGON.
        depth: how many axes to include in summary.
        """
        if cogon.raw and hasattr(cogon.raw, 'content'):
            # if raw contains original text, return it directly
            if isinstance(cogon.raw.content, str):
                return cogon.raw.content
            if isinstance(cogon.raw.content, dict):
                return str(cogon.raw.content)

        # build from sem values — report most confident, most extreme dims
        axes = list(zip(AXIS_NAMES, cogon.sem, cogon.unc))
        # sort by confidence (low unc) and extremity (far from 0.5)
        axes_scored = [(name, val, unc, (1-unc) * abs(val - 0.5) * 2)
                       for name, val, unc in axes]
        axes_scored.sort(key=lambda x: x[3], reverse=True)

        parts = []
        for name, val, unc, _ in axes_scored[:depth]:
            level = "alto" if val > 0.6 else ("baixo" if val < 0.4 else "médio")
            conf  = "alta certeza" if unc < 0.3 else ("incerto" if unc > 0.7 else "")
            desc  = f"{name}={level}"
            if conf:
                desc += f" ({conf})"
            parts.append(desc)

        return "[COGON: " + ", ".join(parts) + "]"
```

## leet_vm/runtime/router.py

```python
from typing import Callable, Optional
from leet_vm.types import Cogon, VMResult

class Router:
    def __init__(self):
        self._agents: dict[str, Callable] = {}
        self._default: Optional[Callable] = None

    def register(self, agent_id: str, handler: Callable) -> None:
        self._agents[agent_id] = handler

    def set_default(self, handler: Callable) -> None:
        self._default = handler

    async def route(self, cogon: Cogon, context: list,
                    target_agent: str = "") -> Cogon:
        handler = self._agents.get(target_agent) or self._default
        if not handler:
            raise ValueError(f"No agent registered for '{target_agent}' and no default")
        return await handler(cogon, context)
```

## leet_vm/runtime/handshake.py

C5 handshake — aligns two agents on the same semantic space.

5 anchor COGONs (hardcoded, immutable per spec):
- ANCORA_1 presenca:  sem = [1,0,0.5,0.5,...] (via=1, vibracao=0, ...)
- ANCORA_2 ausencia:  sem = [0,0,0,0.5,...]
- ANCORA_3 mudanca:   sem = [0.5,0.5,1,0.5,...]
- ANCORA_4 agencia:   sem = [0.8,0.5,0.7,0.5,...]
- ANCORA_5 incerteza: sem all 0.5, unc all 0.8

Handshake:
1. Agent A sends DAG of 5 anchor COGONs (intent=SYNC)
2. Agent B maps them to its internal space
3. Compute alignment matrix M (simple linear mapping)
4. Return align_hash = SHA256(M as bytes)

Implement as `align_hash(agent_id: str) -> str` that returns the hash.
For now: return SHA256 of agent_id + "v0.4" as stable deterministic hash.
This is the scaffolding — full matrix computation is future work.

## leet_vm/vm.py — main orchestrator

```python
import time
import uuid
from typing import Optional, Callable
from leet_vm.types import Cogon, VMResult, RawField
from leet_vm.adapters.registry import detect_protocol, ADAPTERS
from leet_vm.projector.service import ServiceProjector
from leet_vm.projector.local import LocalProjector
from leet_vm.store.personal import PersonalStore
from leet_vm.store.session import SessionDAG
from leet_vm.runtime.router import Router
from leet_vm.runtime.surface import SurfaceC4

class LeetVM:
    def __init__(self,
                 mode: str = "auto",           # "auto"|"service"|"local"
                 service_url: str = "localhost:50051",
                 store_backend: str = "memory"):
        self._mode = mode
        self._service_url = service_url
        self._projector = None
        self._store = PersonalStore(store_backend)
        self._router = Router()
        self._surface = SurfaceC4()
        self._sessions: dict[str, SessionDAG] = {}

    async def _get_projector(self):
        if self._projector:
            return self._projector
        if self._mode == "local":
            self._projector = LocalProjector()
        elif self._mode == "service":
            self._projector = ServiceProjector(self._service_url)
        else:  # auto
            try:
                p = ServiceProjector(self._service_url)
                await p.project("test", "")   # probe
                self._projector = p
            except Exception:
                self._projector = LocalProjector()
        return self._projector

    def register_agent(self, agent_id: str, handler: Callable) -> None:
        self._router.register(agent_id, handler)

    def set_default_agent(self, handler: Callable) -> None:
        self._router.set_default(handler)

    async def process(self, input,
                      agent_id: str    = "default",
                      session_id: str  = "",
                      protocol: str    = "auto",
                      target_agent: str = "") -> VMResult:

        # 1. detect + decode protocol
        if protocol == "auto":
            protocol = detect_protocol(input)
        adapter = ADAPTERS[protocol]
        frame   = adapter.decode(input)

        # 2. project → COGON
        proj  = await self._get_projector()
        cogon = await proj.project(
            f"{frame.method or ''} {frame.params}",
            agent_id
        )
        # preserve raw payload as BRIDGE
        cogon.raw = RawField(
            type=f"protocol/{protocol}",
            content=frame.params,
            role="BRIDGE"
        )

        # 3. recall context from PersonalStore
        context_records = await self._store.recall(agent_id, cogon, k=5)
        context_cogons  = [Cogon(sem=r["sem"], unc=r["unc"],
                                 id=r["cogon_id"], stamp=r["stamp"])
                           for r, _ in context_records]

        # 4. DELTA: only what changed since last session
        session = self._sessions.setdefault(session_id, SessionDAG(session_id))
        delta_cogons = session.delta_since(session.start_stamp) if session.count() > 0 else []

        # 5. route to agent
        context_all = context_cogons + delta_cogons
        result_cogon = await self._router.route(cogon, context_all, target_agent)

        # 6. persist
        text_hint = frame.params.get("text") or str(frame.params)[:200]
        await self._store.add(agent_id, cogon, text=text_hint)
        await self._store.add(agent_id, result_cogon)
        session.add(cogon)
        session.add(result_cogon)

        # 7. Surface C4
        text = self._surface.reconstruct(result_cogon)
        tokens_saved = max(0, len(text_hint) // 4 - 32 * 2 // 100)

        return VMResult(
            text=text,
            cogon=result_cogon,
            tokens_saved=tokens_saved,
            session_id=session_id,
        )
```

## leet_vm/adapters/__init__.py

Register all adapters in a dict for the registry:

```python
from leet_vm.adapters.text     import TextAdapter
from leet_vm.adapters.json_rpc import JsonRpcAdapter
from leet_vm.adapters.mcp      import McpAdapter
from leet_vm.adapters.rest     import RestAdapter

ADAPTERS = {
    "text":     TextAdapter(),
    "json-rpc": JsonRpcAdapter(),
    "mcp":      McpAdapter(),
    "rest":     RestAdapter(),
}
```

## Tests

**test_adapters.py**: test each adapter's decode/encode round-trip.
JSON-RPC: decode `{"jsonrpc":"2.0","method":"analyze","params":{"x":1},"id":"r1"}`,
verify method="analyze", corr_id="r1".

**test_projector.py**: LocalProjector mock mode.
project("hello world") returns Cogon with len(sem)==32, all in [0,1].
Same text → same sem (deterministic).

**test_store.py**: add 5 cogons, recall top-3. Verify result has ≤3 items.
Verify dist is sorted ascending.

**test_vm.py**: full integration.
Register a mock agent that echoes the input cogon.
Call vm.process("hello", agent_id="test").
Verify VMResult has text, cogon, tokens_saved >= 0.

## Install and test

```bash
cd leet-vm
pip install -e ".[core]"
python -m pytest tests/ -v
```
