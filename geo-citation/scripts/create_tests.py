#!/usr/bin/env python3
"""Submit citation tests for one or more GEO prompts.

Sends each prompt to multiple AI platforms (ChatGPT, Perplexity, Google AI
Overviews, etc.) to check whether your brand is cited in the responses.
Results are processed asynchronously — check with get_results.py.

Usage:
  python3 scripts/create_tests.py --prompt-ids <id1,id2,...> [--project-id <id>]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_post, extract_data, print_json

parser = argparse.ArgumentParser(description="Submit GEO citation tests")
parser.add_argument("--prompt-ids", required=True,
                    help="Comma-separated prompt IDs to test")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--json", action="store_true", help="Output raw JSON response")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

prompt_ids = [p.strip() for p in args.prompt_ids.split(",") if p.strip()]
if not prompt_ids:
    print("ERROR: --prompt-ids must contain at least one ID")
    sys.exit(1)

print(f"Submitting citation tests for {len(prompt_ids)} prompt(s)...")

body = {"prompt_ids": prompt_ids}
result = api_post(f"/api/projects/{pid}/citation-tests", key, base, body)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

tests = data if isinstance(data, list) else data.get("tests") or data.get("items") or []
print(f"\nCreated {len(tests)} citation test(s)")
print()

# Group by prompt
by_prompt = {}
for t in tests:
    prompt_id = t.get("prompt_id", "unknown")
    by_prompt.setdefault(prompt_id, []).append(t)

for prompt_id, prompt_tests in by_prompt.items():
    platforms = [t.get("platform", "?") for t in prompt_tests]
    print(f"  Prompt [{prompt_id[:36]}]")
    print(f"    Platforms : {', '.join(platforms)}")
    print()

print("Results are processed asynchronously (5–15 minutes per platform).")
print("Check results with:")
for pid_str in prompt_ids:
    print(f"  python3 scripts/get_results.py --prompt-id {pid_str}")
