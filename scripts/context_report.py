#!/usr/bin/env python3
"""Context Window Reporter for OpenClaw.

Lightweight context usage check. Shows tokens used, percentage remaining,
estimated turns left, and cache hit rate.

Usage:
    python3 context_report.py [--session <session_key>] [--agent <agent_name>]

If no session/agent specified, auto-detects the most recently updated session.
"""

import argparse
import json
import sys
from pathlib import Path

OPENCLAW_DIR = Path.home() / ".openclaw"
AGENTS_DIR = OPENCLAW_DIR / "agents"


def find_current_session(agent: str | None = None) -> tuple[str, dict, str]:
    """Find the most recently updated session.

    Returns (session_key, session_data, agent_name).
    """
    if agent is None:
        agent = "main"

    store_path = AGENTS_DIR / agent / "sessions" / "sessions.json"
    if not store_path.exists():
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

    best_key = max(sessions, key=lambda k: sessions[k].get("updatedAt", ""))
    return best_key, sessions[best_key], agent


def read_usage_entries(transcript_path: str) -> list[dict]:
    """Read all assistant usage entries from the transcript."""
    entries = []
    if not Path(transcript_path).exists():
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


def fmt(n: int) -> str:
    """Format number with K suffix."""
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def health_indicator(pct_used: float) -> str:
    """Return a colour indicator based on context usage percentage."""
    if pct_used >= 80:
        return "🔴"
    if pct_used >= 60:
        return "🟡"
    return "🟢"


def build_report(session: dict) -> str:
    """Build the context usage report."""
    transcript_path = session.get("sessionFile", "")
    context_window = session.get("contextTokens") or 0
    usage_entries = read_usage_entries(transcript_path)

    if not usage_entries:
        return "No usage data found in transcript."

    latest = usage_entries[-1]
    current_total = latest.get("totalTokens", 0)

    # Lines
    lines = []

    if context_window > 0:
        pct_used = current_total / context_window * 100
        pct_remaining = 100 - pct_used
        remaining = context_window - current_total
        indicator = health_indicator(pct_used)

        lines.append(f"{indicator} **{pct_remaining:.0f}% remaining** — {fmt(current_total)} / {fmt(context_window)} tokens used")

        # Turns estimate
        if len(usage_entries) >= 2:
            window = min(10, len(usage_entries))
            recent = usage_entries[-window:]
            growths = []
            for i in range(1, len(recent)):
                growth = recent[i]["totalTokens"] - recent[i - 1]["totalTokens"]
                if growth > 0:
                    growths.append(growth)
            if growths and remaining > 0:
                avg_g = sum(growths) / len(growths)
                turns = int(remaining / avg_g)
                lines.append(f"~{turns} turns left")
    else:
        lines.append(f"📊 {fmt(current_total)} tokens used (context limit unknown)")

    # Cache hit rate
    cache_read = latest.get("cacheRead", 0)
    cache_write = latest.get("cacheWrite", 0)
    non_cached_input = latest.get("input", 0)
    cache_total = cache_read + cache_write + non_cached_input
    if cache_total > 0:
        hit_rate = cache_read / cache_total * 100
        lines.append(f"Cache hit rate: {hit_rate:.0f}%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Context Window Reporter")
    parser.add_argument("--session", "-s", help="Session key")
    parser.add_argument("--agent", "-a", help="Agent name (default: auto-detect)")
    args = parser.parse_args()

    if args.session:
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
        session = sessions[args.session]
    else:
        _, session, _ = find_current_session(args.agent)

    print(build_report(session))


if __name__ == "__main__":
    main()
