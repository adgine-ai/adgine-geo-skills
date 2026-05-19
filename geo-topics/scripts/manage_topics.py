#!/usr/bin/env python3
"""List, create, batch-create, update, or delete GEO topics.

Usage:
  python3 scripts/manage_topics.py list   [--project-id <id>] [--page 1] [--limit 20] [--json]
  python3 scripts/manage_topics.py create --name "Product Reviews" [--description "..."]
  python3 scripts/manage_topics.py batch  --names "Topic A,Topic B,Topic C"
  python3 scripts/manage_topics.py update --topic-id <id> [--name "..."] [--description "..."]
  python3 scripts/manage_topics.py delete --topic-id <id>
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post, api_put, api_delete,
    extract_data, print_json,
)

parser = argparse.ArgumentParser(description="Manage GEO topics")
parser.add_argument("action", choices=["list", "create", "batch", "update", "delete"])
parser.add_argument("--project-id",  help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--topic-id",    help="Topic ID (required for update/delete)")
parser.add_argument("--name",        help="Topic name")
parser.add_argument("--description", help="Topic description")
parser.add_argument("--names",       help="Comma-separated names for batch create")
parser.add_argument("--page",  type=int, default=1,  help="Page number (list only)")
parser.add_argument("--limit", type=int, default=20, help="Results per page (list only)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

# ── LIST ─────────────────────────────────────────────────────────────────────
if args.action == "list":
    result = api_get(
        f"/api/projects/{pid}/topics",
        key, base,
        params={"page": args.page, "limit": args.limit},
    )
    topics = extract_data(result)
    items = topics if isinstance(topics, list) else topics.get("items") or topics.get("topics") or []

    if args.json:
        print_json(topics)
        sys.exit(0)

    total = topics.get("total", len(items)) if isinstance(topics, dict) else len(items)
    print(f"Topics ({len(items)} of {total})  |  project: {pid}")
    print()
    if not items:
        print("  No topics found. Create one with: python3 scripts/manage_topics.py create --name \"...\"")
    else:
        print(f"  {'ID':<38}  {'Name':<30}  {'Prompts':>7}  Description")
        print(f"  {'-'*38}  {'-'*30}  {'-'*7}  {'-'*30}")
        for t in items:
            tid    = t.get("id", "")[:36]
            name   = (t.get("name") or "")[:30]
            count  = t.get("prompt_count", 0)
            desc   = (t.get("description") or "")[:40]
            print(f"  {tid:<38}  {name:<30}  {count:>7}  {desc}")

# ── CREATE ────────────────────────────────────────────────────────────────────
elif args.action == "create":
    if not args.name:
        print("ERROR: --name is required for create")
        sys.exit(1)
    body = {"name": args.name}
    if args.description:
        body["description"] = args.description
    result = api_post(f"/api/projects/{pid}/topics", key, base, body)
    topic = extract_data(result)
    if args.json:
        print_json(topic)
        sys.exit(0)
    print(f"✓  Created topic: {topic.get('name')}")
    print(f"   ID: {topic.get('id')}")

# ── BATCH CREATE ──────────────────────────────────────────────────────────────
elif args.action == "batch":
    if not args.names:
        print("ERROR: --names is required (comma-separated list of topic names)")
        sys.exit(1)
    name_list = [n.strip() for n in args.names.split(",") if n.strip()]
    if not name_list:
        print("ERROR: --names must contain at least one topic name")
        sys.exit(1)
    body = {"topics": [{"name": n} for n in name_list]}
    result = api_post(f"/api/projects/{pid}/topics/batch", key, base, body)
    created = extract_data(result)
    if args.json:
        print_json(created)
        sys.exit(0)
    items = created if isinstance(created, list) else created.get("topics") or created.get("items") or []
    print(f"✓  Created {len(items)} topics:")
    for t in items:
        print(f"   {t.get('id', '')[:36]}  {t.get('name', '')}")

# ── UPDATE ────────────────────────────────────────────────────────────────────
elif args.action == "update":
    if not args.topic_id:
        print("ERROR: --topic-id is required for update")
        sys.exit(1)
    body = {}
    if args.name:
        body["name"] = args.name
    if args.description:
        body["description"] = args.description
    if not body:
        print("ERROR: Provide at least one of --name or --description to update")
        sys.exit(1)
    result = api_put(f"/api/projects/{pid}/topics/{args.topic_id}", key, base, body)
    topic = extract_data(result)
    if args.json:
        print_json(topic)
        sys.exit(0)
    print(f"✓  Updated topic: {topic.get('name')}")

# ── DELETE ────────────────────────────────────────────────────────────────────
elif args.action == "delete":
    if not args.topic_id:
        print("ERROR: --topic-id is required for delete")
        sys.exit(1)
    api_delete(f"/api/projects/{pid}/topics/{args.topic_id}", key, base)
    print(f"✓  Deleted topic {args.topic_id}")
