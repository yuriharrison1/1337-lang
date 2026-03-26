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
        description="Grau em que o conceito existe por si mesmo, independente de relações externas. Alta = essência pura. Baixa = só existe em função de outro."
    ),
    Axis(
        index=1, code="A1", name="CORRESPONDÊNCIA", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito espelha padrões em outros níveis de abstração. Alta = mesmo padrão em múltiplas escalas."
    ),
    Axis(
        index=2, code="A2", name="VIBRAÇÃO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito está em movimento/transformação contínua. Alta = fluxo constante. Baixa = estático."
    ),
    Axis(
        index=3, code="A3", name="POLARIDADE", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito está posicionado num espectro entre extremos. Alta = fortemente polar. Baixa = neutro."
    ),
    Axis(
        index=4, code="A4", name="RITMO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito exibe padrão cíclico ou periódico. Alta = ritmo claro. Baixa = irregular ou único."
    ),
    Axis(
        index=5, code="A5", name="CAUSA E EFEITO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é agente causal vs efeito. Alta = causa primária. Baixa = consequência pura."
    ),
    Axis(
        index=6, code="A6", name="GÊNERO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é gerador/ativo vs receptivo/passivo. Alta = princípio ativo. Baixa = princípio receptivo."
    ),
    Axis(
        index=7, code="A7", name="SISTEMA", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é um conjunto com comportamento emergente."
    ),
    Axis(
        index=8, code="A8", name="ESTADO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é uma configuração num dado momento."
    ),
    Axis(
        index=9, code="A9", name="PROCESSO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é transformação no tempo."
    ),
    Axis(
        index=10, code="A10", name="RELAÇÃO", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é conexão entre entidades."
    ),
    Axis(
        index=11, code="A11", name="SINAL", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito é informação carregando variação."
    ),
    Axis(
        index=12, code="A12", name="ESTABILIDADE", group=AxisGroup.ONTOLOGICAL,
        description="Grau em que o conceito tende ao equilíbrio ou à divergência. Alta = convergente. Baixa = instável/caótico."
    ),
    Axis(
        index=13, code="A13", name="VALÊNCIA ONTOLÓGICA", group=AxisGroup.ONTOLOGICAL,
        description="Sinal intrínseco do conceito em si. 0 = negativo/contrativo → 0.5 = neutro → 1 = positivo/expansivo. Independente do contexto ou do agente."
    ),

    # Group B — Epistemic (14-21)
    Axis(
        index=14, code="B1", name="VERIFICABILIDADE", group=AxisGroup.EPISTEMIC,
        description="Grau em que o conceito pode ser confirmado externamente. Alta = verificável por evidência. Baixa = não falsificável."
    ),
    Axis(
        index=15, code="B2", name="TEMPORALIDADE", group=AxisGroup.EPISTEMIC,
        description="Grau em que o conceito tem âncora temporal definida. Alta = momento preciso. Baixa = atemporal ou indefinido."
    ),
    Axis(
        index=16, code="B3", name="COMPLETUDE", group=AxisGroup.EPISTEMIC,
        description="Grau em que o conceito está resolvido. Alta = fechado, conclusivo. Baixa = aberto, em construção."
    ),
    Axis(
        index=17, code="B4", name="CAUSALIDADE", group=AxisGroup.EPISTEMIC,
        description="Grau em que a origem do conceito é identificável. Alta = causa clara. Baixa = origem opaca ou difusa."
    ),
    Axis(
        index=18, code="B5", name="REVERSIBILIDADE", group=AxisGroup.EPISTEMIC,
        description="Grau em que o conceito pode ser desfeito. Alta = totalmente reversível. Baixa = irreversível."
    ),
    Axis(
        index=19, code="B6", name="CARGA", group=AxisGroup.EPISTEMIC,
        description="Grau de recurso cognitivo que o conceito consome. Alta = pesado, exige atenção. Baixa = automático, fluido. (Eixo TDAH do criador)"
    ),
    Axis(
        index=20, code="B7", name="ORIGEM", group=AxisGroup.EPISTEMIC,
        description="Grau em que o conhecimento é observado vs inferido vs assumido. Alta = observação direta. Baixa = suposição pura."
    ),
    Axis(
        index=21, code="B8", name="VALÊNCIA EPISTÊMICA", group=AxisGroup.EPISTEMIC,
        description="Sinal do conhecimento que o agente tem sobre o conceito. 0 = evidência contraditória → 0.5 = inconclusivo → 1 = evidência confirmatória."
    ),

    # Group C — Pragmatic (22-31)
    Axis(
        index=22, code="C1", name="URGÊNCIA", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito exige resposta imediata. Alta = pressão temporal crítica. Baixa = sem pressa."
    ),
    Axis(
        index=23, code="C2", name="IMPACTO", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito gera consequências. Alta = muda estado do sistema. Baixa = inócuo."
    ),
    Axis(
        index=24, code="C3", name="AÇÃO", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito exige resposta ativa vs é só alinhamento. Alta = demanda execução. Baixa = puramente informativo."
    ),
    Axis(
        index=25, code="C4", name="VALOR", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito conecta com algo que importa de verdade — ativa valores, não só lógica. Alta = carregado de significado. Baixa = neutro axiologicamente. (Eixo INFP)"
    ),
    Axis(
        index=26, code="C5", name="ANOMALIA", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito é desvio do padrão esperado. Alta = ruptura forte. Baixa = dentro do normal."
    ),
    Axis(
        index=27, code="C6", name="AFETO", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito carrega valência emocional relevante. Alta = forte carga afetiva. Baixa = neutro emocionalmente."
    ),
    Axis(
        index=28, code="C7", name="DEPENDÊNCIA", group=AxisGroup.PRAGMATIC,
        description="Grau em que o conceito precisa de outro para existir. Alta = totalmente acoplado. Baixa = autônomo."
    ),
    Axis(
        index=29, code="C8", name="VETOR TEMPORAL", group=AxisGroup.PRAGMATIC,
        description="Orientação do conceito no tempo. 0 = passado puro → 0.5 = presente → 1 = futuro puro. Distinto de TEMPORALIDADE que mede se tem âncora."
    ),
    Axis(
        index=30, code="C9", name="NATUREZA", group=AxisGroup.PRAGMATIC,
        description="Categoria semântica fundamental. 0 = substantivo puro (coisa, ser, estado) → 1 = verbo puro (processo, ação, transformação)."
    ),
    Axis(
        index=31, code="C10", name="VALÊNCIA DE AÇÃO", group=AxisGroup.PRAGMATIC,
        description="Sinal da intenção do agente ao transmitir. 0 = negativo/alerta/contrativo → 0.5 = neutro/consulta → 1 = positivo/confirmação/expansivo."
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
