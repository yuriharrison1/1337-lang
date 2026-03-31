from typing import Callable
from leet_vm.vm    import LeetVM
from leet_vm.types import Cogon
from leet.providers import ProviderAdapter
from leet.response  import Response


class AgentNetwork:
    def __init__(self, vm: LeetVM, provider: ProviderAdapter, agent_id: str):
        self._vm       = vm
        self._provider = provider
        self._agent_id = agent_id
        self._agents: dict[str, Callable] = {}

    def add(self, fn: Callable) -> "AgentNetwork":
        name = getattr(fn, "_leet_name", fn.__name__)

        async def handler(cogon: Cogon, context: list) -> Cogon:
            return await fn(cogon, context, vm=self._vm)

        self._vm.register_agent(name, handler)
        self._agents[name] = fn
        return self

    async def run(self, text: str, to: str = "") -> Response:
        result = await self._vm.process(
            input        = text,
            agent_id     = self._agent_id,
            protocol     = "text",
            target_agent = to,
        )
        return Response(
            text         = result.text,
            cogon        = result.cogon,
            tokens_saved = result.tokens_saved,
        )

    async def inject(self, cogon: Cogon, to: str = "") -> Response:
        result_cogon = await self._vm._router.route(cogon, [], to)
        from leet_vm.runtime.surface import SurfaceC4
        text = SurfaceC4().reconstruct(result_cogon)
        return Response(text=text, cogon=result_cogon)
