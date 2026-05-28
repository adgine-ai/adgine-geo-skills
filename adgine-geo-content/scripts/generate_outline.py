#!/usr/bin/env python3
"""Generate an AI-optimized article outline (async job).

Starts an outline generation job, polls until completed (~10–15 min), then prints
the outline and the content_id needed for article generation.

Usage:
  python3 scripts/generate_outline.py \
    --topic-id <tid> --prompt-ids <id1,id2,...> \
    [--project-id <id>] [--title "Your Article Title"] \
    [--reference-urls "https://url1,https://url2"] \
    [--instructions "Target CMO audience, emphasize ROI"] \
    [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_post, extract_data, poll_job, print_json,
)

parser = argparse.ArgumentParser(description="Generate GEO article outline")
parser.add_argument("--topic-id",       required=True, help="Topic ID")
parser.add_argument("--prompt-ids",     required=True, help="Comma-separated prompt IDs")
parser.add_argument("--project-id",     help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--title",          help="Article title (auto-generated if omitted)")
parser.add_argument("--reference-urls", help="Comma-separated reference/competitor URLs")
parser.add_argument("--instructions",   help="Additional AI guidance (audience, tone, focus)")
parser.add_argument("--json", action="store_true", help="Output raw job result as JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

prompt_ids = [p.strip() for p in args.prompt_ids.split(",") if p.strip()]
if not prompt_ids:
    print("ERROR: --prompt-ids must contain at least one ID")
    sys.exit(1)

body = {
    "topic_id":  args.topic_id,
    "prompt_ids": prompt_ids,
}
if args.title:
    body["article_title"] = args.title
if args.reference_urls:
    body["reference_urls"] = [u.strip() for u in args.reference_urls.split(",") if u.strip()]
if args.instructions:
    body["custom_instructions"] = args.instructions

print(f"Starting outline generation...")
print(f"  Topic     : {args.topic_id}")
print(f"  Prompts   : {len(prompt_ids)}")
if args.title:
    print(f"  Title     : {args.title}")
print()

result = api_post(f"/api/projects/{pid}/content/generate-outline", key, base, body)
job_data = extract_data(result)

# The response may contain the job directly (id = job id) or have separate job_id / content_id fields
job_id     = job_data.get("job_id") or job_data.get("outline_job_id") or job_data.get("id")
content_id = job_data.get("content_id")  # may be None; resolved from job output after polling

if not job_id:
    print("ERROR: Outline endpoint did not return a job ID.")
    print_json(job_data)
    sys.exit(1)

print(f"Job ID: {job_id}")
print("Polling for completion (this typically takes 10–15 minutes)...")

# Job status polled via: api_get(f"/api/projects/{pid}/content/jobs/{job_id}", key, base)
final_job = poll_job(
    f"/api/projects/{pid}/content/jobs/{job_id}",
    key, base,
    interval=10,
    max_wait=1200,
)

if args.json:
    print_json(final_job)
    sys.exit(0)

status = final_job.get("status", "")
if status == "failed":
    print(f"ERROR: Outline generation failed — {final_job.get('error', 'unknown error')}")
    sys.exit(1)

output = final_job.get("output") or {}
content_id = output.get("content_id") or content_id
title      = output.get("article_title") or args.title or "(auto-generated)"
outline    = output.get("page_outline") or ""

print(f"\nOutline generation completed!")
print(f"  Content ID : {content_id}")
print(f"  Title      : {title}")
print()

if outline:
    # Print first 2000 chars of outline
    if len(outline) > 2000:
        print(outline[:2000])
        print(f"\n  [... outline continues — {len(outline)} chars total ...]")
    else:
        print(outline)

print()
print("Next: generate the full article with:")
print(f"  python3 scripts/generate_article.py --content-id {content_id}")
