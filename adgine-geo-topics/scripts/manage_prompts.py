#!/usr/bin/env python3
"""List, create, update, or delete prompts within a GEO topic.

Usage:
  python3 scripts/manage_prompts.py list     --topic-id <tid> [--project-id <id>] [--page 1] [--limit 40] [--json]
  python3 scripts/manage_prompts.py list-all [--project-id <id>] [--page 1] [--limit 40] [--json]
  python3 scripts/manage_prompts.py create   --topic-id <tid> --content "What is...?" \
                                            [--language "English"] [--region US] \
                                            [--platforms "ChatGPT,Perplexity,Google AI Overviews"]
  python3 scripts/manage_prompts.py update   --topic-id <tid> --prompt-id <pid> [--content "..."] \
                                            [--language English] [--region US] [--platforms "openai,perplexity"] \
                                            [--types "visibility,sentiment"] [--tag-ids "<id1>,<id2>"]
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
parser.add_argument("--language",   help="Language; create defaults to the Topic/brand value")
parser.add_argument("--region",     help="Region code; create defaults to the Topic/brand value")
parser.add_argument("--platforms",  help="Comma-separated platform IDs (e.g. openai,perplexity,google_aio)")
parser.add_argument("--types",      help="Comma-separated Prompt purposes for update: visibility,sentiment")
parser.add_argument("--clear-types", action="store_true", help="Clear Prompt purpose classification on update")
parser.add_argument("--tag-ids",    help="Comma-separated tag IDs; update replaces the complete tag set")
parser.add_argument("--clear-tags", action="store_true", help="Remove all tags from the Prompt on update")
parser.add_argument("--page", type=int, default=1, help="Page number for list/list-all (default: 1)")
parser.add_argument("--limit", type=int, default=40, help="Rows per page for list/list-all (default: 40)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

def _fmt_platforms(platforms_list):
    if not platforms_list:
        return "—"
    return ", ".join(platforms_list)[:60]


def _csv(value):
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _fmt_tags(tags):
    return ", ".join(
        str(tag.get("name") or tag.get("id") or "") if isinstance(tag, dict) else str(tag)
        for tag in (tags or [])
    ) or "—"

# ── LIST (by topic) ───────────────────────────────────────────────────────────
if args.action == "list":
    if not args.topic_id:
        print("ERROR: --topic-id is required for list")
        sys.exit(1)
    result = api_get(
        f"/api/projects/{pid}/topics/{args.topic_id}/prompts", key, base,
        params={"page": args.page, "limit": args.limit},
    )
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
        print(f"  Types    : {', '.join(p.get('types') or []) or '—'}")
        print(f"  Tags     : {_fmt_tags(p.get('tags'))}")
        print()

# ── LIST-ALL (project-wide) ───────────────────────────────────────────────────
elif args.action == "list-all":
    result = api_get(
        f"/api/projects/{pid}/prompts", key, base,
        params={"page": args.page, "limit": args.limit},
    )
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
    print(f"  Types     : {', '.join(prompt.get('types') or []) or '—'}")
    print(f"  Tags      : {_fmt_tags(prompt.get('tags'))}")
    print(f"  Created   : {prompt.get('created_at', '--')}")

# ── CREATE ────────────────────────────────────────────────────────────────────
elif args.action == "create":
    if not args.topic_id:
        print("ERROR: --topic-id is required for create")
        sys.exit(1)
    if not args.content:
        print("ERROR: --content is required for create")
        sys.exit(1)
    if args.types or args.clear_types or args.tag_ids or args.clear_tags:
        print("ERROR: Prompt types and tags are update-only; create the Prompt first, then update it")
        sys.exit(1)
    body = {"content": args.content}
    if args.language:
        body["language"] = args.language
    if args.region:
        body["region"] = args.region
    if args.platforms:
        body["platforms"] = _csv(args.platforms)
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
    if args.types and args.clear_types:
        print("ERROR: use either --types or --clear-types, not both")
        sys.exit(1)
    if args.tag_ids and args.clear_tags:
        print("ERROR: use either --tag-ids or --clear-tags, not both")
        sys.exit(1)
    body = {}
    if args.content:
        body["content"] = args.content
    if args.language:
        body["language"] = args.language
    if args.region:
        body["region"] = args.region
    if args.platforms:
        body["platforms"] = _csv(args.platforms)
    if args.types:
        prompt_types = _csv(args.types)
        invalid = sorted(set(prompt_types) - {"visibility", "sentiment"})
        if invalid:
            print(f"ERROR: unsupported Prompt types: {', '.join(invalid)}")
            sys.exit(1)
        body["types"] = prompt_types
    elif args.clear_types:
        body["types"] = None
    if args.tag_ids:
        body["tag_ids"] = _csv(args.tag_ids)
    elif args.clear_tags:
        body["tag_ids"] = []
    if not body:
        print("ERROR: provide at least one field to update; omitted fields keep their current values")
        sys.exit(1)
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
