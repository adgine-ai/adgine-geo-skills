#!/usr/bin/env python3
"""List GEO optimization opportunities for a project.

Returns the latest batch of opportunities ranked by impact score.
Handles three states: ready (shows list), pending (generating), empty (never generated).

Usage:
  python3 scripts/list_opportunities.py [--project-id <id>] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json, truncate, pad

parser = argparse.ArgumentParser(description="List GEO opportunities for a project")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw JSON response")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

result = api_get(f"/api/projects/{pid}/opportunities", key, base)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

status = data.get("status", "empty")

if status == "pending":
    print("Opportunities are currently being generated for this project.")
    print("This usually takes a few minutes — please check back shortly.")
    sys.exit(0)

if status == "empty":
    print("No opportunities yet for this project.")
    print()
    print("Opportunity discovery requires approximately 1 week of data after your website")
    print("is added to the platform. The system needs time to build up visibility signals,")
    print("topic coverage, and competitor comparisons before it can generate meaningful")
    print("recommendations.")
    print()
    print("→ Once your first weekly analysis cycle completes, opportunities will appear here.")
    print("  Visit https://platform.adgine.ai to check your project status.")
    sys.exit(0)

# status == "ready"
items = data.get("items") or []
run_date = data.get("run_date") or "--"

if not items:
    print(f"Opportunities ready (run date: {run_date}) but no items found.")
    sys.exit(0)

print(f"Opportunities — {len(items)} item(s) found (run date: {run_date})")
print()

# Table output
col_idx = 4
col_title = 34
col_score = 5
col_cat = 14

header = (f"{'#':>{col_idx}} | "
          f"{pad('Title', col_title)} | "
          f"{'Score':>{col_score}} | "
          f"{pad('Category', col_cat)}")
sep = (f"{'-' * col_idx}-+-"
       f"{'-' * col_title}-+-"
       f"{'-' * col_score}-+-"
       f"{'-' * col_cat}")

print(f"  {header}")
print(f"  {sep}")

for i, item in enumerate(items, 1):
    title = truncate(item.get("title", "--"), col_title)
    score = str(item.get("total_score", "--"))
    category = truncate(item.get("category") or "--", col_cat)

    row = (f"{i:>{col_idx}} | "
           f"{pad(title, col_title)} | "
           f"{score:>{col_score}} | "
           f"{pad(category, col_cat)}")
    print(f"  {row}")

print()
print("Use get_opportunity.py --opportunity-id <id> for full details on any item.")
