#!/usr/bin/env python3
"""AI-powered bulk prompt generation for a GEO topic (async job).

Starts a generate-prompts job, polls until completed (~10–60 s), and prints
the generated prompts.

Usage:
  python3 scripts/generate_prompts.py --topic-id <id> [--project-id <id>] \
    [--count 10] [--language "English (en-US)"] [--region US] \
    [--platforms "openai,perplexity,google_aio"] \
    [--instructions "Focus on enterprise buyers"] [--json]
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
    extract_data, print_json,
)

DEFAULT_PLATFORMS = ["openai", "google_aio", "perplexity"]

parser = argparse.ArgumentParser(description="AI-generate prompts for a GEO topic")
parser.add_argument("--topic-id", required=True, help="Topic ID to generate prompts for")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--count", type=int, default=10,
                    help="Number of prompts to generate, 1–50 (default: 10)")
parser.add_argument("--language", default="English (en-US)",
                    help="Language for generated prompts (default: English (en-US))")
parser.add_argument("--region", default="US",
                    help="Target region code (default: US)")
parser.add_argument("--platforms",
                    help=f"Comma-separated platform IDs (default: {', '.join(DEFAULT_PLATFORMS)}). "
                         "Valid values: openai, google_aio, perplexity")
parser.add_argument("--instructions",
                    help="Additional instructions to guide prompt generation")
parser.add_argument("--json", action="store_true", help="Output raw JSON task result")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

platforms = DEFAULT_PLATFORMS
if args.platforms:
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

if not (1 <= args.count <= 50):
    print("ERROR: --count must be between 1 and 50")
    sys.exit(1)

print(f"Starting AI prompt generation for topic: {args.topic_id}")
print(f"  Count     : {args.count}")
print(f"  Language  : {args.language}  |  Region: {args.region}")
print(f"  Platforms : {', '.join(platforms)}")
print()

body = {
    "count":    args.count,
    "language": args.language,
    "region":   args.region,
    "platforms": platforms,
}
if args.instructions:
    body["additional_instructions"] = args.instructions

result = api_post(
    f"/api/projects/{pid}/topics/{args.topic_id}/generate-prompts",
    key, base, body
)
task_data = extract_data(result)
task_id = task_data.get("task_id") or task_data.get("id")

if not task_id:
    print("ERROR: Generate-prompts endpoint did not return a task ID.")
    print_json(task_data)
    sys.exit(1)

print(f"Task ID: {task_id}")
print("Polling for completion...")

# Poll the task status endpoint
frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
elapsed = 0
max_wait = 180
interval = 3
idx = 0
final_task = None

while elapsed < max_wait:
    status_result = api_get(
        f"/api/projects/{pid}/topics/{args.topic_id}/generate-prompts/{task_id}",
        key, base
    )
    task = extract_data(status_result)
    status = task.get("status", "")
    phase  = task.get("current_phase") or status
    count_so_far = task.get("generated_count", "")
    label  = f"{phase} ({count_so_far} generated)" if count_so_far else phase
    print(f"\r  {frames[idx % len(frames)]} {label}...", end="", flush=True)
    idx += 1

    if status in ("completed", "failed", "done", "success", "error"):
        print()
        final_task = task
        break
    time.sleep(interval)
    elapsed += interval

if final_task is None:
    print()
    print(f"WARNING: Task still running after {max_wait}s.")
    print(f"  Check status manually:")
    print(f"  GET /api/projects/{pid}/topics/{args.topic_id}/generate-prompts/{task_id}")
    sys.exit(0)

if args.json:
    print_json(final_task)
    sys.exit(0)

if final_task.get("status") == "failed":
    print(f"ERROR: Prompt generation failed — {final_task.get('error', 'unknown error')}")
    sys.exit(1)

prompts = final_task.get("prompts") or []
print(f"\nGenerated {len(prompts)} prompts for topic {args.topic_id}:")
print()
for i, p in enumerate(prompts, 1):
    content = p.get("content", "")
    prompt_id = p.get("id", "")
    print(f"  {i:>2}. [{prompt_id[:36]}]")
    print(f"      {content}")
    print()

print(f"These prompts are ready for:")
print(f"  - Citation testing : use the geo-citation skill → python3 scripts/create_tests.py --prompt-ids <id1,id2,...>")
print(f"  - Article outlines : use the geo-content skill  → python3 scripts/generate_outline.py --topic-id {args.topic_id} --prompt-ids <id1,id2,...>")
