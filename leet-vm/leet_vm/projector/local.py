import hashlib
import logging
from leet_vm.types import Cogon, AXIS_NAMES

logger = logging.getLogger(__name__)

class LocalProjector:
    """
    Offline projector — no network, no leet-service needed.
    mode: "mock" | "pyO3" | "auto" (tries pyO3, falls back to mock)
    """
    def __init__(self, mode: str = "auto"):
        self._mode = mode
        self._core = None
        if mode in ("pyO3", "auto"):
            try:
                import leet_core
                self._core = leet_core
                self._mode = "pyO3"
                logger.info("LocalProjector: using leet_core PyO3 binding")
            except ImportError:
                self._mode = "mock"
                if mode == "pyO3":
                    logger.warning("LocalProjector: leet_core not available, falling back to mock")

    async def project(self, text: str, agent_id: str = "") -> Cogon:
        if self._mode == "pyO3" and self._core:
            return self._project_core(text)
        return self._project_mock(text)

    def _project_mock(self, text: str) -> Cogon:
        h = hashlib.sha256(text.encode()).digest()
        sem = []
        for i in range(32):
            b1 = h[i % 32]
            b2 = h[(i + 1) % 32]
            val = ((b1 << 8 | b2) & 0xFFFF) / 65535.0
            sem.append(val)
        unc = [1.0 - abs(s - 0.5) * 2.0 for s in sem]
        return Cogon(sem=sem, unc=unc)

    def _project_core(self, text: str) -> Cogon:
        result = self._core.project_text(text)
        return Cogon(sem=list(result.sem), unc=list(result.unc))

    async def decode(self, cogon: Cogon) -> str:
        parts = []
        for name, val, u in zip(AXIS_NAMES, cogon.sem, cogon.unc):
            if val > 0.7 and u < 0.5:  # high confidence, meaningful value
                parts.append(f"{name}:{val:.2f}")
        if not parts:
            parts = [f"sem[{i}]:{v:.2f}" for i, v in enumerate(cogon.sem[:8])]
        return " ".join(parts[:8])
