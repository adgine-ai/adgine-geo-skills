#!/usr/bin/env python3
"""List GEO content items for a project.

Usage:
  python3 scripts/list_content.py [--project-id <id>] [--status draft|outline|article]
                                 [--topic-id <id>] [--page 1] [--limit 20] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json

parser = argparse.ArgumentParser(description="List GEO content items")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--status",   choices=["draft", "outline", "article"],
                    help="Filter by content status")
parser.add_argument("--topic-id", help="Filter by topic ID")
parser.add_argument("--page",  type=int, default=1,  help="Page number (default: 1)")
parser.add_argument("--limit", type=int, default=20, help="Results per page (default: 20)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

params = {"page": args.page, "limit": args.limit}
if args.status:
    params["status"] = args.status
if args.topic_id:
    params["topic_id"] = args.topic_id

result = api_get(f"/api/projects/{pid}/content", key, base, params=params)
data = extract_data(result)
items = data if isinstance(data, list) else data.get("items") or data.get("content") or []

if args.json:
    print_json(data)
    sys.exit(0)

total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
filter_desc = f"  status={args.status}" if args.status else ""
print(f"Content items ({len(items)} of {total}){filter_desc}  |  project: {pid}")
print()

if not items:
    print("  No content found. Generate an outline with: python3 scripts/generate_outline.py")
    sys.exit(0)

print(f"  {'ID':<38}  {'Status':<10}  {'Words':>5}  Title")
print(f"  {'-'*38}  {'-'*10}  {'-'*5}  {'-'*50}")
for item in items:
    cid    = item.get("id", "")[:36]
    status = item.get("status", "draft")
    words  = item.get("word_count", 0) or 0
    title  = (item.get("article_title") or "(untitled)")[:60]
    print(f"  {cid:<38}  {status:<10}  {words:>5}  {title}")
