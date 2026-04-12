# 1337 Protocol Specification — v0.5.1

## The COGON

COGON is the fundamental unit of the 1337 protocol. It is a 32-dimensional semantic vector representing the *compressed meaning* of any message, concept, or state.

```rust
pub struct Cogon {
    pub id:    Uuid,             // unique identifier
    pub sem:   [f32; 32],       // semantic projection — values in [0.0, 1.0]
    pub unc:   [f32; 32],       // uncertainty per dimension — 0=certain, 1=total uncertainty
    pub stamp: i64,              // timestamp in nanoseconds since Unix epoch
    pub raw:   Option<RawField>, // optional arbitrary content (text, bytes, JSON)
}
```

**COGON_ZERO** — identity, "I exist":
```json
{
  "id": "00000000-0000-0000-0000-000000000000",
  "sem": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
  "unc": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
          0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "stamp": 0,
  "raw": null
}
```

---

## The 32 Canonical Axes (v0.5.1)

The 32 axes are organized in 4 blocks of 8. All values are in `[0.0, 1.0]` except **valence axes** which have 0.5 as the neutral baseline.

### Block S — Semantic (indices 0–7)

| Idx | Name | Description | Extremes |
|-----|------|-------------|---------|
| 0 | S1 ESSENCIA | Concept exists by itself | 0=dependent, 1=self-existent |
| 1 | S2 CORRESPONDENCIA | Mirrors patterns at other abstraction levels | 0=unique, 1=analogous |
| 2 | S3 VIBRACAO | Continuous movement/transformation | 0=static, 1=transforming |
| 3 | S4 POLARIDADE | Position on a spectrum between extremes | 0=negative pole, 1=positive pole |
| 4 | S5 RITMO | Cyclic or periodic pattern | 0=irregular, 1=highly periodic |
| 5 | S6 CAUSA_EFEITO | Causal agent vs effect | 0=pure effect, 1=pure cause |
| 6 | S7 GENERO | Generative/active vs receptive/passive | 0=receptive, 1=generative |
| 7 | S8 SISTEMA | Set with emergent behavior | 0=atom, 1=complex system |

### Block D — Dynamic (indices 8–15)

| Idx | Name | Description | Extremes |
|-----|------|-------------|---------|
| 8 | D1 ESTADO | Configuration at a moment | 0=unknown, 1=fully defined |
| 9 | D2 PROCESSO | Transformation over time | 0=static, 1=active process |
| 10 | D3 RELACAO | Connection between entities | 0=isolated, 1=deeply connected |
| 11 | D4 SINAL | Information carrying variation | 0=noise, 1=clear signal |
| 12 | D5 ESTABILIDADE | Tendency to equilibrium | 0=diverging, 1=very stable |
| 13 | **D6 VALENCIA_ONT** ★ | Intrinsic sign | 0=negative, **0.5=neutral**, 1=positive |
| 14 | D7 CAUSALIDADE | Origin identifiable | 0=opaque, 1=clear cause |
| 15 | D8 VERIFICABILIDADE | Externally confirmable | 0=unverifiable, 1=verifiable |

### Block G — Gravity (indices 16–23)

| Idx | Name | Description | Extremes |
|-----|------|-------------|---------|
| 16 | G1 TEMPORALIDADE | Defined temporal anchor | 0=timeless, 1=time-anchored |
| 17 | **G2 ANCORA_TEMPORAL** ★ | Temporal orientation | 0=past, **0.5=present**, 1=future |
| 18 | G3 COMPLETUDE | Resolved or open | 0=fully open, 1=fully resolved |
| 19 | G4 REVERSIBILIDADE | Can be undone | 0=irreversible, 1=reversible |
| 20 | G5 CARGA | Cognitive load | 0=trivial, 1=maximum load |
| 21 | G6 ORIGEM | Degree of observation | 0=assumed, 0.5=inferred, 1=observed |
| 22 | **G7 VALENCIA_EPIST** ★ | Epistemic sign | 0=contradictory, **0.5=inconclusive**, 1=confirmatory |
| 23 | G8 URGENCIA | Temporal pressure | 0=none, 1=maximum urgency |

### Block P — Precision (indices 24–31)

| Idx | Name | Description | Extremes |
|-----|------|-------------|---------|
| 24 | P1 IMPACTO | Expected consequence | 0=negligible, 1=maximum impact |
| 25 | P2 VALOR | Connects to what truly matters | 0=irrelevant, 1=high value |
| 26 | P3 ANOMALIA | Deviation from expected pattern | 0=normal, 1=strong anomaly |
| 27 | **P4 AFETO** ★ | Emotional valence | 0=negative, **0.5=neutral**, 1=positive |
| 28 | P5 DEPENDENCIA | Needs another to exist | 0=independent, 1=fully dependent |
| 29 | P6 VETOR_TEMPORAL | Temporal direction | 0=past-oriented, 1=future-oriented |
| 30 | P7 ACAO | Active response required | 0=passive, 1=immediate action |
| 31 | **P8 VALENCIA_ACAO** ★ | Action intention sign | 0=alert, **0.5=query**, 1=confirmation |

★ **Valence axes** — neutral baseline at 0.5. To compute activation, use `|value - 0.5|`.

---

## Semantic Coherence Rules

When building or evaluating a COGON, these relationships must hold:

| Rule | Condition | Implication |
|------|-----------|-------------|
| Strong anomaly | P3 > 0.8 | P7 (action) should be > 0.6 |
| High urgency | G8 > 0.7 | G5 (cognitive load) tends to > 0.5 |
| Positive message | D6 > 0.7 | P3 tends to < 0.3 |
| COGON_ZERO | sem = [1.0;32] | Used only as handshake |
| Total uncertainty | unc[i] = 1.0 | Not allowed — indicates encoding error |
| Clear affirmation | D6 or G7 > 0.85 | Strong positive valence |
| Confirmed anomaly | Intent = ANOMALY | P3 > 0.7 required |

---

## MSG_1337 — Full Protocol Message

```rust
pub struct Msg1337 {
    pub id:       Uuid,
    pub sender:   Uuid,
    pub receiver: Receiver,    // All, Agent(Uuid), Surface(String)
    pub intent:   Intent,      // ASSERT | QUERY | DELTA | SYNC | ANOMALY | ACK
    pub ref_hash: Option<[u8; 32]>,  // reference to a previous message
    pub patch:    Option<Cogon>,      // semantic delta (for Intent::DELTA)
    pub payload:  Cogon,              // main content
    pub c5:       Option<CanonicalSpace>,
    pub surface:  Option<String>,
}
```

### Intent Values

| Value | Use |
|-------|-----|
| `ASSERT` | Informational statement (default) |
| `QUERY` | Request for information or clarification |
| `DELTA` | State change (sends a patch COGON) |
| `SYNC` | State synchronization between agents |
| `ANOMALY` | Error report or escalation |
| `ACK` | Acknowledgement of receipt or completion |

---

## C5 Handshake

The C5 handshake is executed before any message exchange in server mode. It verifies that the agent knows the 1337 v0.5.1 specification.

### Phases

```
Client                          Server
   │                               │
   │── Register { name, role } ──▶│  PROBE
   │                               │  validates canonical name
   │◀── Registered { id, anchors} ─│  ECHO
   │    5 anchor COGONs            │
   │                               │
   │── Align { hash } ────────────▶│  ALIGN
   │   SHA256("1337:v0.5.1:" + name)│  server recomputes and compares
   │                               │
   │◀── Ready ─────────────────────│  VERIFY (success)
   │                              or
   │◀── Error { "alignment rejected"} │  VERIFY (failure)
```

### align_hash Computation

```rust
// SHA256("1337:v0.5.1:" + agent_name) as lowercase hex
let input = format!("1337:v0.5.1:{}", agent_name);
let hash = Sha256::digest(input.as_bytes());
let hex = hex::encode(hash);
```

Examples:
```
ATLAS  → sha256("1337:v0.5.1:ATLAS")  → a3f7...
CIPHER → sha256("1337:v0.5.1:CIPHER") → 9e2b...
```

The hash is **deterministic and public** — it is not a secret, it is proof that the agent knows the protocol.

### Anchor COGONs (5 immutable references)

| # | Name | Dominant axes |
|---|------|--------------|
| 0 | presence | S1=0.95, D1=0.90, G3=0.90 |
| 1 | absence | S1=0.05, D1=0.05, G3=0.15 |
| 2 | change | S3=0.95, D2=0.90, D7=0.80 |
| 3 | agency | S7=0.90, S6=0.90, P7=0.90 |
| 4 | uncertainty | G7=0.45, unc[*]=0.75 |

---

## Wire Protocol (TCP/Unix)

Messages are newline-delimited JSON (`\n` as terminator).

### WireMsg Variants

```json
// Client → Server: registration
{ "type": "register", "name": "ATLAS", "role": "Strategic planner" }

// Server → Client: confirmation with anchors
{ "type": "registered", "agent_id": "<uuid>", "anchors": [<5 COGONs>] }

// Client → Server: alignment
{ "type": "align", "hash": "<sha256_hex>" }

// Server → Client: ready
{ "type": "ready" }

// Both directions: normal message
{
  "type": "msg",
  "id": "<uuid>",
  "sender": "<uuid>",
  "receiver": "all",           // or { "agent": "<uuid>" }
  "intent": "ASSERT",
  "payload": { <Cogon> },
  "nl": "optional natural language text"
}

// Server → Client: error
{ "type": "error", "message": "alignment rejected" }
```

---

## Binary Codec (96 bytes)

Compact serialization format for efficient storage and transmission.

```
Byte   Size  Field
────   ────  ──────────────────────────────────────────
0-1    2     magic = 0x1337
2      1     version = 0x02
3      1     flags (reserved, = 0x00)
4-35   32    sem[32] quantized: f32 × 255 → u8
36-67  32    unc[32] quantized: f32 × 255 → u8
68-83  16    UUID (raw bytes, big-endian)
84-91  8     stamp: i64 little-endian (nanoseconds)
92-95  4     CRC32 of bytes 0-91
──────────────────────────────────────────────────────
96     TOTAL
```

**Compression:** A typical COGON JSON is 450-600 bytes. The binary codec uses exactly 96 bytes — 4-5× compression.

**Precision:** f32→u8 quantization has a maximum error of `0.5/255 ≈ 0.002` per axis — negligible for semantic use.
