# PROMPT 06 — calibration pipeline (W matrix)

Build the calibration pipeline that trains the W projection matrix:
the linear map from embedding space to the 1337 canonical 32-dim space.

This runs ONCE to produce `W.bin`. After calibration, leet-service uses W for
all projections without calling any LLM. This is what makes the service fast.

## Directory

Create `calibration/` at the workspace root with:

```
calibration/
├── README.md
├── requirements.txt
├── generate_dataset.py     ← Step 1: LLM scores 32 axes for sample texts
├── train_w.py              ← Step 2: linear regression → W matrix
├── evaluate_w.py           ← Step 3: evaluate projection quality
├── export_w.py             ← Step 4: export W.bin for leet-service
└── data/
    └── seed_texts.txt      ← 100 diverse seed texts
```

## requirements.txt

```
openai>=1.12
anthropic>=0.20
numpy>=1.26
scikit-learn>=1.4
scipy>=1.13
tqdm>=4.66
rich>=13.7
```

## data/seed_texts.txt

100 diverse seed texts (one per line) covering:
- Technical (engineering, programming, math, physics)
- Abstract (philosophy, concepts, emotions)
- Actions (verbs, processes, transformations)
- Objects (nouns, entities, states)
- Temporal (past events, future plans, present states)
- Uncertain (hypotheses, possibilities, questions)
- High urgency (errors, alerts, critical situations)
- Low urgency (informational, background, context)

Generate the 100 texts covering all these categories spread across the 32 axes.
Write them directly into the file — no placeholders.

Example entries:
```
controle preditivo baseado em modelo (MPC) para sistemas de manufatura
the bridge collapsed at 3am due to structural failure
I am not sure whether this approach will work
water boils at 100 degrees Celsius at sea level pressure
deploy new microservice to production immediately — breaking change
Beethoven composed the Ninth Symphony while deaf
what would happen if we increased the learning rate to 0.1?
o sistema está em equilíbrio dinâmico
the agent received the message and updated its internal state
this configuration is irreversible once applied
```
(Write all 100 entries — be thorough and diverse)

## generate_dataset.py

```python
"""
Step 1: Generate training data.
For each text, ask an LLM to score all 32 axes.
Output: data/dataset.jsonl

Usage:
    python generate_dataset.py --provider anthropic --n 100
    python generate_dataset.py --provider openai --n 100
"""
```

**LLM prompt to use** (embed this exactly in the script):

```
You are a semantic analysis engine implementing the 1337 protocol.
Score the following text on exactly 32 semantic axes.
Return ONLY a JSON object with keys "sem" (array of 32 floats in [0,1])
and "unc" (array of 32 floats in [0,1] representing your confidence).

The 32 axes in order (index 0 to 31):
[0]  via:               degree of self-existence, independent of external relations. 1=pure essence.
[1]  correspondencia:   degree of mirroring patterns across abstraction levels.
[2]  vibracao:          degree of continuous movement/transformation. 1=constant flux.
[3]  polaridade:        degree of positioning on a spectrum between extremes.
[4]  ritmo:             degree of cyclical/periodic pattern.
[5]  causa_efeito:      degree of being a causal agent vs effect. 1=primary cause.
[6]  genero:            degree of generative/active vs receptive/passive. 1=active.
[7]  sistema:           degree of being a set with emergent behavior.
[8]  estado:            degree of being a configuration at a given moment.
[9]  processo:          degree of being transformation over time.
[10] relacao:           degree of being a connection between entities.
[11] sinal:             degree of being information carrying variation.
[12] estabilidade:      degree of tending toward equilibrium. 1=convergent.
[13] valencia_ont:      intrinsic signal. 0=negative/contractive, 0.5=neutral, 1=positive/expansive.
[14] verificabilidade:  degree of external verifiability. 1=falsifiable evidence.
[15] temporalidade:     degree of having a defined temporal anchor. 1=precise moment.
[16] completude:        degree of being resolved/closed. 1=conclusive.
[17] causalidade:       degree of identifiable origin. 1=clear cause.
[18] reversibilidade:   degree of being undoable. 1=fully reversible.
[19] carga:             degree of cognitive resource consumption. 1=heavy/demands attention.
[20] origem:            degree of observed vs inferred vs assumed. 1=direct observation.
[21] valencia_epist:    knowledge signal. 0=contradictory evidence, 0.5=inconclusive, 1=confirmatory.
[22] urgencia:          degree of requiring immediate response. 1=critical time pressure.
[23] impacto:           degree of generating system consequences. 1=changes system state.
[24] acao:              degree of requiring active response vs just alignment. 1=demands execution.
[25] valor:             degree of activating values, not just logic. 1=meaning-loaded.
[26] anomalia:          degree of deviation from expected pattern. 1=strong rupture.
[27] afeto:             degree of emotional valence. 1=strong affective charge.
[28] dependencia:       degree of needing another to exist. 1=fully coupled.
[29] vetor_temporal:    temporal orientation. 0=pure past, 0.5=present, 1=pure future.
[30] natureza:          semantic category. 0=pure noun (thing/state), 1=pure verb (process/action).
[31] valencia_acao:     agent's transmission intention. 0=alert/contractive, 0.5=neutral/query, 1=positive/confirmation.

Text to score: "{text}"

Respond with ONLY the JSON, no explanation:
{{"sem": [f0, f1, ..., f31], "unc": [u0, u1, ..., u31]}}
```

**Script logic**:
- Load texts from `data/seed_texts.txt`
- For each text, call LLM with the prompt above
- Parse JSON response, validate 32 dims, clamp to [0,1]
- Append to `data/dataset.jsonl` as `{"text": "...", "sem": [...], "unc": [...]}`
- Skip texts already in dataset (resume-safe)
- If JSON parse fails, retry up to 3 times with temperature=0
- Print progress with tqdm

Also compute a 128-dim mock embedding for each text (SHA256 expansion, same as LocalProjector)
and save alongside: `{"text": "...", "emb": [...128 floats...], "sem": [...], "unc": [...]}`

## train_w.py

```python
"""
Step 2: Train W matrix (linear regression).
Input:  data/dataset.jsonl (with emb[128] and sem[32])
Output: data/W.npy (shape [128, 32])

Usage:
    python train_w.py
"""
```

**Algorithm**:
1. Load dataset.jsonl
2. Build X matrix: shape [N, 128] — embeddings
3. Build Y matrix: shape [N, 32]  — sem targets (weighted by 1-unc)
4. Fit linear regression with L2 regularization (Ridge, alpha=0.01):
   `W = Ridge(alpha=0.01).fit(X, Y).coef_.T`  → shape [128, 32]
5. Post-process W: scale columns so output is in [0,1] range
6. Save as `data/W.npy` (numpy format)
7. Also save as `data/W.bin` (raw float32 binary for leet-service)

Print training stats:
```
Training W matrix (128 → 32)
Dataset: 100 samples
Train/val split: 80/20

Training...
  Ridge regression (alpha=0.01)
  
Results on validation set:
  MAE per axis:  0.0823
  R² score:      0.742
  
Worst axes (highest MAE):
  [26] anomalia:   MAE=0.142
  [27] afeto:      MAE=0.138
  [29] vetor_temp: MAE=0.091

Best axes (lowest MAE):
  [9]  processo:   MAE=0.043
  [7]  sistema:    MAE=0.047

W matrix saved: data/W.npy (128 × 32 float32)
W binary saved: data/W.bin (16384 bytes)
```

## evaluate_w.py

```python
"""
Step 3: Evaluate projection quality.
Checks that W produces semantically consistent projections.

Usage:
    python evaluate_w.py
"""
```

**Tests**:

1. **Axis coherence test**: For 10 pairs of semantically similar texts,
   verify DIST(project(a), project(b)) < 0.3.
   Pairs: ("hello world", "greetings universe"), ("MPC control", "model predictive control"), etc.

2. **Axis extremity test**: For texts designed to be high on specific axes,
   verify that axis value > 0.6:
   - "emergency critical failure NOW" → urgencia[22] > 0.6
   - "this happened last year" → vetor_temporal[29] < 0.4 (past)
   - "run the process now" → natureza[30] > 0.6 (verb)
   - "a rock is a solid object" → natureza[30] < 0.4 (noun)

3. **Round-trip coherence**: encode 20 texts, decode, check that
   dominant axes in decoded output match expectations.

4. **UNC calibration**: verify that unc estimates are meaningful
   (definitive statements should have lower avg unc than vague statements).

Print pass/fail for each test with details.

## export_w.py

```python
"""
Step 4: Export W.bin to leet-service location.

Usage:
    python export_w.py [--dest /opt/leet/W.bin]
"""
```

Copies `data/W.bin` to destination.
Updates the README with export timestamp and matrix stats.

## README.md

Explain the calibration pipeline, how to run each step, and how to interpret results.
Include the W matrix dimensions and the expected embedding model.

Include section on how to recalibrate:
- When to recalibrate: adding new axes, changing embedding model, significant semantic drift
- Minimum dataset size: 100 samples (200+ recommended)
- Expected training time: < 1 min for mock embeddings, ~ 5 min with API

## Run the pipeline

```bash
cd calibration
pip install -r requirements.txt

# Step 1: generate dataset (uses mock embeddings by default)
python generate_dataset.py --provider mock --n 100

# Step 2: train W matrix
python train_w.py

# Step 3: evaluate
python evaluate_w.py

# Step 4: export to service
python export_w.py --dest ../leet-service/W.bin
```

All steps must run without errors. The final W.bin must be a valid float32 binary file
of size exactly 128 * 32 * 4 = 16384 bytes.
