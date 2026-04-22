# Data Sources

Where the script reads from and what each source provides.

## Transcript (source of truth)

```
~/.openclaw/agents/<agent>/sessions/<sessionId>.jsonl
```

Each line is JSON. The script reads `type: "message"` entries with `role: "assistant"` and extracts `message.usage`.

Usage fields (already normalized by OpenClaw from any provider):
- `input` — non-cached input tokens
- `output` — generated tokens
- `cacheRead` — tokens served from cache
- `cacheWrite` — new tokens written to cache
- `totalTokens` — the authoritative total (always accurate regardless of provider)
- `cost` — per-response cost breakdown

**Prefer transcript over session store** — the store can lag behind by several thousand tokens.

## Session Store

```
~/.openclaw/agents/<agent>/sessions/sessions.json
```

Provides data the transcript doesn't have:
- `contextTokens` — the context window limit for this model
- `systemPromptReport` — per-file character breakdown of the system prompt
- `estimatedCostUsd` — cumulative session cost
- `sessionFile` — path to the transcript file

### System Prompt Report Structure

```json
{
  "systemPrompt": {
    "chars": 45511,
    "projectContextChars": 23013,
    "nonProjectContextChars": 22498
  },
  "injectedWorkspaceFiles": [
    {"name": "AGENTS.md", "rawChars": 7809, "injectedChars": 7809, "truncated": false}
  ]
}
```

- `projectContextChars` — workspace files (AGENTS.md, SOUL.md, MEMORY.md, etc.)
- `nonProjectContextChars` — framework overhead (tool schemas, skill list, runtime config)

## How OpenClaw Normalizes Provider Responses

```
Provider raw response → OpenClaw normalized format
────────────────────────────────────────────────────
prompt_tokens          → input (minus cached_tokens)
completion_tokens      → output (plus reasoning_tokens if present)
prompt_tokens_details  → cacheRead
.completion_tokens_details
  .reasoning_tokens    → added to output
```

`totalTokens = input + output + cacheRead` is always the real total regardless of provider.
