#!/usr/bin/env python3
"""Check, query, or disconnect third-party data integrations for a project.

Subcommands:
  list                            — list all connected integrations
  status   --service <name>       — get connection status of one service
  disconnect --service <name>     — disconnect a service (DESTRUCTIVE; asks confirmation)

Services typically include: ga4, cloudflare. (GSC is currently inactive in the API.)

Usage examples:
  python3 scripts/check_integrations.py list
  python3 scripts/check_integrations.py status --service ga4
  python3 scripts/check_integrations.py disconnect --service ga4 --yes
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id, api_get, api_delete, extract_data, print_json, truncate,
)


def cmd_list(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/integrations", key, base)
    data = extract_data(result) or []

    if args.json:
        print_json(data)
        return

    items = data if isinstance(data, list) else data.get("integrations", [])

    print(f"Integrations for project {pid}")
    print()
    if not items:
        print("No integrations connected.")
        return

    print("```")
    print("┌────────────────┬──────────────┬──────────────────────┐")
    print("│ Service        │ Status       │ Connected at         │")
    print("├────────────────┼──────────────┼──────────────────────┤")
    for item in items:
        service = truncate(item.get("service") or item.get("provider"), 14)
        status_raw = (item.get("status") or "").lower()
        if status_raw in ("connected", "active"):
            status = "Connected"
        elif status_raw in ("pending",):
            status = "Pending"
        elif status_raw in ("disconnected", "inactive", ""):
            status = "Disconnected"
        else:
            status = truncate(item.get("status"), 12)
        connected_at = truncate(item.get("connected_at") or item.get("created_at") or "--", 20)
        print(f"│ {service:<14} │ {status:<12} │ {connected_at:<20} │")
    print("└────────────────┴──────────────┴──────────────────────┘")
    print("```")


def cmd_status(args, key, base, pid):
    if not args.service:
        print("ERROR: --service is required for `status`.")
        sys.exit(1)
    result = api_get(
        f"/api/projects/{pid}/integrations/{args.service}/status",
        key, base,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    print(f"Integration status: {args.service}")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────┐")
    print("│ Field              │ Value                        │")
    print("├────────────────────┼──────────────────────────────┤")
    for k in ("service", "status", "connected_at", "expires_at", "account", "property_id"):
        if k in data:
            print(f"│ {k:<18} │ {truncate(data.get(k), 28):<28} │")
    print("└────────────────────┴──────────────────────────────┘")
    print("```")


def cmd_disconnect(args, key, base, pid):
    if not args.service:
        print("ERROR: --service is required for `disconnect`.")
        sys.exit(1)
    if not args.yes:
        print(f"About to disconnect '{args.service}' for project {pid}.")
        print("Re-run with --yes to confirm.")
        sys.exit(1)
    result = api_delete(
        f"/api/projects/{pid}/integrations/{args.service}",
        key, base,
    )
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Disconnected: {args.service}")


def main():
    parser = argparse.ArgumentParser(description="Manage GEO project data integrations")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all integrations")

    p_status = sub.add_parser("status", help="Get one integration's status")
    p_status.add_argument("--service", required=True, help="Service key (e.g. ga4, cloudflare)")

    p_disc = sub.add_parser("disconnect", help="Disconnect an integration (DESTRUCTIVE)")
    p_disc.add_argument("--service", required=True, help="Service key (e.g. ga4, cloudflare)")
    p_disc.add_argument("--yes", action="store_true", help="Confirm disconnection")

    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    if args.command == "list":
        cmd_list(args, key, base, pid)
    elif args.command == "status":
        cmd_status(args, key, base, pid)
    elif args.command == "disconnect":
        cmd_disconnect(args, key, base, pid)


if __name__ == "__main__":
    main()
