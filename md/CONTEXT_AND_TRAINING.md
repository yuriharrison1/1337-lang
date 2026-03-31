# 1337 — Context Adjustment & Training Data System

Este documento descreve os dois novos sistemas implementados para melhorar a qualidade das projeções semânticas no 1337:

1. **Context-Aware Projection** — Ajusta projeções baseado no contexto da conversa
2. **Training Data Sources** — Sistema flexível para obter dados de treinamento

---

## 1. Context-Aware Projection

### Visão Geral

O sistema de contexto permite que as projeções semânticas sejam ajustadas dinamicamente baseado no histórico da conversa e no domínio do discurso. Isso resolve o problema de textos idênticos terem interpretações diferentes em contextos distintos.

**Exemplo:**
- "O servidor caiu" em contexto técnico → alto A9 (PROCESSO), alto C5 (ANOMALIA)
- "O servidor caiu" em contexto filosófico → alto A0 (VIA), baixo C1 (URGÊNCIA)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    ContextManager                            │
├─────────────────────────────────────────────────────────────┤
│  • Perfil ativo (ContextProfile)                            │
│  • Histórico de COGONs (janela deslizante)                  │
│  • COGON de contexto acumulado                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Ajuste de Projeção: blend(projecao_original, contexto)     │
└─────────────────────────────────────────────────────────────┘
```

### Perfis de Contexto Built-in

| Perfil | Descrição | Eixos Dominantes |
|--------|-----------|------------------|
| `technical` | Técnico/engineering | SISTEMA, ESTADO, PROCESSO, VERIFICABILIDADE |
| `emergency` | Emergência/crise | URGÊNCIA, IMPACTO, AÇÃO, ANOMALIA |
| `philosophical` | Filosófico/conceitual | VIA, CORRESPONDÊNCIA, RELAÇÃO, VALOR |
| `planning` | Planejamento | PROCESSO, REVERSIBILIDADE, AÇÃO, VETOR TEMPORAL |
| `social` | Social/interpessoal | RELAÇÃO, SINAL, VALOR, AFETO |

### Uso Básico

```python
from leet import set_context_profile, adjust_with_context

# Define o contexto global
set_context_profile("technical")

# Projeta um texto (exemplo com mock)
from leet.bridge import MockProjector
projector = MockProjector()

sem, unc = projector.project("O sistema falhou")

# Ajusta com contexto
adjusted_sem, adjusted_unc = adjust_with_context(sem, unc, context_alpha=0.3)
```

### Uso Avançado

```python
from leet.context import ContextManager, ContextProfile

# Cria manager com janela maior
manager = ContextManager(window_size=20)

# Define perfil
manager.set_profile("emergency")

# Adiciona COGONs ao histórico
from leet import Cogon
cogon = Cogon.new(sem=[...], unc=[...])
manager.add_to_history(cogon)

# Obtém contexto acumulado
context_cogon = manager.get_context_cogon()

# Detecta mudança de contexto
drift = manager.detect_context_drift(threshold=0.5)
if drift:
    print(f"Contexto mudou: {drift}")

# Cria perfil customizado
async def my_projector(text):
    # ... projeção customizada
    return sem, unc

profile = manager.create_custom_profile(
    name="medical",
    description="Contexto médico",
    sample_texts=["Sintoma A", "Diagnóstico B"],
    project_fn=my_projector,
)
```

### API de Contexto

#### `ContextProfile`

```python
@dataclass
class ContextProfile:
    name: str                    # Nome identificador
    description: str             # Descrição
    axis_weights: list[float]    # Pesos para cada eixo (0-1)
    temperature: float           # Temperatura da projeção
    dominant_axes: list[int]     # Eixos especialmente relevantes
```

#### `ContextManager`

| Método | Descrição |
|--------|-----------|
| `set_profile(name)` | Define perfil ativo |
| `add_to_history(cogon)` | Adiciona COGON ao histórico |
| `get_context_cogon(alpha=0.3)` | Obtém contexto acumulado |
| `adjust_projection(sem, unc, alpha)` | Ajusta projeção com contexto |
| `detect_context_drift(threshold)` | Detecta mudança de contexto |
| `create_custom_profile(...)` | Cria perfil a partir de amostras |
| `auto_select_profile(text, projector)` | Seleciona perfil automaticamente |

---

## 2. Training Data Sources

### Visão Geral

O sistema de fontes de treinamento permite expandir além dos 100 seed_texts fixos, coletando dados de múltiplas fontes:

- **Arquivos locais** (CSV, JSONL, TXT)
- **APIs públicas** (Wikipedia, arXiv, Project Gutenberg)
- **Geração sintética** via LLM
- **Domínios especializados** (tech, medical, legal)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                  SourceAggregator                            │
├─────────────────────────────────────────────────────────────┤
│  Fonte A (peso 0.3) ──▶                                     │
│  Fonte B (peso 0.4) ──▶──▶ Deduplicação ──▶ Dataset        │
│  Fonte C (peso 0.3) ──▶                                     │
└─────────────────────────────────────────────────────────────┘
```

### Fontes Disponíveis

#### Locais

```python
from calibration.sources import LocalFileSource

# Arquivo JSONL
source = LocalFileSource("data/extras.jsonl")

# Arquivo CSV
source = LocalFileSource("data/texts.csv", text_field="content")

# Arquivo TXT (uma linha por amostra)
source = LocalFileSource("data/texts.txt")
```

#### APIs

```python
from calibration.sources import WikipediaSource, ArxivSource, GutendexSource

# Wikipedia
wiki = WikipediaSource(config=SourceConfig(max_samples=50, language="pt"))

# arXiv (papers científicos)
arxiv = ArxivSource(category="cs.AI", config=SourceConfig(max_samples=30))

# Project Gutenberg (literatura pública)
gutenberg = GutendexSource(topic="science")
```

#### Domínios Especializados

```python
from calibration.sources import (
    TechDomainSource,      # Logs, commits, alertas, bugs
    MedicalDomainSource,   # Sintomas, diagnósticos, prescrições
    LegalDomainSource,     # Contratos, petições, pareceres
)

# Tech com categorias específicas
tech = TechDomainSource(
    categories=["logs", "alerts"],  # ou "commits", "bugs"
    config=SourceConfig(max_samples=100)
)
```

#### Geração Sintética

```python
from calibration.sources import SyntheticSource

# Mock (sem API key)
synthetic = SyntheticSource(
    provider="mock",           # ou "openai", "anthropic"
    diversity="high",          # ou "medium", "low"
    language="pt",
    config=SourceConfig(max_samples=100)
)

# Com API real
synthetic = SyntheticSource(
    provider="openai",
    config=SourceConfig(
        max_samples=50,
        api_keys={"openai": "sk-..."}
    )
)
```

### Agregação de Fontes

```python
from calibration.sources import SourceAggregator, SourceConfig

# Cria fontes individuais
local = LocalFileSource("data/extras.jsonl")
wiki = WikipediaSource(config=SourceConfig(max_samples=50))
synthetic = SyntheticSource(provider="mock")

# Agrega com pesos
aggregator = SourceAggregator(
    [
        (local, 0.2),      # 20% dados locais
        (wiki, 0.3),       # 30% Wikipedia
        (synthetic, 0.5),  # 50% sintéticos
    ],
    config=SourceConfig(max_samples=200),
    deduplicate=True,
    balance=True,
)

# Busca dados balanceados
samples = aggregator.fetch_all()

# Exporta para arquivo
aggregator.export_combined("data/combined.jsonl", format="jsonl")

# Analisa composição
stats = aggregator.analyze_sources()
print(f"Total: {stats['total_samples']}")
print(f"Domínios: {stats['domain_distribution']}")
```

### Configuração Padrão

```python
from calibration.sources import create_default_aggregator

# Configuração recomendada para treinamento inicial
aggregator = create_default_aggregator(
    target_samples=500,
    include_apis=False,        # True se tiver internet/API keys
    include_synthetic=True,
    include_domains=True,
)

samples = aggregator.fetch_all()
```

### Pipeline de Geração (v2)

```bash
# Gera dataset com configuração padrão (várias fontes)
cd calibration
python generate_dataset_v2.py --output data/dataset_augmented.jsonl --n 500

# Apenas dados sintéticos
python generate_dataset_v2.py --source synthetic --provider mock

# Apenas dados técnicos
python generate_dataset_v2.py --source domain_tech

# Com APIs externas
python generate_dataset_v2.py --include-apis --n 200

# Analisa composição
python generate_dataset_v2.py --analyze
```

### Fluxo Completo de Treinamento

```bash
cd calibration

# 1. Gera dataset enriquecido
python generate_dataset_v2.py --output data/dataset_augmented.jsonl --n 500

# 2. Treina matriz W
python train_w.py --input data/dataset_augmented.jsonl

# 3. Avalia qualidade
python evaluate_w.py

# 4. Exporta para serviço
python export_w.py --dest ../leet1337/leet-service/W.bin
```

---

## Integração entre Sistemas

### Contexto + Projeção

```python
from leet import encode, set_context_profile
from leet.bridge import AnthropicProjector

# Configura contexto
set_context_profile("technical")

# Projeta com contexto
projector = AnthropicProjector()
cogon = await encode("O deploy falhou", projector)

# O resultado é automaticamente ajustado pelo contexto técnico
# (mais ênfase em A9_PROCESSO, C5_ANOMALIA)
```

### Treinamento + Contexto

Ao treinar a matriz W, você pode usar dados de domínios específicos para criar perfis de contexto especializados:

```python
from calibration.sources import TechDomainSource
from leet.context import ContextManager

# Coleta dados técnicos
tech_source = TechDomainSource()
tech_samples = tech_source.fetch_all()

# Projeta amostras para criar perfil
manager = ContextManager()
profile = manager.create_custom_profile(
    name="production_incident",
    description="Contexto de incidente em produção",
    sample_texts=[s.text for s in tech_samples[:20]],
    project_fn=projector.project,
)
```

---

## Benefícios

### Context-Aware Projection

1. **Precisão contextual**: Mesmo texto, interpretações diferentes por contexto
2. **Conversação coerente**: Histórico influencia projeções futuras
3. **Detecção de drift**: Identifica quando o assunto muda
4. **Perfis customizáveis**: Domínios específicos da aplicação

### Training Data Sources

1. **Escalabilidade**: Além dos 100 seeds fixos
2. **Diversidade**: Múltiplas fontes = maior cobertura semântica
3. **Especialização**: Dados específicos por domínio
4. **Atualização**: Fácil adicionar novas fontes

---

## Testes

```bash
# Testes de contexto
cd python
pytest tests/test_context.py -v

# Testes de fontes
cd calibration/sources
pytest test_sources.py -v
```

---

## Próximos Passos

- [ ] Fine-tuning da W matrix por contexto
- [ ] Feedback loop: usar conversas reais para refinar
- [ ] Clustering automático de contextos
- [ ] Fontes adicionais (GitHub, StackOverflow, etc.)
