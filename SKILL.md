---
name: context-window-tracker
description: >
homepage: https://github.com/99rebels/context-window-tracker

  Track and report OpenClaw context window usage with a detailed breakdown of what's
  consuming tokens. Use when: user asks about context usage, token usage,
  "how much context am I using", "how full is my context window", "tokens remaining",
  "am I close to the limit", thinking/reasoning token costs, what's eating context
  (system prompt vs conversation vs overhead), or how many turns are left.
  NOT for: estimating tokens for arbitrary text, managing context (compact/prune),
  or cross-session cost aggregation.
---

# Context Window Tracker

**See exactly how full your context window is — without opening the TUI.**

Built for OpenClaw sessions running through Slack, WhatsApp, or Discord where you can't see the terminal. One script, no dependencies, reads real provider token counts directly from your session files.

## Why

OpenClaw normalizes token counts from every provider (Anthropic, OpenAI, z.ai) into a standard format. This script reads that normalized data — no estimation, no guesswork.

Other frameworks (Claude Code, Cursor, Codex) have their own built-in context displays. This exists because OpenClaw sessions often live in chat apps where those displays aren't visible.

## When to Use

- "Check my context"
- "How much context am I using?"
- "How full is my context window?"
- "Tokens remaining"
- "Am I close to the limit?"
- "What's eating my context?"

## Quick Start

```bash
python3 scripts/context_report.py
```

Auto-detects the most recently updated session. Options:

```
--session <key>    Target a specific session
--agent <name>     Target a specific agent (default: main)
```

## Output Example

```
CONTEXT: 47.2K / 202.8K (23%)
Model: zai/glm-5-turbo

BREAKDOWN
  System Prompt: ~15.6K tokens (8%)
    Workspace files: 23.0K chars
    Framework overhead: 22.5K chars
  Conversation: ~31.7K tokens (16%)
  Remaining: 155.6K (77%)

TURNS: ~171 remaining (48-1690 range)
  Recent growth: 92-3.2K tokens/turn (avg 908)

SESSION STATS
  Input: 778 | Output: 37
  Cache hit rate: 98%
  Assistant turns: 31
  Cost this turn: $0.0122 | Session total: $0.3547
  Thinking: varies by model (z.ai)
```

Format output for the current channel — adapt formatting to match what the platform supports.

## What's Exact vs Estimated

```
✅ Exact (from provider):
  • Per-response input, output, cacheRead, cacheWrite, totalTokens
  • Context window limit (from model config)
  • Cost (exact token counts × configured pricing)

⚠ Estimated:
  • Per-file system prompt breakdown (chars ÷ 4)
  • Turns remaining (extrapolated from recent growth)
  • Thinking tokens when provider bundles them
```

## Notes

- Script uses the **transcript** (`.jsonl`) as source of truth, not the session store. The store can lag by several thousand tokens.
- System prompt tokens derived from: `first_response.input - first_user_message_tokens`
- See [references/data-sources.md](references/data-sources.md) for file paths and normalization details.
- See [references/thinking-tokens.md](references/thinking-tokens.md) for how each provider handles reasoning tokens.
