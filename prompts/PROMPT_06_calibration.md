# PROMPT 06 — CALIBRAÇÃO DA MATRIZ W (Dataset → Treino → Avaliação → Export)

Build the W matrix calibration pipeline. After this, the Semantic Projector runs
in pure Rust — no LLM calls needed for text→sem[32] projection.

**PREREQUISITES**: PROMPT_01 (leet-core) + PROMPT_02 (leet-service) completed.

**IMPORTANT**: At the end, update CONTRACT.md and Taskwarrior.

---

## CONCEPT

The W matrix projects from embedding space (e.g., 768D or 1536D) to semantic space (32D).
```
sem[32] = normalize(clamp(W @ embedding[D], 0, 1))
```

Calibration pipeline:
1. **Generate dataset**: Use LLM to score texts across all 32 axes → (text, sem[32]) pairs
2. **Train W**: Ridge regression from embeddings to sem[32] targets
3. **Evaluate**: Semantic coherence benchmarks
4. **Export**: Binary W.bin loadable by leet-service

---

## STRUCTURE

```
calibration/
├── pyproject.toml
├── config.yaml
├── run_pipeline.py          # Orchestrator: generate → train → evaluate → export
├── generate_dataset.py      # Step 1: LLM scoring
├── train_w.py               # Step 2: Ridge regression
├── evaluate.py              # Step 3: Coherence benchmarks
├── export.py                # Step 4: Binary export
├── prompts/
│   └── axis_scorer.txt      # Prompt template for LLM scoring
├── data/                    # Generated artifacts (gitignored)
│   ├── dataset.jsonl
│   ├── embeddings.npy
│   ├── W.npy
│   └── W.bin
├── tests/
│   ├── test_generate.py
│   ├── test_train.py
│   ├── test_evaluate.py
│   └── test_export.py
└── README.md
```

**pyproject.toml:**
```toml
[project]
name = "leet-calibration"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.26",
    "scikit-learn>=1.4",
    "litellm>=1.30",
    "sentence-transformers>=3.0",
    "pyyaml>=6.0",
    "tqdm>=4.66",
    "click>=8.0",
]

[project.optional-dependencies]
dev = ["pytest>=8"]
```

---

## config.yaml

```yaml
# Calibration pipeline configuration

dataset:
  size: 2000                    # number of texts to score
  languages: ["pt", "en"]      # text languages
  categories:                   # semantic categories to cover
    - technical
    - emotional
    - abstract
    - concrete
    - temporal
    - causal
    - social
    - scientific
    - philosophical
    - practical

embedding:
  model: "all-MiniLM-L6-v2"    # sentence-transformers model
  dimension: 384                 # embedding dimension

llm:
  provider: "deepseek"           # via litellm
  model: "deepseek/deepseek-chat"
  temperature: 0.3
  max_retries: 3

training:
  method: "ridge"                # ridge | lasso | elastic_net
  alpha: 1.0                    # regularization strength
  test_split: 0.2
  random_state: 1337

evaluation:
  coherence_threshold: 0.7       # minimum acceptable coherence
  benchmark_pairs: 100           # number of similarity pairs to test

export:
  output_path: "data/W.bin"
  format: "f32_le"               # little-endian float32
```

---

## DETAILED SPECS

### generate_dataset.py

```python
"""Step 1: Generate (text, sem[32]) pairs via LLM scoring."""

def generate_texts(config: dict) -> list[str]:
    """Generate diverse texts covering all semantic categories.
    Mix of: short phrases, sentences, paragraphs, technical terms,
    emotional expressions, abstract concepts, concrete descriptions."""

def score_text(text: str, llm_config: dict) -> list[float]:
    """Ask LLM to score text on all 32 axes.
    
    Uses prompt template from prompts/axis_scorer.txt.
    Returns sem[32] with values in [0,1].
    
    The prompt gives the LLM:
    - Each axis name + description
    - The text to score
    - Instructions to return JSON array of 32 floats
    """

def generate_dataset(config_path: str) -> None:
    """Main function. Generates dataset.jsonl with lines:
    {"text": "...", "sem": [0.8, 0.2, ...], "lang": "pt"}
    """
```

The axis scorer prompt MUST include ALL 32 axes with their full descriptions
from the spec. Use the exact names and descriptions.

### prompts/axis_scorer.txt

```
You are a semantic axis scorer for the 1337 inter-agent communication protocol.

Given a text, score it on each of the 32 canonical axes below.
Each score is a float in [0, 1].

## Axes

[0] VIA — Degree concept exists by itself. High=pure essence. Low=exists only in relation to another.
[1] CORRESPONDÊNCIA — Degree concept mirrors patterns at other abstraction levels. High=fractal. Low=unique.
[2] VIBRAÇÃO — Degree concept is in continuous motion. High=constant flux. Low=static.
[3] POLARIDADE — Degree concept on spectrum between extremes. High=strongly polar. Low=neutral.
[4] RITMO — Degree concept exhibits cyclic pattern. High=clear rhythm. Low=irregular.
[5] CAUSA E EFEITO — Degree concept is causal agent. High=primary cause. Low=pure consequence.
[6] GÊNERO — Degree concept is generative/active. High=active principle. Low=receptive.
[7] SISTEMA — Degree concept is a set with emergent behavior.
[8] ESTADO — Degree concept is a configuration at a given moment.
[9] PROCESSO — Degree concept is transformation over time.
[10] RELAÇÃO — Degree concept is connection between entities.
[11] SINAL — Degree concept is information carrying variation.
[12] ESTABILIDADE — Degree tends toward equilibrium. High=convergent. Low=chaotic.
[13] VALÊNCIA ONTOLÓGICA — Intrinsic sign. 0=negative → 0.5=neutral → 1=positive.
[14] VERIFICABILIDADE — Can be externally confirmed? High=verifiable. Low=unfalsifiable.
[15] TEMPORALIDADE — Has temporal anchor? High=precise moment. Low=timeless.
[16] COMPLETUDE — Resolved? High=closed. Low=open.
[17] CAUSALIDADE — Origin identifiable? High=clear cause. Low=opaque.
[18] REVERSIBILIDADE — Can be undone? High=reversible. Low=irreversible.
[19] CARGA — Cognitive resource consumption. High=heavy. Low=automatic.
[20] ORIGEM — Observed vs inferred? High=direct observation. Low=pure assumption.
[21] VALÊNCIA EPISTÊMICA — 0=contradictory evidence → 0.5=inconclusive → 1=confirmatory.
[22] URGÊNCIA — Requires immediate response? High=critical. Low=no rush.
[23] IMPACTO — Consequences? High=changes system state. Low=innocuous.
[24] AÇÃO — Requires active response? High=demands execution. Low=informational.
[25] VALOR — Connects with something that truly matters? High=loaded. Low=neutral.
[26] ANOMALIA — Deviation from expected? High=strong rupture. Low=normal.
[27] AFETO — Emotional valence? High=strong affect. Low=neutral.
[28] DEPENDÊNCIA — Needs another to exist? High=coupled. Low=autonomous.
[29] VETOR TEMPORAL — 0=past → 0.5=present → 1=future.
[30] NATUREZA — 0=noun/thing → 1=verb/process.
[31] VALÊNCIA DE AÇÃO — 0=alert/contractive → 0.5=neutral → 1=confirmation/expansive.

## Text to score:
"{text}"

Respond with ONLY a JSON array of 32 floats, nothing else:
```

### train_w.py

```python
"""Step 2: Train W matrix via Ridge regression."""

def load_dataset(path: str) -> tuple[list[str], np.ndarray]:
    """Load dataset.jsonl → (texts, targets[N,32])"""

def compute_embeddings(texts: list[str], model_name: str) -> np.ndarray:
    """Compute embeddings using sentence-transformers. Returns [N, D]."""

def train_w_matrix(embeddings: np.ndarray, targets: np.ndarray, config: dict) -> np.ndarray:
    """Train W[32, D] via Ridge regression.
    
    For each of 32 axes independently:
        w_i = Ridge(alpha=config.alpha).fit(embeddings, targets[:, i])
    
    Stack into W[32, D].
    
    Returns: W matrix, train_score, test_score
    """

def main(config_path: str) -> None:
    """Run training. Save W.npy and report metrics."""
```

### evaluate.py

```python
"""Step 3: Evaluate semantic coherence."""

def coherence_benchmark(W: np.ndarray, model_name: str) -> dict:
    """Test that semantically similar concepts have low DIST
    and semantically different concepts have high DIST.
    
    Benchmark pairs (hardcoded):
    - Similar: ("amor","carinho"), ("medo","terror"), ("sol","luz"), ...
    - Different: ("amor","matemática"), ("medo","alegria"), ...
    
    Compute embeddings → W @ emb → sem[32] → DIST for each pair.
    
    Returns:
        similar_mean_dist: float   (should be LOW, < 0.3)
        different_mean_dist: float (should be HIGH, > 0.6)
        coherence_score: float     (different_mean - similar_mean, > threshold)
        per_axis_variance: [32]    (axes with near-zero variance are suspicious)
    """

def axis_coverage(W: np.ndarray, model_name: str) -> dict:
    """Check that each axis has meaningful variation.
    Generate 100 random texts, project through W, compute variance per axis.
    Axes with variance < 0.01 are flagged as potentially collapsed."""

def main(config_path: str) -> None:
    """Run full evaluation suite. Print report. Fail if below threshold."""
```

### export.py

```python
"""Step 4: Export W matrix as binary for leet-service."""

def export_w_bin(W: np.ndarray, output_path: str, format: str = "f32_le") -> None:
    """Export W[32, D] as flat binary file.
    
    Format f32_le:
    - Header: 4 bytes magic "L337"
    - 4 bytes: rows (32) as uint32 LE
    - 4 bytes: cols (D) as uint32 LE
    - rows * cols * 4 bytes: float32 LE values, row-major
    
    Total size: 12 + 32 * D * 4 bytes
    For D=384: 12 + 49152 = ~48KB
    """

def verify_export(path: str) -> dict:
    """Read back W.bin, verify header, shape, value ranges."""
```

### run_pipeline.py

```python
"""Orchestrator: full calibration pipeline."""

@click.command()
@click.option("--config", default="config.yaml")
@click.option("--step", default="all", type=click.Choice(["all","generate","train","evaluate","export"]))
@click.option("--skip-generate", is_flag=True, help="Use existing dataset")
def main(config, step, skip_generate):
    """Run calibration pipeline.
    
    Steps:
    1. generate — Create dataset via LLM scoring (slow, costs API tokens)
    2. train    — Ridge regression (fast, local)
    3. evaluate — Coherence benchmarks (fast, local)
    4. export   — Binary W.bin for leet-service
    """
```

---

## TESTS (minimum 10)

- generate_texts produces diverse texts
- score_text returns 32 floats in [0,1] (mock LLM)
- dataset.jsonl has correct format
- compute_embeddings returns correct shape
- train_w_matrix returns W with shape [32, D]
- train_w_matrix R² > 0 on training set
- coherence_benchmark similar < different
- axis_coverage flags zero-variance axes
- export_w_bin creates file with correct header
- verify_export reads back correct shape and values
- run_pipeline end-to-end with mock LLM

---

## TASKWARRIOR + CONTRACT UPDATE

```bash
task project:1337 +prompt06 status:pending done

sed -i 's/| W matrix calibração | PROMPT_06 | `\[ \]` PENDENTE/| W matrix calibração | PROMPT_06 | `[x]` CONCLUÍDO/' CONTRACT.md
sed -i "s/Última atualização: .*/Última atualização: $(date +%Y-%m-%d)/" CONTRACT.md

# Final metrics update in CONTRACT
RUST_TESTS=$(cargo test --workspace 2>&1 | grep "test result" | awk '{sum += $2} END {print sum}')
echo "Final Rust tests: $RUST_TESTS"

git add -A
git commit -m "feat(prompt-06): W matrix calibration pipeline

- generate_dataset.py: LLM scoring across 32 axes
- train_w.py: Ridge regression embedding→sem[32]
- evaluate.py: coherence benchmarks + axis coverage
- export.py: W.bin binary for leet-service
- run_pipeline.py: full orchestrator
- config.yaml: configurable pipeline
- CONTRACT.md + Taskwarrior updated
- BUILD COMPLETE"

git push origin main
```

---

## VERIFICATION

```bash
cd calibration

# With mock LLM (no API key needed)
python run_pipeline.py --config config.yaml

# Check output
ls -la data/
python -c "
import numpy as np
W = np.load('data/W.npy')
print(f'W shape: {W.shape}')
print(f'W range: [{W.min():.4f}, {W.max():.4f}]')
"

# Verify binary export
python export.py --verify data/W.bin

# Copy to service
cp data/W.bin ../leet-service/

# Tests
pytest tests/ -v

# Taskwarrior final status
task project:1337 summary
task project:1337 status:completed count
task project:1337 status:pending count
```

**END OF PROMPT_06 — BUILD COMPLETE**
