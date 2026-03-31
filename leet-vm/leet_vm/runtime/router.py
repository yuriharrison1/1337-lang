from typing import Callable, Optional
from leet_vm.types import Cogon

class Router:
    def __init__(self):
        self._agents: dict[str, Callable] = {}
        self._default: Optional[Callable] = None

    def register(self, agent_id: str, handler: Callable) -> None:
        self._agents[agent_id] = handler

    def set_default(self, handler: Callable) -> None:
        self._default = handler

    async def route(self, cogon: Cogon, context: list,
                    target_agent: str = "") -> Cogon:
        handler = self._agents.get(target_agent) or self._default
        if not handler:
            raise ValueError(
                f"No agent registered for '{target_agent}' and no default"
            )
        return await handler(cogon, context)
