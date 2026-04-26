//! Production content of ~/.claude/skills/leet/SKILL.md, embedded as a const.
//! `setup::install_global_skill` writes this into place.

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

# Leet — persistent project memory via 1337 (v0.5.1)

This skill is how Claude Code remembers what happened in prior sessions of
the current project without bloating the context with pasted transcripts.
State lives in `.leet/store.bin` inside the project root — auto-created,
git-ignored by default, binary append-only.

## The two tools that matter

**`leet_recall`** — fetches the most semantically relevant past entries
for the current intent. Call at the **start of any session that isn't a
truly fresh topic**. Accepts an optional `query` string; omit it to get
recent-first ordering. Default `limit=5` is usually right — bump to 10–15
for "give me everything" moments.

**`leet_remember`** — compresses a piece of text into one COGON and
appends it to the store. Call when the conversation reaches a natural
closing point: a decision made, a topic concluded, a direction committed
to, an assumption nailed down. Pass a compact `text` (1–3 sentences
describing *what* was decided or discussed, not how).

The other tools (`leet_encode`, `leet_decode`, `leet_dist`) are advanced
and rarely needed during normal conversation. Use them only if the user
explicitly asks about semantic distances or vector inspection.

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
query — the chronological fallback is fine.

**Do NOT** call `leet_recall` repeatedly in the same session. One call at
the top covers most cases. If the conversation pivots to a new topic
mid-session, a second call with a narrower `query` is appropriate, but
three or more starts feeling noisy.

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
something is worth remembering, it probably isn't. The user's wellbeing
is better served by a store full of signal than one cluttered with noise.

## Worked examples

### Session resume
User: "Continuing where we left off on the gastos app"
  → `leet_recall({query: "gastos app", limit: 8})`
  → Read the results silently; use them to inform the response.
  → Respond to the user as if you remembered. Do not announce the call.

### Decision made
User: "I think we should use FastAPI instead of Flask."
Claude: "Agreed — FastAPI gives you async and auto-generated OpenAPI
        out of the box. Let me scaffold a basic app."
  → Before (or right after) the scaffold, call:
    `leet_remember({text: "Chose FastAPI over Flask for the gastos API.
                          Reasons: async support, auto OpenAPI."})`

### Structural fact
User: "This project targets Python 3.10 minimum because of TypedDict."
  → `leet_remember({text: "Target Python 3.10+ minimum (required for
                          TypedDict usage)."})`

### Ambiguous, skip
User: "Cool, let's keep going."
  → Do not call `leet_remember`. Just continue.

## Interaction with the user

Calls to `leet_recall` and `leet_remember` happen silently. **Do not
announce them** ("let me check our history..." / "I'll remember that..."
is exactly the wrong register). The user asked for persistent memory;
delivering it without theatrics is the whole point.

If the user explicitly asks "what do you remember about X?", you may
surface `leet_recall` output more openly, e.g. summarizing the returned
entries in natural language.

If the store is empty on first call, `leet_recall` returns "No prior
context in this project. Starting fresh." — acknowledge by moving on,
not by apologizing for the absence.

## Edge cases

- **Multiple projects in one Claude Code session**: Each invocation of
  the MCP server is scoped to `LEET_PROJECT_ROOT`, which Claude Code
  sets to the current workspace folder. Switching projects means a
  different store — no cross-contamination.

- **User denies a tool call**: Respect it. Do not retry. Continue without
  persistence for that turn.

- **Low-confidence recall result** (distance > 1.2 to every entry): the
  store has content but nothing matches. Mention it lightly: "Nothing
  from prior sessions seems directly relevant — continuing fresh on this."

- **Server unavailable** (tool call errors): fall back gracefully. The
  conversation still works without memory; just do not keep retrying.

## A note on the underlying protocol

The 1337 canonical space has 32 axes split across 4 functional blocks
(Semantics, Dynamics, Gravity, Precision). The `leet_dist` tool returns
cosine distance weighted by P6_CONFIDENCE — which means low-confidence
entries contribute less to matching. This is intentional: a half-formed
thought should not crowd out a firm decision when recalling.

If the user wants more detail about what's inside a specific recalled
COGON, use `leet_decode` to show them the dominant semantic axes. But
most of the time they do not care — they just want their context back.
"#;

#[cfg(test)]
mod tests {
    use super::SKILL_MD;

    #[test]
    fn starts_with_frontmatter() {
        assert!(SKILL_MD.starts_with("---\n"));
    }

    #[test]
    fn frontmatter_has_required_fields() {
        let end = SKILL_MD[4..].find("\n---\n").expect("closing frontmatter");
        let front = &SKILL_MD[..end + 4];
        assert!(front.contains("name: leet"));
        assert!(front.contains("description:"));
    }

    #[test]
    fn mentions_all_four_blocks() {
        assert!(SKILL_MD.contains("Semantics"));
        assert!(SKILL_MD.contains("Dynamics"));
        assert!(SKILL_MD.contains("Gravity"));
        assert!(SKILL_MD.contains("Precision"));
    }

    #[test]
    fn mentions_the_two_main_tools() {
        assert!(SKILL_MD.contains("leet_recall"));
        assert!(SKILL_MD.contains("leet_remember"));
    }

    #[test]
    fn instructs_silent_operation() {
        assert!(SKILL_MD.to_lowercase().contains("silently")
             || SKILL_MD.to_lowercase().contains("do not announce"));
    }

    #[test]
    fn covers_empty_store_case() {
        assert!(SKILL_MD.contains("Starting fresh") || SKILL_MD.contains("starting fresh"));
    }
}
