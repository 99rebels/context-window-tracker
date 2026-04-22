#!/usr/bin/env python3
"""Context Window Reporter for OpenClaw.

Reads session transcript and session store to produce a compact context usage report.
Designed to be run by the LLM agent — output is human-readable text, not JSON.

Usage:
    python3 context_report.py [--session <session_key>] [--agent <agent_name>]

If no session/agent specified, auto-detects the current session from sessions.json
by picking the most recently updated one.
"""

import argparse
import json
import os
import sys
from pathlib import Path

OPENCLAW_DIR = Path.home() / ".openclaw"
AGENTS_DIR = OPENCLAW_DIR / "agents"


def find_current_session(agent: str | None = None) -> tuple[str, dict, str]:
    """Find the most recently updated session.

    Returns (session_key, session_data, agent_name).
    """
    if agent is None:
        # Pick the agent directory that exists (usually "main")
        agent = "main"

    store_path = AGENTS_DIR / agent / "sessions" / "sessions.json"
    if not store_path.exists():
        # Try to find any agent with a sessions.json
        for d in AGENTS_DIR.iterdir():
            if d.is_dir():
                p = d / "sessions" / "sessions.json"
                if p.exists():
                    agent = d.name
                    store_path = p
                    break

    if not store_path.exists():
        print("ERROR: No sessions.json found", file=sys.stderr)
        sys.exit(1)

    with open(store_path) as f:
        sessions = json.load(f)

    if not sessions:
        print("ERROR: No sessions found", file=sys.stderr)
        sys.exit(1)

    # Find most recently updated session
    best_key = max(sessions, key=lambda k: sessions[k].get("updatedAt", ""))
    return best_key, sessions[best_key], agent


def read_transcript_latest(transcript_path: str) -> list[dict]:
    """Read all assistant usage entries from transcript, return them."""
    entries = []
    if not os.path.exists(transcript_path):
        return entries

    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "message":
                continue
            msg = entry.get("message", {})
            if msg.get("role") != "assistant":
                continue
            usage = msg.get("usage", {})
            if usage and usage.get("totalTokens"):
                entries.append(usage)

    return entries


def get_first_user_message_chars(transcript_path: str) -> int:
    """Get the character length of the first user message."""
    if not os.path.exists(transcript_path):
        return 0

    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "message":
                continue
            msg = entry.get("message", {})
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return len(json.dumps(content))
    return 0


def format_number(n: int) -> str:
    """Format large numbers with K suffix."""
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def build_report(session_key: str, session: dict, agent: str) -> str:
    """Build the context usage report."""
    lines = []

    # Session info
    context_window = session.get("contextTokens", 0)
    model = session.get("model", "unknown")
    provider = session.get("modelProvider", "unknown")

    # Transcript data (source of truth for current totals)
    transcript_path = session.get("sessionFile", "")
    usage_entries = read_transcript_latest(transcript_path)

    if not usage_entries:
        lines.append("No usage data found in transcript.")
        return "\n".join(lines)

    latest = usage_entries[-1]
    current_total = latest.get("totalTokens", 0)
    current_input = latest.get("input", 0)
    current_output = latest.get("output", 0)
    current_cache_read = latest.get("cacheRead", 0)
    current_cache_write = latest.get("cacheWrite", 0)

    # Latest cost
    cost_data = latest.get("cost", {})
    latest_cost = cost_data.get("total", 0)

    # Session store cumulative cost (more accurate total)
    store_cost = session.get("estimatedCostUsd", 0)

    # Percentage
    if context_window > 0:
        pct = current_total / context_window * 100
        remaining = context_window - current_total
    else:
        pct = 0
        remaining = 0

    # Header
    lines.append(f"CONTEXT: {format_number(current_total)} / {format_number(context_window)} ({pct:.0f}%)")
    lines.append(f"Model: {provider}/{model}")
    lines.append("")

    # System prompt breakdown
    spr = session.get("systemPromptReport", {})
    sp = spr.get("systemPrompt", {})
    sp_chars = sp.get("chars", 0)
    project_chars = sp.get("projectContextChars", 0)
    framework_chars = sp.get("nonProjectContextChars", 0)

    # Estimate system prompt tokens from first response
    first_user_chars = get_first_user_message_chars(transcript_path)
    first_user_tokens = first_user_chars // 4
    first_response = usage_entries[0] if usage_entries else None

    if first_response:
        first_input = first_response.get("input", 0) + first_response.get("cacheRead", 0)
        sys_prompt_tokens = max(0, first_input - first_user_tokens)
    else:
        sys_prompt_tokens = sp_chars // 4  # fallback

    conversation_tokens = max(0, current_total - sys_prompt_tokens)

    if context_window > 0:
        sp_pct = sys_prompt_tokens / context_window * 100
        conv_pct = conversation_tokens / context_window * 100
    else:
        sp_pct = 0
        conv_pct = 0

    lines.append("BREAKDOWN")
    lines.append(f"  System Prompt: ~{format_number(sys_prompt_tokens)} tokens ({sp_pct:.0f}%)")
    if project_chars > 0 or framework_chars > 0:
        lines.append(f"    Workspace files: {format_number(project_chars)} chars")
        lines.append(f"    Framework overhead: {format_number(framework_chars)} chars")
    lines.append(f"  Conversation: ~{format_number(conversation_tokens)} tokens ({conv_pct:.0f}%)")
    lines.append(f"  Remaining: {format_number(remaining)} ({100 - pct:.0f}%)")
    lines.append("")

    # Turn prediction
    if len(usage_entries) >= 2:
        # Growth from last N entries
        window = min(10, len(usage_entries))
        recent = usage_entries[-window:]
        growths = []
        for i in range(1, len(recent)):
            growth = recent[i]["totalTokens"] - recent[i - 1]["totalTokens"]
            if growth > 0:
                growths.append(growth)
        if growths:
            min_g = min(growths)
            max_g = max(growths)
            avg_g = sum(growths) / len(growths)
            if remaining > 0 and avg_g > 0:
                turns_min = int(remaining / max_g)
                turns_max = int(remaining / min_g)
                turns_avg = int(remaining / avg_g)
                if min_g == max_g:
                    lines.append(f"TURNS: ~{turns_avg} remaining ({format_number(int(avg_g))} tokens/turn)")
                else:
                    lines.append(f"TURNS: ~{turns_avg} remaining ({turns_max}-{turns_min} range)")
                    lines.append(f"  Recent growth: {format_number(min_g)}-{format_number(max_g)} tokens/turn (avg {format_number(int(avg_g))})")
                lines.append("")

    # Stats
    total_input = current_input
    total_output = current_output
    total_cache = current_cache_read

    cache_total = current_input + current_cache_read + current_cache_write
    if cache_total > 0:
        cache_hit = current_cache_read / cache_total * 100
    else:
        cache_hit = 0

    lines.append("SESSION STATS")
    lines.append(f"  Input: {format_number(total_input)} | Output: {format_number(total_output)}")
    lines.append(f"  Cache hit rate: {cache_hit:.0f}%")
    lines.append(f"  Assistant turns: {len(usage_entries)}")
    lines.append(f"  Cost this turn: ${latest_cost:.4f} | Session total: ${store_cost:.4f}")

    # Thinking detection — check if any response had unusually high input relative to growth
    # (thinking tokens get bundled into input for most providers)
    # We can't detect this perfectly from usage alone, so note the model/provider behavior
    if provider in ("anthropic",):
        lines.append("  Thinking: bundled into input (Anthropic)")
    elif provider in ("openai",):
        lines.append("  Thinking: separate reasoning_tokens field (OpenAI)")
    elif provider in ("zai",):
        lines.append("  Thinking: varies by model (z.ai)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Context Window Reporter")
    parser.add_argument("--session", "-s", help="Session key (e.g. agent:main:whatsapp:direct:+353...)")
    parser.add_argument("--agent", "-a", help="Agent name (default: auto-detect)")
    args = parser.parse_args()

    # Find session
    if args.session:
        # If session key provided, find it in sessions.json
        agent = args.agent or "main"
        store_path = AGENTS_DIR / agent / "sessions" / "sessions.json"
        if not store_path.exists():
            print(f"ERROR: {store_path} not found", file=sys.stderr)
            sys.exit(1)
        with open(store_path) as f:
            sessions = json.load(f)
        if args.session not in sessions:
            print(f"ERROR: Session '{args.session}' not found", file=sys.stderr)
            sys.exit(1)
        session_key = args.session
        session = sessions[args.session]
    else:
        session_key, session, agent = find_current_session(args.agent)

    print(build_report(session_key, session, agent))


if __name__ == "__main__":
    main()