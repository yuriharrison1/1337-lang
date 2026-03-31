import time
import pytest
from leet_vm.store.personal import PersonalStore
from leet_vm.store.session  import SessionDAG
from leet_vm.types import Cogon

def _cogon(offset: float = 0.0) -> Cogon:
    sem = [(i / 32.0 + offset) % 1.0 for i in range(32)]
    unc = [0.3] * 32
    return Cogon(sem=sem, unc=unc)

# ── PersonalStore ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_and_count():
    store = PersonalStore()
    for _ in range(5):
        await store.add("agent1", _cogon())
    assert await store.count("agent1") == 5

@pytest.mark.asyncio
async def test_recall_returns_at_most_k():
    store = PersonalStore()
    for i in range(5):
        await store.add("agent1", _cogon(i * 0.1))
    query   = _cogon(0.0)
    results = await store.recall("agent1", query, k=3)
    assert len(results) <= 3

@pytest.mark.asyncio
async def test_recall_sorted_ascending():
    store = PersonalStore()
    for i in range(5):
        await store.add("agent1", _cogon(i * 0.15))
    query   = _cogon(0.0)
    results = await store.recall("agent1", query, k=5)
    dists   = [d for _, d in results]
    assert dists == sorted(dists), "distances should be ascending"

@pytest.mark.asyncio
async def test_recall_empty_store():
    store   = PersonalStore()
    results = await store.recall("nobody", _cogon(), k=5)
    assert results == []

@pytest.mark.asyncio
async def test_delta_context():
    store = PersonalStore()
    c1 = _cogon(0.1)
    await store.add("agent2", c1)
    cutoff = time.time_ns()
    c2 = _cogon(0.2)   # stamp is set at creation → after cutoff
    await store.add("agent2", c2)
    delta = await store.delta_context("agent2", cutoff)
    assert len(delta) == 1
    assert delta[0]["cogon_id"] == c2.id

# ── SessionDAG ────────────────────────────────────────────────────────────────

def test_session_add_and_count():
    s = SessionDAG("sess-1")
    assert s.count() == 0
    s.add(_cogon())
    s.add(_cogon())
    assert s.count() == 2

def test_session_last_stamp():
    s  = SessionDAG("sess-2")
    c1 = _cogon()
    c2 = _cogon(0.5)
    s.add(c1)
    s.add(c2)
    assert s.last_stamp() == c2.stamp

def test_session_delta_since():
    s      = SessionDAG("sess-3")
    c1     = _cogon()
    cutoff = time.time_ns()
    c2     = _cogon(0.5)
    s.add(c1)
    s.add(c2)
    delta = s.delta_since(cutoff)
    # c2 was added after cutoff
    assert c2 in delta
