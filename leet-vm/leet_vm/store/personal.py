import numpy as np
from typing import Optional
from leet_vm.types import Cogon

class PersonalStore:
    """
    Stores COGONs per agent. Provides semantic recall via DIST.
    backend: 'memory' (default) | 'redis://...' | 'sqlite://...'
    """
    def __init__(self, backend: str = "memory"):
        self._backend = backend
        self._data: dict[str, list[dict]] = {}
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

    async def recall(self, agent_id: str, query: Cogon,
                     k: int = 5) -> list[tuple[dict, float]]:
        """Returns list of (record, dist) sorted ascending by dist (closest first)."""
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

    def _dist(self, sem1: list, unc1: list,
               sem2: list, unc2: list) -> float:
        """Weighted cosine distance. Uncertain dims contribute less."""
        s1 = np.array(sem1, dtype=np.float32)
        s2 = np.array(sem2, dtype=np.float32)
        u1 = np.array(unc1, dtype=np.float32)
        u2 = np.array(unc2, dtype=np.float32)
        w   = (1 - u1) * (1 - u2)
        dot = float(np.sum(s1 * s2 * w))
        n1  = float(np.sqrt(np.sum(s1**2 * w)) + 1e-8)
        n2  = float(np.sqrt(np.sum(s2**2 * w)) + 1e-8)
        sim = dot / (n1 * n2)
        return 1.0 - sim
