# Bugs and Optimizations Report - 1337 Project

**Analysis date:** 2026-04-01
**Version analyzed:** v0.4
**Tests run:** 146 Python ✓ | Rust: did not compile (missing lib.rs)

---

## 🐛 BUGS FOUND

### 1. **Redundant Code in `validate.py` (line 53-56)**
**Severity:** Low
**File:** `python/leet/validate.py`

```python
# Useless code that does nothing
if isinstance(msg.payload, Payload):
    payload = msg.payload
else:
    payload = msg.payload
```

**Problem:** Both branches perform exactly the same assignment. The `Payload` type is an alias for `Union['Cogon', 'Dag']`.

**Fix:** Remove the conditional block and use `payload = msg.payload` directly.

---

### 2. **Incorrect Optional Check in R7 (`validate.py`)**
**Severity:** Medium
**File:** `python/leet/validate.py` (line 137)

```python
def _r7_zone_emergent_c5(msg: Msg1337) -> Optional[str]:
    if msg.c5 and msg.c5.zone_emergent:  # c5 is not Optional in the dataclass!
```

**Problem:** In the `Msg1337` dataclass, `c5` is of type `CanonicalSpace` (not Optional), so the `if msg.c5` check will always be True. If the field can be None, the type hint is incorrect.

**Fix:** Either make `c5: Optional[CanonicalSpace]` in the dataclass, or remove the redundant check.

---

### 3. **Async/Sync Interface Inconsistency in Cache (`cache.py`)**
**Severity:** High
**File:** `python/leet/cache.py`

```python
# CacheBackend defines synchronous methods
class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...

# RedisCache implements them as async
class RedisCache(CacheBackend):
    async def get(self, key: str) -> Optional[Any]: ...  # Incompatible!
```

**Problem:** `RedisCache` implements methods as `async` but the base class defines them as synchronous. This breaks the Liskov Substitution Principle and will cause runtime errors.

**Fix:** Separate synchronous and asynchronous interfaces, or make all backends compatible with both modes.

---

### 4. **Hardcoded Index Used in `bridge.py`**
**Severity:** Low
**File:** `python/leet/bridge.py` (line 43)

```python
sem[13] = 0.15  # A13_VALÊNCIA_ONTOLÓGICA (negative)
```

**Problem:** Uses a magic numeric index instead of the already-imported `A13_VALENCIA_ONTOLOGICA` constant.

**Fix:** Replace with `sem[A13_VALENCIA_ONTOLOGICA] = 0.15`

---

### 5. **Incomplete Error Handling in `Msg1337.from_dict`**
**Severity:** Medium
**File:** `python/leet/types.py` (line 364-371)

```python
@classmethod
def from_dict(cls, d: dict) -> Msg1337:
    payload_dict = d["payload"]
    if "root" in payload_dict:
        payload = Dag.from_dict(payload_dict)
    else:
        payload = Cogon.from_dict(payload_dict)  # Can fail silently
```

**Problem:** If the payload does not have "root" and is also not a valid Cogon, the error will propagate without clear context.

**Fix:** Add explicit validation and a descriptive error message.

---

### 6. **Possible Timezone Issue in Timestamps**
**Severity:** Low
**Files:** `python/leet/types.py`, `net1337.py`

```python
stamp=int(datetime.now().timestamp() * 1e9)  # nanoseconds
```

**Problem:** `datetime.now()` returns local time, not UTC. This can cause inconsistencies in distributed systems.

**Fix:** Use `datetime.now(timezone.utc).timestamp()` or `time.time_ns()` (Python 3.7+).

---

### 7. **Conditional Import Inside a Function (`batch.py`)**
**Severity:** Low
**File:** `python/leet/batch.py`

```python
async def _process_one(self, index: int, item: T) -> BatchResult[T, R]:
    import time  # Import inside the method!
```

**Problem:** Importing inside functions hurts performance (especially in loops) and makes dependency tracking harder.

**Fix:** Move imports to the top of the file.

---

### 8. **Inconsistent Return Value in `anomaly_score`**
**Severity:** Medium
**File:** `python/leet/operators.py` (line 67-84)

```python
def anomaly_score(cogon: Cogon, history: list[Cogon]) -> float:
    if not history:
        return 1.0  # Returns 1.0 for empty history
    # ... computes normalized distance
```

**Problem:** Returning 1.0 (maximum anomaly) for empty history can be counterintuitive. Document the behavior or use a neutral value (0.5).

---

### 9. **Reference Issue in `Dag.parents_of`**
**Severity:** Low
**File:** `python/leet/types.py` (line 198-200)

```python
def parents_of(self, node_id: str) -> list[str]:
    """Returns IDs of parent nodes (nodes with edges TO node_id)."""
    return [e.from_id for e in self.edges if e.to_id == node_id]
```

**Problem:** The docstring says "nodes with edges TO node_id" but the concept of "parent" in DAGs is generally the opposite (edges FROM parent TO child).

**Fix:** Verify the logic is consistent with its usage in `topological_order`.

---

### 10. **Missing `alpha` Validation in `blend`**
**Severity:** Medium
**File:** `python/leet/operators.py` (line 8-18)

```python
def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    sem = [alpha * s1 + (1 - alpha) * s2 ...]  # No alpha validation!
```

**Problem:** `alpha` can be any float. Values outside [0, 1] produce results outside the valid range.

**Fix:** Add `alpha = max(0.0, min(1.0, alpha))` or raise ValueError.

---

## ⚡ SUGGESTED OPTIMIZATIONS

### 1. **Use NumPy for Vector Operations**
**Files:** `python/leet/operators.py`, `python/leet/types.py`

**Current:**
```python
sem = [alpha * s1 + (1 - alpha) * s2 for s1, s2 in zip(c1.sem, c2.sem)]
```

**Optimized:**
```python
import numpy as np
# Pre-allocate arrays once
sem = alpha * c1.sem_array + (1 - alpha) * c2.sem_array  # 10-50x faster
```

**Impact:** Optimized BLAS operations, less GC pressure, automatic SIMD.

---

### 2. **LRU Projection Cache**
**File:** `python/leet/bridge.py`

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _cached_projection(text_hash: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    ...
```

**Impact:** Avoids re-projecting identical or similar texts.

---

### 3. **Lazy Validation with `@cached_property`**
**File:** `python/leet/types.py`

```python
from functools import cached_property

@dataclass
class Cogon:
    # ...
    @cached_property
    def _low_confidence_cache(self) -> list[int]:
        return [i for i, u in enumerate(self.unc) if u > 0.9]
```

**Impact:** Avoids recomputing on every call to `low_confidence_dims()`.

---

### 4. **Prevent Unnecessary Vector Copies**
**File:** `python/leet/types.py` (several methods)

```python
def with_raw(self, raw: Raw) -> Cogon:
    return Cogon(
        id=self.id,
        sem=self.sem.copy(),  # Always copies!
        unc=self.unc.copy(),
        ...
    )
```

**Optimization:** Using `list(self.sem)` or `self.sem[:]` is faster. Even better: use tuples (immutable) for sem/unc.

---

### 5. **More Efficient Serialization with `orjson` or `msgspec`**
**Files:** All files using `json.dumps`

```python
# Current
import json
return json.dumps(self.to_dict(), indent=2)

# Optimized
import orjson
return orjson.dumps(self.to_dict(), option=orjson.OPT_INDENT_2)
```

**Impact:** 2-10x faster, less memory.

---

### 6. **Use `__slots__` in Dataclasses**
**Files:** `python/leet/types.py`

```python
@dataclass(slots=True)
class Cogon:
    ...
```

**Impact:** Reduces memory by ~50%, faster attribute access.

---

### 7. **Parallelization with `ProcessPoolExecutor` for Batch**
**File:** `python/leet/batch.py`

```python
from concurrent.futures import ProcessPoolExecutor

# For CPU-bound operations (distance computation)
with ProcessPoolExecutor() as executor:
    results = list(executor.map(compute_dist, pairs))
```

**Impact:** Takes advantage of multiple cores for processing large batches.

---

### 8. **Memoization of `topological_order`**
**File:** `python/leet/types.py` (`Dag` class)

```python
@dataclass
class Dag:
    _topological_cache: Optional[list[str]] = field(default=None, init=False, repr=False)
    
    def topological_order(self) -> list[str]:
        if self._topological_cache is None:
            self._topological_cache = self._compute_topological_order()
        return self._topological_cache
```

**Impact:** Avoids recomputing topological order for immutable DAGs.

---

### 9. **Use `array.array` Instead of `list[float]`**
**File:** `python/leet/types.py`

```python
from array import array

# More memory-efficient, typed
sem: array = field(default_factory=lambda: array('f', [0.0] * 32))
```

**Impact:** 4x less memory than list, faster access.

---

### 10. **Batch Validations with `asyncio.gather`**
**File:** `python/leet/validate.py`

```python
async def validate_async(msg: Msg1337) -> Optional[str]:
    validators = [...]
    results = await asyncio.gather(*[v(msg) for v in validators])
    for result in results:
        if result is not None:
            return result
    return None
```

**Impact:** Independent validations run in parallel (if any are async).

---

## 📊 Summary

| Category | Count | Priority |
|-----------|------------|------------|
| Critical Bugs | 1 (Redis async) | 🔴 High |
| Medium Bugs | 3 | 🟡 Medium |
| Low Bugs | 6 | 🟢 Low |
| High-Impact Optimizations | 3 (NumPy, slots, cache) | 🔴 High |
| Medium-Impact Optimizations | 4 | 🟡 Medium |
| Low-Impact Optimizations | 3 | 🟢 Low |

---

## 🛠️ Immediate Recommendations

1. **Fix the RedisCache inconsistency** - could break in production
2. **Add `alpha` validation in `blend`** - prevents invalid results
3. **Use `__slots__`** in high-volume classes (Cogon, Msg1337)
4. **Consider NumPy** if vector performance is critical
5. **Add `orjson`** for high-performance serialization
