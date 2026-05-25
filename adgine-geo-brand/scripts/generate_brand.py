#!/usr/bin/env python3
"""Generate an AI brand cognition profile for a GEO project (async job).

Starts a brand generation job, polls until completed (~30–90 s), and prints
the resulting brand profile.

Usage:
  python3 scripts/generate_brand.py [--project-id <id>] [--language English] [--region US]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
    extract_data, poll_job, print_json,
)

parser = argparse.ArgumentParser(description="Generate GEO brand cognition profile")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--language", default="English", help="Brand content language (default: English)")
parser.add_argument("--region",   default="US",      help="Target region code, e.g. US, UK, CN (default: US)")
parser.add_argument("--json", action="store_true",   help="Output final job result as raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

print(f"Starting brand cognition generation for project: {pid}")
print(f"  Language : {args.language}  |  Region : {args.region}")
print()

body = {
    "language":   args.language,
    "region":     args.region,
    "auto_start": True,
}
result = api_post(f"/api/projects/{pid}/brand/generate", key, base, body)
job_data = extract_data(result)

job_id = job_data.get("id") or job_data.get("job_id")
if not job_id:
    print("ERROR: Brand generate endpoint did not return a job ID.")
    print_json(job_data)
    sys.exit(1)

print(f"Job ID: {job_id}")
print("Polling for completion (press Ctrl+C to cancel and check status later)...")

# Job status polled via: api_get(f"/api/projects/{pid}/brand/jobs/{job_id}", key, base)
final_job = poll_job(
    f"/api/projects/{pid}/brand/jobs/{job_id}",
    key, base,
    interval=5,
    max_wait=300,
)

if args.json:
    print_json(final_job)
    sys.exit(0)

status = final_job.get("status", "")
if status == "failed":
    print(f"ERROR: Brand generation failed — {final_job.get('error', 'unknown error')}")
    sys.exit(1)

print(f"\nBrand generation completed!")

# Fetch the final brand profile from the brand endpoint
brand_result = api_get(f"/api/projects/{pid}/brand", key, base)
brand_data = extract_data(brand_result)
profile = brand_data.get("profile") or {}

FIELDS = [
    ("brand_introduction", "Brand Introduction"),
    ("ideal_customer",     "Ideal Customer"),
    ("competitors",        "Competitors"),
    ("brand_perspective",  "Brand Perspective"),
    ("author_persona",     "Author Persona"),
    ("voice_and_tone",     "Voice & Tone"),
    ("writing_rules",      "Writing Rules"),
]

for field_key, label in FIELDS:
    value = profile.get(field_key, "")
    if value:
        display = value[:400] + "\n  [truncated...]" if len(value) > 400 else value
        print(f"\n[{label}]")
        print(f"  {display}")

print(f"\n---")
print(f"To refine any field, run:")
print(f"  python3 scripts/update_brand.py --project-id {pid} --field <field> --value \"...\"")
