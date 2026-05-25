#!/usr/bin/env python3
"""Create a new SaaS-hosted website (async deployment).

This kicks off an async deployment job. Use get_task.py to poll the returned
task_id until it reaches a terminal state.

Usage:
  python3 scripts/create_website.py --subdomain mysite \\
      --brand-name "My Site" --industry "SaaS" \\
      --description "An AI-first content platform" \\
      --language English [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_post, extract_data, print_json


def main():
    parser = argparse.ArgumentParser(description="Create a SaaS-hosted website")
    parser.add_argument("--subdomain", required=True, help="Subdomain (e.g. mysite)")
    parser.add_argument("--brand-name", required=True, help="Brand name")
    parser.add_argument("--industry", required=True, help="Industry")
    parser.add_argument("--description", required=True, help="Short brand description")
    parser.add_argument("--language", default="English", help="Content language")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    body = {
        "subdomain": args.subdomain,
        "brand_name": args.brand_name,
        "industry": args.industry,
        "description": args.description,
        "language": args.language,
    }
    result = api_post("/api/saas/websites", key, base, body=body)
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    task_id = data.get("task_id") or data.get("id")
    print(f"Website deployment started.")
    if task_id:
        print(f"  Task ID: {task_id}")
        print(f"  Poll status: python3 scripts/get_task.py --task-id {task_id}")
    else:
        print("  (no task_id returned — inspect raw response with --json)")


if __name__ == "__main__":
    main()
