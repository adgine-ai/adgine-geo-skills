#!/usr/bin/env python3
"""Get, create, update, or delete a GEO project.

Usage:
  python3 scripts/manage_project.py get    --project-id <id> [--json]
  python3 scripts/manage_project.py create --url https://example.com [--description "text"]
  python3 scripts/manage_project.py update --project-id <id> [--name "Name"] [--url "url"] [--description "text"]
  python3 scripts/manage_project.py delete --project-id <id>
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, api_post, api_put, api_delete, extract_data, print_json

parser = argparse.ArgumentParser(description="Manage a GEO project")
parser.add_argument("action", choices=["get", "create", "update", "delete"])
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--url",         help="Website URL (required for create)")
parser.add_argument("--name",        help="Project name")
parser.add_argument("--description", help="Project description")
parser.add_argument("--json",        action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()

# ── GET ──────────────────────────────────────────────────────────────────────
if args.action == "get":
    pid = get_project_id(args.project_id)
    result = api_get(f"/api/projects/{pid}", key, base)
    p = extract_data(result)
    if args.json:
        print_json(p)
        sys.exit(0)
    print(f"Project: {p.get('name') or p.get('url')}")
    print(f"  ID          : {p.get('id')}")
    print(f"  URL         : {p.get('url')}")
    print(f"  Domain      : {p.get('domain') or '—'}")
    print(f"  Description : {p.get('description') or '—'}")
    print(f"  Brand ready : {'Yes' if p.get('has_brand_profile') else 'No'}")
    print(f"  Created     : {p.get('created_at', '')[:10]}")

# ── CREATE ───────────────────────────────────────────────────────────────────
elif args.action == "create":
    if not args.url:
        print("ERROR: --url is required for create")
        sys.exit(1)
    body = {"url": args.url}
    if args.description:
        body["description"] = args.description
    result = api_post("/api/projects", key, base, body)
    p = extract_data(result)
    if args.json:
        print_json(p)
        sys.exit(0)
    print(f"✓ Project created")
    print(f"  ID     : {p.get('id')}")
    print(f"  Name   : {p.get('name') or p.get('url')}")
    print(f"  Domain : {p.get('domain') or '—'}")
    print()
    print(f"To set as active: export GEO_PROJECT_ID={p.get('id')}")

# ── UPDATE ───────────────────────────────────────────────────────────────────
elif args.action == "update":
    pid = get_project_id(args.project_id)
    body = {}
    if args.name:        body["name"]        = args.name
    if args.url:         body["url"]         = args.url
    if args.description: body["description"] = args.description
    if not body:
        print("ERROR: Provide at least one of --name, --url, --description")
        sys.exit(1)
    result = api_put(f"/api/projects/{pid}", key, base, body)
    p = extract_data(result)
    if args.json:
        print_json(p)
        sys.exit(0)
    print(f"✓ Project updated: {p.get('name') or p.get('url')}")

# ── DELETE ───────────────────────────────────────────────────────────────────
elif args.action == "delete":
    pid = get_project_id(args.project_id)
    api_delete(f"/api/projects/{pid}", key, base)
    print(f"✓ Project {pid} deleted")
    if os.environ.get("GEO_PROJECT_ID") == pid:
        print("  NOTE: Unset GEO_PROJECT_ID since the deleted project was active.")
        print("  Run: unset GEO_PROJECT_ID")
