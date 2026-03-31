import uuid
from typing import AsyncIterator
from leet_vm.vm    import LeetVM
from leet_vm.types import Cogon, RawField
from leet.providers import ProviderAdapter
from leet.response  import Response
from leet.stats     import Stats


class LeetClient:
    def __init__(self, vm: LeetVM, provider: ProviderAdapter, agent_id: str = "default"):
        self._vm         = vm
        self._provider   = provider
        self._agent_id   = agent_id
        self._session_id = str(uuid.uuid4())
        self._stats      = Stats()
        self._last_stamp = 0

        self._vm.set_default_agent(self._llm_agent)

    async def _llm_agent(self, cogon: Cogon, context: list) -> Cogon:
        """Bridge between the 1337 runtime and the LLM provider."""
        query_text = ""
        if cogon.raw and isinstance(cogon.raw.content, dict):
            query_text = str(cogon.raw.content)
        elif cogon.raw and isinstance(cogon.raw.content, str):
            query_text = cogon.raw.content

        resp_text, tokens_used = await self._provider.complete(context, cogon, query_text)
        self._stats.tokens_used += tokens_used

        proj = await self._vm._get_projector()
        resp_cogon = await proj.project(resp_text, self._agent_id)
        resp_cogon.raw = RawField(type="text/plain", content=resp_text, role="ARTIFACT")
        return resp_cogon

    async def chat(self, text: str) -> Response:
        """
        Send a message. Memory, context, and compression are automatic.
        Returns Response with .text and .tokens_saved.
        """
        result = await self._vm.process(
            input      = text,
            agent_id   = self._agent_id,
            session_id = self._session_id,
            protocol   = "text",
        )
        self._stats.tokens_saved += result.tokens_saved
        self._stats.requests     += 1
        self._stats.cogons_stored = await self._vm._store.count(self._agent_id)
        self._last_stamp = result.cogon.stamp

        return Response(
            text         = result.text,
            cogon        = result.cogon,
            tokens_saved = result.tokens_saved,
            model        = self._provider.model,
            provider     = self._provider.provider,
            session_id   = self._session_id,
        )

    async def chat_stream(self, text: str) -> AsyncIterator[str]:
        """Streaming version of chat."""
        proj  = await self._vm._get_projector()
        cogon = await proj.project(text, self._agent_id)
        await self._vm._store.add(self._agent_id, cogon, text=text)

        context_records = await self._vm._store.recall(self._agent_id, cogon, k=3)
        context_cogons  = [
            Cogon(sem=r["sem"], unc=r["unc"], id=r["cogon_id"])
            for r, _ in context_records
        ]

        async for token in self._provider.stream(context_cogons, cogon, text):
            yield token

    def agents(self, *agent_fns) -> "AgentNetwork":
        from leet.network import AgentNetwork
        net = AgentNetwork(vm=self._vm, provider=self._provider,
                           agent_id=self._agent_id)
        for fn in agent_fns:
            net.add(fn)
        return net

    async def recall(self, query: str, k: int = 5) -> list[dict]:
        """Semantic search in PersonalStore. No embedding setup needed."""
        proj    = await self._vm._get_projector()
        cogon   = await proj.project(query, self._agent_id)
        results = await self._vm._store.recall(self._agent_id, cogon, k=k)
        return [
            {"text": r.get("text", ""), "dist": d,
             "stamp": r["stamp"], "cogon_id": r["cogon_id"]}
            for r, d in results
        ]

    async def remember(self, text: str) -> None:
        """Explicitly add to PersonalStore."""
        proj  = await self._vm._get_projector()
        cogon = await proj.project(text, self._agent_id)
        await self._vm._store.add(self._agent_id, cogon, text=text)
        self._stats.cogons_stored += 1

    async def encode(self, text: str) -> Cogon:
        proj = await self._vm._get_projector()
        return await proj.project(text, self._agent_id)

    async def decode(self, cogon: Cogon) -> str:
        proj = await self._vm._get_projector()
        return await proj.decode(cogon)

    @property
    def stats(self) -> Stats:
        return self._stats

    @property
    def session_id(self) -> str:
        return self._session_id

    def new_session(self) -> None:
        """Start a fresh session (DELTA resets)."""
        self._session_id = str(uuid.uuid4())
        self._last_stamp = 0
