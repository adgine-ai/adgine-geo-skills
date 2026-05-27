#!/usr/bin/env python3
"""List WordPress publish history, or push the latest content version to an
existing WP post.

Subcommands:
  list                             — list publish records (newest first)
  update --record-id <id>          — push latest content to the existing WP post
        [--category-ids 1,2,3]     —   optionally update categories
        [--status publish|draft]   —   optionally change post status

Examples:
  python3 scripts/manage_publishes.py list
  python3 scripts/manage_publishes.py update --record-id <id>
  python3 scripts/manage_publishes.py update --record-id <id> --status draft
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_put,
    extract_data, print_json, truncate,
    pad,
)


def cmd_list(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/integrations/wordpress/publishes",
        key, base,
    )
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("records") or (data or {}).get("publishes", [])

    if args.json:
        print_json(items)
        return

    if not items:
        print("No WordPress publishes yet.")
        return

    print(f"WordPress publishes ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────────────┬──────────────────────────────┬────────────┐")
    print("│ Record ID                            │ Title                        │ Published  │")
    print("├──────────────────────────────────────┼──────────────────────────────┼────────────┤")
    for r in items:
        rid = truncate(r.get("id") or r.get("record_id"), 36)
        title = truncate(r.get("title") or r.get("wp_post_title") or "(untitled)", 28)
        pub = truncate((r.get("published_at") or r.get("created_at") or "--")[:10], 10)
        print(f"│ {pad(rid, 36)} │ {pad(title, 28)} │ {pad(pub, 10)} │")
    print("└──────────────────────────────────────┴──────────────────────────────┴────────────┘")
    print("```")


def cmd_update(args, key, base, pid):
    body = {}
    if args.status:
        body["status"] = args.status
    if args.category_ids:
        body["category_ids"] = [
            int(c.strip()) for c in args.category_ids.split(",") if c.strip()
        ]
    result = api_put(
        f"/api/projects/{pid}/integrations/wordpress/publishes/{args.record_id}",
        key, base, body=body or None,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    print(f"Updated WP record: {args.record_id}")
    for k in ("wp_post_url", "status", "last_synced_at"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


def main():
    parser = argparse.ArgumentParser(description="List or update WordPress publishes")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List publish history")

    p_u = sub.add_parser("update", help="Push latest content version to existing WP post")
    p_u.add_argument("--record-id", required=True)
    p_u.add_argument("--status", choices=["publish", "draft"])
    p_u.add_argument("--category-ids")

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    if args.command == "list":
        cmd_list(args, key, base, pid)
    else:
        cmd_update(args, key, base, pid)


if __name__ == "__main__":
    main()
