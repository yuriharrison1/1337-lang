# PROMPT 03 — LEET-VM (Python · Adapters · Projector · PersonalStore · Runtime)

Build `leet-vm` — the Python Virtual Machine that connects everything.
It's the glue between external protocols, the semantic engine, and LLM providers.

**PREREQUISITES**: PROMPT_01 + PROMPT_02 completed. leet-core, leet-bridge, leet-service exist.

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## CONTEXT

The VM has 4 internal stages:
```
Protocol Adapters → Semantic Projector → 1337 Runtime → Context Cache
```

**Asymmetry principle**: external protocols compile through Adapters → Projector.
Native 1337 agents connect directly to Runtime, bypassing compilation overhead.

---

## STRUCTURE

```
leet-vm/
├── pyproject.toml
├── leet_vm/
│   ├── __init__.py
│   ├── vm.py                    # LeetVM — main orchestrator
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py              # AdapterFrame + BaseAdapter ABC
│   │   ├── text.py              # Plain text → AdapterFrame
│   │   ├── jsonrpc.py           # JSON-RPC → AdapterFrame
│   │   ├── mcp.py               # MCP protocol → AdapterFrame
│   │   ├── rest.py              # REST → AdapterFrame
│   │   └── detector.py          # auto_detect(payload) → correct Adapter
│   ├── projector/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseProjector ABC
│   │   ├── grpc_client.py       # GrpcProjector (connects to leet-service)
│   │   ├── local.py             # LocalProjector (PyO3 direct, no network)
│   │   └── mock.py              # MockProjector (heuristics, zero deps)
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── session_dag.py       # SessionDAG with DELTA compression
│   │   ├── dag_router.py        # Priority routing: ANOMALY > URGENCY > topological
│   │   └── validator.py         # R1-R21 validation pipeline
│   ├── store/
│   │   ├── __init__.py
│   │   ├── personal_store.py    # PersonalStore — RAG replacement
│   │   └── context_cache.py     # Cache with align_hash + correlation table
│   └── surface/
│       ├── __init__.py
│       └── c4.py                # Surface C4: DAG → natural language
└── tests/
    ├── __init__.py
    ├── test_adapters.py
    ├── test_projector.py
    ├── test_runtime.py
    ├── test_store.py
    ├── test_surface.py
    └── test_vm.py
```

**pyproject.toml:**
```toml
[project]
name = "leet-vm"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["leet1337>=0.4.0"]

[project.optional-dependencies]
grpc = ["grpcio>=1.60"]
dev = ["pytest>=8", "pytest-asyncio"]
```

---

## DETAILED SPECS PER FILE

### adapters/base.py
```python
@dataclass
class AdapterFrame:
    """Normalized frame from any protocol."""
    text: str                    # extracted text content
    intent_hint: str | None      # ASSERT, QUERY, etc. if detectable
    metadata: dict               # protocol-specific metadata
    source_protocol: str         # "text", "jsonrpc", "mcp", "rest"
    raw_payload: Any = None      # original payload for BRIDGE

class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, payload: Any) -> AdapterFrame: ...
    @abstractmethod
    def serialize(self, cogon: Cogon, metadata: dict) -> Any: ...
```

### adapters/text.py
Simple: text string → AdapterFrame(text=input, source_protocol="text").
Intent detection via keywords: "?" → QUERY, "!" → ASSERT, "alert"/"warning" → ANOMALY.

### adapters/jsonrpc.py
Parses JSON-RPC 2.0 envelopes. Extracts method as intent_hint, params as text.
serialize() wraps Cogon as JSON-RPC result.

### adapters/mcp.py
Parses MCP tool_use / tool_result blocks. Extracts tool name + arguments.
Maps tool calls to ASSERT, tool results to ACK.

### adapters/rest.py
Parses HTTP-like payloads: method → intent (GET=QUERY, POST=ASSERT, PATCH=DELTA).
Extracts body as text.

### adapters/detector.py
```python
def auto_detect(payload: Any) -> BaseAdapter:
    """Auto-detect protocol and return correct adapter."""
    if isinstance(payload, str): return TextAdapter()
    if isinstance(payload, dict):
        if "jsonrpc" in payload: return JSONRPCAdapter()
        if "type" in payload and payload["type"] in ("tool_use","tool_result"): return MCPAdapter()
        if "method" in payload and "path" in payload: return RESTAdapter()
    return TextAdapter()  # fallback
```

### projector/base.py
```python
class BaseProjector(ABC):
    @abstractmethod
    async def encode(self, text: str) -> tuple[list[float], list[float]]: ...
    @abstractmethod
    async def decode(self, sem: list[float], unc: list[float], lang: str = "pt") -> str: ...
```

### projector/grpc_client.py
Connects to leet-service via gRPC. Calls Encode/Decode RPCs.
Connection pool with retry logic. Configurable host:port.

### projector/local.py
Uses leet-core PyO3 bindings directly (if compiled). No network.
Fallback to Python mock if PyO3 not available.

### projector/mock.py
Same heuristic logic as leet-bridge MockProjector in Rust, but pure Python.
Keyword → axis mapping for all 32 axes.

### runtime/session_dag.py
```python
class SessionDAG:
    """Manages session state with DELTA compression."""
    def __init__(self, session_id: str): ...
    def add(self, cogon: Cogon) -> Cogon | None:
        """Add cogon. Returns DELTA if previous state exists, full cogon if first."""
    def get_context_delta(self) -> list[Cogon]:
        """Returns only what changed since last sync."""
    def compress(self) -> dict:
        """Serialize session state for caching."""
    @classmethod
    def decompress(cls, data: dict) -> 'SessionDAG':
        """Restore from cached state."""
```
Uses DELTA operator internally. Tracks align_hash for consistency.

### runtime/dag_router.py
```python
def route_dag(dag: Dag) -> list[Cogon]:
    """Process DAG nodes in priority order per spec:
    1. Nodes with intent=ANOMALY
    2. Nodes with URGÊNCIA (idx 22) > 0.8
    3. Topological order
    Ties broken by stamp ascending (oldest first).
    """
```

### runtime/validator.py
```python
def validate_pipeline(msg: Msg1337) -> list[str]:
    """Full R1-R21 validation. Returns list of violations."""
```
Wraps the Python validate from leet package.

### store/personal_store.py
```python
class PersonalStore:
    """RAG replacement — COGONs accumulated per user in 32D space."""
    def __init__(self, agent_id: str): ...
    async def add(self, cogon: Cogon) -> None: ...
    async def recall(self, query: Cogon, k: int = 5) -> list[tuple[Cogon, float]]:
        """Top-k by DIST weighted by (1-unc). Returns (cogon, distance) pairs."""
    async def delta_context(self, session: SessionDAG) -> list[Cogon]:
        """Recall relevant COGONs + session delta. Flat cost over time."""
    def emergent_check(self, cogon: Cogon) -> list[int]:
        """Check if cogon activates any emergent zone dimensions."""
    @property
    def size(self) -> int: ...
```
Internal storage: list of Cogons sorted by stamp. DIST uses leet.operators.dist().
DELTA compression keeps session costs flat over time.

### store/context_cache.py
```python
class ContextCache:
    """Cache with align_hash verification and correlation table."""
    def __init__(self): ...
    def get(self, key: str, align_hash: str) -> Any | None: ...
    def set(self, key: str, value: Any, align_hash: str) -> None: ...
    def invalidate_on_drift(self, new_hash: str) -> int:
        """Invalidate entries with different align_hash. Returns count invalidated."""
```

### surface/c4.py
```python
def surface_c4(dag: Dag, depth: int = 3, lang: str = "pt") -> str:
    """Deterministic DAG → natural language reconstruction.
    Walks from leaves to root up to `depth` levels.
    NOT generative — uses axis values to construct description.
    """
```
For each cogon: identify top-3 axes by sem value, construct sentence describing concept.
Edge types map to connectors: CAUSA→"causou", CONDICIONA→"depende de", etc.

### vm.py
```python
class LeetVM:
    """Central orchestrator — the 1337 Virtual Machine."""
    def __init__(self, projector: BaseProjector, store: PersonalStore | None = None): ...

    async def process(self, input: Any, agent_id: str, session_id: str) -> dict:
        """Full pipeline:
        1. Auto-detect protocol → Adapter
        2. Adapter.parse() → AdapterFrame
        3. Projector.encode() → sem[32] + unc[32]
        4. Build Cogon + validate (R1-R21)
        5. PersonalStore.recall() → context
        6. SessionDAG.add() → delta
        7. PersonalStore.add()
        8. Return { cogon, context, delta, surface }
        """
```

---

## TESTS (minimum 30)

- auto_detect correctly identifies 4 protocol types
- TextAdapter parses and detects intent from keywords
- JSONRPCAdapter roundtrip
- MCPAdapter parses tool_use/tool_result
- RESTAdapter maps HTTP methods to intents
- MockProjector encode/decode consistency
- GrpcProjector connection (mock server or skip)
- SessionDAG add returns delta on second call
- SessionDAG compress/decompress roundtrip
- dag_router priority ordering (ANOMALY > URGÊNCIA > topological)
- dag_router tie-breaking by stamp
- PersonalStore add/recall top-k
- PersonalStore delta_context returns relevant + changed
- ContextCache set/get with matching align_hash
- ContextCache invalidate_on_drift
- surface_c4 produces readable text from simple DAG
- surface_c4 respects depth parameter
- LeetVM.process() full pipeline with mock projector
- LeetVM.process() with PersonalStore integration
- Validation pipeline catches R1-R21 violations

---

## TASKWARRIOR + CONTRACT UPDATE

```bash
task project:1337 +prompt03 status:pending done

sed -i 's/| leet-vm (Python) | PROMPT_03 | `\[ \]` PENDENTE/| leet-vm (Python) | PROMPT_03 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

git add -A
git commit -m "feat(prompt-03): leet-vm — adapters, projector, PersonalStore, runtime

- 4 protocol adapters + auto-detect
- 3 projector backends (gRPC, local, mock)
- SessionDAG with DELTA compression
- PersonalStore as RAG replacement
- Surface C4 deterministic reconstruction
- LeetVM orchestrator
- CONTRACT.md + Taskwarrior updated"

git push origin main
```

---

## VERIFICATION

```bash
cd leet-vm && pip install -e ".[dev]" && pytest tests/ -v

# Quick smoke test
python -c "
import asyncio
from leet_vm import LeetVM
from leet_vm.projector.mock import MockProjector
from leet_vm.store.personal_store import PersonalStore

async def test():
    vm = LeetVM(MockProjector(), PersonalStore('test'))
    result = await vm.process('controle preditivo urgente', 'agent-1', 'session-1')
    print(result['cogon'])
    print(f'Context: {len(result[\"context\"])} items')

asyncio.run(test())
"
```

**END OF PROMPT_03**
