#!/usr/bin/env python3
"""List, create, update, or delete prompts within a GEO topic.

Usage:
  python3 scripts/manage_prompts.py list     --topic-id <tid> [--project-id <id>] [--json]
  python3 scripts/manage_prompts.py list-all [--project-id <id>] [--json]
  python3 scripts/manage_prompts.py create   --topic-id <tid> --content "What is...?" \
                                            [--language "English (en-US)"] [--region US] \
                                            [--platforms "ChatGPT,Perplexity,Google AI Overviews"]
  python3 scripts/manage_prompts.py update   --topic-id <tid> --prompt-id <pid> --content "..."
  python3 scripts/manage_prompts.py delete   --topic-id <tid> --prompt-id <pid>
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post, api_put, api_delete,
    extract_data, print_json,
)

parser = argparse.ArgumentParser(description="Manage GEO prompts")
parser.add_argument("action", choices=["list", "list-all", "get", "create", "update", "delete"])
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--topic-id",   help="Topic ID")
parser.add_argument("--prompt-id",  help="Prompt ID (required for update/delete)")
parser.add_argument("--content",    help="Prompt text content")
parser.add_argument("--language",   default="English (en-US)", help="Language (default: English (en-US))")
parser.add_argument("--region",     default="US", help="Region code (default: US)")
parser.add_argument("--platforms",  help="Comma-separated platform IDs (e.g. openai,perplexity,google_aio)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

def _fmt_platforms(platforms_list):
    if not platforms_list:
        return "—"
    return ", ".join(platforms_list)[:60]

# ── LIST (by topic) ───────────────────────────────────────────────────────────
if args.action == "list":
    if not args.topic_id:
        print("ERROR: --topic-id is required for list")
        sys.exit(1)
    result = api_get(f"/api/projects/{pid}/topics/{args.topic_id}/prompts", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else data.get("items") or data.get("prompts") or []
    if args.json:
        print_json(data)
        sys.exit(0)
    print(f"Prompts for topic {args.topic_id}  ({len(items)} found)")
    print()
    for p in items:
        print(f"  ID: {p.get('id', '')[:36]}")
        content = p.get("content", "")
        print(f"  {content[:120]}{'...' if len(content) > 120 else ''}")
        print(f"  Platforms: {_fmt_platforms(p.get('platforms'))}")
        print()

# ── LIST-ALL (project-wide) ───────────────────────────────────────────────────
elif args.action == "list-all":
    result = api_get(f"/api/projects/{pid}/prompts", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else data.get("items") or data.get("prompts") or []
    if args.json:
        print_json(data)
        sys.exit(0)
    total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
    print(f"All prompts in project {pid}  ({total} found)")
    print()
    for p in items:
        content = p.get("content", "")
        print(f"  [{p.get('id', '')[:36]}]  {content[:100]}{'...' if len(content) > 100 else ''}")

# ── GET (detail) ──────────────────────────────────────────────────────────────
elif args.action == "get":
    if not args.topic_id or not args.prompt_id:
        print("ERROR: --topic-id and --prompt-id are required for get")
        sys.exit(1)
    result = api_get(
        f"/api/projects/{pid}/topics/{args.topic_id}/prompts/{args.prompt_id}",
        key, base,
    )
    prompt = extract_data(result) or {}
    if args.json:
        print_json(prompt)
        sys.exit(0)
    print(f"Prompt detail: {args.prompt_id}")
    print()
    print(f"  Content   : {prompt.get('content', '')}")
    print(f"  Language  : {prompt.get('language', '--')}")
    print(f"  Region    : {prompt.get('region', '--')}")
    print(f"  Platforms : {_fmt_platforms(prompt.get('platforms'))}")
    print(f"  Created   : {prompt.get('created_at', '--')}")

# ── CREATE ────────────────────────────────────────────────────────────────────
elif args.action == "create":
    if not args.topic_id:
        print("ERROR: --topic-id is required for create")
        sys.exit(1)
    if not args.content:
        print("ERROR: --content is required for create")
        sys.exit(1)
    body = {
        "content":  args.content,
        "language": args.language,
        "region":   args.region,
    }
    if args.platforms:
        body["platforms"] = [p.strip() for p in args.platforms.split(",") if p.strip()]
    result = api_post(f"/api/projects/{pid}/topics/{args.topic_id}/prompts", key, base, body)
    prompt = extract_data(result)
    if args.json:
        print_json(prompt)
        sys.exit(0)
    print(f"✓  Created prompt")
    print(f"   ID      : {prompt.get('id')}")
    print(f"   Content : {prompt.get('content', '')[:100]}")

# ── UPDATE ────────────────────────────────────────────────────────────────────
elif args.action == "update":
    if not args.topic_id or not args.prompt_id:
        print("ERROR: --topic-id and --prompt-id are required for update")
        sys.exit(1)
    if not args.content:
        print("ERROR: --content is required for update")
        sys.exit(1)
    body = {"content": args.content}
    result = api_put(
        f"/api/projects/{pid}/topics/{args.topic_id}/prompts/{args.prompt_id}",
        key, base, body
    )
    prompt = extract_data(result)
    if args.json:
        print_json(prompt)
        sys.exit(0)
    print(f"✓  Updated prompt {args.prompt_id}")
    print(f"   Content : {prompt.get('content', '')[:100]}")

# ── DELETE ────────────────────────────────────────────────────────────────────
elif args.action == "delete":
    if not args.topic_id or not args.prompt_id:
        print("ERROR: --topic-id and --prompt-id are required for delete")
        sys.exit(1)
    api_delete(
        f"/api/projects/{pid}/topics/{args.topic_id}/prompts/{args.prompt_id}",
        key, base
    )
    print(f"✓  Deleted prompt {args.prompt_id}")
