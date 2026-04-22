---
name: context-window-tracker
description: >
  Track and report OpenClaw context window usage with a detailed breakdown of what's
  consuming tokens. Use when: user asks about context usage, token usage,
  "how much context am I using", "how full is my context window", "tokens remaining",
  "am I close to the limit", thinking/reasoning token costs, what's eating context
  (session setup vs conversation vs overhead), or how many turns are left.
  NOT for: estimating tokens for arbitrary text, managing context (compact/prune),
  or cross-session cost aggregation.
homepage: https://github.com/99rebels/context-window-tracker
---

# Context Window Tracker

Shows how much context window is left — without opening the terminal.

## When to Use

- "Check my context"
- "How much context am I using?"
- "How full is my context window?"
- "Tokens remaining"
- "Am I close to the limit?"
- Any question about context usage

## Quick Start

```bash
python3 scripts/context_report.py
```

Auto-detects the most recently updated session. Options:

```
--session <key>    Target a specific session
--agent <name>     Target a specific agent (default: main)
```

## Auto-Check Every 10 Messages

Maintain a message counter in `.msg-counter.json` (same directory as SKILL.md). On every user message:

1. Increment the counter
2. If the count is a multiple of 10, run the script and append the output to your reply
3. If not, reply normally

The counter survives compaction. If the file is missing, create it starting at 0:

```json
{"count": 0}
```

## Output Format

```
🟢 [███░░░░░░░░░░░░░░░░░] 85% remaining — 29.8K / 202.8K tokens
~736 turns left
Cache hit rate: 99%
```

The bar uses `█` (filled) and `░` (empty) across 20 segments (each = 5%).

### Health Indicator

- 🟢 Under 60% used — plenty of room
- 🟡 60–80% used — getting tight
- 🔴 Over 80% used — consider wrapping up

## What's Exact vs Estimated

```
✅ Exact (from provider):
  • Total tokens used (from transcript)
  • Context window limit (from session store)
  • Cache hit rate

⚠ Estimated:
  • Turns remaining (extrapolated from recent token growth per turn)
```

## Notes

- Script reads the transcript (`.jsonl`) as source of truth — the session store can lag behind by thousands of tokens
- If the session store doesn't provide a context window limit (some thread sessions), it shows tokens used without a percentage
- See [references/data-sources.md](references/data-sources.md) for file paths
- See [references/thinking-tokens.md](references/thinking-tokens.md) for how reasoning tokens affect counts
