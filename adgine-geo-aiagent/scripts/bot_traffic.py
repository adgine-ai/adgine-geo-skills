#!/usr/bin/env python3
"""AI bot/crawler traffic tracking.

Subcommands:
  overview   [--start <>] [--end <>]    — 5 KPI cards + dual-period daily trend
                                          (citation / training / index / agent / total)
  platforms                              — ranking: which AI platforms crawl most
                                          (OpenAI / Anthropic / Google / Perplexity ...)
  by-platform                            — bot list grouped by AI platform
  types                                  — distribution by bot purpose
                                          (index / training / assistant / agent)
  useragents                             — detailed access by specific User-Agent
                                          (GPTBot, ClaudeBot, GoogleBot, PerplexityBot...)
  pages-by-bot [--limit 5]               — per-bot top pages

Common opts: --start --end --platform

Usage:
  python3 scripts/bot_traffic.py overview
  python3 scripts/bot_traffic.py platforms
  python3 scripts/bot_traffic.py useragents --start 2025-11-01
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get,
    extract_data, print_json, truncate,
)


def _fmt_num(n):
    if n is None:
        return "--"
    try:
        f = float(n)
        if f == int(f):
            return f"{int(f):,}"
        return f"{f:,.1f}"
    except (TypeError, ValueError):
        return str(n)


def _fmt_change(c):
    if c is None:
        return "--"
    try:
        f = float(c)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f:.1f}%"
    except (TypeError, ValueError):
        return str(c)


def _date_params(args):
    p = {}
    if args.start:
        p["start_date"] = args.start
    if args.end:
        p["end_date"] = args.end
    if getattr(args, "platform", None):
        p["platform"] = args.platform
    return p or None


def cmd_overview(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/bot-traffic-overview",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    kpis_raw = data.get("kpis") or data
    # API returns kpis as a list of {key, label, current, prev, delta}
    # Build a lookup dict keyed by the "key" field
    if isinstance(kpis_raw, list):
        kpis = {item["key"]: item for item in kpis_raw if "key" in item}
    else:
        kpis = kpis_raw if isinstance(kpis_raw, dict) else {}
    print("AI Bot Traffic Overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ KPI                │      Current │       Change │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for k, label in [
        ("ai_citation", "AI Citation"),
        ("ai_training", "AI Training"),
        ("ai_search",   "AI Index"),
        ("ai_agent",    "AI Agent"),
        ("all_bots",    "All bot visits"),
    ]:
        v = kpis.get(k)
        if isinstance(v, dict):
            cur = v.get("current")
            delta = v.get("delta")
            prev = v.get("prev")
            if delta is not None and prev:
                pct = (delta / prev * 100)
                ch_str = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
            else:
                ch_str = _fmt_change(None)
        else:
            cur, ch_str = v, "--"
        print(f"│ {label:<18} │ {_fmt_num(cur):>12} │ {ch_str:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_platforms(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/platforms",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("platforms", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No AI platform crawler data.")
        return
    print(f"AI Platforms ranked by bot visits ({len(items)})")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ Platform           │     Requests │        Share │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for p in items:
        name = truncate(p.get("name") or p.get("platform"), 18)
        req = _fmt_num(p.get("requests") or p.get("count") or p.get("total"))
        pct = p.get("share") or p.get("percentage") or p.get("pct")
        pct_str = (f"{float(pct):.1f}%" if pct is not None else "--")
        print(f"│ {name:<18} │ {req:>12} │ {pct_str:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_by_platform(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/bot-platforms",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("platforms", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No bot-platform data.")
        return
    print(f"Bots grouped by AI platform ({len(items)})")
    print()
    for p in items[:10]:
        name = p.get("name") or p.get("platform")
        total = _fmt_num(p.get("total") or p.get("requests"))
        print(f"• {name} — total {total}")
        bots = p.get("bots") or []
        for b in bots[:5]:
            bn = truncate(b.get("name") or b.get("bot"), 28)
            br = _fmt_num(b.get("requests") or b.get("count"))
            print(f"    - {bn:<28} {br:>10}")
        print()


def cmd_types(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/bot-types",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("types", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No bot-type data.")
        return
    print("AI Bot Type Distribution")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ Type               │     Requests │        Share │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for t in items:
        name = truncate(t.get("name") or t.get("type"), 18)
        req = _fmt_num(t.get("requests") or t.get("count"))
        pct = t.get("share") or t.get("percentage")
        pct_str = (f"{float(pct):.1f}%" if pct is not None else "--")
        print(f"│ {name:<18} │ {req:>12} │ {pct_str:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_useragents(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/bot-useragents",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("useragents") or (data or {}).get("bots", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No user-agent data.")
        return
    print(f"AI Bot User-Agents ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────┬────────────────────┬──────────────┐")
    print("│ Bot name                     │ Platform           │     Requests │")
    print("├──────────────────────────────┼────────────────────┼──────────────┤")
    for u in items:
        name = truncate(u.get("bot_name") or u.get("name") or u.get("user_agent"), 28)
        plat = truncate(u.get("platform") or "--", 18)
        req = _fmt_num(u.get("requests") or u.get("count"))
        print(f"│ {name:<28} │ {plat:<18} │ {req:>12} │")
    print("└──────────────────────────────┴────────────────────┴──────────────┘")
    print("```")


def cmd_pages_by_bot(args, key, base, pid):
    params = _date_params(args) or {}
    params["limit"] = args.limit
    result = api_get(f"/api/projects/{pid}/ai-agent/pages-by-bot",
                     key, base, params=params)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("bots", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No pages-by-bot data.")
        return
    print(f"Top pages per AI bot ({len(items)} bots)")
    print()
    for b in items[:10]:
        bn = b.get("bot_name") or b.get("name")
        print(f"• {bn}")
        for p in (b.get("pages") or [])[:args.limit]:
            path = truncate(p.get("path") or p.get("url"), 50)
            hits = _fmt_num(p.get("requests") or p.get("count"))
            print(f"    {path:<50} {hits:>8}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AI bot/crawler traffic tracking")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("overview", "platforms", "by-platform", "types", "useragents"):
        p = sub.add_parser(name)
        p.add_argument("--start", help="Start date YYYY-MM-DD")
        p.add_argument("--end", help="End date YYYY-MM-DD")
        p.add_argument("--platform", help="Filter by platform code")

    p_pbb = sub.add_parser("pages-by-bot")
    p_pbb.add_argument("--start")
    p_pbb.add_argument("--end")
    p_pbb.add_argument("--platform")
    p_pbb.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "overview": cmd_overview,
        "platforms": cmd_platforms,
        "by-platform": cmd_by_platform,
        "types": cmd_types,
        "useragents": cmd_useragents,
        "pages-by-bot": cmd_pages_by_bot,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
