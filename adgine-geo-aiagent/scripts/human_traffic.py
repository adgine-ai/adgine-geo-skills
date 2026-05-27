#!/usr/bin/env python3
"""Real human visits driven by AI platforms (UTM + referral + GA4).

Subcommands:
  overview                        — 3 KPI cards: UTM AI visits / referral AI
                                    visits / AI share of total + daily trend
  platforms                       — by AI platform (UTM + referral) detail table
  pages                           — by page path: human AI visits per page
  platform-flow                   — Sankey: AI platform → landing page (real humans)
  referral                        — referral-only traffic by AI source

GA4-based (require GA4 connected):
  ga-overview                     — GA4 sessions/revenue from AI sources (trend)
  ga-platforms                    — GA4 sessions/transactions/revenue by AI platform
  ga-landing-pages [--limit 20]   — GA4 top landing pages from AI traffic
  ga-landing-flow                 — GA4 Sankey: AI platform → landing page

Common opts: --start --end --platform

Usage:
  python3 scripts/human_traffic.py overview
  python3 scripts/human_traffic.py ga-platforms
  python3 scripts/human_traffic.py pages --start 2025-11-01
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get,
    extract_data, print_json, truncate,
    pad,
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
    result = api_get(f"/api/projects/{pid}/ai-agent/human-traffic-overview",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    kpis_raw = data.get("kpis") or data
    # API returns kpis as a list of {key, label, current, prev, delta, delta_pct}
    # Build a lookup dict keyed by the "key" field
    if isinstance(kpis_raw, list):
        kpis = {item["key"]: item for item in kpis_raw if "key" in item}
    else:
        kpis = kpis_raw if isinstance(kpis_raw, dict) else {}
    print("AI Human Traffic Overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ KPI                │      Current │       Change │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for k, label in [
        ("utm",      "UTM AI visits"),
        ("referral", "Referral visits"),
        ("ai_ratio", "AI share %"),
    ]:
        v = kpis.get(k)
        if isinstance(v, dict):
            cur = v.get("current")
            delta_pct = v.get("delta_pct")
            if delta_pct is not None:
                ch_str = f"+{delta_pct:.1f}%" if delta_pct >= 0 else f"{delta_pct:.1f}%"
            else:
                ch_str = "--"
        else:
            cur, ch_str = v, "--"
        print(f"│ {pad(label, 18)} │ {_fmt_num(cur):>12} │ {ch_str:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_platforms(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/human-platforms",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("platforms", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No human-platform data.")
        return
    print(f"AI Platforms — real human visits ({len(items)})")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ Platform           │       Visits │       Change │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for p in items:
        name = truncate(p.get("name") or p.get("platform"), 18)
        v = _fmt_num(p.get("visits") or p.get("sessions") or p.get("count"))
        ch = _fmt_change(p.get("change") or p.get("delta"))
        print(f"│ {pad(name, 18)} │ {v:>12} │ {ch:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_pages(args, key, base, pid):
    params = _date_params(args) or {}
    params["page"] = args.page
    params["limit"] = args.limit
    result = api_get(f"/api/projects/{pid}/ai-agent/human-pages",
                     key, base, params=params)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("pages", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No human-pages data.")
        return
    print(f"Human AI visits per page ({len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────────────────┬──────────┐")
    print("│ Page                                       │   Visits │")
    print("├────────────────────────────────────────────┼──────────┤")
    for p in items:
        path = truncate(p.get("path") or p.get("url"), 42)
        v = _fmt_num(p.get("visits") or p.get("count"))
        print(f"│ {pad(path, 42)} │ {v:>8} │")
    print("└────────────────────────────────────────────┴──────────┘")
    print("```")


def cmd_platform_flow(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/human-platform-flow",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    print(f"Sankey (real human): {len(nodes)} nodes, {len(links)} links")
    print()
    print("Top links:")
    sorted_links = sorted(links, key=lambda l: l.get("value", 0), reverse=True)[:10]
    for ln in sorted_links:
        s = ln.get("source")
        t = ln.get("target")
        v = _fmt_num(ln.get("value"))
        print(f"  {s} → {t}  ({v})")


def cmd_referral(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/referral-traffic",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("sources", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No referral data.")
        return
    print("AI Referral Traffic by source")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Source             │     Sessions │")
    print("├────────────────────┼──────────────┤")
    for s in items:
        name = truncate(s.get("name") or s.get("source"), 18)
        v = _fmt_num(s.get("sessions") or s.get("visits"))
        print(f"│ {pad(name, 18)} │ {v:>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def cmd_ga_overview(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/ga-overview",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("GA4 — AI source overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Metric             │        Value │")
    print("├────────────────────┼──────────────┤")
    for k, label in [
        ("sessions", "Sessions"),
        ("users", "Users"),
        ("revenue", "Revenue"),
        ("transactions", "Transactions"),
    ]:
        if k in data:
            print(f"│ {pad(label, 18)} │ {_fmt_num(data.get(k)):>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def cmd_ga_platforms(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/ga-platforms",
                     key, base, params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("platforms", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No GA4 platform data — is GA4 connected?")
        return
    print(f"GA4 by AI Platform ({len(items)})")
    print()
    print("```")
    print("┌────────────────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│ Platform           │ Sessions │   Trans  │  Revenue │   Conv % │")
    print("├────────────────────┼──────────┼──────────┼──────────┼──────────┤")
    for p in items:
        name = truncate(p.get("name") or p.get("platform"), 18)
        s = _fmt_num(p.get("sessions"))
        t = _fmt_num(p.get("transactions"))
        r = _fmt_num(p.get("revenue"))
        c = p.get("conversion_rate")
        c_str = (f"{float(c):.2f}%" if c is not None else "--")
        print(f"│ {pad(name, 18)} │ {s:>8} │ {t:>8} │ {r:>8} │ {c_str:>8} │")
    print("└────────────────────┴──────────┴──────────┴──────────┴──────────┘")
    print("```")


def cmd_ga_landing_pages(args, key, base, pid):
    params = _date_params(args) or {}
    params["limit"] = args.limit
    result = api_get(f"/api/projects/{pid}/ai-agent/ga-landing-pages",
                     key, base, params=params)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("pages", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No GA4 landing page data.")
        return
    print(f"GA4 Top Landing Pages from AI ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────────────┬──────────┬──────────┐")
    print("│ Landing page                         │ Sessions │  Revenue │")
    print("├──────────────────────────────────────┼──────────┼──────────┤")
    for p in items:
        path = truncate(p.get("path") or p.get("url") or p.get("page_path"), 36)
        s = _fmt_num(p.get("sessions"))
        r = _fmt_num(p.get("revenue"))
        print(f"│ {pad(path, 36)} │ {s:>8} │ {r:>8} │")
    print("└──────────────────────────────────────┴──────────┴──────────┘")
    print("```")


def cmd_ga_landing_flow(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/ga-platform-landing-flow",
                     key, base, params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    print(f"GA4 Sankey: {len(nodes)} nodes, {len(links)} links")
    print()
    sorted_links = sorted(links, key=lambda l: l.get("value", 0), reverse=True)[:10]
    for ln in sorted_links:
        s = ln.get("source")
        t = ln.get("target")
        v = _fmt_num(ln.get("value"))
        print(f"  {s} → {t}  ({v})")


def main():
    parser = argparse.ArgumentParser(description="Real human AI-driven traffic tracking")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("overview", "platforms", "platform-flow", "referral",
                 "ga-overview", "ga-platforms", "ga-landing-flow"):
        p = sub.add_parser(name)
        p.add_argument("--start")
        p.add_argument("--end")
        p.add_argument("--platform")

    p_pages = sub.add_parser("pages")
    p_pages.add_argument("--start")
    p_pages.add_argument("--end")
    p_pages.add_argument("--platform")
    p_pages.add_argument("--page", type=int, default=1)
    p_pages.add_argument("--limit", type=int, default=20)

    p_glp = sub.add_parser("ga-landing-pages")
    p_glp.add_argument("--start")
    p_glp.add_argument("--end")
    p_glp.add_argument("--platform")
    p_glp.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "overview": cmd_overview,
        "platforms": cmd_platforms,
        "pages": cmd_pages,
        "platform-flow": cmd_platform_flow,
        "referral": cmd_referral,
        "ga-overview": cmd_ga_overview,
        "ga-platforms": cmd_ga_platforms,
        "ga-landing-pages": cmd_ga_landing_pages,
        "ga-landing-flow": cmd_ga_landing_flow,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
