Crie um pacote Python que wrapa o leet_core Rust e adiciona interface Pythonica + CLI + integração com LLM.

O leet_core Rust já está compilado no workspace leet1337/ e expõe módulo PyO3 (feature python).
Se o módulo Rust compilado não estiver disponível, o Python deve funcionar em modo "pure-python" com implementação fallback dos operadores (mais lento, mas funcional).

---

# CONTEXTO RÁPIDO DA SPEC 1337 v0.4

- COGON: {id, sem[32], unc[32], stamp, raw?} — unidade atômica de significado
- COGON_ZERO: sem=[1]*32, unc=[0]*32, id=nil UUID, stamp=0
- DAG: {root, nodes[], edges[]} — raciocínio composto
- MSG_1337: envelope completo com identity, intent, ref/patch, payload, c5, surface
- 32 eixos canônicos em 3 grupos:
  - A (0-13): Ontológico — VIA, CORRESPONDÊNCIA, VIBRAÇÃO, POLARIDADE, RITMO, CAUSA E EFEITO, GÊNERO, SISTEMA, ESTADO, PROCESSO, RELAÇÃO, SINAL, ESTABILIDADE, VALÊNCIA ONTOLÓGICA
  - B (14-21): Epistêmico — VERIFICABILIDADE, TEMPORALIDADE, COMPLETUDE, CAUSALIDADE, REVERSIBILIDADE, CARGA, ORIGEM, VALÊNCIA EPISTÊMICA
  - C (22-31): Pragmático — URGÊNCIA, IMPACTO, AÇÃO, VALOR, ANOMALIA, AFETO, DEPENDÊNCIA, VETOR TEMPORAL, NATUREZA, VALÊNCIA DE AÇÃO
- Operadores: FOCUS, DELTA, BLEND(sem=α·c1+(1-α)·c2, unc=max), DIST(cosseno ponderado), ANOMALY_SCORE
- Regras R1-R21 (validação estrutural)
- Intents: ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK

---

# ESTRUTURA

```
python/
├── pyproject.toml
├── setup.py                    (fallback se maturin não disponível)
├── leet/
│   ├── __init__.py
│   ├── types.py
│   ├── axes.py
│   ├── operators.py
│   ├── validate.py
│   ├── bridge.py
│   └── cli.py
└── tests/
    ├── __init__.py
    ├── test_types.py
    ├── test_operators.py
    ├── test_validate.py
    ├── test_bridge.py
    └── test_cli.py
```

# REQUISITOS POR ARQUIVO

## pyproject.toml
```toml
[project]
name = "leet1337"
version = "0.4.0"
description = "1337 inter-agent communication language — Python SDK"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
dev = ["pytest>=8", "pytest-asyncio"]

[project.scripts]
leet = "leet.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends._legacy:_Backend"
```

## leet/__init__.py
```python
"""1337 — Native inter-agent communication language. v0.4 (32 axes)."""

from leet.types import Cogon, Edge, Dag, Msg1337, Raw, RawRole, Intent, Receiver, Surface, CanonicalSpace
from leet.operators import blend, delta, dist, focus, anomaly_score, apply_patch
from leet.bridge import SemanticProjector, MockProjector, encode, decode

__version__ = "0.4.0"
FIXED_DIMS = 32
MAX_INHERITANCE_DEPTH = 4
LOW_CONFIDENCE_THRESHOLD = 0.9

# Tenta importar backend Rust. Se não disponível, usa pure-python.
try:
    import leet_core as _rust_backend
    BACKEND = "rust"
except ImportError:
    _rust_backend = None
    BACKEND = "python"
```

## leet/types.py — Dataclasses Python espelhando Rust

Todas as classes com:
- @dataclass
- .to_json() → str (serializa pra JSON)
- .from_json(cls, json_str) → Self (classmethod, desserializa)
- Validação no __post_init__

Classes obrigatórias:
- RawRole(Enum): EVIDENCE, ARTIFACT, TRACE, BRIDGE
- Raw: content_type (str), content (Any), role (RawRole)
- Cogon: id (str UUID), sem (list[float] len=32), unc (list[float] len=32), stamp (int nanoseg), raw (Optional[Raw])
  - Cogon.zero() → classmethod, retorna COGON_ZERO
  - Cogon.is_zero() → bool
  - Cogon.low_confidence_dims() → list[int] onde unc > 0.9
  - Cogon.with_raw(raw) → Cogon (retorna cópia com raw)
- EdgeType(Enum): CAUSA, CONDICIONA, CONTRADIZ, REFINA, EMERGE
- Edge: from_id (str), to_id (str), edge_type (EdgeType), weight (float 0-1)
- Dag: root (str), nodes (list[Cogon]), edges (list[Edge])
  - Dag.from_root(cogon) → Dag
  - Dag.add_node(cogon), add_edge(edge)
  - Dag.topological_order() → list[str] (levanta ValueError se ciclo)
  - Dag.parents_of(node_id) → list[str]
- Intent(Enum): ASSERT, QUERY, DELTA, SYNC, ANOMALY, ACK
- Receiver: agent_id (Optional[str]) — None = BROADCAST
  - Receiver.broadcast() → classmethod
  - Receiver.is_broadcast() → bool
- CanonicalSpace: zone_fixed (list[float] 32), zone_emergent (dict[str,float]), schema_ver (str), align_hash (str)
- Surface: human_required (bool), urgency (Optional[float]), reconstruct_depth (int), lang (str)
- Msg1337: TODOS os campos na ordem canônica
  - id, sender, receiver, intent, ref_hash (Optional), patch (Optional), payload (Cogon|Dag), c5, surface
  - Msg1337.hash() → str (SHA256 do JSON)

Se o backend Rust está disponível (_rust_backend), delegar serialização/operações pra ele.
Se não, usar json + uuid + hashlib do Python.

## leet/axes.py — Os 32 eixos como constantes Python

```python
from dataclasses import dataclass
from enum import Enum

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

# Constantes de índice
A0_VIA = 0
A1_CORRESPONDENCIA = 1
# ... todos os 32 ...
C10_VALENCIA_ACAO = 31

# Tabela completa
CANONICAL_AXES: list[Axis] = [
    Axis(0, "A0", "VIA", AxisGroup.ONTOLOGICAL, "Grau em que o conceito existe por si mesmo..."),
    # ... todos os 32 com descrição COMPLETA da spec ...
]

def axis(index: int) -> Axis: ...
def axes_in_group(group: AxisGroup) -> list[Axis]: ...
```

Inclua TODOS os 32 eixos com descrições COMPLETAS (copie da spec acima).

## leet/operators.py — Operadores chamando Rust ou pure-python

Cada operador tenta usar o backend Rust. Se não disponível, usa implementação Python:

```python
def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    """Fusão semântica interpolada.
    sem = α·c1.sem + (1-α)·c2.sem
    unc = max(c1.unc, c2.unc)  # incerteza conservadora
    """

def delta(prev: Cogon, curr: Cogon) -> list[float]:
    """Diferença semântica entre dois estados."""

def dist(c1: Cogon, c2: Cogon) -> float:
    """Distância cosseno ponderada por (1-unc)."""

def focus(cogon: Cogon, dims: list[int]) -> Cogon:
    """Projeta COGON em subconjunto de dimensões."""

def anomaly_score(cogon: Cogon, history: list[Cogon]) -> float:
    """Distância média do centroide histórico."""

def apply_patch(base: Cogon, patch: list[float]) -> Cogon:
    """Aplica delta patch clamped [0,1]."""
```

Implementação pure-python deve ser IDENTICA à do Rust:
- blend: sem = [α*a + (1-α)*b for a,b in zip(c1.sem, c2.sem)], unc = [max(a,b) for ...]
- dist: cosseno ponderado por (1-max(unc_a, unc_b)), retorna 1-similaridade
- anomaly_score: centroide = média dos history, dist pro centroide. Vazio = 1.0
- apply_patch: [max(0, min(1, s+p)) for s,p in zip(base.sem, patch)]

## leet/validate.py — Validação Python (fallback do Rust)

```python
def validate(msg: Msg1337) -> Optional[str]:
    """Valida MSG_1337 contra R1-R21. Retorna None se ok, string de erro se inválido."""

def check_confidence(msg: Msg1337) -> list[tuple[str, int, float]]:
    """Retorna flags de baixa confiança (cogon_id, dim_index, unc_value)."""
```

Implementa R1-R9 e R10 (verificação de dimensão). R11-R21 são mais complexas e podem ser stubs que retornam Ok por enquanto.

## leet/bridge.py — Interface de tradução humano ↔ 1337

```python
from abc import ABC, abstractmethod

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
            sem[22] = 0.95  # C1_URGÊNCIA
            sem[24] = 0.9   # C3_AÇÃO
            unc[22] = 0.05
            unc[24] = 0.1

        if "caiu" in text_lower or "falhou" in text_lower or "erro" in text_lower:
            sem[8] = 0.9    # A8_ESTADO
            sem[26] = 0.9   # C5_ANOMALIA
            sem[13] = 0.15  # A13_VALÊNCIA_ONTOLÓGICA (negativo)
            unc[8] = 0.1
            unc[26] = 0.1

        if "deploy" in text_lower or "processo" in text_lower:
            sem[9] = 0.85   # A9_PROCESSO
            sem[30] = 0.8   # C9_NATUREZA (verbo)
            unc[9] = 0.1

        if "reverter" in text_lower or "desfazer" in text_lower:
            sem[18] = 0.9   # B5_REVERSIBILIDADE
            sem[24] = 0.85  # C3_AÇÃO
            unc[18] = 0.1

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
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")

    async def project(self, text: str) -> tuple[list[float], list[float]]:
        # Monta o prompt com os 32 eixos
        # Chama a API Anthropic
        # Parseia JSON response → (sem, unc)
        ...  # IMPLEMENTAR COMPLETO

    async def reconstruct(self, cogon: Cogon) -> str:
        # Monta prompt com valores sem/unc e nomes dos eixos
        # Chama API → texto natural
        ...  # IMPLEMENTAR COMPLETO


# Funções de conveniência
async def encode(text: str, projector: SemanticProjector | None = None) -> Cogon:
    """Texto → COGON."""
    if projector is None:
        projector = MockProjector()
    sem, unc = await projector.project(text)
    return Cogon(sem=sem, unc=unc)

async def decode(cogon: Cogon, projector: SemanticProjector | None = None) -> str:
    """COGON → texto."""
    if projector is None:
        projector = MockProjector()
    return await projector.reconstruct(cogon)
```

O AnthropicProjector DEVE estar completo — com prompt template que lista os 32 eixos, chamada à API, parsing do JSON. Use a lib `anthropic` (import condicional, tá em optional-dependencies).

O prompt de projeção deve listar cada eixo como:
```
[0] A0 VIA: Grau em que o conceito existe por si mesmo (0=dependente, 1=essência pura)
[1] A1 CORRESPONDÊNCIA: Grau em que espelha padrões em outras escalas (0=único, 1=fractal)
...todos os 32...
```
E pedir resposta JSON: `{"sem": [0.0, ...], "unc": [0.0, ...]}`

## leet/cli.py — CLI completo

```python
import argparse, json, asyncio

def main():
    parser = argparse.ArgumentParser(prog="leet", description="1337 Language CLI")
    sub = parser.add_subparsers(dest="command")

    # leet zero
    sub.add_parser("zero", help="Print COGON_ZERO (I AM)")

    # leet encode "texto"
    enc = sub.add_parser("encode", help="Encode text → COGON JSON")
    enc.add_argument("text", help="Text to encode")
    enc.add_argument("--projector", choices=["mock", "anthropic"], default="mock")

    # leet decode cogon.json
    dec = sub.add_parser("decode", help="Decode COGON JSON → text")
    dec.add_argument("file", help="Path to COGON JSON file")
    dec.add_argument("--projector", choices=["mock", "anthropic"], default="mock")

    # leet validate msg.json
    val = sub.add_parser("validate", help="Validate MSG_1337 JSON")
    val.add_argument("file", help="Path to MSG_1337 JSON file")

    # leet blend c1.json c2.json --alpha 0.5
    bl = sub.add_parser("blend", help="BLEND two COGONs")
    bl.add_argument("c1", help="Path to COGON 1 JSON")
    bl.add_argument("c2", help="Path to COGON 2 JSON")
    bl.add_argument("--alpha", type=float, default=0.5)

    # leet dist c1.json c2.json
    di = sub.add_parser("dist", help="DIST between two COGONs")
    di.add_argument("c1", help="Path to COGON 1 JSON")
    di.add_argument("c2", help="Path to COGON 2 JSON")

    # leet axes [--group A|B|C]
    ax = sub.add_parser("axes", help="List canonical axes")
    ax.add_argument("--group", choices=["A", "B", "C"], help="Filter by group")

    # leet version
    sub.add_parser("version", help="Print version")

    args = parser.parse_args()
    # ... dispatch commands ...
```

Cada comando IMPLEMENTADO COMPLETO. Não stubs. O CLI funciona de verdade.

---

# TESTES

## tests/test_types.py
- test_cogon_zero: valores exatos
- test_cogon_creation: 32 dims
- test_cogon_to_json_roundtrip: serializa → desserializa = igual
- test_dag_from_root: DAG com 1 nó
- test_dag_topological_order: ordem correta
- test_dag_cycle_detection: levanta ValueError
- test_edge_types: todos os 5 tipos
- test_msg_creation: envelope completo
- test_msg_hash: hash determinístico

## tests/test_operators.py
- test_blend_midpoint: α=0.5
- test_blend_unc_conservative: max
- test_delta: diferença correta
- test_dist_identical: ~0
- test_dist_orthogonal: ~1
- test_focus: dims selecionadas mantém
- test_anomaly_score_empty: 1.0
- test_apply_patch_clamp: sempre [0,1]

## tests/test_validate.py
- test_valid_msg: passa
- test_r2_delta_no_ref: falha
- test_r6_human_no_urgency: falha
- test_r8_broadcast_assert: falha

## tests/test_bridge.py
- test_mock_encode_basic: texto → COGON
- test_mock_encode_urgent: urgência alta
- test_mock_decode: COGON → texto com eixos dominantes
- test_roundtrip: encode → decode preserva semântica
- test_anthropic_projector_init: falha sem api_key (mas não crasha)

## tests/test_cli.py
- test_cli_zero: saída = COGON_ZERO JSON
- test_cli_version: "0.4.0"
- test_cli_axes: lista 32 eixos
- test_cli_encode: texto → JSON válido

---

# CRITÉRIOS DE ACEITE

1. `pip install .` funciona (modo pure-python, sem Rust)
2. `pip install ".[dev]"` instala pytest
3. `pytest -v` passa TODOS os testes
4. `leet zero` imprime COGON_ZERO JSON válido
5. `leet encode "o servidor caiu"` imprime COGON com ANOMALIA alta
6. `leet validate msg.json` reporta erros de validação
7. `leet axes` lista os 32 eixos
8. `leet version` imprime "0.4.0"
9. Funciona 100% sem Rust backend (pure-python fallback)
10. AnthropicProjector completo (funciona com ANTHROPIC_API_KEY no env)
