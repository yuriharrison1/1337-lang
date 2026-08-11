"""
Quickstart — leet-py SDK.

One-line setup. No API key needed with the mock provider.

Run:
    cd leet-py
    python examples/quickstart.py
"""

import asyncio
import leet


async def main() -> None:
    # ── 1. Connect (mock = no API key, no network) ─────────────────────
    client = leet.connect("mock")
    print("Connected with mock provider.")
    print()

    # ── 2. Chat ──────────────────────────────────────────────────────────
    resp = await client.chat("explain MPC predictive control")
    print("Response:", resp.text)
    print(f"Tokens saved (vs raw text): {client.stats.tokens_saved}")
    print()

    # ── 3. Semantic memory ───────────────────────────────────────────────
    await client.remember("MPC stands for Model Predictive Control")
    await client.remember("predictive control minimizes a cost function over a finite horizon")
    results = await client.recall("control system", k=3)
    print(f"Recalled {len(results)} similar memories from PersonalStore:")
    for r in results:
        text = (r["text"] or "")[:60]
        print(f"  dist={r['dist']:.4f}  text={text!r}")
    print()

    # ── 4. Direct COGON access ───────────────────────────────────────────
    cogon = await client.encode("system in critical failure — maximum urgency")
    print(f"COGON id   : {cogon.id}")
    print(f"  axis[22] C1_URGENCY    : {cogon.sem[22]:.3f}")
    print(f"  axis[26] C5_ANOMALY    : {cogon.sem[26]:.3f}")
    print(f"  axis[23] C2_IMPACT     : {cogon.sem[23]:.3f}")
    print()

    # Decode back to text description
    description = await client.decode(cogon)
    print("Decoded:", description)
    print()

    # ── 5. Session stats ─────────────────────────────────────────────────
    s = client.stats
    print(f"Session stats:")
    print(f"  requests     : {s.requests}")
    print(f"  tokens saved : {s.tokens_saved}")
    print(f"  cogons stored: {s.cogons_stored}")


if __name__ == "__main__":
    asyncio.run(main())
