# /leet-stats — Token savings report with 1337

$ARGUMENTS

Run the steps below in order and present the final report.

## Step 1 — Store pyramid

Use the Bash tool to run:

```bash
leet consolidate inspect --json 2>/dev/null || ~/.cargo/bin/leet consolidate inspect --json 2>/dev/null
```

If the project doesn't have a store yet, the command will report that. In that case, show the message:
"Empty store — no context has been saved yet. Use `leet_remember` to get started."
And stop.

## Step 2 — Current recall state

Call `leet_recall` with `limit=50` to get all live records and the count footer.

## Step 3 — Savings calculation

Use the conservative estimates below (based on analysis of real Claude Code sessions):

| Category | Estimate |
|---|---|
| Original context tokens per remembered decision | ~400 tokens |
| Tokens for a recall excerpt (256 chars) | ~70 tokens |
| Tokens for a consolidated excerpt (L1+) | ~90 tokens (contains multiple) |
| Fixed overhead of `leet_recall` (header + footer) | ~60 tokens |

**Calculation:**

From the Step 1 JSON:
- `total_records` = sum of all records in the pyramid
- `consolidated` = sum of the `consolidated` fields across all levels
- `live` = sum of the `live` fields across all levels
- `bytes_store` = `store.bytes`

**Without leet** (cost per session if pasting the raw history):
```
tokens_without_leet = total_records × 400
```

**With leet** (real cost of a typical `leet_recall` with limit=5):
```
tokens_with_leet = min(live, 5) × 75 + 60
```

**Savings per session**:
```
savings = tokens_without_leet - tokens_with_leet
pct = (savings / tokens_without_leet) × 100
```

**Cumulative compression** (all history already absorbed):
```
tokens_absorbed = consolidated × 400
```

## Step 4 — Presentation

Show the report in this format (adapt to Portuguese if the user speaks Portuguese):

```
╔══════════════════════════════════════════╗
║       leet-stats · token savings         ║
╚══════════════════════════════════════════╝

Store: <path>  (<bytes_store> bytes)

Memory pyramid:
  L0 (raw):  X live records  (Y consolidated)
  L1:        X live records  (Y consolidated)
  L2+:       X live records  (Y consolidated)
  Total:     N records  (V live · C absorbed)

─────────────────────────────────────────────

Estimated cost per new session:

  Without leet  →  ~Z tokens   (pasting the raw history)
  With leet     →  ~W tokens   (leet_recall with 5 entries)

  Savings: ~(Z-W) tokens / session  (~pct%)

─────────────────────────────────────────────

Context already absorbed by the pyramid:
  C compressed decisions  =  ~tokens_absorbed tokens
  that never need to enter context again.

Last recall: <last_recall_at date, or "never">
```

Make it clear these are conservative estimates. Don't expose internal COGON numbers or level details to the average user — only if they ask for more detail.
