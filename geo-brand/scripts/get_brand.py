#!/usr/bin/env python3
"""View the brand cognition profile for a GEO project.

Usage:
  python3 scripts/get_brand.py [--project-id <id>] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json

parser = argparse.ArgumentParser(description="View GEO brand cognition profile")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

result = api_get(f"/api/projects/{pid}/brand", key, base)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

status = data.get("status", "none")
profile = data.get("profile") or {}

print(f"Brand Profile  (project: {pid})")
print(f"Status         : {status}")

if status == "none":
    print("\nNo brand profile yet.")
    print("  Run: python3 scripts/generate_brand.py --project-id " + pid)
    sys.exit(0)

if status == "generating":
    job_id = data.get("job_id", "")
    print(f"Job ID         : {job_id}")
    print("\nGeneration is in progress. Run generate_brand.py to wait for completion.")
    sys.exit(0)

FIELDS = [
    ("brand_introduction", "Brand Introduction"),
    ("ideal_customer",     "Ideal Customer"),
    ("competitors",        "Competitors"),
    ("brand_perspective",  "Brand Perspective"),
    ("author_persona",     "Author Persona"),
    ("voice_and_tone",     "Voice & Tone"),
    ("writing_rules",      "Writing Rules"),
    ("cta_text",           "CTA Text"),
    ("cta_landing_page",   "CTA URL"),
    ("language",           "Language"),
    ("region",             "Region"),
]

print()
for field_key, label in FIELDS:
    value = profile.get(field_key, "")
    if value:
        display = value[:300] + "\n  [truncated]" if len(value) > 300 else value
        print(f"[{label}]")
        print(f"  {display}")
        print()
