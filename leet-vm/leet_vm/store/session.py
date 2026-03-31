import time
from leet_vm.types import Cogon

class SessionDAG:
    """Tracks the current session's COGONs for DELTA compression."""

    def __init__(self, session_id: str):
        self.session_id  = session_id
        self.start_stamp = time.time_ns()
        self._cogons: list[Cogon] = []

    def add(self, cogon: Cogon) -> None:
        self._cogons.append(cogon)

    def delta_since(self, stamp: int) -> list[Cogon]:
        return [c for c in self._cogons if c.stamp > stamp]

    def last_stamp(self) -> int:
        if not self._cogons:
            return self.start_stamp
        return self._cogons[-1].stamp

    def count(self) -> int:
        return len(self._cogons)
