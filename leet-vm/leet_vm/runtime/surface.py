from leet_vm.types import Cogon, AXIS_NAMES

class SurfaceC4:
    """Surface C4: COGON → natural language. Deterministic, not generative."""

    def reconstruct(self, cogon: Cogon, depth: int = 3) -> str:
        if cogon.raw and hasattr(cogon.raw, "content"):
            if isinstance(cogon.raw.content, str):
                return cogon.raw.content
            if isinstance(cogon.raw.content, dict):
                return str(cogon.raw.content)

        # build from sem values — most confident and most extreme dims first
        axes = list(zip(AXIS_NAMES, cogon.sem, cogon.unc))
        axes_scored = [
            (name, val, unc, (1 - unc) * abs(val - 0.5) * 2)
            for name, val, unc in axes
        ]
        axes_scored.sort(key=lambda x: x[3], reverse=True)

        parts = []
        for name, val, unc, _ in axes_scored[:depth]:
            level = "alto" if val > 0.6 else ("baixo" if val < 0.4 else "médio")
            conf  = "alta certeza" if unc < 0.3 else ("incerto" if unc > 0.7 else "")
            desc  = f"{name}={level}"
            if conf:
                desc += f" ({conf})"
            parts.append(desc)

        return "[COGON: " + ", ".join(parts) + "]"
