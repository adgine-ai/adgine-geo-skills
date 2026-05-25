#!/usr/bin/env python3
"""Google Analytics 4: data sync + traffic/AI-referral/page/source queries.

Subcommands:
  sync                                            — pull latest GA4 data into the local DB (POST)
  overview      [--start <YYYY-MM-DD>] [--end <>] — sessions/users/pageviews + channel split
  ai-referrals  [--start <>] [--end <>]           — AI-platform referral detail + trends
  pages         [--page 1] [--limit 20]           — top pages by views
  sources       [--start <>] [--end <>]           — traffic by channel group

Usage:
  python3 scripts/ga4_data.py sync
  python3 scripts/ga4_data.py overview --start 2025-11-01 --end 2025-11-30
  python3 scripts/ga4_data.py ai-referrals --json
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
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


def cmd_sync(args, key, base, pid):
    result = api_post(f"/api/projects/{pid}/integrations/ga4/sync", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("GA4 sync started.")
    for k in ("status", "rows_synced", "started_at"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


def _date_params(args):
    p = {}
    if args.start:
        p["start_date"] = args.start
    if args.end:
        p["end_date"] = args.end
    return p or None


def cmd_overview(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/overview", key, base,
                     params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("GA4 Overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Metric             │        Value │")
    print("├────────────────────┼──────────────┤")
    for k, label in [
        ("sessions", "Sessions"),
        ("active_users", "Active users"),
        ("pageviews", "Pageviews"),
        ("ai_referral_sessions", "AI ref sessions"),
    ]:
        if k in data:
            print(f"│ {label:<18} │ {_fmt_num(data.get(k)):>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def cmd_ai_referrals(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/ai-referrals", key, base,
                     params=_date_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    plats = data.get("platforms") or data.get("by_platform") or []
    print("GA4 AI Referrals")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ Platform           │     Sessions │        Users │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for p in plats[:10]:
        name = truncate(p.get("name") or p.get("platform"), 18)
        sess = _fmt_num(p.get("sessions"))
        users = _fmt_num(p.get("users") or p.get("active_users"))
        print(f"│ {name:<18} │ {sess:>12} │ {users:>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_pages(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/pages", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("pages", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No page data. Run `sync` first or check the date range.")
        return
    print(f"GA4 Top Pages ({len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────────────────┬──────────┬──────────┐")
    print("│ Page                                       │    Views │ Sessions │")
    print("├────────────────────────────────────────────┼──────────┼──────────┤")
    for p in items:
        path = truncate(p.get("page_path") or p.get("path") or p.get("url"), 42)
        views = _fmt_num(p.get("views") or p.get("page_views"))
        sess = _fmt_num(p.get("sessions"))
        print(f"│ {path:<42} │ {views:>8} │ {sess:>8} │")
    print("└────────────────────────────────────────────┴──────────┴──────────┘")
    print("```")


def cmd_sources(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/sources", key, base,
                     params=_date_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("sources") or (data or {}).get("channels", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No source data available.")
        return
    print("GA4 Traffic Sources")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Channel            │     Sessions │")
    print("├────────────────────┼──────────────┤")
    for s in items[:10]:
        name = truncate(s.get("name") or s.get("channel") or s.get("source"), 18)
        sess = _fmt_num(s.get("sessions"))
        print(f"│ {name:<18} │ {sess:>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="GA4 sync + data queries")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="Pull latest GA4 data into local DB")

    for name in ("overview", "ai-referrals", "sources"):
        p = sub.add_parser(name)
        p.add_argument("--start", help="Start date YYYY-MM-DD")
        p.add_argument("--end", help="End date YYYY-MM-DD")

    p_pages = sub.add_parser("pages")
    p_pages.add_argument("--page", type=int, default=1)
    p_pages.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "sync": cmd_sync,
        "overview": cmd_overview,
        "ai-referrals": cmd_ai_referrals,
        "pages": cmd_pages,
        "sources": cmd_sources,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
