#!/usr/bin/env python3
"""Inspect, edit, or delete a single GEO content item.

Usage:
  python3 scripts/manage_content.py get    --content-id <id> [--project-id <id>] [--json]
  python3 scripts/manage_content.py edit   --content-id <id> [--title "..."] [--body-file path.md]
  python3 scripts/manage_content.py delete --content-id <id>

The `get` action returns the full content detail (title, status, word count,
body, outline, metadata) for one record. Use `list_content.py` to discover IDs.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_patch, api_delete,
    extract_data, print_json,
)

parser = argparse.ArgumentParser(description="Manage a single GEO content item")
parser.add_argument("action", choices=["get", "edit", "delete"])
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--content-id", required=True, help="Content ID")
parser.add_argument("--title",      help="(edit) New article title")
parser.add_argument("--body-file",  help="(edit) Path to a markdown file with the new body")
parser.add_argument("--status",     help="(edit) New status (draft|outline|article|published)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

# ── GET ───────────────────────────────────────────────────────────────────────
if args.action == "get":
    result = api_get(f"/api/projects/{pid}/content/{args.content_id}", key, base)
    item = extract_data(result) or {}
    if args.json:
        print_json(item)
        sys.exit(0)
    print(f"Content {args.content_id}")
    print()
    print(f"  Title         : {item.get('article_title') or item.get('title') or '(untitled)'}")
    print(f"  Status        : {item.get('status', '--')}")
    print(f"  Publish status: {item.get('publish_status') or '—'}")
    print(f"  Words         : {item.get('word_count', 0)}")
    print(f"  Topic ID      : {item.get('topic_id', '--')}")
    print(f"  Created       : {item.get('created_at', '--')}")
    print(f"  Updated       : {item.get('updated_at', '--')}")
    body = item.get("article_body") or item.get("body") or ""
    if body:
        preview = body[:600]
        print()
        print("  --- body preview ---")
        for line in preview.splitlines():
            print(f"  {line}")
        if len(body) > 600:
            print(f"  [... truncated, {len(body)} chars total ...]")
    sys.exit(0)

# ── EDIT ──────────────────────────────────────────────────────────────────────
if args.action == "edit":
    body = {}
    if args.title:
        body["article_title"] = args.title
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as fh:
            body["article_body"] = fh.read()
    if args.status:
        body["status"] = args.status
    if not body:
        print("ERROR: provide at least one of --title, --body-file or --status")
        sys.exit(1)
    result = api_patch(f"/api/projects/{pid}/content/{args.content_id}", key, base, body)
    updated = extract_data(result) or {}
    if args.json:
        print_json(updated)
        sys.exit(0)
    print(f"✓  Updated content {args.content_id}")
    print(f"   Title  : {updated.get('article_title') or updated.get('title', '')}")
    print(f"   Status : {updated.get('status', '--')}")
    sys.exit(0)

# ── DELETE ────────────────────────────────────────────────────────────────────
if args.action == "delete":
    api_delete(f"/api/projects/{pid}/content/{args.content_id}", key, base)
    print(f"✓  Deleted content {args.content_id}")
    sys.exit(0)
