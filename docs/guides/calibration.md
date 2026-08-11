# W Matrix Calibration

The W matrix `[32 × D]` maps text embeddings (dimension D) to the 32 canonical COGON axes. A well-calibrated W produces accurate semantic projections.

## Overview

```
text → embedding provider → D-dim vector
                              │
                              ▼
                    W [32 × D] @ embedding
                              │
                              ▼
                    clamp(0, 1) → sem[32]
```

## Directory Structure

```
calibration/
├── data/
│   ├── anchors.json     — (text, target_sem) training pairs
│   └── W.bin            — calibrated W matrix (output)
├── calibrate.py         — main calibration script
└── validate_w.py        — validation of the produced W
```

## Prerequisites

```bash
pip install numpy anthropic sentence-transformers
# or: pip install numpy openai  (for OpenAI embeddings)
```

## Calibration Anchors

The `anchors.json` file defines the training pairs — texts along with the target semantic vector they should produce:

```json
[
  {
    "text": "deploy urgente falhou em produção",
    "sem": [0.5, 0.0, 0.0, 0.0,  0.0, 0.5, 0.5, 0.8,
            0.9, 0.7, 0.3, 0.6,  0.2, 0.15, 0.7, 0.8,
            0.7, 0.3, 0.2, 0.3,  0.6, 0.8, 0.3, 0.95,
            0.85, 0.6, 0.90, 0.2, 0.5, 0.7, 0.80, 0.2]
  },
  {
    "text": "sistema operando normalmente",
    "sem": [0.7, 0.5, 0.3, 0.5,  0.4, 0.6, 0.5, 0.8,
            0.5, 0.3, 0.4, 0.8,  0.9, 0.8, 0.7, 0.9,
            0.5, 0.5, 0.8, 0.6,  0.2, 0.9, 0.8, 0.1,
            0.3, 0.8, 0.1, 0.7,  0.3, 0.5, 0.1, 0.8]
  }
]
```

### Key Axes for Diagnostic Anchors

| Situation | Axes activated |
|----------|----------------|
| Error/failure | D1_STATE (8) ↑, P3_ANOMALY (26) ↑, D6_ONTOLOGICAL_VALENCE (13) ↓ |
| Urgency | G8_URGENCY (23) ↑, P7_ACTION (30) ↑ |
| Process in progress | D2_PROCESS (9) ↑, G1_TEMPORALITY (16) ↑ |
| Stable system | D5_STABILITY (12) ↑, D8_VERIFIABILITY (15) ↑ |
| Reversible | G4_REVERSIBILITY (19) ↑ |
| Confirmation | G7_EPISTEMIC_VALENCE (22) ↑, P8_ACTION_VALENCE (31) ↑ |

## Calibration Process

### 1. Generate Embeddings

```python
# calibrate.py — example with sentence-transformers
from sentence_transformers import SentenceTransformer
import json, numpy as np

model = SentenceTransformer("all-mpnet-base-v2")  # dim=768

with open("calibration/data/anchors.json") as f:
    anchors = json.load(f)

texts = [a["text"] for a in anchors]
targets = np.array([a["sem"] for a in anchors])    # shape: (N, 32)

embeddings = model.encode(texts, normalize_embeddings=True)  # shape: (N, 768)
```

### 2. Solve for W via Least Squares

```python
# Solve for W: targets = embeddings @ W.T
# W [32 x D], embeddings [N x D], targets [N x 32]
W, _, _, _ = np.linalg.lstsq(embeddings, targets, rcond=None)
W = W.T   # shape: (32, D)
```

### 3. Calibrate Scale

```python
# Ensure projections fall within [0, 1]
preds = np.clip(embeddings @ W.T, 0, 1)
error = np.mean(np.abs(preds - targets))
print(f"MAE médio: {error:.4f}")  # target: < 0.08
```

### 4. Save W.bin

```python
# Format: [u32 rows][u32 cols][f32 * rows * cols] (little-endian)
rows, cols = W.shape
with open("calibration/data/W.bin", "wb") as f:
    f.write(rows.to_bytes(4, "little"))
    f.write(cols.to_bytes(4, "little"))
    f.write(W.astype(np.float32).tobytes())

print(f"W.bin salvo: {rows}x{cols} ({rows*cols*4/1024:.1f} KB)")
```

## Validation

```bash
# Validate the produced W
LEET_W_PATH=calibration/data/W.bin python3 calibration/validate_w.py

# Or via CLI (uses LEET_W_PATH automatically)
LEET_W_PATH=calibration/data/W.bin ./target/release/leet encode "deploy falhou"
```

### Quality Criteria

| Metric | Target |
|---------|------|
| MAE on anchors | < 0.08 |
| Projections outside [0, 1] | 0% (automatic clamp) |
| Distance "urgent" vs "calm" | > 0.5 |
| Distance "failed" vs "working" | > 0.4 |

## Embedding Providers

| Provider | Dimension | Quality | Cost |
|----------|----------|-----------|-------|
| `all-mpnet-base-v2` (local) | 768 | High | Free |
| `text-embedding-3-small` (OpenAI) | 1536 | High | Paid |
| `text-embedding-ada-002` (OpenAI) | 1536 | High | Paid |
| `voyage-3` (Anthropic) | 1024 | High | Paid |

## Re-calibration

Situations that require re-calibration:

- Adding new emergent axes to the protocol
- Changing the embedding provider
- Expanding the semantic domain of the anchors
- MAE above 0.10 on the validation set

## Deploying the W Matrix

```bash
# Copy to the server
scp calibration/data/W.bin servidor:/opt/leet/W.bin

# Set the environment variable
export LEET_W_PATH=/opt/leet/W.bin

# Or in systemd (see deployment guide)
Environment=LEET_W_PATH=/opt/leet/W.bin
```

The W matrix is loaded once per process via `OnceLock` — no per-request overhead.
