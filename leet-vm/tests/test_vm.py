import pytest
from leet_vm.vm    import LeetVM
from leet_vm.types import Cogon, VMResult

# ── mock agent ────────────────────────────────────────────────────────────────

async def echo_agent(cogon: Cogon, context: list) -> Cogon:
    """Echo handler: returns the input cogon unchanged."""
    return cogon

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_vm() -> LeetVM:
    vm = LeetVM(mode="local")
    vm.set_default_agent(echo_agent)
    return vm

# ── basic process ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_plain_text():
    vm  = _make_vm()
    res = await vm.process("hello", agent_id="test")
    assert isinstance(res, VMResult)
    assert isinstance(res.text, str)
    assert len(res.text) > 0
    assert res.cogon is not None
    assert res.tokens_saved >= 0

@pytest.mark.asyncio
async def test_process_sets_session_id():
    vm  = _make_vm()
    res = await vm.process("hello", agent_id="test", session_id="my-session")
    assert res.session_id == "my-session"

@pytest.mark.asyncio
async def test_process_json_rpc():
    vm      = _make_vm()
    payload = '{"jsonrpc":"2.0","method":"ping","params":{},"id":"1"}'
    res     = await vm.process(payload, agent_id="test")
    assert isinstance(res, VMResult)
    assert res.cogon is not None

@pytest.mark.asyncio
async def test_process_mcp():
    vm      = _make_vm()
    payload = {"type": "tool_use", "name": "summarize", "input": {"text": "hi"}, "id": "m1"}
    res     = await vm.process(payload, agent_id="test")
    assert isinstance(res, VMResult)

@pytest.mark.asyncio
async def test_process_named_agent():
    results = []

    async def custom_agent(cogon: Cogon, context: list) -> Cogon:
        results.append("called")
        return cogon

    vm = LeetVM(mode="local")
    vm.register_agent("custom", custom_agent)
    await vm.process("hello", agent_id="test", target_agent="custom")
    assert results == ["called"]

@pytest.mark.asyncio
async def test_process_accumulates_store():
    vm = _make_vm()
    for i in range(3):
        await vm.process(f"message {i}", agent_id="acc-agent")
    count = await vm.store_count("acc-agent")
    # each process adds input + result cogon = 2 per call → 6
    assert count == 6

@pytest.mark.asyncio
async def test_no_default_agent_raises():
    vm = LeetVM(mode="local")   # no agent registered
    with pytest.raises(ValueError, match="No agent"):
        await vm.process("hello")

# ── surface c4 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_surface_output_non_empty():
    vm  = _make_vm()
    res = await vm.process("surface test")
    assert len(res.text) > 0
