# PROMPT 10d — Global SKILL.md for `leet` (teach Claude Code when to use the MCP tools)

Write the real content of the global skill at `~/.claude/skills/leet/SKILL.md`. This file is what teaches Claude Code when to call `leet_recall` and `leet_remember` without the user having to instruct it every time.

**PRE-REQUISITES**: 10a + 10b + 10c landed. `leet setup claude-code` installs a stub at `~/.claude/skills/leet/SKILL.md`. This prompt replaces that stub with the production content.

**SCOPE**: one file — `leet-cli/src/cmd/setup_skill_content.rs` (a `pub const SKILL_MD: &str = ...`) that `setup.rs` embeds. Plus one integration test.

**Taskwarrior**: `+prompt10d`.

---

## WHY A SKILL INSTEAD OF A SYSTEM PROMPT

Claude Code's skill system is declarative: each skill has a front-matter `description` that Claude reads to decide if the skill is relevant **before** it loads the full content. This means:

- Skills are loaded on-demand → no token waste on unused skills
- The `description` field is what triggers the skill — it must be precise
- Once loaded, the body teaches Claude *when and how* to act

Alternative (system prompt injection via the MCP server) would force context on every turn. Skill is lighter and more idiomatic.

---

## DESIGN OF THE SKILL

Four things the skill must accomplish:

1. **Trigger correctly** — the front-matter description must mention "recall", "remember", "prior context", "project memory" to match intent phrasings
2. **Instruct on entry** — the first thing Claude should do each session is call `leet_recall`
3. **Instruct on natural pauses** — decisions, topic shifts, structural changes → `leet_remember`
4. **Avoid over-calling** — keep the conversation natural; don't announce what the skill is doing

The skill file itself is rendered verbatim into Claude's context when triggered. So the writing matters. Prose-first, no bullet-point spam. Written in English (skill files are LLM-facing, and Claude Code internally treats them as instructions to itself).

---

## FILE 1 — `leet-cli/src/cmd/setup_skill_content.rs` (new)

```rust
//! The real content of ~/.claude/skills/leet/SKILL.md, embedded as a const.
//! `setup.rs::install_global_skill` writes this into place.

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
  → Respond to the user as if you remembered. Don't announce the call.

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
  → Don't call `leet_remember`. Just continue.

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

- **User denies a tool call**: Respect it. Don't retry. Continue without
  persistence for that turn.

- **Low-confidence recall result** (distance > 1.2 to every entry): the
  store has content but nothing matches. Mention it lightly: "Nothing
  from prior sessions seems directly relevant — continuing fresh on this."

- **Server unavailable** (tool call errors): fall back gracefully. The
  conversation still works without memory; just don't keep retrying.

## A note on the underlying protocol

The 1337 canonical space has 32 axes split across 4 functional blocks
(Semantics, Dynamics, Gravity, Precision). The `leet_dist` tool returns
cosine distance weighted by P6_CONFIDENCE — which means low-confidence
entries contribute less to matching. This is intentional: a half-formed
thought shouldn't crowd out a firm decision when recalling.

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
    fn frontmatter_has_required_fields() {
        let end = SKILL_MD[4..].find("\n---\n").expect("closing frontmatter");
        let front = &SKILL_MD[..end + 4];
        assert!(front.contains("name: leet"));
        assert!(front.contains("description:"));
    }

    #[test]
    fn mentions_all_four_blocks() {
        // The prose should ground the skill in the v0.5.1 architecture.
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
    fn warns_against_announcing_tool_calls() {
        assert!(SKILL_MD.to_lowercase().contains("do not announce")
             || SKILL_MD.to_lowercase().contains("silently"));
    }

    #[test]
    fn covers_empty_store_case() {
        assert!(SKILL_MD.contains("Starting fresh") || SKILL_MD.contains("starting fresh"));
    }
}
```

---

## FILE 2 — `leet-cli/src/cmd/setup.rs` (integrate the real content)

Currently `setup.rs` has `const SKILL_STUB` — replace that constant with a reference to the new module. Two small changes:

**At the top of the file**, add:

```rust
mod setup_skill_content;
```

(Or `pub(super) mod setup_skill_content;` depending on the crate layout.)

**In `install_global_skill`**, swap the content source:

```rust
fn install_global_skill(claude_dir: &Path) -> Result<()> {
    let skill_dir = claude_dir.join("skills").join("leet");
    std::fs::create_dir_all(&skill_dir)?;

    let skill_md = skill_dir.join("SKILL.md");
    let write_now = match std::fs::read_to_string(&skill_md) {
        Ok(existing) => {
            // Upgrade automatically if the existing file is a prior version we wrote.
            // Fingerprint: all our files mention "managed by `leet setup claude-code`"
            // or the front-matter `name: leet`. User-edited files usually don't have both.
            let is_ours = existing.contains("managed by `leet setup claude-code`")
                || (existing.starts_with("---\n") && existing.contains("name: leet")
                    && existing.contains("leet_recall")
                    && existing.contains("leet_remember"));
            is_ours
        }
        Err(_) => true,
    };

    if write_now {
        std::fs::write(&skill_md, setup_skill_content::SKILL_MD)?;
    }

    Ok(())
}
```

**Delete** the old `const SKILL_STUB: &str = ...` (it lived in `setup.rs`).

---

## FILE 3 — add a smoke test for the installed path

Add this to `leet-cli/src/cmd/setup.rs` (`#[cfg(test)] mod tests`):

```rust
#[test]
fn install_global_skill_writes_real_content() {
    let tmp = tempfile::tempdir().unwrap();
    install_global_skill(tmp.path()).unwrap();
    let path = tmp.path().join("skills/leet/SKILL.md");
    assert!(path.exists());
    let content = std::fs::read_to_string(&path).unwrap();
    assert!(content.contains("leet_recall"));
    assert!(content.contains("leet_remember"));
    assert!(content.starts_with("---\n"));
}

#[test]
fn install_global_skill_does_not_overwrite_user_edits() {
    let tmp = tempfile::tempdir().unwrap();
    let skill_dir = tmp.path().join("skills/leet");
    std::fs::create_dir_all(&skill_dir).unwrap();
    let user_content = "---\nname: custom\n---\n\n# My own skill\n";
    std::fs::write(skill_dir.join("SKILL.md"), user_content).unwrap();

    install_global_skill(tmp.path()).unwrap();
    let content = std::fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
    assert_eq!(content, user_content, "user content must be preserved");
}

#[test]
fn install_global_skill_upgrades_our_prior_version() {
    let tmp = tempfile::tempdir().unwrap();
    let skill_dir = tmp.path().join("skills/leet");
    std::fs::create_dir_all(&skill_dir).unwrap();
    // Write something that looks like a prior leet skill.
    std::fs::write(
        skill_dir.join("SKILL.md"),
        "---\nname: leet\n---\n\nOld version\nleet_recall\nleet_remember\n",
    ).unwrap();

    install_global_skill(tmp.path()).unwrap();
    let content = std::fs::read_to_string(skill_dir.join("SKILL.md")).unwrap();
    assert!(content.len() > 500, "should have been upgraded to the real content");
    assert!(content.contains("Do not announce") || content.contains("silently"));
}
```

---

## VERIFICATION

```bash
cargo build --workspace
cargo test -p leet-cli setup
cargo test -p leet-cli skill_content

# End-to-end
cargo run -p leet-cli -- setup claude-code
cat ~/.claude/skills/leet/SKILL.md | head -30
# Expected: front-matter + "Leet — persistent project memory via 1337"

wc -l ~/.claude/skills/leet/SKILL.md
# Expected: >100 lines (substantial skill, not stub)
```

---

## GIT + TASKWARRIOR

```bash
task add project:1337 +prompt10d "Write production SKILL.md: triggering, recall/remember guidance, worked examples"
# work
task project:1337 +prompt10d done

git add leet-cli/src/cmd/setup_skill_content.rs leet-cli/src/cmd/setup.rs
git commit -m "feat(cli): real SKILL.md content for global leet skill

Replaces the setup.rs stub with the production skill that teaches Claude
Code when to call leet_recall (session start, continuity phrasings) and
leet_remember (decisions, structural facts, natural closing points).

Key properties:
- Front-matter description tuned for trigger coverage
  (\"prior context\", \"continuity\", \"last time\", \"project memory\")
- Instructs Claude to call tools silently — no \"let me check...\" noise
- Worked examples for resume, decision-made, structural-fact, and skip cases
- Edge cases covered: empty store, low-confidence results, server down,
  user denies tool call
- Upgrade path: install_global_skill replaces prior leet-owned skill
  automatically but preserves user edits

Part of Claude Code integration, sub-prompt 10d."
git push origin main
```

---

**END OF PROMPT_10d**
