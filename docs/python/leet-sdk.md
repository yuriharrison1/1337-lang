# SDK Python — python/leet

SDK Python puro (sem dependências Rust em runtime) que implementa os tipos, operadores, bridge, cache e validação do protocolo 1337.

Namespace de pacote: `leet1337` (instalação) / `leet` (import).

## Tipos Principais

### `Cogon`

```python
from leet_vm.types import Cogon

c = Cogon(
    sem=[0.5] * 32,   # list[float], todos em [0, 1]
    id="uuid-str",    # opcional, gerado automaticamente
    stamp=1700000000000,  # Unix ms
)
```

Métodos:
- `cogon.is_zero()` — verifica se é o COGON_ZERO canônico
- `cogon.is_low_confidence()` — `sem[29] < 0.1` (R5)
- `cogon.to_dict()` / `Cogon.from_dict(d)` — serialização
- `cogon.to_bytes()` / `Cogon.from_bytes(b)` — codec binário 96 bytes

### `Dag`

```python
from leet_vm.types import Dag, Edge

dag = Dag(root="uuid-raiz")
dag.add_node(cogon)
dag.add_edge(Edge(from_id="a", to_id="b", edge_type="CAUSA", weight=0.9))
order = dag.topological_order()   # algoritmo de Kahn, cacheado
```

### `Msg1337`

Envelope completo:

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
    content="conteúdo",         # str | dict | bytes
    role="ARTIFACT",            # EVIDENCE | ARTIFACT | TRACE | BRIDGE
)
```

## Operadores

```python
from leet_vm.types import blend, delta, dist, focus, anomaly_score

# BLEND
result = blend(c1, c2, alpha=0.7)

# DELTA — retorna list[float], pode ser negativo
patch = delta(c_prev, c_curr)

# DIST — distância cosseno [0, 2]
d = dist(c1, c2)

# FOCUS — zera dimensões não selecionadas
focused = focus(cogon, dims=[8, 23, 26])

# ANOMALY_SCORE — distância ao centróide histórico
score = anomaly_score(cogon, history=[c1, c2, c3])
```

Regras especiais de BLEND (espelham a implementação Rust):

| Eixo | Regra |
|------|-------|
| D4 SIGNAL (11) | `min(c1, c2)` |
| G1 TEMPORALITY (16) | `clamp(c1 + c2, 0, 1)` |
| G7 EPISTEMIC_VALENCE (22) | `max(c1, c2)` |
| P6 TEMPORAL_VECTOR (29) | `min(c1, c2)` |
| demais | `α·c1 + (1-α)·c2` |

## Bridge

```python
from leet.bridge import Bridge, MockBridge

bridge = Bridge()     # usa heurísticas
mock   = MockBridge() # determinístico para testes

cogon = bridge.encode("deploy urgente falhou")
text  = bridge.decode(cogon)
```

### Heurísticas de Projeção

A implementação Python usa as mesmas regras que o `MockProjector` Rust:

```python
RULES = [
    (["caiu", "falhou", "erro", "down"], 8,  0.9),   # D1_STATE
    (["caiu", "falhou", "erro", "down"], 26, 0.9),   # P3_ANOMALY
    (["deploy", "pipeline"],             9,  0.85),  # D2_PROCESS
    (["urgente", "crítico"],             23, 0.95),  # G8_URGENCY
    # ...
]
```

## Validação

```python
from leet.validate import validate, check_confidence

error = validate(msg)      # None se válido, str se erro
flags = check_confidence(msg)  # list[str] de warnings R5
```

Todas as regras R2–R23 de escopo estrutural são implementadas. Erros retornam a primeira violação encontrada.

## Cache

```python
from leet.cache import MemoryCache, RedisCache, CacheBackend

# Memória (padrão)
cache = MemoryCache()

# Redis (requer redis-py)
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

## Eixos

```python
from leet_vm.types import CANONICAL_AXES, axis_by_code

ax = axis_by_code("G8")  # {"index": 23, "name": "URGENCY", ...}
```

## Testes

```bash
cd python
python -m pytest                # todos os testes
python -m pytest leet/          # testes do SDK
```
