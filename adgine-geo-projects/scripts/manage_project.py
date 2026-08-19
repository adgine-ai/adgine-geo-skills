#!/usr/bin/env python3
"""Get, create, update, or delete a GEO project.

Usage:
  python3 scripts/manage_project.py get    --project-id <id> [--json]
  python3 scripts/manage_project.py create --url https://example.com [--description "text"] [--metadata-file metadata.json]
  python3 scripts/manage_project.py update --project-id <id> --name "Name"
  python3 scripts/manage_project.py delete --project-id <id>
"""
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, api_post, api_put, api_delete, extract_data, print_json

parser = argparse.ArgumentParser(description="Manage a GEO project")
parser.add_argument("action", choices=["get", "create", "update", "delete"])
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--url",         help="Website URL (required for create)")
parser.add_argument("--name",        help="Project name")
parser.add_argument("--description", help="Project description")
parser.add_argument("--metadata-file", help="(create) JSON object with metadata overrides")
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
    if args.metadata_file:
        try:
            with open(args.metadata_file, "r", encoding="utf-8") as fh:
                metadata = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: could not read --metadata-file as JSON — {exc}")
            sys.exit(1)
        if not isinstance(metadata, dict):
            print("ERROR: --metadata-file must contain a JSON object")
            sys.exit(1)
        body["metadata_override"] = metadata
    result = api_post("/api/projects", key, base, body)
    p = extract_data(result)
    if args.name and p.get("id"):
        p = extract_data(api_put(
            f"/api/projects/{p.get('id')}", key, base, {"name": args.name}
        )) or p
    if args.json:
        print_json(p)
        sys.exit(0)
    print(f"✓ Project created")
    print(f"  ID     : {p.get('id')}")
    print(f"  Name   : {p.get('name') or p.get('url')}")
    print(f"  Domain : {p.get('domain') or '—'}")
    if args.name:
        print("  Name was applied automatically after project creation.")
    print()
    print(f"To set as active: export GEO_PROJECT_ID={p.get('id')}")

# ── UPDATE ───────────────────────────────────────────────────────────────────
elif args.action == "update":
    pid = get_project_id(args.project_id)
    if args.url or args.description or args.metadata_file:
        print("ERROR: GEO-Api only allows changing a project's name after creation")
        print("  URL, description, and metadata overrides can only be supplied during create.")
        sys.exit(1)
    if not args.name:
        print("ERROR: --name is required for update; all other project fields remain unchanged")
        sys.exit(1)
    current = extract_data(api_get(f"/api/projects/{pid}", key, base)) or {}
    body = {"name": args.name}
    result = api_put(f"/api/projects/{pid}", key, base, body)
    p = extract_data(result)
    if args.json:
        print_json(p)
        sys.exit(0)
    old_name = current.get("name") or current.get("url") or "(unnamed)"
    print(f"✓ Project updated: {old_name} -> {p.get('name') or args.name}")
    print("  URL, description, and metadata were retained unchanged.")

# ── DELETE ───────────────────────────────────────────────────────────────────
elif args.action == "delete":
    pid = get_project_id(args.project_id)
    api_delete(f"/api/projects/{pid}", key, base)
    print(f"✓ Project {pid} deleted")
    if os.environ.get("GEO_PROJECT_ID") == pid:
        print("  NOTE: Unset GEO_PROJECT_ID since the deleted project was active.")
        print("  Run: unset GEO_PROJECT_ID")
