# leet-vm

Python agent orchestration VM. Manages projection, semantic memory, sessions, and message routing.

## Overview

```
Input (text | JSON-RPC | MCP | REST)
     │
     ▼
LeetVM.process()
     ├── Adapter → Frame   (protocol detection and decode)
     ├── Projector → Cogon (LocalProjector | ServiceProjector)
     ├── PersonalStore     (semantic context recall)
     ├── SessionDAG        (session delta)
     ├── Router            (dispatches to the agent handler)
     └── SurfaceC4         (text reconstruction)
     │
     ▼
VMResult { text, cogon, tokens_saved, session_id }
```

## LeetVM

```python
from leet_vm.vm import LeetVM

vm = LeetVM(
    mode="auto",               # "auto" | "local" | "service"
    service_url="localhost:50051",
    store_backend="memory",    # "memory" | Redis URL
)
```

### Projection Modes

| Mode | Behavior |
|------|----------|
| `"local"` | Always uses `LocalProjector` (heuristics, no network) |
| `"service"` | Always uses `ServiceProjector` (connects to leet-service gRPC) |
| `"auto"` | Tries `ServiceProjector`; falls back to `LocalProjector` if unavailable |

### Processing

```python
result = await vm.process(
    input=text_or_frame,
    agent_id="my-agent",
    session_id="sess-uuid",
    protocol="auto",        # "auto" | "text" | "json_rpc" | "mcp" | "rest"
    target_agent="",        # specific agent or "" for default
)

print(result.text)           # reconstructed text
print(result.tokens_saved)   # estimated tokens saved
print(result.cogon)          # resulting Cogon
```

### Processing Pipeline (7 steps)

1. **Protocol detection** — identifies the input format
2. **Decode via Adapter** — extracts `Frame(method, params)`
3. **Projection → COGON** — `Projector.project(text, agent_id)`
4. **Context recall** — 5 nearest COGONs from `PersonalStore`
5. **Session DELTA** — only what changed since the last request in the session
6. **Routing** — dispatches `(cogon, context)` to the registered handler
7. **Persistence** — saves input and result to the store and the session

### Agent Registration

```python
async def my_handler(cogon: Cogon, context: list[Cogon]) -> Cogon:
    # processes and returns response cogon
    ...

vm.register_agent("agent-x", my_handler)
vm.set_default_agent(my_handler)  # handler for unregistered agents
```

## Projectors

### LocalProjector

Local projection via keyword heuristics. No network, no API.

```python
from leet_vm.projector.local import LocalProjector

proj = LocalProjector()
cogon = await proj.project("text", "agent-id")
text  = await proj.decode(cogon)
```

### ServiceProjector

Connects to `leet-service` gRPC. Uses the service's `encode` and `decode`.

```python
from leet_vm.projector.service import ServiceProjector

proj = ServiceProjector("localhost:50051")
cogon = await proj.project("text", "agent-id")
```

Falls back gracefully — if the service doesn't respond, `LeetVM` in `auto` mode substitutes `LocalProjector`.

## PersonalStore

Persistent per-agent semantic memory. Supports recall by cosine similarity.

```python
from leet_vm.store.personal import PersonalStore

store = PersonalStore("memory")   # or Redis URL

await store.add(agent_id, cogon, text="optional hint")
results = await store.recall(agent_id, cogon, k=5)
# results: list[(record_dict, dist_float)]

count = await store.count(agent_id)
```

## SessionDAG

Session trace — DAG of COGONs exchanged in the current session. Enables incremental DELTA computation.

```python
from leet_vm.store.session import SessionDAG

session = SessionDAG(session_id="uuid")
session.add(cogon)
prev_stamp = session.last_stamp()
delta = session.delta_since(prev_stamp)  # list[Cogon]
```

## Adapters

Detect and decode different input formats:

| Protocol | Detection |
|-----------|----------|
| `text` | simple string |
| `json_rpc` | `{"jsonrpc": "2.0", ...}` |
| `mcp` | `{"method": "tools/call", ...}` |
| `rest` | `{"path": ..., "body": ...}` |

```python
from leet_vm.adapters.registry import detect_protocol, ADAPTERS

protocol = detect_protocol(input_data)
frame = ADAPTERS[protocol].decode(input_data)
# frame.method, frame.params
```

## SurfaceC4

Text reconstruction for a human interface from a COGON.

```python
from leet_vm.runtime.surface import SurfaceC4

surface = SurfaceC4()
text = surface.reconstruct(cogon)
```

## Router

Dispatches COGONs to registered handlers.

```python
from leet_vm.runtime.router import Router

router = Router()
router.register("agent-x", handler_x)
router.set_default(handler_default)

result = await router.route(cogon, context, target_agent="")
```

## Tests

```bash
cd leet-vm
python -m pytest      # all VM tests
```

Tests cover: adapters, projectors (local and service mock), store (add/recall/count), VM end-to-end.
