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

## Two Modes

### Compact (default)
One line. Glanceable. Use for auto-checks or quick status.

```bash
python3 scripts/context_report.py
```

### Detailed
Full breakdown with per-file system prompt, conversation split, trends, and thinking status. Use when the user asks for specifics.

```bash
python3 scripts/context_report.py --detailed
```

Both modes auto-detect the most recently updated session. Options:

```
--session <key>    Target a specific session
--agent <name>     Target a specific agent (default: main)
--detailed         Full breakdown instead of compact one-liner
```

## Auto-Check Every 10 Messages

Maintain a message counter in `.msg-counter.json` (same directory as SKILL.md). On every user message:

1. Increment the counter
2. If the count is a multiple of 10, run the compact script and append the output to your reply
3. If not, reply normally

The counter survives compaction. If the file is missing, create it starting at 0:

```json
{"count": 0}
```

## Output Format

### Compact
```
🟢 [███░░░░░░░░░░░░░░░░░] 85% remaining — 29.8K / 202.8K tokens
~736 turns left | Cache: 99% | Cost: $0.02
```

### Detailed
```
🟢 Context Usage: 29.8K / 202.8K (15%)

Token Breakdown
• System Prompt: ~10.2K tokens (5%)
  ├─ AGENTS.md: ~2.0K
  ├─ SOUL.md: ~416
  ├─ TOOLS.md: ~717
  ├─ IDENTITY.md: ~65
  ├─ USER.md: ~83
  ├─ HEARTBEAT.md: ~48
  ├─ BOOTSTRAP.md: ~18
  ├─ MEMORY.md: ~2.3K
  └─ Framework overhead: ~5.3K (tool schemas, skill list, runtime)
• Conversation: ~19.6K tokens (10%)
• Total Used: 29.8K (15%)
• Remaining: 173.0K (85%)

Trends
• Avg growth per turn: ~1.2K tokens
• Estimated turns remaining: ~144

Session Stats
• Total input: 25K | Total output: 1.8K | Cache hit rate: 99%
• Estimated cost: $0.02
• Thinking: active (3/12 responses)
```

The bar uses `█` (filled) and `░` (empty) across 20 segments (each = 5%).

### Health Indicator

- 🟢 Under 60% used — plenty of room
- 🟡 60–80% used — getting tight
- 🔴 Over 80% used — consider wrapping up

## Guidance Rules

The report presents facts. Only add actionable guidance when:
1. **Context is above 80%** — mention that `/compact` can free space, or `/new` starts fresh
2. **A specific file dominates** — note its size but don't prescribe action (e.g. "MEMORY.md accounts for 2.3K tokens" not "you should trim MEMORY.md")
3. **Cache hit rate is below 50%** — note it, don't diagnose why

Never suggest deleting workspace files, editing system config, or changing skill setup. The user owns those decisions.

## What's Exact vs Estimated

```
✅ Exact (from provider):
  • Total tokens used (from transcript)
  • Context window limit (from session store)
  • Cache hit rate
  • Cost (derived from exact token counts)

⚠ Estimated:
  • Per-file system prompt breakdown (chars ÷ 4)
  • Turns remaining (extrapolated from recent growth rate)
  • Thinking token count (bundled by provider, not separately reported)
```

## Notes

- Script reads the transcript (`.jsonl`) as source of truth — the session store can lag behind by thousands of tokens
- If the session store doesn't provide a context window limit (some thread sessions), it shows tokens used without a percentage
- See [references/data-sources.md](references/data-sources.md) for file paths
- See [references/thinking-tokens.md](references/thinking-tokens.md) for how reasoning tokens affect counts
