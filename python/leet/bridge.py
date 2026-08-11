"""Bridge for human ↔ 1337 translation."""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional
import os

from leet.types import Cogon, Dag, FIXED_DIMS
from leet.axes import (
    CANONICAL_AXES,
    A8_ESTADO, A9_PROCESSO, A13_VALENCIA_ONTOLOGICA,
    B5_REVERSIBILIDADE,
    C1_URGENCIA, C3_ACAO, C5_ANOMALIA, C9_NATUREZA,
)


class SemanticProjector(ABC):
    """Interface for any semantic projection backend."""

    @abstractmethod
    async def project(self, text: str) -> tuple[list[float], list[float]]:
        """Projects text onto the 32 axes. Returns (sem, unc)."""
        ...

    @abstractmethod
    async def reconstruct(self, cogon: Cogon) -> str:
        """Reconstructs text from a COGON."""
        ...


class MockProjector(SemanticProjector):
    """Deterministic projector for tests. No API, no network."""

    def __init__(self, cache_size: int = 1000):
        self._cache: dict[str, tuple[list[float], list[float]]] = {}
        self._cache_order: list[str] = []  # LRU order
        self._cache_size = cache_size

    def _get_cached(self, text: str) -> Optional[tuple[list[float], list[float]]]:
        """Get from LRU cache."""
        if text in self._cache:
            # Move to end (most recently used)
            self._cache_order.remove(text)
            self._cache_order.append(text)
            return self._cache[text]
        return None

    def _set_cached(self, text: str, result: tuple[list[float], list[float]]) -> None:
        """Set in LRU cache."""
        if text in self._cache:
            self._cache_order.remove(text)
        elif len(self._cache) >= self._cache_size:
            # Evict least recently used
            lru = self._cache_order.pop(0)
            del self._cache[lru]

        self._cache[text] = result
        self._cache_order.append(text)

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        # Check cache first
        cached = self._get_cached(text)
        if cached is not None:
            return cached

        text_lower = text.lower()
        sem = [0.5] * 32
        unc = [0.2] * 32

        # Keyword-based heuristics
        if "urgente" in text_lower or "urgência" in text_lower:
            sem[C1_URGENCIA] = 0.95
            sem[C3_ACAO] = 0.9
            unc[C1_URGENCIA] = 0.05
            unc[C3_ACAO] = 0.1

        if "caiu" in text_lower or "falhou" in text_lower or "erro" in text_lower or "down" in text_lower:
            sem[A8_ESTADO] = 0.9
            sem[C5_ANOMALIA] = 0.9
            sem[A13_VALENCIA_ONTOLOGICA] = 0.15  # negative valence
            unc[A8_ESTADO] = 0.1
            unc[C5_ANOMALIA] = 0.1

        if "deploy" in text_lower or "processo" in text_lower or "pipeline" in text_lower:
            sem[A9_PROCESSO] = 0.85
            sem[C9_NATUREZA] = 0.8   # verb/action
            unc[A9_PROCESSO] = 0.1

        if "reverter" in text_lower or "desfazer" in text_lower or "rollback" in text_lower:
            sem[B5_REVERSIBILIDADE] = 0.9
            sem[C3_ACAO] = 0.85
            unc[B5_REVERSIBILIDADE] = 0.1

        result = (sem, unc)
        self._set_cached(text, result)
        return result

    async def reconstruct(self, cogon: Cogon) -> str:
        # Find the 3 most activated axes
        top_axes = sorted(range(32), key=lambda i: cogon.sem[i], reverse=True)[:3]
        parts = []
        for idx in top_axes:
            ax = CANONICAL_AXES[idx]
            parts.append(f"{ax.name}={cogon.sem[idx]:.2f}")
        return f"[COGON: {', '.join(parts)}]"


class AnthropicProjector(SemanticProjector):
    """Projector using the Anthropic Claude API."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

        # Conditional import
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def _projection_prompt(self, text: str) -> str:
        """Generates the prompt for projection onto the 32 axes."""
        lines = [
            "You are a specialized semantic projector.",
            "Project the text onto the 32 canonical axes of the 1337 language.",
            "",
            "CANONICAL AXES:",
        ]
        for ax in CANONICAL_AXES:
            lines.append(f"[{ax.index:2d}] {ax.code} {ax.name}: {ax.description[:60]}...")

        lines.extend([
            "",
            f"TEXT: \"{text}\"",
            "",
            "Respond ONLY with JSON in the format:",
            '{"sem": [0.0, ..., 0.0], "unc": [0.0, ..., 0.0]}',
        ])
        return "\n".join(lines)

    def _reconstruction_prompt(self, cogon: Cogon) -> str:
        """Generates the prompt for text reconstruction."""
        lines = ["Reconstruct natural text from this 1337 projection:"]
        for ax in CANONICAL_AXES:
            s = cogon.sem[ax.index]
            u = cogon.unc[ax.index]
            lines.append(f"  {ax.name}: sem={s:.2f} unc={u:.2f}")
        lines.append("\nReconstructed text:")
        return "\n".join(lines)

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        import json

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="You are a semantic projector that returns only JSON.",
            messages=[{"role": "user", "content": self._projection_prompt(text)}]
        )

        content = response.content[0].text
        # Extract JSON
        try:
            # Try direct parse
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try extracting from markdown
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                data = json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
                data = json.loads(json_str)
            else:
                raise ValueError(f"Could not parse JSON from: {content}")

        return data["sem"], data["unc"]

    async def reconstruct(self, cogon: Cogon) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            system="You are a semantic reconstructor. Respond in Portuguese.",
            messages=[{"role": "user", "content": self._reconstruction_prompt(cogon)}]
        )
        return response.content[0].text.strip()


# Convenience functions
async def encode(text: str, projector: Optional[SemanticProjector] = None) -> Cogon:
    """Text → COGON."""
    if projector is None:
        projector = MockProjector()
    sem, unc = await projector.project(text)
    return Cogon.new(sem=sem, unc=unc)


async def decode(cogon: Cogon, projector: Optional[SemanticProjector] = None) -> str:
    """COGON → text."""
    if projector is None:
        projector = MockProjector()
    return await projector.reconstruct(cogon)
