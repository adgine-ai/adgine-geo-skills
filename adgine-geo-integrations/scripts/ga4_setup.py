#!/usr/bin/env python3
"""Google Analytics 4: OAuth setup, property selection, and connection state.

Subcommands:
  auth-url                         — get the OAuth URL for the user to visit
  connect --code <auth_code>       — manually exchange an auth code (debug)
  properties                       — list available GA4 properties
  select --property-id <id>        — select which GA4 property to use

After `select`, a 7-day backfill sync is triggered automatically by the API.

Usage:
  python3 scripts/ga4_setup.py auth-url
  python3 scripts/ga4_setup.py properties
  python3 scripts/ga4_setup.py select --property-id 123456789
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

def cmd_auth_url(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/auth-url", key, base)
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    url = data.get("url") or data.get("auth_url")
    print("GA4 OAuth — open this URL in a browser:")
    print(url or "(no URL returned)")


def cmd_connect(args, key, base, pid):
    result = api_post(
        f"/api/projects/{pid}/integrations/ga4/connect",
        key, base, body={"code": args.code},
    )
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print("GA4 connected.")


def cmd_properties(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations/ga4/properties", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("properties", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No GA4 properties accessible with the current token.")
        return
    print(f"GA4 properties ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────┬────────────────────────────┬────────────────────┐")
    print("│ Property ID          │ Display name               │ Web stream domain  │")
    print("├──────────────────────┼────────────────────────────┼────────────────────┤")
    for p in items:
        pid_ = truncate(p.get("id") or p.get("property_id"), 20)
        name = truncate(p.get("display_name") or p.get("name"), 26)
        domain = truncate(p.get("domain") or p.get("web_domain") or "--", 18)
        print(f"│ {pad(pid_, 20)} │ {pad(name, 26)} │ {pad(domain, 18)} │")
    print("└──────────────────────┴────────────────────────────┴────────────────────┘")
    print("```")


def cmd_select(args, key, base, pid):
    result = api_post(
        f"/api/projects/{pid}/integrations/ga4/select-property",
        key, base, body={"property_id": args.property_id},
    )
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Selected GA4 property: {args.property_id}")
    print("(API will trigger a 7-day backfill sync in the background.)")


def main():
    parser = argparse.ArgumentParser(description="GA4 OAuth setup & property selection")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-url", help="Get the OAuth URL")

    p_c = sub.add_parser("connect", help="Manual auth-code exchange (debug)")
    p_c.add_argument("--code", required=True, help="Google OAuth authorization code")

    sub.add_parser("properties", help="List available GA4 properties")

    p_s = sub.add_parser("select", help="Choose which GA4 property to bind")
    p_s.add_argument("--property-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "auth-url": cmd_auth_url,
        "connect": cmd_connect,
        "properties": cmd_properties,
        "select": cmd_select,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
