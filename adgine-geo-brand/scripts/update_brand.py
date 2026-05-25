#!/usr/bin/env python3
"""Update a specific field in the GEO brand cognition profile.

Usage:
  python3 scripts/update_brand.py [--project-id <id>] --field <field> --value "<text>"

Examples:
  python3 scripts/update_brand.py --field voice_and_tone --value "Friendly, expert, data-driven"
  python3 scripts/update_brand.py --field competitors --value "Semrush, Ahrefs, Moz"
  python3 scripts/update_brand.py --field language --value "Chinese (Simplified)" --region CN
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_patch, extract_data, print_json

UPDATABLE_FIELDS = [
    "brand_introduction",
    "ideal_customer",
    "competitors",
    "brand_perspective",
    "author_persona",
    "voice_and_tone",
    "writing_rules",
    "cta_text",
    "cta_landing_page",
    "writing_sample_url",
    "writing_sample_title",
    "writing_sample_body",
    "writing_sample_outline",
    "language",
    "region",
]

parser = argparse.ArgumentParser(description="Update a GEO brand profile field")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--field", required=True, choices=UPDATABLE_FIELDS,
                    help="Name of the brand field to update")
parser.add_argument("--value", required=True,
                    help="New value for the field")
parser.add_argument("--json", action="store_true", help="Output the updated profile as raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

body = {args.field: args.value}
result = api_patch(f"/api/projects/{pid}/brand", key, base, body)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

print(f"✓  Updated [{args.field}] for project {pid}")
profile = data.get("profile") or data
updated_value = profile.get(args.field, args.value)
display = updated_value[:300] + "..." if len(str(updated_value)) > 300 else str(updated_value)
print(f"   New value: {display}")
