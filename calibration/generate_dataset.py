"""
Step 1: Generate training data.
For each text in data/seed_texts.txt, generate a mock embedding + LLM-scored sem/unc.

Provider 'mock' uses SHA256-based scoring (no API needed).
Provider 'anthropic' or 'openai' calls the real LLM.

Output: data/dataset.jsonl
Each line: {"text": "...", "emb": [...128 floats...], "sem": [...32 floats...], "unc": [...32 floats...]}

Usage:
    python generate_dataset.py --provider mock --n 100
    python generate_dataset.py --provider anthropic --n 100
"""

import argparse
import hashlib
import json
import os
import sys
import time

from tqdm import tqdm


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def mock_embed(text: str) -> list[float]:
    """128-dim SHA256 expansion — same algorithm as LocalProjector but 128 dims."""
    h = hashlib.sha256(text.encode()).digest()
    emb = []
    for i in range(128):
        b1 = h[i % 32]
        b2 = h[(i + 1) % 32]
        b3 = h[(i + 2) % 32]
        val = ((b1 << 16 | b2 << 8 | b3) & 0xFFFFFF) / 16777215.0
        emb.append(val)
    return emb


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def mock_score(text: str) -> tuple[list[float], list[float]]:
    """Deterministic scoring for 32 axes based on text hash. Used for --provider mock."""
    h = hashlib.sha256(text.encode()).digest()
    sem = []
    unc = []
    for i in range(32):
        b1 = h[i % 32]
        b2 = h[(i + 1) % 32]
        val = ((b1 << 8 | b2) & 0xFFFF) / 65535.0
        sem.append(val)
        unc.append(1.0 - abs(val - 0.5) * 2.0)
    return sem, unc


LLM_PROMPT = """You are a semantic analysis engine implementing the 1337 protocol.
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
{{"sem": [f0, f1, ..., f31], "unc": [u0, u1, ..., u31]}}"""


def clamp(val: float) -> float:
    return max(0.0, min(1.0, float(val)))


def llm_score_openai(text: str, client) -> tuple[list[float], list[float]]:
    prompt = LLM_PROMPT.format(text=text)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            sem = [clamp(v) for v in data["sem"]]
            unc = [clamp(v) for v in data["unc"]]
            if len(sem) != 32 or len(unc) != 32:
                raise ValueError(f"Expected 32 dims, got sem={len(sem)}, unc={len(unc)}")
            return sem, unc
        except Exception as e:
            print(f"  [openai] attempt {attempt+1} failed: {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"OpenAI scoring failed after 3 attempts for: {text[:60]}")


def llm_score_anthropic(text: str, client) -> tuple[list[float], list[float]]:
    prompt = LLM_PROMPT.format(text=text)
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            content = message.content[0].text.strip()
            data = json.loads(content)
            sem = [clamp(v) for v in data["sem"]]
            unc = [clamp(v) for v in data["unc"]]
            if len(sem) != 32 or len(unc) != 32:
                raise ValueError(f"Expected 32 dims, got sem={len(sem)}, unc={len(unc)}")
            return sem, unc
        except Exception as e:
            print(f"  [anthropic] attempt {attempt+1} failed: {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Anthropic scoring failed after 3 attempts for: {text[:60]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate 1337 calibration dataset.")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai", "anthropic"],
                        help="Scoring provider (default: mock)")
    parser.add_argument("--n", type=int, default=100,
                        help="Number of texts to process (default: 100)")
    parser.add_argument("--output", default="data/dataset.jsonl",
                        help="Output path (default: data/dataset.jsonl)")
    args = parser.parse_args()

    seed_path = "data/seed_texts.txt"
    if not os.path.exists(seed_path):
        print(f"ERROR: {seed_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(seed_path, "r", encoding="utf-8") as f:
        texts = [line.strip() for line in f if line.strip()]
    texts = texts[: args.n]
    print(f"Loaded {len(texts)} texts from {seed_path}")

    # Load already-processed texts for resume support
    existing = set()
    if os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    existing.add(rec["text"])
                except json.JSONDecodeError:
                    pass
        print(f"Resuming: {len(existing)} texts already in {args.output}")

    # Init LLM client if needed
    client = None
    if args.provider == "openai":
        import openai
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        client = openai.OpenAI(api_key=api_key)
    elif args.provider == "anthropic":
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)

    with open(args.output, "a", encoding="utf-8") as out_f:
        for text in tqdm(texts, desc=f"Generating [{args.provider}]"):
            if text in existing:
                continue

            emb = mock_embed(text)

            if args.provider == "mock":
                sem, unc = mock_score(text)
            elif args.provider == "openai":
                sem, unc = llm_score_openai(text, client)
            else:
                sem, unc = llm_score_anthropic(text, client)

            record = {"text": text, "emb": emb, "sem": sem, "unc": unc}
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()

    # Final count
    total = 0
    with open(args.output, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                total += 1
    print(f"Done. {total} records in {args.output}")


if __name__ == "__main__":
    main()
