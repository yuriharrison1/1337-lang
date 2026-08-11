"""
Context-Aware Projection for 1337.

This module implements semantic projection adjustment based on conversation
context, allowing the system to adapt projections according to the domain
and history of the interaction.

The context is represented as a cumulative COGON that emphasizes or
attenuates certain semantic axes based on recent history.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from collections import deque

from leet.types import Cogon, FIXED_DIMS
from leet.operators import blend, dist
from leet.axes import (
    CANONICAL_AXES, AxisGroup,
    A0_VIA, A1_CORRESPONDENCIA, A2_VIBRACAO, A3_POLARIDADE,
    A4_RITMO, A5_CAUSA_EFEITO, A6_GENERO, A7_SISTEMA,
    A8_ESTADO, A9_PROCESSO, A10_RELACAO, A11_SINAL,
    A12_ESTABILIDADE, A13_VALENCIA_ONTOLOGICA,
    B1_VERIFICABILIDADE, B2_TEMPORALIDADE, B3_COMPLETUDE,
    B4_CAUSALIDADE, B5_REVERSIBILIDADE, B6_CARGA,
    B7_ORIGEM, B8_VALENCIA_EPISTEMICA,
    C1_URGENCIA, C2_IMPACTO, C3_ACAO, C4_VALOR,
    C5_ANOMALIA, C6_AFETO, C7_DEPENDENCIA, C8_VETOR_TEMPORAL,
    C9_NATUREZA, C10_VALENCIA_ACAO,
)


@dataclass
class ContextProfile:
    """
    Context profile representing a domain or conversational state.

    A profile emphasizes certain semantic axes and attenuates others,
    creating a "lens" through which texts are projected.
    """
    name: str
    description: str
    # Adjustment vector for each axis (0.5 = neutral, >0.5 = emphasize, <0.5 = attenuate)
    axis_weights: list[float] = field(default_factory=lambda: [0.5] * FIXED_DIMS)
    # Projection temperature (the higher, the more extreme the values)
    temperature: float = 1.0
    # Axes that are especially relevant in this context
    dominant_axes: list[int] = field(default_factory=list)
    # Metadata
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def __post_init__(self):
        if len(self.axis_weights) != FIXED_DIMS:
            raise ValueError(f"axis_weights must have {FIXED_DIMS} elements")
        self.axis_weights = [max(0.0, min(1.0, w)) for w in self.axis_weights]
        self.temperature = max(0.1, min(2.0, self.temperature))

    def to_cogon(self) -> Cogon:
        """Converts this profile into an adjustment COGON."""
        # sem = weights adjusted to stay within [0, 1]
        sem = [0.5 + (w - 0.5) * self.temperature for w in self.axis_weights]
        # unc = lower for dominant axes (more confidence)
        unc = [0.3 if i in self.dominant_axes else 0.5 for i in range(FIXED_DIMS)]
        return Cogon.new(sem=sem, unc=unc)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "axis_weights": self.axis_weights,
            "temperature": self.temperature,
            "dominant_axes": self.dominant_axes,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ContextProfile:
        return cls(
            name=d["name"],
            description=d["description"],
            axis_weights=d.get("axis_weights", [0.5] * FIXED_DIMS),
            temperature=d.get("temperature", 1.0),
            dominant_axes=d.get("dominant_axes", []),
            created_at=d.get("created_at", time.time()),
            usage_count=d.get("usage_count", 0),
        )


class ContextManager:
    """
    Context manager for 1337 projections.

    Maintains a history of recent COGONs and computes an accumulated context
    that can be used to adjust new projections.
    """

    # Pre-defined context profiles for common domains
    BUILTIN_PROFILES: dict[str, ContextProfile] = {
        "technical": ContextProfile(
            name="technical",
            description="Technical/engineering context - focus on systems, processes, states",
            axis_weights=[
                0.5, 0.5, 0.4, 0.5,  # A0-A3: neutral
                0.5, 0.7, 0.6, 0.9,  # A4-A7: system, active causality
                0.9, 0.9, 0.7, 0.8,  # A8-A11: state, process, signal
                0.6, 0.5,            # A12-A13: moderate stability
                0.8, 0.6, 0.7, 0.8,  # B1-B4: verifiable, causal
                0.7, 0.6, 0.8, 0.6,  # B5-B8: reversibility, observed origin
                0.5, 0.8, 0.7, 0.5,  # C1-C4: high impact, action
                0.7, 0.4, 0.8, 0.5,  # C5-C8: detectable anomaly, dependency
                0.5, 0.5,            # C9-C10: neutral
            ],
            temperature=1.1,
            dominant_axes=[A7_SISTEMA, A8_ESTADO, A9_PROCESSO, B1_VERIFICABILIDADE, C2_IMPACTO],
        ),

        "emergency": ContextProfile(
            name="emergency",
            description="Emergency/crisis context - urgency, anomaly, action",
            axis_weights=[
                0.6, 0.5, 0.8, 0.7,  # A0-A3: high vibration (change)
                0.6, 0.9, 0.8, 0.7,  # A4-A7: active causality
                0.9, 0.9, 0.6, 0.9,  # A8-A11: critical state, signal
                0.2, 0.3,            # A12-A13: instability, negative valence
                0.7, 0.9, 0.9, 0.8,  # B1-B4: verifiable, temporal, complete
                0.4, 0.9, 0.9, 0.2,  # B5-B8: irreversible, high load, negative evidence
                1.0, 1.0, 1.0, 0.9,  # C1-C4: maximum urgency, impact, action
                1.0, 0.9, 0.7, 0.9,  # C5-C10: maximum anomaly, affect, future
                0.8, 0.2,            # C9-C10: verb/action, alert
            ],
            temperature=1.3,
            dominant_axes=[C1_URGENCIA, C2_IMPACTO, C3_ACAO, C5_ANOMALIA, A9_PROCESSO],
        ),

        "philosophical": ContextProfile(
            name="philosophical",
            description="Philosophical/conceptual context - abstraction, correspondence, nature",
            axis_weights=[
                0.9, 0.9, 0.7, 0.8,  # A0-A3: high via, correspondence, polarity
                0.6, 0.6, 0.7, 0.8,  # A4-A7: rhythm, causality, system
                0.5, 0.6, 0.8, 0.7,  # A8-A11: relation, high signal
                0.5, 0.5,            # A12-A13: neutral stability
                0.4, 0.3, 0.3, 0.4,  # B1-B4: less verifiable, diffuse temporality
                0.5, 0.8, 0.4, 0.5,  # B5-B8: high cognitive load, inferred origin
                0.2, 0.3, 0.4, 0.8,  # C1-C4: no urgency, high value
                0.3, 0.5, 0.6, 0.5,  # C5-C8: no anomaly
                0.3, 0.5,            # C9-C10: noun/state
            ],
            temperature=0.9,
            dominant_axes=[A0_VIA, A1_CORRESPONDENCIA, A10_RELACAO, C4_VALOR],
        ),

        "planning": ContextProfile(
            name="planning",
            description="Planning context - future, process, reversibility",
            axis_weights=[
                0.5, 0.6, 0.6, 0.5,  # A0-A3: neutral
                0.7, 0.8, 0.7, 0.8,  # A4-A7: rhythm, active causality, system
                0.5, 0.9, 0.7, 0.6,  # A8-A11: high process, relation
                0.6, 0.7,            # A12-A13: stability, positive valence
                0.6, 0.8, 0.4, 0.7,  # B1-B4: defined temporality, causality
                0.9, 0.7, 0.6, 0.7,  # B5-B8: high reversibility (plans change)
                0.5, 0.6, 0.8, 0.7,  # C1-C4: high action, value
                0.3, 0.4, 0.5, 1.0,  # C5-C8: no anomaly, temporal vector = future
                0.7, 0.8,            # C9-C10: verb/action, positive intention
            ],
            temperature=1.0,
            dominant_axes=[A9_PROCESSO, B5_REVERSIBILIDADE, C3_ACAO, C8_VETOR_TEMPORAL],
        ),

        "social": ContextProfile(
            name="social",
            description="Social/interpersonal context - affect, relation, communication",
            axis_weights=[
                0.5, 0.5, 0.6, 0.5,  # A0-A3: neutral
                0.5, 0.5, 0.6, 0.7,  # A4-A7: active gender, social system
                0.5, 0.5, 0.9, 0.8,  # A8-A11: high relation, signal
                0.5, 0.6,            # A12-A13: neutral, slightly positive
                0.4, 0.5, 0.4, 0.4,  # B1-B4: subjective
                0.5, 0.5, 0.4, 0.5,  # B5-B8: inferred
                0.3, 0.4, 0.5, 0.8,  # C1-C4: no urgency, high personal value
                0.2, 0.9, 0.6, 0.5,  # C5-C10: low anomaly, high affect
                0.4, 0.6,            # C9-C10: neutral
            ],
            temperature=0.95,
            dominant_axes=[A10_RELACAO, A11_SINAL, C4_VALOR, C6_AFETO],
        ),
    }

    def __init__(self, window_size: int = 10, decay_factor: float = 0.8):
        """
        Args:
            window_size: Number of recent COGONs to keep in history
            decay_factor: Decay factor for older COGONs (0-1)
        """
        self.window_size = window_size
        self.decay_factor = decay_factor
        self.history: deque[Cogon] = deque(maxlen=window_size)
        self.current_profile: Optional[ContextProfile] = None
        self.custom_profiles: dict[str, ContextProfile] = {}
        self._context_cogon: Optional[Cogon] = None
        self._last_update: float = 0

    def set_profile(self, profile_name: str) -> ContextProfile:
        """Sets the active context profile."""
        if profile_name in self.BUILTIN_PROFILES:
            self.current_profile = self.BUILTIN_PROFILES[profile_name]
        elif profile_name in self.custom_profiles:
            self.current_profile = self.custom_profiles[profile_name]
        else:
            raise ValueError(f"Profile '{profile_name}' not found. "
                           f"Available: {list(self.BUILTIN_PROFILES.keys()) + list(self.custom_profiles.keys())}")

        self.current_profile.usage_count += 1
        self._invalidate_cache()
        return self.current_profile

    def add_to_history(self, cogon: Cogon) -> None:
        """Adds a COGON to the context history."""
        self.history.append(cogon)
        self._invalidate_cache()

    def get_context_cogon(self, alpha: float = 0.3) -> Optional[Cogon]:
        """
        Computes the current context COGON.

        This COGON represents the accumulated "mental state" of the conversation
        and can be used to adjust new projections via BLEND.

        Args:
            alpha: Context weight when blending (0 = ignore context, 1 = context only)

        Returns:
            COGON representing the accumulated context, or None if there is no history
        """
        # Check cache
        if self._context_cogon is not None:
            return self._context_cogon

        if not self.history and self.current_profile is None:
            return None

        # Start with the current profile, if any
        if self.current_profile is not None:
            base = self.current_profile.to_cogon()
        else:
            # Start with a neutral COGON
            base = Cogon.new(sem=[0.5] * FIXED_DIMS, unc=[0.5] * FIXED_DIMS)

        # Incorporate history with decay
        if self.history:
            weights = [self.decay_factor ** i for i in range(len(self.history))]
            total_weight = sum(weights)

            # Compute weighted average of sem/unc from history
            hist_sem = [0.0] * FIXED_DIMS
            hist_unc = [0.0] * FIXED_DIMS

            for i, cogon in enumerate(reversed(self.history)):
                w = weights[i] / total_weight
                for j in range(FIXED_DIMS):
                    hist_sem[j] += cogon.sem[j] * w
                    hist_unc[j] += cogon.unc[j] * w

            hist_cogon = Cogon.new(sem=hist_sem, unc=hist_unc)

            # BLEND between profile and history
            base = blend(base, hist_cogon, alpha=0.5)

        self._context_cogon = base
        self._last_update = time.time()
        return base

    def adjust_projection(
        self,
        sem: list[float],
        unc: list[float],
        context_alpha: float = 0.2,
    ) -> tuple[list[float], list[float]]:
        """
        Adjusts a projection based on the current context.

        Args:
            sem: Original semantic vector (32 dims)
            unc: Original uncertainty vector (32 dims)
            context_alpha: How much to mix in the context (0-1)

        Returns:
            (adjusted_sem, adjusted_unc)
        """
        context_cogon = self.get_context_cogon()
        if context_cogon is None or context_alpha <= 0:
            return sem, unc

        # Create COGON for the original projection
        original = Cogon.new(sem=sem, unc=unc)

        # BLEND with context
        adjusted = blend(original, context_cogon, alpha=1 - context_alpha)

        return adjusted.sem, adjusted.unc

    def detect_context_drift(self, threshold: float = 0.5) -> Optional[str]:
        """
        Detects whether the context has changed significantly.

        Compares the most recent COGON with the accumulated context.
        If the distance is high, it suggests a context shift.

        Returns:
            Message describing the detected drift, or None
        """
        if len(self.history) < 2:
            return None

        recent = self.history[-1]
        context = self.get_context_cogon()
        if context is None:
            return None

        distance = dist(recent, context)
        if distance > threshold:
            return f"Context drift detected: distance={distance:.3f} > {threshold}"
        return None

    def auto_select_profile(self, sample_text: str, project_fn: Callable[[str], tuple[list[float], list[float]]]) -> ContextProfile:
        """
        Automatically selects the best-suited profile for a text.

        Args:
            sample_text: Sample text for analysis
            project_fn: Projection function (text -> (sem, unc))

        Returns:
            Best-suited profile
        """
        sem, unc = project_fn(sample_text)
        sample_cogon = Cogon.new(sem=sem, unc=unc)

        best_profile = None
        best_score = float('inf')

        all_profiles = {**self.BUILTIN_PROFILES, **self.custom_profiles}

        for name, profile in all_profiles.items():
            profile_cogon = profile.to_cogon()
            distance = dist(sample_cogon, profile_cogon)
            if distance < best_score:
                best_score = distance
                best_profile = profile

        return best_profile

    def create_custom_profile(
        self,
        name: str,
        description: str,
        sample_texts: list[str],
        project_fn: Callable[[str], tuple[list[float], list[float]]],
        temperature: float = 1.0,
    ) -> ContextProfile:
        """
        Creates a custom context profile based on sample texts.

        Args:
            name: Profile name
            description: Description
            sample_texts: Texts representative of the domain
            project_fn: Projection function
            temperature: Projection temperature

        Returns:
            Newly created profile
        """
        if len(sample_texts) == 0:
            raise ValueError("At least one sample text is required")

        # Project all texts
        cogons = []
        for text in sample_texts:
            sem, unc = project_fn(text)
            cogons.append(Cogon.new(sem=sem, unc=unc))

        # Compute average
        avg_sem = [0.0] * FIXED_DIMS
        for cogon in cogons:
            for i in range(FIXED_DIMS):
                avg_sem[i] += cogon.sem[i] / len(cogons)

        # Convert to weights (inverse: high sem -> high weight)
        axis_weights = [min(1.0, max(0.0, s)) for s in avg_sem]

        # Dominant axes = top 5
        dominant = sorted(range(FIXED_DIMS), key=lambda i: avg_sem[i], reverse=True)[:5]

        profile = ContextProfile(
            name=name,
            description=description,
            axis_weights=axis_weights,
            temperature=temperature,
            dominant_axes=dominant,
        )

        self.custom_profiles[name] = profile
        return profile

    def export_profile(self, name: str, path: str) -> None:
        """Exports a profile to JSON."""
        if name in self.BUILTIN_PROFILES:
            profile = self.BUILTIN_PROFILES[name]
        elif name in self.custom_profiles:
            profile = self.custom_profiles[name]
        else:
            raise ValueError(f"Profile '{name}' not found")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

    def import_profile(self, path: str) -> ContextProfile:
        """Imports a profile from JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        profile = ContextProfile.from_dict(data)
        self.custom_profiles[profile.name] = profile
        return profile

    def get_stats(self) -> dict:
        """Returns statistics for the current context."""
        return {
            "history_size": len(self.history),
            "window_size": self.window_size,
            "current_profile": self.current_profile.name if self.current_profile else None,
            "custom_profiles": list(self.custom_profiles.keys()),
            "available_profiles": list(self.BUILTIN_PROFILES.keys()),
            "context_drift": self.detect_context_drift(),
        }

    def _invalidate_cache(self) -> None:
        """Invalidates the context cache."""
        self._context_cogon = None


# Global instance for convenient use
_default_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Returns the default context manager (singleton)."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ContextManager()
    return _default_manager


def set_context_profile(profile_name: str) -> ContextProfile:
    """Sets the active context profile globally."""
    return get_context_manager().set_profile(profile_name)


def adjust_with_context(
    sem: list[float],
    unc: list[float],
    context_alpha: float = 0.2,
) -> tuple[list[float], list[float]]:
    """Adjusts a projection using the global context."""
    return get_context_manager().adjust_projection(sem, unc, context_alpha)
