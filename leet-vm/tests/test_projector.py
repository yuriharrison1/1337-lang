import pytest
import asyncio
from leet_vm.projector.local import LocalProjector

@pytest.mark.asyncio
async def test_project_returns_cogon():
    p = LocalProjector(mode="mock")
    c = await p.project("hello world")
    assert len(c.sem) == 32
    assert len(c.unc) == 32

@pytest.mark.asyncio
async def test_project_values_in_range():
    p = LocalProjector(mode="mock")
    c = await p.project("test input")
    for v in c.sem:
        assert 0.0 <= v <= 1.0, f"sem value out of range: {v}"
    for v in c.unc:
        assert 0.0 <= v <= 1.0, f"unc value out of range: {v}"

@pytest.mark.asyncio
async def test_project_deterministic():
    p = LocalProjector(mode="mock")
    c1 = await p.project("hello world")
    c2 = await p.project("hello world")
    assert c1.sem == c2.sem
    assert c1.unc == c2.unc

@pytest.mark.asyncio
async def test_project_different_texts_differ():
    p = LocalProjector(mode="mock")
    c1 = await p.project("hello world")
    c2 = await p.project("goodbye world")
    assert c1.sem != c2.sem

@pytest.mark.asyncio
async def test_decode_returns_string():
    p = LocalProjector(mode="mock")
    c = await p.project("test decode")
    text = await p.decode(c)
    assert isinstance(text, str)
    assert len(text) > 0

@pytest.mark.asyncio
async def test_auto_mode_falls_back_to_mock():
    # leet_core is not installed in test env, so auto should use mock
    p = LocalProjector(mode="auto")
    c = await p.project("auto mode test")
    assert len(c.sem) == 32
