from dataclasses import dataclass, field

@dataclass
class Stats:
    tokens_saved:  int = 0
    tokens_used:   int = 0
    cogons_stored: int = 0
    sessions:      int = 0
    requests:      int = 0

    @property
    def savings_pct(self) -> float:
        total = self.tokens_saved + self.tokens_used
        if total == 0:
            return 0.0
        return round(self.tokens_saved / total * 100, 1)

    def __repr__(self) -> str:
        return (f"Stats(requests={self.requests}, "
                f"tokens_saved={self.tokens_saved} ({self.savings_pct}%), "
                f"cogons={self.cogons_stored})")
