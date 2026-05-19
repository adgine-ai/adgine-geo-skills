#!/usr/bin/env python3
"""Retrieve citation test results for a GEO prompt.

Usage:
  # Results for a single prompt (all platforms):
  python3 scripts/get_results.py --prompt-id <id> [--project-id <id>] [--json]

  # Aggregated cited URLs across multiple prompts:
  python3 scripts/get_results.py --aggregate --prompt-ids <id1,id2,...> [--project-id <id>]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, api_post, extract_data, print_json

parser = argparse.ArgumentParser(description="View GEO citation test results")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--prompt-id",  help="Prompt ID to retrieve results for")
parser.add_argument("--prompt-ids", help="Comma-separated prompt IDs (used with --aggregate)")
parser.add_argument("--aggregate",  action="store_true",
                    help="Aggregate cited URLs across multiple prompts")
parser.add_argument("--show-response", action="store_true",
                    help="Print the full AI response text for each test")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

STATUS_ICONS = {
    "completed": "✓",
    "running":   "⏳",
    "pending":   "◌",
    "failed":    "✗",
}

# ── AGGREGATE MODE ────────────────────────────────────────────────────────────
if args.aggregate:
    if not args.prompt_ids:
        print("ERROR: --prompt-ids is required with --aggregate")
        sys.exit(1)
    prompt_ids = [p.strip() for p in args.prompt_ids.split(",") if p.strip()]
    body = {"prompt_ids": prompt_ids}
    result = api_post(f"/api/projects/{pid}/citation-tests/urls", key, base, body)
    data = extract_data(result)

    if args.json:
        print_json(data)
        sys.exit(0)

    urls   = data.get("urls") or []
    total  = data.get("total", len(urls))
    print(f"Cited URLs ({total} found across {len(prompt_ids)} prompts):")
    print()
    for url in urls:
        print(f"  {url}")
    sys.exit(0)

# ── SINGLE PROMPT MODE ────────────────────────────────────────────────────────
if not args.prompt_id:
    print("ERROR: One of --prompt-id or (--aggregate + --prompt-ids) is required")
    sys.exit(1)

result = api_get(
    f"/api/projects/{pid}/citation-tests/prompts/{args.prompt_id}",
    key, base,
)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

tests = data if isinstance(data, list) else data.get("tests") or data.get("items") or [data]

# Handle case where a single test object is returned
if isinstance(data, dict) and "platform" in data:
    tests = [data]

print(f"Citation results for prompt: {args.prompt_id}")
print()

for test in tests:
    platform    = test.get("platform", "Unknown")
    status      = test.get("status", "pending")
    icon        = STATUS_ICONS.get(status, "?")
    cited       = test.get("is_cited") or test.get("cited", False)
    response    = test.get("response_text") or ""
    citations   = test.get("citations") or []

    print(f"  [{platform}]  {icon} {status}")
    print(f"    Brand cited : {'Yes ✓' if cited else 'No'}")

    if citations:
        print(f"    Cited URLs  : {len(citations)}")
        for url in citations[:5]:
            print(f"      - {url}")
        if len(citations) > 5:
            print(f"      ... and {len(citations) - 5} more")

    if args.show_response and response:
        print(f"    AI Response :")
        # Indent response for readability
        for line in response[:800].splitlines():
            print(f"      {line}")
        if len(response) > 800:
            print(f"      [... truncated, {len(response)} chars total ...]")

    print()

# Summary
completed = [t for t in tests if t.get("status") == "completed"]
cited_tests = [t for t in completed if t.get("is_cited") or t.get("cited")]
print(f"Summary: {len(cited_tests)}/{len(completed)} completed tests cited your brand", end="")
pending_count = len([t for t in tests if t.get("status") in ("pending", "running")])
if pending_count:
    print(f"  ({pending_count} still running)", end="")
print()
