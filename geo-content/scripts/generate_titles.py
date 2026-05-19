#!/usr/bin/env python3
"""Suggest article titles for a given topic and set of prompts (sync, fast).

Usage:
  python3 scripts/generate_titles.py --topic-id <tid> --prompt-ids <id1,id2,...>
                                    [--project-id <id>] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_post, extract_data, print_json

parser = argparse.ArgumentParser(description="Suggest article titles for a topic")
parser.add_argument("--topic-id",   required=True, help="Topic ID")
parser.add_argument("--prompt-ids", required=True, help="Comma-separated prompt IDs")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

prompt_ids = [p.strip() for p in args.prompt_ids.split(",") if p.strip()]
if not prompt_ids:
    print("ERROR: --prompt-ids must contain at least one prompt ID")
    sys.exit(1)

body = {
    "topic_id":  args.topic_id,
    "prompt_ids": prompt_ids,
}

result = api_post(f"/api/projects/{pid}/content/generate-titles", key, base, body)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

titles = data.get("titles") or (data if isinstance(data, list) else [])
print(f"Suggested titles ({len(titles)}):")
print()
for i, title in enumerate(titles, 1):
    print(f"  {i:>2}. {title}")

print()
print("Use a title with generate_outline.py:")
print(f"  python3 scripts/generate_outline.py --topic-id {args.topic_id} \\")
print(f"    --prompt-ids {args.prompt_ids} --title \"<chosen title>\"")
