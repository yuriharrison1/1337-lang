import pytest
import leet
from leet.agent   import agent
from leet.network import AgentNetwork
from leet.response import Response
from leet_vm.types import Cogon


@agent(name="echo_agent")
async def echo_agent(cogon: Cogon, ctx) -> Cogon:
    return await ctx.assert_("echo: processed")


@pytest.fixture
def client():
    return leet.connect("mock")


def test_add_agent_to_network(client):
    net = client.agents(echo_agent)
    assert isinstance(net, AgentNetwork)
    assert "echo_agent" in net._agents


@pytest.mark.asyncio
async def test_network_run_returns_response(client):
    net = client.agents(echo_agent)
    r   = await net.run("test message", to="echo_agent")
    assert isinstance(r, Response)
    assert r.text
