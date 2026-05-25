#!/usr/bin/env python3
"""Manage competitors for a GEO project.

Subcommands:
  list                                — list all competitors
  add  --name <name> [--domain <url>] [--aliases a,b,c] [--source manual]
  remove --competitor-id <id> --yes   — DESTRUCTIVE

Usage examples:
  python3 scripts/manage_competitors.py list
  python3 scripts/manage_competitors.py add --name "Acme" --domain acme.com \\
      --aliases "Acme Inc,Acme Corp"
  python3 scripts/manage_competitors.py remove --competitor-id <id> --yes
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post, api_delete,
    extract_data, print_json, truncate,
)


def cmd_list(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/competitors", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("competitors", [])

    if args.json:
        print_json(items)
        return

    print(f"Competitors for project {pid}")
    print()
    if not items:
        print("No competitors yet. Use `add` to create one.")
        return

    print("```")
    print("┌──────────────────────────────────────┬────────────────────┬────────────────────┐")
    print("│ ID                                   │ Name               │ Domain             │")
    print("├──────────────────────────────────────┼────────────────────┼────────────────────┤")
    for c in items:
        cid = truncate(c.get("id") or c.get("competitor_id") or c.get("brand_id"), 36)
        name = truncate(c.get("name"), 18)
        domain = truncate(c.get("domain") or "--", 18)
        print(f"│ {cid:<36} │ {name:<18} │ {domain:<18} │")
    print("└──────────────────────────────────────┴────────────────────┴────────────────────┘")
    print("```")


def cmd_add(args, key, base, pid):
    body = {"name": args.name, "source": args.source}
    if args.domain:
        body["domain"] = args.domain
    if args.aliases:
        body["aliases"] = [a.strip() for a in args.aliases.split(",") if a.strip()]
    result = api_post(f"/api/projects/{pid}/competitors", key, base, body=body)
    data = extract_data(result)
    if args.json:
        print_json(data)
        return
    print(f"Added competitor: {args.name}")
    if isinstance(data, dict):
        cid = data.get("id") or data.get("competitor_id") or data.get("brand_id")
        if cid:
            print(f"  ID: {cid}")


def cmd_remove(args, key, base, pid):
    if not args.yes:
        print(f"About to remove competitor {args.competitor_id} from project {pid}.")
        print("Re-run with --yes to confirm.")
        sys.exit(1)
    result = api_delete(
        f"/api/projects/{pid}/competitors/{args.competitor_id}",
        key, base,
    )
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Removed competitor: {args.competitor_id}")


def main():
    parser = argparse.ArgumentParser(description="Manage GEO project competitors")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all competitors")

    p_add = sub.add_parser("add", help="Add a competitor")
    p_add.add_argument("--name", required=True, help="Competitor brand name")
    p_add.add_argument("--domain", help="Competitor domain")
    p_add.add_argument("--aliases", help="Comma-separated alias list")
    p_add.add_argument("--source", default="manual",
                       choices=["manual", "brand_profile", "ai_discovery"])

    p_rm = sub.add_parser("remove", help="Remove a competitor (DESTRUCTIVE)")
    p_rm.add_argument("--competitor-id", required=True)
    p_rm.add_argument("--yes", action="store_true", help="Confirm deletion")

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    if args.command == "list":
        cmd_list(args, key, base, pid)
    elif args.command == "add":
        cmd_add(args, key, base, pid)
    elif args.command == "remove":
        cmd_remove(args, key, base, pid)


if __name__ == "__main__":
    main()
