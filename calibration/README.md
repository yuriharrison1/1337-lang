# 1337 Calibration Pipeline

This pipeline trains the **W matrix** — a linear projection from 128-dimensional text embeddings into the 32-dimensional 1337 canonical semantic space.

## What it does

The 1337 protocol represents any message as a vector in a fixed 32-axis semantic space. Each axis captures a specific semantic property (urgency, temporality, causality, etc.). The W matrix (shape `[128, 32]`) is the bridge between raw text embeddings and this canonical space.

The calibration pipeline:
1. Generates a labeled dataset: text → embedding + semantic scores
2. Trains W via Ridge regression, minimizing MAE between projected embeddings and LLM-scored semantic targets
3. Evaluates W quality via coherence and extremity tests
4. Exports the resulting `W.bin` to the service location

## Directory structure

```
calibration/
├── generate_dataset.py   # Step 1: generate data/dataset.jsonl
├── train_w.py            # Step 2: train and save data/W.npy + data/W.bin
├── evaluate_w.py         # Step 3: run coherence tests
├── export_w.py           # Step 4: copy W.bin to service
├── requirements.txt
└── data/
    ├── seed_texts.txt    # 100 diverse seed texts
    ├── dataset.jsonl     # generated (Step 1 output)
    ├── W.npy             # trained W (Step 2 output)
    └── W.bin             # raw float32 binary (Step 2 output)
```

## How to run

### Install dependencies

```bash
pip install -r requirements.txt
```

### Step 1 — Generate dataset

```bash
# Fast mock mode (no API key needed, deterministic SHA256 scoring)
python generate_dataset.py --provider mock --n 100

# With a real LLM (better quality)
python generate_dataset.py --provider anthropic --n 100
python generate_dataset.py --provider openai --n 100
```

The script is resume-safe: it skips texts already present in `data/dataset.jsonl`.

### Step 2 — Train W

```bash
python train_w.py
```

Outputs:
- `data/W.npy` — numpy array, shape `[128, 32]`, dtype `float32`
- `data/W.bin` — raw little-endian float32, exactly **16384 bytes** (128 × 32 × 4)

### Step 3 — Evaluate

```bash
python evaluate_w.py
```

Runs three test suites:
- **Axis coherence**: similar texts should be close in semantic space
- **Axis extremity**: critical alerts should score high on axis 22 (urgency), etc.
- **Uncertainty calibration**: definitive statements should have lower uncertainty than vague questions

### Step 4 — Export

```bash
python export_w.py --dest ../leet-service/W.bin
```

## W matrix dimensions

| Dimension | Size | Description |
|-----------|------|-------------|
| Input     | 128  | SHA256-expanded text embedding (mock) or dense embedding (production) |
| Output    | 32   | 1337 canonical semantic axes |
| Binary    | 16384 bytes | 128 × 32 × 4 bytes (float32 little-endian) |

## The 32 semantic axes

| Index | Name | Description |
|-------|------|-------------|
| 0 | via | Self-existence, independent of external relations |
| 1 | correspondencia | Mirroring across abstraction levels |
| 2 | vibracao | Continuous movement/transformation |
| 3 | polaridade | Positioning on a spectrum between extremes |
| 4 | ritmo | Cyclical/periodic pattern |
| 5 | causa_efeito | Causal agent vs effect |
| 6 | genero | Generative/active vs receptive/passive |
| 7 | sistema | Set with emergent behavior |
| 8 | estado | Configuration at a given moment |
| 9 | processo | Transformation over time |
| 10 | relacao | Connection between entities |
| 11 | sinal | Information-carrying variation |
| 12 | estabilidade | Tendency toward equilibrium |
| 13 | valencia_ont | Intrinsic signal (contractive ↔ expansive) |
| 14 | verificabilidade | External verifiability |
| 15 | temporalidade | Defined temporal anchor |
| 16 | completude | Resolved/closed |
| 17 | causalidade | Identifiable origin |
| 18 | reversibilidade | Undoable |
| 19 | carga | Cognitive resource consumption |
| 20 | origem | Observed vs inferred vs assumed |
| 21 | valencia_epist | Knowledge signal (contradictory ↔ confirmatory) |
| 22 | urgencia | Requires immediate response |
| 23 | impacto | Generates system consequences |
| 24 | acao | Requires active response vs alignment |
| 25 | valor | Activates values, not just logic |
| 26 | anomalia | Deviation from expected pattern |
| 27 | afeto | Emotional valence |
| 28 | dependencia | Needs another to exist |
| 29 | vetor_temporal | Temporal orientation (past ↔ future) |
| 30 | natureza | Semantic category (noun/state ↔ verb/process) |
| 31 | valencia_acao | Transmission intention (alert ↔ confirmation) |

## When to recalibrate

Recalibrate W when:
- The embedding model changes (different SHA256 expansion or new dense encoder)
- New semantic axes are added or redefined in the 1337 protocol
- Significant domain shift in the target corpus (e.g., adding financial or medical texts)
- Validation MAE exceeds 0.15 on a held-out evaluation set
- The LLM scorer is upgraded and produces systematically different scores

## Expected training time

| Provider | N=100 | N=1000 |
|----------|-------|--------|
| mock     | < 1s  | ~2s    |
| anthropic | ~2-5 min | ~20-50 min |
| openai   | ~2-5 min | ~20-50 min |

Training itself (Step 2) takes under 1 second for N ≤ 10,000 on any modern CPU.
