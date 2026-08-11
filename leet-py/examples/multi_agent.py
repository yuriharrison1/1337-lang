"""
Multi-agent example — leet-py SDK.

Two specialized agents (Researcher + Analyst) work together
on the same 1337 semantic bus. All communication goes through
compressed COGON vectors — no raw text between agents.

Run:
    cd leet-py
    python examples/multi_agent.py
"""

import asyncio
import leet
from leet import agent, AgentContext
from leet_vm.types import Cogon


# ── Agent definitions ─────────────────────────────────────────────────────────

@agent(name="pesquisador")
async def pesquisador(cogon: Cogon, ctx: AgentContext) -> Cogon:
    """Collects and structures information on the received COGON topic."""
    # In production this would call an LLM with semantic context
    summary = (
        "Research complete. Data collected on the topic: high-reliability "
        "empirical evidence, precise temporality, identified causality."
    )
    return await ctx.assert_(summary)


@agent(name="analista")
async def analista(cogon: Cogon, ctx: AgentContext) -> Cogon:
    """Analyses patterns and extracts actionable conclusions."""
    analysis = (
        "Analysis complete. Pattern identified: positive correlation between variables, "
        "anomaly detected on axis C5 — immediate action recommended."
    )
    return await ctx.assert_(analysis)


@agent(name="sintetizador")
async def sintetizador(cogon: Cogon, ctx: AgentContext) -> Cogon:
    """Synthesises outputs from the other agents into a final report."""
    # Access conversation history from context
    n_hist = len(ctx.history)
    synthesis = (
        f"Final synthesis: {n_hist} interactions processed. "
        "Conclusion: high impact, moderate urgency, action recommended."
    )
    return await ctx.assert_(synthesis)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=== 1337 Multi-Agent Network ===")
    print()

    client = leet.connect("mock")

    # Register all agents into a network
    net = client.agents(pesquisador, analista, sintetizador)

    # Phase 1: Research
    print("Phase 1 — Research")
    r1 = await net.run("impact of generative AI on higher education", to="pesquisador")
    print(f"  Researcher: {r1.text[:80]}...")
    print()

    # Phase 2: Analysis
    print("Phase 2 — Analysis")
    r2 = await net.run("analyze the findings on AI in education", to="analista")
    print(f"  Analyst: {r2.text[:80]}...")
    print()

    # Phase 3: Synthesis via direct COGON injection
    print("Phase 3 — Synthesis (COGON injection)")
    research_cogon = await client.encode("AI education research")
    r3 = await net.inject(research_cogon, to="sintetizador")
    print(f"  Synthesizer: {r3.text[:80]}...")
    print()

    # Stats
    s = client.stats
    print("=== Session Stats ===")
    print(f"  requests     : {s.requests}")
    print(f"  tokens saved : {s.tokens_saved}")
    print(f"  cogons stored: {s.cogons_stored}")
    print()
    print("Note: In production replace 'mock' with 'anthropic', 'openai', or 'deepseek'.")
    print("      leet.connect('anthropic')  # reads ANTHROPIC_API_KEY from env")


if __name__ == "__main__":
    asyncio.run(main())
