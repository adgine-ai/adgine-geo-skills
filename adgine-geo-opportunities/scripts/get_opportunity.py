#!/usr/bin/env python3
"""Get full detail of a single GEO opportunity.

Shows title, scores, rationale, guidance, implementation steps,
coverage data, and source URLs.

Usage:
  python3 scripts/get_opportunity.py --opportunity-id <id> [--project-id <id>] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json, pad

parser = argparse.ArgumentParser(description="Get GEO opportunity detail")
parser.add_argument("--opportunity-id", required=True,
                    help="Opportunity ID (UUID)")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw JSON response")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

result = api_get(
    f"/api/projects/{pid}/opportunities/{args.opportunity_id}",
    key, base,
)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

title = data.get("title", "Untitled")
total_score = data.get("total_score", "--")
category = data.get("category") or "--"
rationale = data.get("rationale") or "--"
guidance = data.get("guidance") or "--"
implementation = data.get("implementation") or []
scores = data.get("scores") or {}
coverage = data.get("coverage") or {}
source_urls = data.get("source_urls") or []
created_at = (data.get("created_at") or "--")[:10]

print(f"Opportunity: {title}")
print(f"Score: {total_score}  |  Category: {category}  |  Date: {created_at}")
print()

# Score breakdown
if scores:
    print("Score Breakdown:")
    col_dim = 14
    col_val = 5
    print(f"  {pad('Dimension', col_dim)} | {'Score':>{col_val}}")
    print(f"  {'-' * col_dim}-+-{'-' * col_val}")
    for dim, val in scores.items():
        print(f"  {pad(dim, col_dim)} | {str(val):>{col_val}}")
    print()

# Rationale
print(f"Rationale: {rationale}")
print()

# Guidance
if guidance != "--":
    print(f"Guidance: {guidance}")
    print()

# Implementation steps
if implementation:
    print("Implementation Steps:")
    for i, step in enumerate(implementation, 1):
        print(f"  {i}. {step}")
    print()

# Coverage
if coverage:
    print("Coverage:")
    for k, v in coverage.items():
        print(f"  {k}: {v}")
    print()

# Source URLs
if source_urls:
    print("Source URLs:")
    for url in source_urls:
        print(f"  - {url}")
