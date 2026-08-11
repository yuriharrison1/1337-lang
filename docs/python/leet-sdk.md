# Python SDK — python/leet

Pure Python SDK (no Rust runtime dependencies) that implements the types, operators, bridge, cache, and validation for the 1337 protocol.

Package namespace: `leet1337` (install) / `leet` (import).

## Main Types

### `Cogon`

```python
from leet_vm.types import Cogon

c = Cogon(
    sem=[0.5] * 32,   # list[float], all in [0, 1]
    id="uuid-str",    # optional, auto-generated
    stamp=1700000000000,  # Unix ms
)
```

Methods:
- `cogon.is_zero()` — checks whether it's the canonical COGON_ZERO
- `cogon.is_low_confidence()` — `sem[29] < 0.1` (R5)
- `cogon.to_dict()` / `Cogon.from_dict(d)` — serialization
- `cogon.to_bytes()` / `Cogon.from_bytes(b)` — 96-byte binary codec

### `Dag`

```python
from leet_vm.types import Dag, Edge

dag = Dag(root="uuid-root")
dag.add_node(cogon)
dag.add_edge(Edge(from_id="a", to_id="b", edge_type="CAUSA", weight=0.9))
order = dag.topological_order()   # Kahn's algorithm, cached
```

### `Msg1337`

Complete envelope:

```python
from leet_vm.types import Msg1337, C5Block, SurfaceBlock

msg = Msg1337(
    id=str(uuid.uuid4()),
    sender="agent-uuid",
    receiver="target-uuid",
    intent="ASSERT",
    payload=cogon,
    c5=C5Block(...),
    surface=SurfaceBlock(human_required=False, lang="pt"),
)
```

### `RawField`

```python
RawField(
    type="text/plain",          # MIME type
    content="content",          # str | dict | bytes
    role="ARTIFACT",            # EVIDENCE | ARTIFACT | TRACE | BRIDGE
)
```

## Operators

```python
from leet_vm.types import blend, delta, dist, focus, anomaly_score

# BLEND
result = blend(c1, c2, alpha=0.7)

# DELTA — returns list[float], can be negative
patch = delta(c_prev, c_curr)

# DIST — cosine distance [0, 2]
d = dist(c1, c2)

# FOCUS — zeroes out unselected dimensions
focused = focus(cogon, dims=[8, 23, 26])

# ANOMALY_SCORE — distance to historical centroid
score = anomaly_score(cogon, history=[c1, c2, c3])
```

Special BLEND rules (mirror the Rust implementation):

| Axis | Rule |
|------|------|
| D4 SIGNAL (11) | `min(c1, c2)` |
| G1 TEMPORALITY (16) | `clamp(c1 + c2, 0, 1)` |
| G7 EPISTEMIC_VALENCE (22) | `max(c1, c2)` |
| P6 TEMPORAL_VECTOR (29) | `min(c1, c2)` |
| others | `α·c1 + (1-α)·c2` |

## Bridge

```python
from leet.bridge import Bridge, MockBridge

bridge = Bridge()     # uses heuristics
mock   = MockBridge() # deterministic for testing

cogon = bridge.encode("urgent deploy failed")
text  = bridge.decode(cogon)
```

### Projection Heuristics

The Python implementation uses the same rules as the Rust `MockProjector`:

```python
RULES = [
    (["caiu", "falhou", "erro", "down"], 8,  0.9),   # D1_STATE
    (["caiu", "falhou", "erro", "down"], 26, 0.9),   # P3_ANOMALY
    (["deploy", "pipeline"],             9,  0.85),  # D2_PROCESS
    (["urgente", "crítico"],             23, 0.95),  # G8_URGENCY
    # ...
]
```

## Validation

```python
from leet.validate import validate, check_confidence

error = validate(msg)      # None if valid, str if error
flags = check_confidence(msg)  # list[str] of R5 warnings
```

All R2–R23 structural-scope rules are implemented. Errors return the first violation found.

## Cache

```python
from leet.cache import MemoryCache, RedisCache, CacheBackend

# Memory (default)
cache = MemoryCache()

# Redis (requires redis-py)
cache = RedisCache(host="localhost", port=6379)
```

Interface `CacheBackend`:
```python
class CacheBackend:
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: int = 300) -> None: ...
    def delete(self, key: str) -> None: ...
```

## Batch

```python
from leet.batch import BatchProcessor

async def process_item(index, item):
    return await encode(item)

bp = BatchProcessor(process_item, max_concurrent=10)
results = await bp.run(items)
```

## Axes

```python
from leet_vm.types import CANONICAL_AXES, axis_by_code

ax = axis_by_code("G8")  # {"index": 23, "name": "URGENCY", ...}
```

## Tests

```bash
cd python
python -m pytest                # all tests
python -m pytest leet/          # SDK tests
```
