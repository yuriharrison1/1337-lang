# Relatório de Bugs e Otimizações - Projeto 1337

**Data da análise:** 2026-04-01  
**Versão analisada:** v0.4  
**Testes executados:** 146 Python ✓ | Rust: não compilou (falta lib.rs)

---

## 🐛 BUGS ENCONTRADOS

### 1. **Código Redundante em `validate.py` (linha 53-56)**
**Severidade:** Baixa  
**Arquivo:** `python/leet/validate.py`

```python
# Código inútil que não faz nada
if isinstance(msg.payload, Payload):
    payload = msg.payload
else:
    payload = msg.payload
```

**Problema:** As duas branches fazem exatamente a mesma atribuição. O tipo `Payload` é um alias para `Union['Cogon', 'Dag']`.

**Correção:** Remover o bloco condicional e usar `payload = msg.payload` diretamente.

---

### 2. **Verificação de Optional Incorreta em R7 (`validate.py`)**
**Severidade:** Média  
**Arquivo:** `python/leet/validate.py` (linha 137)

```python
def _r7_zone_emergent_c5(msg: Msg1337) -> Optional[str]:
    if msg.c5 and msg.c5.zone_emergent:  # c5 não é Optional no dataclass!
```

**Problema:** No dataclass `Msg1337`, `c5` é do tipo `CanonicalSpace` (não Optional), então a verificação `if msg.c5` sempre será True. Se o campo puder ser None, o type hint está incorreto.

**Correção:** Ou tornar `c5: Optional[CanonicalSpace]` no dataclass, ou remover a verificação redundante.

---

### 3. **Inconsistência de Interface Async/Sync no Cache (`cache.py`)**
**Severidade:** Alta  
**Arquivo:** `python/leet/cache.py`

```python
# CacheBackend define métodos síncronos
class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...

# RedisCache implementa como async
class RedisCache(CacheBackend):
    async def get(self, key: str) -> Optional[Any]: ...  # Incompatível!
```

**Problema:** `RedisCache` implementa métodos como `async` mas a classe base define como síncronos. Isso quebra o Liskov Substitution Principle e causará erros em runtime.

**Correção:** Separar interfaces síncronas e assíncronas, ou tornar todos os backends compatíveis com ambos os modos.

---

### 4. **Uso de Índice Hardcoded em `bridge.py`**
**Severidade:** Baixa  
**Arquivo:** `python/leet/bridge.py` (linha 43)

```python
sem[13] = 0.15  # A13_VALÊNCIA_ONTOLÓGICA (negativo)
```

**Problema:** Usa índice numérico mágico ao invés da constante `A13_VALENCIA_ONTOLOGICA` já importada.

**Correção:** Substituir por `sem[A13_VALENCIA_ONTOLOGICA] = 0.15`

---

### 5. **Tratamento de Erro Incompleto em `Msg1337.from_dict`**
**Severidade:** Média  
**Arquivo:** `python/leet/types.py` (linha 364-371)

```python
@classmethod
def from_dict(cls, d: dict) -> Msg1337:
    payload_dict = d["payload"]
    if "root" in payload_dict:
        payload = Dag.from_dict(payload_dict)
    else:
        payload = Cogon.from_dict(payload_dict)  # Pode falhar silenciosamente
```

**Problema:** Se o payload não tiver "root" e também não for um Cogon válido, o erro será propagado sem contexto claro.

**Correção:** Adicionar validação explícita e mensagem de erro descritiva.

---

### 6. **Possível Problema de Timezone em Timestamps**
**Severidade:** Baixa  
**Arquivos:** `python/leet/types.py`, `net1337.py`

```python
stamp=int(datetime.now().timestamp() * 1e9)  # nanoseconds
```

**Problema:** `datetime.now()` retorna hora local, não UTC. Isso pode causar inconsistências em sistemas distribuídos.

**Correção:** Usar `datetime.now(timezone.utc).timestamp()` ou `time.time_ns()` (Python 3.7+).

---

### 7. **Importação Condicional Dentro de Função (`batch.py`)**
**Severidade:** Baixa  
**Arquivo:** `python/leet/batch.py`

```python
async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
    import time  # Import dentro do método!
```

**Problema:** Importar dentro de funções prejudica performance (especialmente em loops) e dificulta rastreamento de dependências.

**Correção:** Mover imports para o topo do arquivo.

---

### 8. **Valor de Retorno Inconsistente em `anomaly_score`**
**Severidade:** Média  
**Arquivo:** `python/leet/operators.py` (linha 67-84)

```python
def anomaly_score(cogon: Cogon, history: list[Cogon]) -> float:
    if not history:
        return 1.0  # Retorna 1.0 para histórico vazio
    # ... calcula distância normalizada
```

**Problema:** Retornar 1.0 (anomalia máxima) para histórico vazio pode ser contraintuitivo. Documentar comportamento ou usar valor neutro (0.5).

---

### 9. **Problema de Referência em `Dag.parents_of`**
**Severidade:** Baixa  
**Arquivo:** `python/leet/types.py` (linha 198-200)

```python
def parents_of(self, node_id: str) -> list[str]:
    """Returns IDs of parent nodes (nodes with edges TO node_id)."""
    return [e.from_id for e in self.edges if e.to_id == node_id]
```

**Problema:** O docstring diz "nodes with edges TO node_id" mas o conceito de "parent" em DAGs geralmente é o contrário (edges FROM parent TO child).

**Correção:** Verificar se a lógica está consistente com o uso em `topological_order`.

---

### 10. **Validação de `alpha` em `blend` Ausente**
**Severidade:** Média  
**Arquivo:** `python/leet/operators.py` (linha 8-18)

```python
def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    sem = [alpha * s1 + (1 - alpha) * s2 ...]  # Sem validação de alpha!
```

**Problema:** `alpha` pode ser qualquer float. Valores fora de [0, 1] produzem resultados fora do range válido.

**Correção:** Adicionar `alpha = max(0.0, min(1.0, alpha))` ou lançar ValueError.

---

## ⚡ OTIMIZAÇÕES SUGERIDAS

### 1. **Usar NumPy para Operações Vetoriais**
**Arquivos:** `python/leet/operators.py`, `python/leet/types.py`

**Atual:**
```python
sem = [alpha * s1 + (1 - alpha) * s2 for s1, s2 in zip(c1.sem, c2.sem)]
```

**Otimizado:**
```python
import numpy as np
# Pré-alocar arrays uma vez
sem = alpha * c1.sem_array + (1 - alpha) * c2.sem_array  # 10-50x mais rápido
```

**Impacto:** Operações BLAS otimizadas, menos GC pressure, SIMD automático.

---

### 2. **Cache de Projeções com LRU**
**Arquivo:** `python/leet/bridge.py`

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _cached_projection(text_hash: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    ...
```

**Impacto:** Evita re-projetar textos idênticos ou similares.

---

### 3. **Validação Lazy com `@cached_property`**
**Arquivo:** `python/leet/types.py`

```python
from functools import cached_property

@dataclass
class Cogon:
    # ...
    @cached_property
    def _low_confidence_cache(self) -> list[int]:
        return [i for i, u in enumerate(self.unc) if u > 0.9]
```

**Impacto:** Evita recalcular a cada chamada de `low_confidence_dims()`.

---

### 4. **Prevenir Cópias Desnecessárias de Vetores**
**Arquivo:** `python/leet/types.py` (vários métodos)

```python
def with_raw(self, raw: Raw) -> Cogon:
    return Cogon(
        id=self.id,
        sem=self.sem.copy(),  # Sempre copia!
        unc=self.unc.copy(),
        ...
    )
```

**Otimização:** Usar `list(self.sem)` ou `self.sem[:]` é mais rápido. Melhor ainda: usar tuplas (imutáveis) para sem/unc.

---

### 5. **Serialização mais Eficiente com `orjson` ou `msgspec`**
**Arquivos:** Todos os arquivos com `json.dumps`

```python
# Atual
import json
return json.dumps(self.to_dict(), indent=2)

# Otimizado
import orjson
return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2)
```

**Impacto:** 2-10x mais rápido, menos memória.

---

### 6. **Uso de `__slots__` em Dataclasses**
**Arquivos:** `python/leet/types.py`

```python
@dataclass(slots=True)
class Cogon:
    ...
```

**Impacto:** Reduz memória em ~50%, acesso mais rápido aos atributos.

---

### 7. **Paralelização com `ProcessPoolExecutor` para Batch**
**Arquivo:** `python/leet/batch.py`

```python
from concurrent.futures import ProcessPoolExecutor

# Para operações CPU-bound (cálculo de distâncias)
with ProcessPoolExecutor() as executor:
    results = list(executor.map(compute_dist, pairs))
```

**Impacto:** Aproveita múltiplos cores para processamento de grandes batches.

---

### 8. **Memoização de `topological_order`**
**Arquivo:** `python/leet/types.py` (classe `Dag`)

```python
@dataclass
class Dag:
    _topological_cache: Optional[list[str]] = field(default=None, init=False, repr=False)
    
    def topological_order(self) -> list[str]:
        if self._topological_cache is None:
            self._topological_cache = self._compute_topological_order()
        return self._topological_cache
```

**Impacto:** Evita recalcular ordem topológica para DAGs imutáveis.

---

### 9. **Uso de `array.array` ao invés de `list[float]`**
**Arquivo:** `python/leet/types.py`

```python
from array import array

# Mais eficiente em memória, tipado
sem: array = field(default_factory=lambda: array('f', [0.0] * 32))
```

**Impacto:** 4x menos memória que list, acesso mais rápido.

---

### 10. **Batch de Validações com `asyncio.gather`**
**Arquivo:** `python/leet/validate.py`

```python
async def validate_async(msg: Msg1337) -> Optional[str]:
    validators = [...]
    results = await asyncio.gather(*[v(msg) for v in validators])
    for result in results:
        if result is not None:
            return result
    return None
```

**Impacto:** Validações independentes rodam em paralelo (se alguma for async).

---

## 📊 Resumo

| Categoria | Quantidade | Prioridade |
|-----------|------------|------------|
| Bugs Críticos | 1 (Redis async) | 🔴 Alta |
| Bugs Médios | 3 | 🟡 Média |
| Bugs Baixos | 6 | 🟢 Baixa |
| Otimizações Alto Impacto | 3 (NumPy, slots, cache) | 🔴 Alta |
| Otimizações Médio Impacto | 4 | 🟡 Média |
| Otimizações Baixo Impacto | 3 | 🟢 Baixa |

---

## 🛠️ Recomendações Imediatas

1. **Corrigir a inconsistência do RedisCache** - pode quebrar em produção
2. **Adicionar validação de `alpha` em `blend`** - evita resultados inválidos
3. **Usar `__slots__`** nas classes de alto volume (Cogon, Msg1337)
4. **Considerar NumPy** se performance vetorial for crítica
5. **Adicionar `orjson`** para serialização de alta performance
