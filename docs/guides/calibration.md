# Calibração da W Matrix

A W matrix `[32 × D]` mapeia embeddings de texto (dimensão D) para os 32 eixos canônicos do COGON. Uma W bem calibrada produz projeções semânticas precisas.

## Visão Geral

```
text → embedding provider → vetor D-dim
                              │
                              ▼
                    W [32 × D] @ embedding
                              │
                              ▼
                    clamp(0, 1) → sem[32]
```

## Estrutura do Diretório

```
calibration/
├── data/
│   ├── anchors.json     — pares (texto, sem_alvo) de treinamento
│   └── W.bin            — W matrix calibrada (saída)
├── calibrate.py         — script principal de calibração
└── validate_w.py        — validação da W produzida
```

## Pré-requisitos

```bash
pip install numpy anthropic sentence-transformers
# ou: pip install numpy openai  (para embeddings OpenAI)
```

## Âncoras de Calibração

O arquivo `anchors.json` define os pares de treinamento — textos com o vetor semântico alvo que eles devem produzir:

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

### Eixos-chave para Âncoras de Diagnóstico

| Situação | Eixos ativados |
|----------|----------------|
| Erro/falha | D1_STATE (8) ↑, P3_ANOMALY (26) ↑, D6_ONTOLOGICAL_VALENCE (13) ↓ |
| Urgência | G8_URGENCY (23) ↑, P7_ACTION (30) ↑ |
| Processo em andamento | D2_PROCESS (9) ↑, G1_TEMPORALITY (16) ↑ |
| Sistema estável | D5_STABILITY (12) ↑, D8_VERIFIABILITY (15) ↑ |
| Reversível | G4_REVERSIBILITY (19) ↑ |
| Confirmação | G7_EPISTEMIC_VALENCE (22) ↑, P8_ACTION_VALENCE (31) ↑ |

## Processo de Calibração

### 1. Gerar Embeddings

```python
# calibrate.py — exemplo com sentence-transformers
from sentence_transformers import SentenceTransformer
import json, numpy as np

model = SentenceTransformer("all-mpnet-base-v2")  # dim=768

with open("calibration/data/anchors.json") as f:
    anchors = json.load(f)

texts = [a["text"] for a in anchors]
targets = np.array([a["sem"] for a in anchors])    # shape: (N, 32)

embeddings = model.encode(texts, normalize_embeddings=True)  # shape: (N, 768)
```

### 2. Resolver W por Mínimos Quadrados

```python
# Resolver W: targets = embeddings @ W.T
# W [32 x D], embeddings [N x D], targets [N x 32]
W, _, _, _ = np.linalg.lstsq(embeddings, targets, rcond=None)
W = W.T   # shape: (32, D)
```

### 3. Calibrar Escala

```python
# Garantir que as projeções caem em [0, 1]
preds = np.clip(embeddings @ W.T, 0, 1)
error = np.mean(np.abs(preds - targets))
print(f"MAE médio: {error:.4f}")  # meta: < 0.08
```

### 4. Salvar W.bin

```python
# Formato: [u32 rows][u32 cols][f32 * rows * cols] (little-endian)
rows, cols = W.shape
with open("calibration/data/W.bin", "wb") as f:
    f.write(rows.to_bytes(4, "little"))
    f.write(cols.to_bytes(4, "little"))
    f.write(W.astype(np.float32).tobytes())

print(f"W.bin salvo: {rows}x{cols} ({rows*cols*4/1024:.1f} KB)")
```

## Validação

```bash
# Validar a W produzida
LEET_W_PATH=calibration/data/W.bin python3 calibration/validate_w.py

# Ou via CLI (usa LEET_W_PATH automaticamente)
LEET_W_PATH=calibration/data/W.bin ./target/release/leet encode "deploy falhou"
```

### Critérios de Qualidade

| Métrica | Meta |
|---------|------|
| MAE nas âncoras | < 0.08 |
| Projeções fora de [0, 1] | 0% (clamp automático) |
| Distância "urgente" vs "tranquilo" | > 0.5 |
| Distância "falhou" vs "funcionando" | > 0.4 |

## Providers de Embedding

| Provider | Dimensão | Qualidade | Custo |
|----------|----------|-----------|-------|
| `all-mpnet-base-v2` (local) | 768 | Alta | Gratuito |
| `text-embedding-3-small` (OpenAI) | 1536 | Alta | Pago |
| `text-embedding-ada-002` (OpenAI) | 1536 | Alta | Pago |
| `voyage-3` (Anthropic) | 1024 | Alta | Pago |

## Re-calibração

Situações que exigem re-calibração:

- Adição de novos eixos emergentes ao protocolo
- Mudança de provider de embedding
- Expansão do domínio semântico das âncoras
- MAE acima de 0.10 no conjunto de validação

## Deploy da W Matrix

```bash
# Copiar para o servidor
scp calibration/data/W.bin servidor:/opt/leet/W.bin

# Configurar variável de ambiente
export LEET_W_PATH=/opt/leet/W.bin

# Ou em systemd (ver guia de deploy)
Environment=LEET_W_PATH=/opt/leet/W.bin
```

A W matrix é carregada uma única vez por processo via `OnceLock` — sem overhead por requisição.
