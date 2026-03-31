import logging
from typing import Optional, Callable
from leet_vm.types import Cogon, VMResult, RawField
from leet_vm.adapters.registry import detect_protocol, ADAPTERS
from leet_vm.projector.service import ServiceProjector
from leet_vm.projector.local   import LocalProjector
from leet_vm.store.personal    import PersonalStore
from leet_vm.store.session     import SessionDAG
from leet_vm.runtime.router    import Router
from leet_vm.runtime.surface   import SurfaceC4

logger = logging.getLogger(__name__)

class LeetVM:
    def __init__(self,
                 mode: str = "auto",
                 service_url: str = "localhost:50051",
                 store_backend: str = "memory"):
        self._mode        = mode
        self._service_url = service_url
        self._projector   = None
        self._store       = PersonalStore(store_backend)
        self._router      = Router()
        self._surface     = SurfaceC4()
        self._sessions: dict[str, SessionDAG] = {}

    async def _get_projector(self):
        if self._projector:
            return self._projector
        if self._mode == "local":
            self._projector = LocalProjector()
        elif self._mode == "service":
            self._projector = ServiceProjector(self._service_url)
        else:  # auto
            try:
                p = ServiceProjector(self._service_url)
                await p.project("test", "")   # probe connection
                self._projector = p
                logger.info("LeetVM: using ServiceProjector at %s", self._service_url)
            except Exception as e:
                logger.warning("LeetVM: service unavailable (%s), falling back to LocalProjector", e)
                self._projector = LocalProjector()
        return self._projector

    def register_agent(self, agent_id: str, handler: Callable) -> None:
        self._router.register(agent_id, handler)

    def set_default_agent(self, handler: Callable) -> None:
        self._router.set_default(handler)

    async def store_count(self, agent_id: str) -> int:
        return await self._store.count(agent_id)

    async def process(self,
                      input: bytes | str | dict,
                      agent_id:     str = "default",
                      session_id:   str = "",
                      protocol:     str = "auto",
                      target_agent: str = "") -> VMResult:

        # 1. detect + decode protocol
        if protocol == "auto":
            protocol = detect_protocol(input)
        adapter = ADAPTERS[protocol]
        frame   = adapter.decode(input)

        # 2. project → COGON
        proj  = await self._get_projector()
        text_for_proj = f"{frame.method or ''} {frame.params}".strip()
        cogon = await proj.project(text_for_proj, agent_id)

        # preserve raw payload as BRIDGE
        cogon.raw = RawField(
            type=f"protocol/{protocol}",
            content=frame.params,
            role="BRIDGE",
        )

        # 3. recall context from PersonalStore
        context_records = await self._store.recall(agent_id, cogon, k=5)
        context_cogons  = [
            Cogon(sem=r["sem"], unc=r["unc"], id=r["cogon_id"], stamp=r["stamp"])
            for r, _ in context_records
        ]

        # 4. DELTA: only what changed since last request in this session
        session      = self._sessions.setdefault(session_id, SessionDAG(session_id))
        prev_stamp   = session.last_stamp()   # snapshot before we add the new ones
        delta_cogons = session.delta_since(prev_stamp) if session.count() > 0 else []

        # 5. route to agent
        context_all  = context_cogons + delta_cogons
        result_cogon = await self._router.route(cogon, context_all, target_agent)

        # 6. persist
        text_hint = (frame.params.get("text") or str(frame.params))[:200]
        await self._store.add(agent_id, cogon, text=text_hint)
        await self._store.add(agent_id, result_cogon)
        session.add(cogon)
        session.add(result_cogon)

        # 7. Surface C4
        text         = self._surface.reconstruct(result_cogon)
        tokens_saved = len(text_hint) // 4  # approx tokens in original text

        return VMResult(
            text=text,
            cogon=result_cogon,
            tokens_saved=tokens_saved,
            session_id=session_id,
        )
