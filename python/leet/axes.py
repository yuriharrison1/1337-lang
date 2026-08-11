"""Canonical axes for 1337 — 32 dimensions."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AxisGroup(Enum):
    ONTOLOGICAL = "A"
    EPISTEMIC = "B"
    PRAGMATIC = "C"


@dataclass(frozen=True)
class Axis:
    index: int
    code: str
    name: str
    group: AxisGroup
    description: str


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Group A — Ontological (0-13)
A0_VIA = 0
A1_CORRESPONDENCIA = 1
A2_VIBRACAO = 2
A3_POLARIDADE = 3
A4_RITMO = 4
A5_CAUSA_EFEITO = 5
A6_GENERO = 6
A7_SISTEMA = 7
A8_ESTADO = 8
A9_PROCESSO = 9
A10_RELACAO = 10
A11_SINAL = 11
A12_ESTABILIDADE = 12
A13_VALENCIA_ONTOLOGICA = 13

# Group B — Epistemic (14-21)
B1_VERIFICABILIDADE = 14
B2_TEMPORALIDADE = 15
B3_COMPLETUDE = 16
B4_CAUSALIDADE = 17
B5_REVERSIBILIDADE = 18
B6_CARGA = 19
B7_ORIGEM = 20
B8_VALENCIA_EPISTEMICA = 21

# Group C — Pragmatic (22-31)
C1_URGENCIA = 22
C2_IMPACTO = 23
C3_ACAO = 24
C4_VALOR = 25
C5_ANOMALIA = 26
C6_AFETO = 27
C7_DEPENDENCIA = 28
C8_VETOR_TEMPORAL = 29
C9_NATUREZA = 30
C10_VALENCIA_ACAO = 31


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL AXES TABLE
# ═══════════════════════════════════════════════════════════════════════════════

CANONICAL_AXES: list[Axis] = [
    # Group A — Ontological (0-13)
    Axis(
        index=0, code="A0", name="VIA", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept exists in itself, independent of external relations. High = pure essence. Low = only exists in relation to another."
    ),
    Axis(
        index=1, code="A1", name="CORRESPONDÊNCIA", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept mirrors patterns at other levels of abstraction. High = same pattern across multiple scales."
    ),
    Axis(
        index=2, code="A2", name="VIBRAÇÃO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is in continuous movement/transformation. High = constant flux. Low = static."
    ),
    Axis(
        index=3, code="A3", name="POLARIDADE", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is positioned on a spectrum between extremes. High = strongly polar. Low = neutral."
    ),
    Axis(
        index=4, code="A4", name="RITMO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept exhibits a cyclical or periodic pattern. High = clear rhythm. Low = irregular or one-off."
    ),
    Axis(
        index=5, code="A5", name="CAUSA E EFEITO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is a causal agent vs an effect. High = primary cause. Low = pure consequence."
    ),
    Axis(
        index=6, code="A6", name="GÊNERO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is generative/active vs receptive/passive. High = active principle. Low = receptive principle."
    ),
    Axis(
        index=7, code="A7", name="SISTEMA", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is a set with emergent behavior."
    ),
    Axis(
        index=8, code="A8", name="ESTADO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is a configuration at a given moment."
    ),
    Axis(
        index=9, code="A9", name="PROCESSO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is transformation over time."
    ),
    Axis(
        index=10, code="A10", name="RELAÇÃO", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is a connection between entities."
    ),
    Axis(
        index=11, code="A11", name="SINAL", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept is information carrying variation."
    ),
    Axis(
        index=12, code="A12", name="ESTABILIDADE", group=AxisGroup.ONTOLOGICAL,
        description="Degree to which the concept tends toward equilibrium or divergence. High = convergent. Low = unstable/chaotic."
    ),
    Axis(
        index=13, code="A13", name="VALÊNCIA ONTOLÓGICA", group=AxisGroup.ONTOLOGICAL,
        description="Intrinsic sign of the concept itself. 0 = negative/contractive → 0.5 = neutral → 1 = positive/expansive. Independent of context or agent."
    ),

    # Group B — Epistemic (14-21)
    Axis(
        index=14, code="B1", name="VERIFICABILIDADE", group=AxisGroup.EPISTEMIC,
        description="Degree to which the concept can be externally confirmed. High = verifiable by evidence. Low = unfalsifiable."
    ),
    Axis(
        index=15, code="B2", name="TEMPORALIDADE", group=AxisGroup.EPISTEMIC,
        description="Degree to which the concept has a defined temporal anchor. High = precise moment. Low = timeless or undefined."
    ),
    Axis(
        index=16, code="B3", name="COMPLETUDE", group=AxisGroup.EPISTEMIC,
        description="Degree to which the concept is resolved. High = closed, conclusive. Low = open, in progress."
    ),
    Axis(
        index=17, code="B4", name="CAUSALIDADE", group=AxisGroup.EPISTEMIC,
        description="Degree to which the concept's origin is identifiable. High = clear cause. Low = opaque or diffuse origin."
    ),
    Axis(
        index=18, code="B5", name="REVERSIBILIDADE", group=AxisGroup.EPISTEMIC,
        description="Degree to which the concept can be undone. High = fully reversible. Low = irreversible."
    ),
    Axis(
        index=19, code="B6", name="CARGA", group=AxisGroup.EPISTEMIC,
        description="Degree of cognitive resource the concept consumes. High = heavy, demands attention. Low = automatic, fluid. (The creator's ADHD axis)"
    ),
    Axis(
        index=20, code="B7", name="ORIGEM", group=AxisGroup.EPISTEMIC,
        description="Degree to which the knowledge is observed vs inferred vs assumed. High = direct observation. Low = pure assumption."
    ),
    Axis(
        index=21, code="B8", name="VALÊNCIA EPISTÊMICA", group=AxisGroup.EPISTEMIC,
        description="Sign of the knowledge the agent holds about the concept. 0 = contradictory evidence → 0.5 = inconclusive → 1 = confirmatory evidence."
    ),

    # Group C — Pragmatic (22-31)
    Axis(
        index=22, code="C1", name="URGÊNCIA", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept demands an immediate response. High = critical time pressure. Low = no rush."
    ),
    Axis(
        index=23, code="C2", name="IMPACTO", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept generates consequences. High = changes system state. Low = harmless."
    ),
    Axis(
        index=24, code="C3", name="AÇÃO", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept demands an active response vs is merely alignment. High = demands execution. Low = purely informative."
    ),
    Axis(
        index=25, code="C4", name="VALOR", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept connects with something that truly matters — activates values, not just logic. High = charged with meaning. Low = axiologically neutral. (The INFP axis)"
    ),
    Axis(
        index=26, code="C5", name="ANOMALIA", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept deviates from the expected pattern. High = strong disruption. Low = within the normal range."
    ),
    Axis(
        index=27, code="C6", name="AFETO", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept carries relevant emotional valence. High = strong affective charge. Low = emotionally neutral."
    ),
    Axis(
        index=28, code="C7", name="DEPENDÊNCIA", group=AxisGroup.PRAGMATIC,
        description="Degree to which the concept needs another to exist. High = fully coupled. Low = autonomous."
    ),
    Axis(
        index=29, code="C8", name="VETOR TEMPORAL", group=AxisGroup.PRAGMATIC,
        description="Orientation of the concept in time. 0 = pure past → 0.5 = present → 1 = pure future. Distinct from TEMPORALITY, which measures whether it has an anchor."
    ),
    Axis(
        index=30, code="C9", name="NATUREZA", group=AxisGroup.PRAGMATIC,
        description="Fundamental semantic category. 0 = pure noun (thing, being, state) → 1 = pure verb (process, action, transformation)."
    ),
    Axis(
        index=31, code="C10", name="VALÊNCIA DE AÇÃO", group=AxisGroup.PRAGMATIC,
        description="Sign of the agent's intention when transmitting. 0 = negative/alert/contractive → 0.5 = neutral/query → 1 = positive/confirmation/expansive."
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def axis(index: int) -> Optional[Axis]:
    """Returns the Axis at the given index, or None if out of range."""
    if 0 <= index < len(CANONICAL_AXES):
        return CANONICAL_AXES[index]
    return None


def axes_in_group(group: AxisGroup) -> list[Axis]:
    """Returns all axes belonging to the given group."""
    return [ax for ax in CANONICAL_AXES if ax.group == group]


# Named constants for easier access
A0_VIA = 0
A1_CORRESPONDENCIA = 1
A2_VIBRACAO = 2
A3_POLARIDADE = 3
A4_RITMO = 4
A5_CAUSA_EFEITO = 5
A6_GENERO = 6
A7_SISTEMA = 7
A8_ESTADO = 8
A9_PROCESSO = 9
A10_RELACAO = 10
A11_SINAL = 11
A12_ESTABILIDADE = 12
A13_VALENCIA_ONTOLOGICA = 13
B1_VERIFICABILIDADE = 14
B2_TEMPORALIDADE = 15
B3_COMPLETUDE = 16
B4_CAUSALIDADE = 17
B5_REVERSIBILIDADE = 18
B6_CARGA = 19
B7_ORIGEM = 20
B8_VALENCIA_EPISTEMICA = 21
C1_URGENCIA = 22
C2_IMPACTO = 23
C3_ACAO = 24
C4_VALOR = 25
C5_ANOMALIA = 26
C6_AFETO = 27
C7_DEPENDENCIA = 28
C8_VETOR_TEMPORAL = 29
C9_NATUREZA = 30
C10_VALENCIA_ACAO = 31
