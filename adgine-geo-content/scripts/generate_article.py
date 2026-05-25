#!/usr/bin/env python3
"""Generate a full article from an approved outline (async job).

The content item must have status='outline' and a completed outline.
Polls until the article is done (~60–180 s), then prints a summary.

Usage:
  python3 scripts/generate_article.py --content-id <cid> [--project-id <id>] [--json]
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

parser = argparse.ArgumentParser(description="Generate a full article from outline")
parser.add_argument("--content-id", required=True,
                    help="Content item ID (must have status=outline)")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw job result as JSON")
parser.add_argument("--show-article", action="store_true",
                    help="Print the full article text (can be long)")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

# Quick pre-check: verify content exists and has outline status
content_result = api_get(f"/api/projects/{pid}/content/{args.content_id}", key, base)
content = extract_data(content_result)
status = content.get("status", "")
if status not in ("outline", "article"):
    print(f"WARNING: Content status is '{status}'. Expected 'outline' to generate an article.")
    if status == "draft":
        print("  Generate an outline first: python3 scripts/generate_outline.py --topic-id <tid> --prompt-ids <ids>")
        sys.exit(1)

title = content.get("article_title") or "(untitled)"
print(f"Generating article for: {title}")
print(f"  Content ID : {args.content_id}")
print()

body = {"content_id": args.content_id}
result = api_post(f"/api/projects/{pid}/content/generate-article", key, base, body)
job_data = extract_data(result)

job_id = job_data.get("job_id") or job_data.get("id") or job_data.get("article_job_id")
if not job_id:
    print("ERROR: Article generate endpoint did not return a job ID.")
    print_json(job_data)
    sys.exit(1)

print(f"Job ID: {job_id}")
print("Polling for completion (this may take 60–180 seconds)...")

# Job status polled via: api_get(f"/api/projects/{pid}/content/jobs/{job_id}", key, base)
final_job = poll_job(
    f"/api/projects/{pid}/content/jobs/{job_id}",
    key, base,
    interval=6,
    max_wait=360,
)

if args.json:
    print_json(final_job)
    sys.exit(0)

if final_job.get("status") == "failed":
    print(f"ERROR: Article generation failed — {final_job.get('error', 'unknown error')}")
    sys.exit(1)

output = final_job.get("output") or {}
content_id_out = output.get("content_id") or args.content_id

# Retrieve the final content
final_content_result = api_get(f"/api/projects/{pid}/content/{content_id_out}", key, base)
article = extract_data(final_content_result)

print(f"\nArticle generation completed!")
print(f"  Content ID  : {article.get('id')}")
print(f"  Title       : {article.get('article_title') or '(untitled)'}")
print(f"  Status      : {article.get('status')}")
print(f"  Word count  : {article.get('word_count', 0)}")
print(f"  Meta title  : {(article.get('meta_title') or '—')[:80]}")
print(f"  Meta desc   : {(article.get('meta_description') or '—')[:120]}")
print(f"  Slug        : {article.get('meta_slug') or '—'}")

if article.get("faq_section"):
    print(f"\n[FAQ Section — first 500 chars]")
    faq = article["faq_section"]
    print(faq[:500] + ("..." if len(faq) > 500 else ""))

if args.show_article:
    full = article.get("full_content") or article.get("article_body") or ""
    if full:
        print(f"\n{'='*60}")
        print(full)
    else:
        print("\nno full_content returned yet")
else:
    print(f"\nTo print the full article, re-run with --show-article")
    print(f"  python3 scripts/generate_article.py --content-id {content_id_out} --show-article")
