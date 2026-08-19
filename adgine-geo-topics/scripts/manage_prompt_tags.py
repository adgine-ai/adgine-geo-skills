#!/usr/bin/env python3
"""Manage project Prompt tags and cross-Topic batch Prompt operations.

Examples:
  python3 scripts/manage_prompt_tags.py list
  python3 scripts/manage_prompt_tags.py create --name "Purchase intent"
  python3 scripts/manage_prompt_tags.py update --tag "Purchase intent" --name "Commercial"
  python3 scripts/manage_prompt_tags.py assign --tag "Commercial" --prompt-ids <id1,id2>
  python3 scripts/manage_prompt_tags.py batch-delete --prompt-ids <id1,id2> --yes
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import (  # noqa: E402
    _do_request,
    api_delete,
    api_get,
    api_post,
    api_put,
    extract_data,
    get_api_config,
    get_project_id,
    print_json,
)


def _csv(value):
    return list(dict.fromkeys(
        item.strip() for item in (value or "").split(",") if item.strip()
    ))


def _list_tags(key, base, project_id):
    result = api_get(f"/api/projects/{project_id}/prompts/tags", key, base)
    data = extract_data(result) or {}
    return data if isinstance(data, list) else data.get("items") or []


def _resolve_tag(reference, key, base, project_id):
    reference_key = reference.strip().casefold()
    matches = [
        tag for tag in _list_tags(key, base, project_id)
        if str(tag.get("id") or "").casefold() == reference_key
        or str(tag.get("name") or "").casefold() == reference_key
    ]
    if len(matches) != 1:
        print(f"ERROR: tag reference matched {len(matches)} records; use an exact name or tag ID")
        sys.exit(1)
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description="Manage Prompt tags and batch Prompt deletion")
    parser.add_argument(
        "action",
        choices=["list", "get", "create", "update", "delete", "assign", "batch-delete"],
    )
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--tag", help="Exact current tag name or tag ID")
    parser.add_argument("--name", help="Tag name for create, or replacement name for update")
    parser.add_argument("--prompt-ids", help="Comma-separated Prompt IDs")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive deletion")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    root = f"/api/projects/{project_id}/prompts"

    if args.action == "list":
        items = _list_tags(key, base, project_id)
        if args.json:
            print_json(items)
            return
        print(f"Prompt tags ({len(items)}):")
        for index, tag in enumerate(items, 1):
            print(f"  {index:>2}. {tag.get('name') or '(unnamed)'}")
        return

    if args.action == "create":
        if not args.name:
            parser.error("--name is required for create")
        data = extract_data(api_post(f"{root}/tags", key, base, {"name": args.name})) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Created Prompt tag: {data.get('name') or args.name}")
        return

    if args.action == "batch-delete":
        prompt_ids = _csv(args.prompt_ids)
        if not prompt_ids:
            parser.error("--prompt-ids is required for batch-delete")
        if not args.yes:
            print(f"About to delete {len(prompt_ids)} Prompt(s) across Topics. Re-run with --yes to confirm.")
            return
        result = _do_request(
            "DELETE",
            f"{base}{root}/batch",
            key,
            {"prompt_ids": prompt_ids},
        )
        data = extract_data(result) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Deleted {data.get('deleted_count', len(prompt_ids))} Prompt(s).")
        return

    if not args.tag:
        parser.error(f"--tag is required for {args.action}")
    tag = _resolve_tag(args.tag, key, base, project_id)
    tag_id = tag.get("id")

    if args.action == "get":
        data = extract_data(api_get(f"{root}/tags/{tag_id}", key, base)) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Prompt tag: {data.get('name') or tag.get('name')}")
            print(f"  Created: {data.get('created_at') or '—'}")
            print(f"  Updated: {data.get('updated_at') or '—'}")
        return

    if args.action == "update":
        if not args.name:
            parser.error("--name is required for update")
        data = extract_data(api_put(f"{root}/tags/{tag_id}", key, base, {"name": args.name})) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Updated Prompt tag: {tag.get('name')} -> {data.get('name') or args.name}")
        return

    if args.action == "assign":
        prompt_ids = _csv(args.prompt_ids)
        if not prompt_ids:
            parser.error("--prompt-ids is required for assign")
        data = extract_data(api_post(
            f"{root}/tags/{tag_id}/prompts",
            key,
            base,
            {"prompt_ids": prompt_ids},
        )) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Assigned {data.get('assigned_count', 0)} new Prompt(s) to tag {tag.get('name')}.")
        return

    if not args.yes:
        print(f"About to delete Prompt tag {tag.get('name')}. Re-run with --yes to confirm.")
        return
    api_delete(f"{root}/tags/{tag_id}", key, base)
    print(f"Deleted Prompt tag: {tag.get('name')}")


if __name__ == "__main__":
    main()
