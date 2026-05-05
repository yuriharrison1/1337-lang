//! The real content of ~/.claude/skills/leet/SKILL.md, embedded as a const.
//! `setup.rs::install_global_skill` writes this into place.
//!
//! v11d: updated for delta-aware tiered recall.

pub const SKILL_MD: &str = r#"---
name: leet
description: |
  Retrieve and preserve persistent project memory across Claude Code sessions
  using the 1337 semantic protocol. Triggers on: resuming work on a project,
  referencing "what we decided", "last time", "earlier today", or any phrasing
  that implies continuity with prior sessions. Also triggers proactively at
  session start and when the user mentions a decision, conclusion, or topic
  shift worth preserving. Calls the MCP server `leet` (tools: leet_recall,
  leet_remember, leet_encode, leet_decode, leet_dist).
---

# Leet — persistent project memory via 1337 (v0.5.1, tiered recall)

This skill is how Claude Code remembers what happened in prior sessions of
the current project without bloating the context with pasted transcripts.
State lives in `.leet/store.bin` inside the project root — auto-created,
git-ignored by default, binary append-only.

The store auto-consolidates: every 7 raw entries collapse into one summary
entry at level 1; every 7 level-1 entries collapse into one level 2; etc.
Recall returns a small, bounded mix of summary + recent detail no matter
how long the project runs.

## The two tools that matter

**`leet_recall`** — fetches the most semantically relevant past entries
for the current intent. Call at the **start of any session that isn't a
truly fresh topic**. Accepts an optional `query` string; omit it for the
default tier-aware response (foundation summary + mid-tier + recent raw).
Default `limit=5` is right for most cases — bump to 10–15 only when the
user explicitly asks for a comprehensive recap.

**`leet_remember`** — compresses a piece of text into one COGON and
appends it to the store. Call when the conversation reaches a natural
closing point: a decision made, a topic concluded, a direction committed
to, an assumption nailed down. Pass a compact `text` (1–3 sentences
describing *what* was decided or discussed, not how).

The other tools (`leet_encode`, `leet_decode`, `leet_dist`) are advanced
and rarely needed during normal conversation. Use them only if the user
explicitly asks about semantic distances or vector inspection.

## Reading recall output (tiered format)

Each recall entry comes tagged with its tier. Read them as a hierarchy:

  - **`L2` / `L3` / higher** (foundation): a single summary of much earlier
    project history. Excerpt usually starts with `[L2×7]` or similar.
    Treat as "the gist of what came before". Do **not** quote it verbatim
    to the user — translate to natural prose.

  - **`L1`** (mid-tier): summaries of mid-range activity. Each represents
    7 raw entries that have already been compacted. Excerpt starts with
    `[L1×7]`. Same rule: paraphrase, don't quote the bracket prefix.

  - **`raw`**: individual entries from recent sessions. These are concrete,
    direct, and quotable in user-facing output.

When the user asks "what did we decide about X", weight raw entries more
than summaries — they have specific facts. When the user asks "where are
we overall", weight foundation/mid-tier — they have the structural picture.

The number after the timestamp ("L2", "L1", "raw") and the footer
("1 foundation + 2 mid-tier + 4 raw") are diagnostic information for you.
**Do not surface them to the user** unless the user is debugging the
memory system itself.

## When to call `leet_recall`

Call it **proactively at the start of a session** whenever one of the
following is true:

- The user says something that assumes shared history ("where did we
  leave off", "continue from yesterday", "the thing we discussed", "my
  project", "the bug we were chasing")
- The user opens with a short message that references "this" or "it"
  without an antecedent in the current session
- The project directory contains `.leet/store.bin` AND the conversation
  has been going for fewer than 3 turns

Pass a `query` derived from the user's opening message when there's
enough signal. If the user just says "hey" or "continue", call without a
query — the tiered fallback (foundation + mid + raw) is the right shape.

**Do NOT** call `leet_recall` repeatedly in the same session. One call at
the top covers most cases. If the conversation pivots to a sharply
different topic mid-session, a second call with a narrower `query` is
appropriate. Three or more starts feeling noisy.

## When to call `leet_remember`

Call it when the conversation crosses one of these thresholds:

- A decision is reached ("let's go with Postgres", "we'll skip
  authentication for the MVP")
- A structural fact is established that isn't in the code itself
  ("this project targets Python 3.10+", "we're billing weekly, not
  monthly")
- A constraint or invariant is discovered ("the API rate limit is 60/min
  per user")
- A topic concludes, especially if the user says something like "moving
  on", "next", "done", or starts a new subject
- The user explicitly signals they want to end or pause ("let's stop
  here", "bye", "see you tomorrow")

Pass a `text` that captures the *gist* — not a transcript. Aim for 1–3
sentences. The 256-byte excerpt cap ensures brevity naturally.

**Do NOT** call it for every trivial exchange. If you're unsure whether
something is worth remembering, it probably isn't. The store consolidates
automatically every 7 entries — flooding it with noise dilutes the
foundation summaries that future recalls depend on.

## Worked examples

### Session resume with project history
User: "Continuing where we left off on the gastos app"

  → `leet_recall({query: "gastos app", limit: 8})`
  → Suppose the response includes:
       [0] L2 — "[L2×7] Architecture: FastAPI+SQLite, dashboard via Streamlit..."
       [1] L1 — "[L1×7] Auth: JWT-based, refresh tokens, ..."
       [2] raw — "Login endpoint working, JWT validation pending"
       [3] raw — "Choosing pytest fixtures for auth testing"
       [4] raw — "Hit a bug in token refresh expiry"
  → Read silently. Synthesize:
       "Welcome back. The gastos app has FastAPI+SQLite with a Streamlit
        dashboard. We're mid-implementation on JWT auth — login endpoint
        works, validation is pending, and you ran into a token-refresh
        bug last session. Want to continue with the bug or move on?"
  → Don't quote the L2/L1 brackets to the user.

### Decision made
User: "I think we should use FastAPI instead of Flask."
Claude: "Agreed — FastAPI gives you async and auto-generated OpenAPI
        out of the box. Let me scaffold a basic app."
  → `leet_remember({text: "Chose FastAPI over Flask for the gastos API.
                          Reasons: async support, auto OpenAPI."})`

### Comprehensive project status request
User: "Give me a summary of everything we've done on this project"

  → `leet_recall({limit: 25})`
     (high limit so we get foundation + many mid + many raw)
  → Synthesize a structured summary, leaning on the foundation/mid-tier
    entries for high-level structure and raw entries for recent details.

### Ambiguous, skip
User: "Cool, let's keep going."
  → Don't call `leet_remember`. Just continue.

## Interaction with the user

Calls to `leet_recall` and `leet_remember` happen silently. **Do not
announce them** ("let me check our history..." / "I'll remember that..."
is exactly the wrong register). The user asked for persistent memory;
delivering it without theatrics is the whole point.

If the user explicitly asks "what do you remember about X?" or "what's
in your memory?", you may surface tier information openly — explaining
"I have one consolidated summary covering older sessions plus 4 recent
specific entries" is fine in that case.

If the store is empty on first call, `leet_recall` returns "No prior
context in this project. Starting fresh." — acknowledge by moving on,
not by apologizing for the absence.

## Edge cases

- **Multiple projects in one Claude Code session**: Each invocation of
  the MCP server is scoped to `LEET_PROJECT_ROOT`, which Claude Code
  sets to the current workspace folder. Switching projects means a
  different store — no cross-contamination.

- **User denies a tool call**: Respect it. Don't retry. Continue without
  persistence for that turn.

- **Foundation but no raw**: All recent activity has been consolidated.
  This means the project has had little new activity since the last
  consolidation. Read the foundation as authoritative.

- **Raw but no foundation**: Project is young (< 7 entries) or all
  consolidated entries were just absorbed into a higher tier. Treat as
  fresh-ish — no prior summary exists yet, but the raw entries you do
  have are the full memory.

- **Recall returns "No prior context" but the user expected something**:
  Either this is a different project than they think, or `.leet/store.bin`
  was deleted/never populated. Mention it lightly: "I don't see prior
  notes for this project — was it stored elsewhere?" Don't assume bad
  faith; many users have multiple project trees.

- **Server unavailable** (tool call errors): fall back gracefully. The
  conversation still works without memory; just don't keep retrying.

## A note on the underlying protocol

The 1337 canonical space has 32 axes split across 4 functional blocks
(Semantics, Dynamics, Gravity, Precision). The `leet_dist` tool returns
cosine distance weighted by P6_CONFIDENCE — which means low-confidence
entries contribute less to matching. This is intentional: a half-formed
thought shouldn't crowd out a firm decision when recalling.

When records are consolidated via BLEND, P6_CONFIDENCE takes the
**minimum** across the merged entries. This makes consolidated summaries
self-deprecating: if any of the seven inputs was uncertain, the summary
inherits that uncertainty. Trust foundation excerpts at the level
suggested by their natural confidence — phrases like "tentatively"
or "decided to try" came through for a reason.

If the user wants more detail about what's inside a specific recalled
COGON, use `leet_decode` to show them the dominant semantic axes. But
most of the time they don't care — they just want their context back.
"#;

#[cfg(test)]
mod tests {
    use super::SKILL_MD;

    #[test]
    fn starts_with_frontmatter() {
        assert!(SKILL_MD.starts_with("---\n"));
    }

    #[test]
    fn covers_tier_interpretation() {
        assert!(SKILL_MD.contains("L1"));
        assert!(SKILL_MD.contains("L2"));
        assert!(SKILL_MD.contains("foundation"));
        assert!(SKILL_MD.contains("mid-tier"));
        assert!(SKILL_MD.contains("raw"));
    }

    #[test]
    fn warns_against_quoting_brackets() {
        let lower = SKILL_MD.to_lowercase();
        assert!(lower.contains("don't quote") || lower.contains("do not quote"));
        assert!(SKILL_MD.contains("[L1") || SKILL_MD.contains("[L2"));
    }

    #[test]
    fn explains_p6_min_consolidation() {
        let lower = SKILL_MD.to_lowercase();
        assert!(lower.contains("p6_confidence"));
        assert!(lower.contains("minimum") || lower.contains("min"));
    }

    #[test]
    fn covers_edge_cases() {
        assert!(SKILL_MD.contains("Foundation but no raw"));
        assert!(SKILL_MD.contains("Raw but no foundation"));
    }

    #[test]
    fn still_warns_against_announcing_tool_calls() {
        let lower = SKILL_MD.to_lowercase();
        assert!(lower.contains("do not announce") || lower.contains("silently"));
    }

    #[test]
    fn mentions_two_main_tools() {
        assert!(SKILL_MD.contains("leet_recall"));
        assert!(SKILL_MD.contains("leet_remember"));
    }

    #[test]
    fn mentions_all_four_blocks() {
        assert!(SKILL_MD.contains("Semantics"));
        assert!(SKILL_MD.contains("Dynamics"));
        assert!(SKILL_MD.contains("Gravity"));
        assert!(SKILL_MD.contains("Precision"));
    }

    #[test]
    fn frontmatter_has_required_fields() {
        assert!(SKILL_MD.contains("name: leet"));
        assert!(SKILL_MD.contains("description:"));
    }

    #[test]
    fn covers_empty_store_case() {
        assert!(SKILL_MD.contains("No prior context") || SKILL_MD.contains("Starting fresh"));
    }

    #[test]
    fn instructs_silent_operation() {
        assert!(SKILL_MD.contains("silently") || SKILL_MD.contains("Do not announce"));
    }
}
