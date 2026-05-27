#!/usr/bin/env python3
"""Cloudflare: token connect, zone discovery, traffic sync & overview.

Subcommands:
  list-zones --token <api_token>   — list zones accessible by a given API token
  connect    --token <api_token>   — connect Cloudflare (saves token, auto-matches zone)
  sync                             — pull latest Cloudflare analytics into local DB
  overview   [--start <>] [--end <>] — Cloudflare traffic overview + daily trend

Worker management (AI-traffic tracking) lives in cloudflare_worker.py.

Usage:
  python3 scripts/cloudflare_connect.py list-zones --token <cf_api_token>
  python3 scripts/cloudflare_connect.py connect --token <cf_api_token>
  python3 scripts/cloudflare_connect.py sync
  python3 scripts/cloudflare_connect.py overview --start 2025-11-01
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
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


def cmd_list_zones(args, key, base, pid):
    result = api_post(f"/api/projects/{pid}/integrations/cloudflare/list-zones", key, base,
                      body={"api_token": args.token})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("zones", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No zones accessible with that token.")
        return
    print(f"Cloudflare zones ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────┬────────────────────────────┐")
    print("│ Zone ID              │ Name                       │")
    print("├──────────────────────┼────────────────────────────┤")
    for z in items:
        zid = truncate(z.get("id") or z.get("zone_id"), 20)
        name = truncate(z.get("name") or z.get("domain"), 26)
        print(f"│ {pad(zid, 20)} │ {pad(name, 26)} │")
    print("└──────────────────────┴────────────────────────────┘")
    print("```")


def cmd_connect(args, key, base, pid):
    result = api_post(f"/api/projects/{pid}/integrations/cloudflare/connect", key, base,
                      body={"api_token": args.token})
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Cloudflare connected.")
    for k in ("zone_id", "zone_name", "account_id"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


def cmd_sync(args, key, base, pid):
    result = api_post(f"/api/projects/{pid}/integrations/cloudflare/sync", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Cloudflare sync started.")
    for k in ("status", "rows_synced", "started_at"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


def cmd_overview(args, key, base, pid):
    params = {}
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end
    result = api_get(f"/api/projects/{pid}/integrations/cloudflare/overview", key, base,
                     params=params or None)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Cloudflare Overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Metric             │        Value │")
    print("├────────────────────┼──────────────┤")
    for k, label in [
        ("total_requests", "Total requests"),
        ("bandwidth", "Bandwidth"),
        ("page_views", "Page views"),
        ("unique_visitors", "Unique visitors"),
        ("threats_blocked", "Threats blocked"),
    ]:
        if k in data:
            print(f"│ {pad(label, 18)} │ {_fmt_num(data.get(k)):>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="Cloudflare connection & traffic queries")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_lz = sub.add_parser("list-zones")
    p_lz.add_argument("--token", required=True, help="Cloudflare API token")

    p_c = sub.add_parser("connect")
    p_c.add_argument("--token", required=True, help="Cloudflare API token")

    sub.add_parser("sync")

    p_o = sub.add_parser("overview")
    p_o.add_argument("--start", help="Start date YYYY-MM-DD")
    p_o.add_argument("--end", help="End date YYYY-MM-DD")

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "list-zones": cmd_list_zones,
        "connect": cmd_connect,
        "sync": cmd_sync,
        "overview": cmd_overview,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
