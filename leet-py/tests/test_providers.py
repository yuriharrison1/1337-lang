import pytest
from leet.providers import ProviderAdapter
from leet_vm.types import Cogon


def _make_cogon() -> Cogon:
    sem = [0.5] * 32
    unc = [0.5] * 32
    return Cogon(sem=sem, unc=unc)


@pytest.mark.asyncio
async def test_mock_complete_returns_tuple():
    adapter = ProviderAdapter("mock")
    cogon   = _make_cogon()
    text, tokens = await adapter.complete([], cogon, "hello world")
    assert isinstance(text, str)
    assert text.startswith("[mock response")
    assert isinstance(tokens, int)


def test_openai_preset_resolved():
    adapter = ProviderAdapter("openai", api_key="sk-test", base_url="http://localhost")
    assert adapter.lib == "openai"
    assert adapter.api_key == "sk-test"
    assert adapter.base_url == "http://localhost"
    assert adapter.model == "gpt-4o-mini"


def test_dag_to_prompt_with_context():
    adapter = ProviderAdapter("mock")
    c1      = _make_cogon()
    c2      = _make_cogon()
    msgs    = adapter._dag_to_prompt([c1, c2], _make_cogon(), "what is 1337?")
    assert any(m["role"] == "user" for m in msgs)
    assert any(m["role"] == "system" for m in msgs)
    assert msgs[-1]["content"] == "what is 1337?"
