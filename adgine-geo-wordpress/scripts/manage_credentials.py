#!/usr/bin/env python3
"""Manage WordPress credentials and category list for a GEO project.

Subcommands:
  status                                          — show connection state
  connect --site-url <url> --username <u> --password <pw>
                                                  — save/update WP credentials (PUT)
  disconnect --yes                                — remove stored credentials
  categories                                      — list WP categories (live call to WP)

Examples:
  python3 scripts/manage_credentials.py status
  python3 scripts/manage_credentials.py connect \\
      --site-url https://example.com --username admin \\
      --password "abcd efgh ijkl mnop"
  python3 scripts/manage_credentials.py categories
  python3 scripts/manage_credentials.py disconnect --yes
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_put, api_delete,
    extract_data, print_json, truncate,
)

def cmd_status(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/wordpress/credentials", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("WordPress connection")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────┐")
    print("│ Field              │ Value                        │")
    print("├────────────────────┼──────────────────────────────┤")
    status_raw = (data.get("status") or "").lower()
    if status_raw in ("connected", "active"):
        status = "Connected"
    elif data.get("site_url") or data.get("username"):
        status = "Connected"
    else:
        status = "Disconnected"
    print(f"│ {'Status':<18} │ {status:<28} │")
    for k in ("site_url", "username", "connected_at", "last_verified_at"):
        if k in data:
            print(f"│ {k:<18} │ {truncate(data.get(k), 28):<28} │")
    print("└────────────────────┴──────────────────────────────┘")
    print("```")


def cmd_connect(args, key, base, pid):
    body = {
        "site_url": args.site_url,
        "username": args.username,
        "application_password": args.password,
    }
    result = api_put(f"/api/projects/{pid}/integrations/wordpress/credentials", key, base, body=body)
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Connected: {args.site_url} (user: {args.username})")


def cmd_disconnect(args, key, base, pid):
    if not args.yes:
        print(f"About to disconnect WordPress from project {pid}.")
        print("Re-run with --yes to confirm.")
        sys.exit(1)
    api_delete(f"/api/projects/{pid}/integrations/wordpress/credentials", key, base)
    print("WordPress disconnected.")


def cmd_categories(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/wordpress/categories", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("categories", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No categories found (or WordPress not connected).")
        return
    print(f"WordPress categories ({len(items)})")
    print()
    print("```")
    print("┌──────────┬────────────────────────────────────┬──────────┐")
    print("│ ID       │ Name                               │ Count    │")
    print("├──────────┼────────────────────────────────────┼──────────┤")
    for c in items:
        cid = truncate(c.get("id"), 8)
        name = truncate(c.get("name"), 34)
        count = c.get("count")
        count_str = str(count) if count is not None else "--"
        print(f"│ {str(cid):<8} │ {name:<34} │ {count_str:<8} │")
    print("└──────────┴────────────────────────────────────┴──────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="Manage WordPress integration")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show connection state")

    p_c = sub.add_parser("connect", help="Save/update WP credentials")
    p_c.add_argument("--site-url", required=True, help="WordPress site URL")
    p_c.add_argument("--username", required=True, help="WordPress username")
    p_c.add_argument("--password", required=True, help="Application password")

    p_d = sub.add_parser("disconnect", help="Remove stored credentials (DESTRUCTIVE)")
    p_d.add_argument("--yes", action="store_true", help="Confirm")

    sub.add_parser("categories", help="List WordPress categories (live call)")

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "status": cmd_status,
        "connect": cmd_connect,
        "disconnect": cmd_disconnect,
        "categories": cmd_categories,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
