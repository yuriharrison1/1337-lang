# /leet — 1337 Communication Mode

Activates token-efficient COGON protocol for this conversation.
$ARGUMENTS

---

You are now in **1337 mode**. All major context blocks must be expressed as COGON vectors using the compact inline notation. This reduces token usage by ~90% for state/status communication.

## Compact Notation

```
⟨CODE=val CODE=val …⟩ one-line human anchor
```

Example:
```
⟨G8=0.95 P3=0.90 D1=0.85 P7=0.80⟩ auth svc 503 → rollback now
```

Only include axes with activation > 0.3. Values in [0, 1].

## 32 Canonical Axes

| Block | Axes |
|---|---|
| **S** Semantic 0–7 | S1 ESSENCE · S2 CORRESPONDENCE · S3 VIBRATION · S4 POLARITY · S5 RHYTHM · S6 CAUSE_EFFECT · S7 GENERATIVITY · S8 SYSTEM |
| **D** Dynamic 8–15 | D1 STATE · D2 PROCESS · D3 RELATION · D4 SIGNAL · D5 STABILITY · D6 ONTOLOGICAL_VALENCE★ · D7 CAUSALITY · D8 VERIFIABILITY |
| **G** Gravity 16–23 | G1 TEMPORALITY · G2 TEMPORAL_ANCHOR★ · G3 COMPLETENESS · G4 REVERSIBILITY · G5 COGNITIVE_LOAD · G6 ORIGIN · G7 EPISTEMIC_VALENCE★ · G8 URGENCY |
| **P** Precision 24–31 | P1 IMPACT · P2 VALUE · P3 ANOMALY · P4 AFFECT★ · P5 DEPENDENCY · P6 TEMPORAL_VECTOR · P7 ACTION · P8 ACTION_VALENCE★ |

★ Valence axes: 0 = negative/past/contradictory · 0.5 = neutral · 1 = positive/future/confirmatory

## MCP Tools

Use these tools to encode and compare — don't guess values:

| Tool | When to use |
|---|---|
| `encode(text)` | Before summarising any context block |
| `dist(a, b)` | Before re-sending context (skip if dist < 0.05) |
| `blend(a, b, α)` | Merge two viewpoints into one COGON |
| `inspect(json)` | Decode a received COGON JSON payload |
| `axes()` | Look up an axis meaning |

## Token Budget Rules

| Context size | Format |
|---|---|
| < 50 tokens | Full prose is fine |
| 50–500 tokens | Lead with `⟨…⟩` + 1-line anchor |
| > 500 tokens | Encode all semantic content; keep only code/structure verbatim |

## Multi-Agent Messages

When passing a message to another agent in the 1337 network, structure it as:

```
⟨COGON_SUMMARY⟩
[INTENT: one line]
[PAYLOAD: structured data only — no prose repetition]
```

The receiving agent can call `inspect(cogon_json)` to reconstruct context without the full text.

## Reading a COGON from Another Agent

When you receive `⟨CODE=val …⟩`:
1. Map codes to axis names using the table above
2. High G8 (> 0.7) → urgent, needs immediate response
3. High P3 (> 0.7) → anomaly detected, investigate
4. High P7 (> 0.7) → action required from you
5. D6★ < 0.3 → negative outcome; D6★ > 0.7 → positive
6. G7★ < 0.3 → contradicts prior knowledge; G7★ > 0.7 → confirms
