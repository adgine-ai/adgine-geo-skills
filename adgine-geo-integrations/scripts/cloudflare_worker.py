#!/usr/bin/env python3
"""Cloudflare Worker management for AI-traffic tracking.

The Worker injects a script that logs AI crawler + referral visits. After
deployment, the Worker page queries (overview/pages) return AI traffic
analytics.

Subcommands:
  config                                  — get the Worker JS code + keys
  deploy [--zone-id <id>]                 — deploy / re-deploy the Worker
  undeploy [--keep-script] --yes          — remove route (and optionally script) DESTRUCTIVE
  deploy-status                           — check whether Worker is deployed
  overview   [--start <>] [--end <>]      — Worker traffic overview (AI grouping)
  pages      [--page 1] [--limit 20]      — Worker page-level AI traffic rankings

Usage:
  python3 scripts/cloudflare_worker.py config
  python3 scripts/cloudflare_worker.py deploy
  python3 scripts/cloudflare_worker.py deploy-status
  python3 scripts/cloudflare_worker.py overview
  python3 scripts/cloudflare_worker.py undeploy --yes
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post, api_delete,
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


def cmd_config(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/cloudflare/worker-config", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Worker configuration")
    print()
    for k in ("worker_name", "receiver_url", "secret_key"):
        if k in data:
            print(f"  {k}: {data.get(k)}")
    script = data.get("script") or data.get("worker_script")
    if script:
        print()
        print("Worker script:")
        print("```javascript")
        print(script)
        print("```")


def cmd_deploy(args, key, base, pid):
    body = {}
    if args.zone_id:
        body["zone_id"] = args.zone_id
    result = api_post(f"/api/projects/{pid}/integrations/cloudflare/worker/deploy", key, base,
                      body=body or None)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Worker deployment started.")
    for k in ("worker_name", "routes", "status"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


def cmd_undeploy(args, key, base, pid):
    if not args.yes:
        print(f"About to remove Worker route for project {pid}.")
        print("Re-run with --yes to confirm.")
        sys.exit(1)
    qs = "?keep_script=true" if args.keep_script else ""
    api_delete(f"/api/projects/{pid}/integrations/cloudflare/worker/deploy" + qs, key, base)
    print("Worker route removed.")


def cmd_deploy_status(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/cloudflare/worker/deploy-status", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    deployed = data.get("deployed")
    print("Worker deployment status")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────┐")
    print("│ Field              │ Value                        │")
    print("├────────────────────┼──────────────────────────────┤")
    print(f"│ {pad('deployed', 18)} │ {pad(('Yes' if deployed else 'No'), 28)} │")
    for k in ("worker_name", "routes", "script_name"):
        if k in data:
            val = data.get(k)
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            print(f"│ {pad(k, 18)} │ {pad(truncate(val, 28), 28)} │")
    print("└────────────────────┴──────────────────────────────┘")
    print("```")


def cmd_overview(args, key, base, pid):
    params = {}
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end
    result = api_get(f"/api/projects/{pid}/integrations/cloudflare/worker/overview", key, base,
                     params=params or None)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Worker AI Traffic Overview")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Metric             │        Value │")
    print("├────────────────────┼──────────────┤")
    for k, label in [
        ("ai_crawler_requests", "AI crawler reqs"),
        ("ai_referral_visits", "AI referral hits"),
        ("total_events", "Total events"),
    ]:
        if k in data:
            print(f"│ {pad(label, 18)} │ {_fmt_num(data.get(k)):>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")


def cmd_pages(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/cloudflare/worker/pages", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("pages", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No Worker page-level AI traffic yet.")
        return
    print(f"Worker page-level AI traffic ({len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────────────────┬──────────┐")
    print("│ Page                                       │ AI Hits  │")
    print("├────────────────────────────────────────────┼──────────┤")
    for p in items:
        path = truncate(p.get("page_path") or p.get("path") or p.get("url"), 42)
        hits = _fmt_num(p.get("ai_hits") or p.get("hits") or p.get("count"))
        print(f"│ {pad(path, 42)} │ {hits:>8} │")
    print("└────────────────────────────────────────────┴──────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="Cloudflare Worker management for AI tracking")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config")

    p_d = sub.add_parser("deploy")
    p_d.add_argument("--zone-id", help="Override zone ID (optional)")

    p_u = sub.add_parser("undeploy", help="Remove route (DESTRUCTIVE)")
    p_u.add_argument("--keep-script", action="store_true", help="Keep the script, remove only the route")
    p_u.add_argument("--yes", action="store_true", help="Confirm")

    sub.add_parser("deploy-status")

    p_o = sub.add_parser("overview")
    p_o.add_argument("--start", help="Start date YYYY-MM-DD")
    p_o.add_argument("--end", help="End date YYYY-MM-DD")

    p_p = sub.add_parser("pages")
    p_p.add_argument("--page", type=int, default=1)
    p_p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "config": cmd_config,
        "deploy": cmd_deploy,
        "undeploy": cmd_undeploy,
        "deploy-status": cmd_deploy_status,
        "overview": cmd_overview,
        "pages": cmd_pages,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
