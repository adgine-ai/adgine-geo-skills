#!/usr/bin/env python3
"""List GEO website projects for the authenticated user.

Usage:
  python3 scripts/list_projects.py [--limit N] [--json]
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json  # _notice printed on import

parser = argparse.ArgumentParser(description="List GEO projects")
parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
result = api_get("/api/projects", key, base, params={"limit": args.limit})
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

items = data.get("items", []) if isinstance(data, dict) else data
total = data.get("total", len(items)) if isinstance(data, dict) else len(items)

if not items:
    print("No projects found.")
    print("Create your first project at: https://app.geoplatform.ai")
    sys.exit(0)

print(f"Found {total} project(s):\n")
print(f"  {'ID':<36}  {'Name':<30}  {'Domain':<30}  {'Brand'}")
print(f"  {'-'*36}  {'-'*30}  {'-'*30}  {'-'*5}")

for p in items:
    pid     = p.get("id", "")
    name    = (p.get("name") or p.get("url") or "")[:30]
    domain  = (p.get("domain") or "")[:30]
    brand   = "✓" if p.get("has_brand_profile") else "—"
    print(f"  {pid:<36}  {name:<30}  {domain:<30}  {brand}")

print()
print("To set the active project:")
print("  export GEO_PROJECT_ID=<id>")
