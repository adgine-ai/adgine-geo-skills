#!/usr/bin/env python3
"""Site-wide AI traffic analytics — overall KPI, page rankings, Sankey, raw logs.

Subcommands:
  overview-kpi                     — site overall KPIs (5 cards + trends):
                                     citation / index / training / agent / referral
  pages       [--page 1] [--limit 20]   — top pages by AI references
  pages-detail [--limit 20]        — 5-metric table per page (citation/index/training/
                                     agent/referral) with previous-period delta
  pages-export [--format csv|json] — download pages-detail as CSV/JSON
  platform-flow                    — Sankey: AI platform → page path
  logs [--limit 50]                — raw AI event logs (bot + human, paginated)

Common opts: --start --end [--platform]

Usage:
  python3 scripts/page_analytics.py overview-kpi
  python3 scripts/page_analytics.py pages-detail --start 2025-11-01
  python3 scripts/page_analytics.py pages-export --format csv > pages.csv
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


def cmd_overview_kpi(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/overview-kpi",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    # This endpoint returns a flat dict:
    # {ai_citations, ai_index, ai_training, ai_agent, human_referrals, ai_human_ratio, ...}
    # Each value is a {current, prev, delta, delta_pct, ...} dict.

    def _get_kpi(d, k):
        v = d.get(k)
        if isinstance(v, dict):
            cur = v.get("current")
            delta_pct = v.get("delta_pct")
            if delta_pct is not None:
                ch_str = f"+{delta_pct:.1f}%" if delta_pct >= 0 else f"{delta_pct:.1f}%"
            else:
                ch_str = "--"
        else:
            cur, ch_str = v, "--"
        return cur, ch_str

    print("Site AI Overview — 5 KPI cards")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ KPI                │      Current │       Change │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for k, label in [
        ("ai_citations",   "AI Citation"),
        ("ai_index",       "AI Index"),
        ("ai_training",    "AI Training"),
        ("ai_agent",       "AI Agent"),
        ("human_referrals","AI Referral"),
        ("ai_human_ratio", "AI Referral %"),
    ]:
        cur, ch_str = _get_kpi(data, k)
        print(f"│ {label:<18} │ {_fmt_num(cur):>12} │ {ch_str:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_pages(args, key, base, pid):
    params = _date_params(args) or {}
    params["page"] = args.page
    params["limit"] = args.limit
    result = api_get(f"/api/projects/{pid}/ai-agent/pages",
                     key, base, params=params)
    data = extract_data(result)
    # API returns {items, total, ...} not a bare list or {"pages": [...]}
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items") or data.get("pages", [])
    else:
        items = []
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    if args.json:
        print_json(items)
        return
    if not items:
        print("No page data.")
        return
    print(f"Top AI-referenced pages ({total} total, showing {len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────────────────┬──────────┬────────┬──────────┐")
    print("│ Page                                       │ Bot Hits │  Human │ Total AI │")
    print("├────────────────────────────────────────────┼──────────┼────────┼──────────┤")
    for p in items:
        path = truncate(p.get("path") or p.get("url"), 42)
        bot = _fmt_num(p.get("bot_requests") or p.get("ai_hits") or p.get("count"))
        human = _fmt_num(p.get("human_referral_requests"))
        total_ai = _fmt_num(p.get("total_ai_requests") or p.get("references"))
        print(f"│ {path:<42} │ {bot:>8} │ {human:>6} │ {total_ai:>8} │")
    print("└────────────────────────────────────────────┴──────────┴────────┴──────────┘")
    print("```")


def cmd_pages_detail(args, key, base, pid):
    params = _date_params(args) or {}
    params["page"] = args.page
    params["limit"] = args.limit
    result = api_get(f"/api/projects/{pid}/ai-agent/pages-detail",
                     key, base, params=params)
    data = extract_data(result)
    # API returns {items, total, ...} not a bare list or {"pages": [...]}
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items") or data.get("pages", [])
    else:
        items = []
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    if args.json:
        print_json(items)
        return
    if not items:
        print("No page detail data.")
        return
    print(f"Pages — 5-metric detail ({total} total, showing {len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────┬──────┬──────┬──────┬──────┬──────┐")
    print("│ Page                           │ Cite │ Indx │ Trn  │ Agnt │ Ref  │")
    print("├────────────────────────────────┼──────┼──────┼──────┼──────┼──────┤")
    for p in items:
        path = truncate(p.get("path") or p.get("url"), 30)
        c = _fmt_num(p.get("ai_citation"))
        i = _fmt_num(p.get("ai_search") or p.get("ai_index"))
        t = _fmt_num(p.get("ai_training"))
        a = _fmt_num(p.get("ai_agent"))
        r = _fmt_num(p.get("ai_referral") or p.get("ai_referral_visits"))
        print(f"│ {path:<30} │ {c:>4} │ {i:>4} │ {t:>4} │ {a:>4} │ {r:>4} │")
    print("└────────────────────────────────┴──────┴──────┴──────┴──────┴──────┘")
    print("```")


def cmd_pages_export(args, key, base, pid):
    params = _date_params(args) or {}
    params["format"] = args.format
    result = api_get(f"/api/projects/{pid}/ai-agent/pages-detail/export",
                     key, base, params=params)
    # Export returns raw CSV or JSON — pass through.
    if isinstance(result, (dict, list)):
        if args.format == "json":
            print_json(result)
        else:
            print(result)
    else:
        print(result)


def cmd_platform_flow(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/pages-platform-flow",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    print(f"Sankey AI platform → page: {len(nodes)} nodes, {len(links)} links")
    print()
    sorted_links = sorted(links, key=lambda l: l.get("value", 0), reverse=True)[:15]
    for ln in sorted_links:
        s = ln.get("source")
        t = ln.get("target")
        v = _fmt_num(ln.get("value"))
        print(f"  {s} → {t}  ({v})")


def cmd_logs(args, key, base, pid):
    params = _date_params(args) or {}
    params["page"] = args.page
    params["limit"] = args.limit
    if args.traffic_type:
        params["traffic_type"] = args.traffic_type
    result = api_get(f"/api/projects/{pid}/ai-agent/logs",
                     key, base, params=params)
    data = extract_data(result)
    # API returns {items, total, page, limit, pages}
    if isinstance(data, list):
        items = data
        total = len(data)
    elif isinstance(data, dict):
        items = data.get("items") or data.get("logs") or data.get("events", [])
        total = data.get("total", len(items))
    else:
        items = []
        total = 0
    if args.json:
        print_json(items)
        return
    if not items:
        print("No log events.")
        return
    print(f"Raw AI event logs (total {total}, showing {len(items)})")
    print()
    print("```")
    print("┌────────────────────┬────────────────────┬────────────┬──────────────────────────┐")
    print("│ Time (UTC)         │ Type               │ Platform   │ Path                     │")
    print("├────────────────────┼────────────────────┼────────────┼──────────────────────────┤")
    for e in items:
        t = truncate(
            (e.get("occurred_at") or e.get("timestamp") or e.get("created_at") or "")[:19].replace("T", " "),
            18)
        ttype = truncate(
            e.get("traffic_type_label") or e.get("bot_name") or e.get("traffic_type") or "(human)",
            18)
        plat = truncate(e.get("platform_name") or e.get("platform") or "--", 10)
        path = truncate(e.get("path") or e.get("url"), 24)
        print(f"│ {t:<18} │ {ttype:<18} │ {plat:<10} │ {path:<24} │")
    print("└────────────────────┴────────────────────┴────────────┴──────────────────────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="Site-wide AI traffic analytics")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("overview-kpi", "platform-flow"):
        p = sub.add_parser(name)
        p.add_argument("--start")
        p.add_argument("--end")
        p.add_argument("--platform")

    for name in ("pages", "pages-detail"):
        p = sub.add_parser(name)
        p.add_argument("--start")
        p.add_argument("--end")
        p.add_argument("--platform")
        p.add_argument("--page", type=int, default=1)
        p.add_argument("--limit", type=int, default=20)

    p_ex = sub.add_parser("pages-export")
    p_ex.add_argument("--start")
    p_ex.add_argument("--end")
    p_ex.add_argument("--platform")
    p_ex.add_argument("--format", choices=["csv", "json"], default="csv")

    p_lg = sub.add_parser("logs")
    p_lg.add_argument("--start")
    p_lg.add_argument("--end")
    p_lg.add_argument("--platform")
    p_lg.add_argument("--page", type=int, default=1)
    p_lg.add_argument("--limit", type=int, default=50)
    p_lg.add_argument("--traffic-type", choices=["bot", "human"])

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "overview-kpi": cmd_overview_kpi,
        "pages": cmd_pages,
        "pages-detail": cmd_pages_detail,
        "pages-export": cmd_pages_export,
        "platform-flow": cmd_platform_flow,
        "logs": cmd_logs,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
