"""Bridge for human ↔ 1337 translation."""

from abc import ABC, abstractmethod
from typing import Optional
import os

from leet.types import Cogon, Dag, FIXED_DIMS
from leet.axes import CANONICAL_AXES, A8_ESTADO, A9_PROCESSO, C1_URGENCIA, C3_ACAO, C5_ANOMALIA, B5_REVERSIBILIDADE


class SemanticProjector(ABC):
    """Interface para qualquer backend de projeção semântica."""

    @abstractmethod
    async def project(self, text: str) -> tuple[list[float], list[float]]:
        """Projeta texto nos 32 eixos. Retorna (sem, unc)."""
        ...

    @abstractmethod
    async def reconstruct(self, cogon: Cogon) -> str:
        """Reconstrói texto a partir de COGON."""
        ...


class MockProjector(SemanticProjector):
    """Projetor determinístico pra testes. Sem API, sem rede."""

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        text_lower = text.lower()
        sem = [0.5] * 32
        unc = [0.2] * 32

        # Heurísticas baseadas em keywords
        if "urgente" in text_lower or "urgência" in text_lower:
            sem[C1_URGENCIA] = 0.95
            sem[C3_ACAO] = 0.9
            unc[C1_URGENCIA] = 0.05
            unc[C3_ACAO] = 0.1

        if "caiu" in text_lower or "falhou" in text_lower or "erro" in text_lower or "down" in text_lower:
            sem[A8_ESTADO] = 0.9
            sem[C5_ANOMALIA] = 0.9
            sem[13] = 0.15  # A13_VALÊNCIA_ONTOLÓGICA (negativo)
            unc[A8_ESTADO] = 0.1
            unc[C5_ANOMALIA] = 0.1

        if "deploy" in text_lower or "processo" in text_lower or "pipeline" in text_lower:
            sem[A9_PROCESSO] = 0.85
            sem[30] = 0.8   # C9_NATUREZA (verbo)
            unc[A9_PROCESSO] = 0.1

        if "reverter" in text_lower or "desfazer" in text_lower or "rollback" in text_lower:
            sem[B5_REVERSIBILIDADE] = 0.9
            sem[C3_ACAO] = 0.85
            unc[B5_REVERSIBILIDADE] = 0.1

        return sem, unc

    async def reconstruct(self, cogon: Cogon) -> str:
        # Encontra os 3 eixos mais ativados
        top_axes = sorted(range(32), key=lambda i: cogon.sem[i], reverse=True)[:3]
        parts = []
        for idx in top_axes:
            ax = CANONICAL_AXES[idx]
            parts.append(f"{ax.name}={cogon.sem[idx]:.2f}")
        return f"[COGON: {', '.join(parts)}]"


class AnthropicProjector(SemanticProjector):
    """Projetor usando a API Anthropic Claude."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        
        # Import condicional
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

    def _projection_prompt(self, text: str) -> str:
        """Gera prompt para projeção nos 32 eixos."""
        lines = [
            "Você é um projetor semântico especializado.",
            "Projete o texto nos 32 eixos canônicos da linguagem 1337.",
            "",
            "EIXOS CANÔNICOS:",
        ]
        for ax in CANONICAL_AXES:
            lines.append(f"[{ax.index:2d}] {ax.code} {ax.name}: {ax.description[:60]}...")
        
        lines.extend([
            "",
            f"TEXTO: \"{text}\"",
            "",
            "Responda APENAS com JSON no formato:",
            '{"sem": [0.0, ..., 0.0], "unc": [0.0, ..., 0.0]}',
        ])
        return "\n".join(lines)

    def _reconstruction_prompt(self, cogon: Cogon) -> str:
        """Gera prompt para reconstrução de texto."""
        lines = ["Reconstrua texto natural a partir desta projeção 1337:"]
        for ax in CANONICAL_AXES:
            s = cogon.sem[ax.index]
            u = cogon.unc[ax.index]
            lines.append(f"  {ax.name}: sem={s:.2f} unc={u:.2f}")
        lines.append("\nTexto reconstruído:")
        return "\n".join(lines)

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        import json
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="Você é um projetor semântico que retorna apenas JSON.",
            messages=[{"role": "user", "content": self._projection_prompt(text)}]
        )
        
        content = response.content[0].text
        # Extrai JSON
        try:
            # Tenta parse direto
            data = json.loads(content)
        except json.JSONDecodeError:
            # Tenta extrair de markdown
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
            system="Você é um reconstrutor semântico. Responda em português.",
            messages=[{"role": "user", "content": self._reconstruction_prompt(cogon)}]
        )
        return response.content[0].text.strip()


# Funções de conveniência
async def encode(text: str, projector: Optional[SemanticProjector] = None) -> Cogon:
    """Texto → COGON."""
    if projector is None:
        projector = MockProjector()
    sem, unc = await projector.project(text)
    return Cogon.new(sem=sem, unc=unc)


async def decode(cogon: Cogon, projector: Optional[SemanticProjector] = None) -> str:
    """COGON → texto."""
    if projector is None:
        projector = MockProjector()
    return await projector.reconstruct(cogon)
