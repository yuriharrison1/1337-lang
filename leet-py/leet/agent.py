import functools
from typing import Callable
from leet_vm.types import Cogon


class AgentContext:
    def __init__(self, agent_id: str, context: list, vm):
        self.agent_id = agent_id
        self.history  = context
        self._vm      = vm

    async def assert_(self, content) -> Cogon:
        """Build a response COGON from text or dict."""
        from leet_vm.types import RawField
        proj  = await self._vm._get_projector()
        text  = content if isinstance(content, str) else str(content)
        cogon = await proj.project(text, self.agent_id)
        cogon.raw = RawField(type="text/plain", content=text, role="ARTIFACT")
        return cogon


def agent(name: str = "", backend: str = "default"):
    """
    Decorator to register a function as a 1337 agent.

    Usage:
        @agent(name="analisador")
        async def analisador(cogon: Cogon, ctx: AgentContext) -> Cogon:
            ...
            return ctx.assert_("resultado da análise")
    """
    def decorator(fn: Callable) -> Callable:
        fn._leet_agent   = True
        fn._leet_name    = name or fn.__name__
        fn._leet_backend = backend

        @functools.wraps(fn)
        async def wrapper(cogon: Cogon, context: list, vm=None) -> Cogon:
            ctx = AgentContext(fn._leet_name, context, vm)
            return await fn(cogon, ctx)

        wrapper._leet_agent   = True
        wrapper._leet_name    = fn._leet_name
        wrapper._leet_backend = backend
        return wrapper

    return decorator
