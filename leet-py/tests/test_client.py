import pytest
import leet
from leet_vm.types import Cogon


@pytest.fixture
def client():
    return leet.connect("mock")


def test_connect_returns_leet_client(client):
    assert isinstance(client, leet.LeetClient)


@pytest.mark.asyncio
async def test_chat_returns_response(client):
    r = await client.chat("hello")
    assert r.text
    assert isinstance(r.text, str)


@pytest.mark.asyncio
async def test_chat_second_call_increments_requests(client):
    await client.chat("hello")
    await client.chat("follow up")
    assert client.stats.requests == 2


@pytest.mark.asyncio
async def test_recall_returns_list(client):
    await client.chat("hello")  # populate store first
    results = await client.recall("hello", k=3)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_remember_no_error(client):
    await client.remember("important fact")


@pytest.mark.asyncio
async def test_encode_returns_cogon(client):
    cogon = await client.encode("test")
    assert isinstance(cogon, Cogon)
    assert len(cogon.sem) == 32


def test_stats_tokens_saved_non_negative(client):
    assert client.stats.tokens_saved >= 0
