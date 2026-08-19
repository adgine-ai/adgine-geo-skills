#!/usr/bin/env python3
"""List, inspect, or retry unified GEO content workflow jobs.

GEO-Api now exposes one job collection for outline, article, refine, and cover
workflows. The legacy command names remain as aliases, but all of them call
``/content/jobs``.

Examples:
  python3 scripts/manage_jobs.py list --workflow-type outline
  python3 scripts/manage_jobs.py get --job-id <id>
  python3 scripts/manage_jobs.py retry --job-id <id>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import (  # noqa: E402
    api_get,
    api_post,
    extract_data,
    get_api_config,
    get_project_id,
    print_json,
)


def _short(value):
    text = str(value or "")
    return f"{text[:8]}…" if len(text) > 8 else (text or "—")


def _print_list(data, args, workflow_type):
    if args.json:
        print_json(data)
        return
    items = data if isinstance(data, list) else (data or {}).get("items") or []
    total = (data or {}).get("total", len(items)) if isinstance(data, dict) else len(items)
    label = workflow_type or "all"
    print(f"Content workflow jobs: {len(items)} of {total} (type={label}, page={args.page})")
    for index, job in enumerate(items, 1):
        print(
            f"  {index:>2}. {_short(job.get('id'))}  "
            f"{job.get('workflow_type') or '—'}  {job.get('status') or '—'}  "
            f"{job.get('progress', 0)}%"
        )


def _print_detail(data, raw_json=False):
    if raw_json:
        print_json(data)
        return
    print(f"Content task {_short(data.get('id'))}")
    print(f"  Type      : {data.get('workflow_type') or '—'}")
    print(f"  Status    : {data.get('status') or '—'}")
    print(f"  Progress  : {data.get('progress', 0)}%")
    print(f"  Content   : {_short(data.get('content_id'))}")
    print(f"  Topic     : {_short(data.get('topic_id'))}")
    if data.get("cover_image_url"):
        print(f"  Cover URL : {data.get('cover_image_url')}")
        print(f"  Cover alt : {data.get('cover_image_alt') or '—'}")
    if data.get("error"):
        print(f"  Error     : {data.get('error')}")
    print(f"  Created   : {data.get('created_at') or '—'}")
    print(f"  Completed : {data.get('completed_at') or '—'}")


def main():
    parser = argparse.ArgumentParser(description="Manage unified content workflow jobs")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_trailing_common(item):
        item.add_argument(
            "--project-id", dest="project_id", default=argparse.SUPPRESS,
            help="Project ID (may also appear before the command)",
        )
        item.add_argument(
            "--json", action="store_true", default=argparse.SUPPRESS,
            help="Output raw JSON (may also appear before the command)",
        )

    list_commands = ("list", "list-workflow", "list-outline", "list-article")
    for command in list_commands:
        item = sub.add_parser(command)
        add_trailing_common(item)
        item.add_argument("--page", type=int, default=1)
        item.add_argument("--limit", type=int, default=40)
        item.add_argument("--topic-id", help="Filter by Topic ID")
        if command in ("list", "list-workflow"):
            item.add_argument(
                "--workflow-type",
                choices=["outline", "article", "refine", "cover_image"],
                help="Filter by workflow type",
            )

    for command in ("get", "get-workflow", "get-outline", "get-article"):
        item = sub.add_parser(command)
        add_trailing_common(item)
        item.add_argument("--job-id", required=True)

    retry = sub.add_parser("retry", help="Retry a failed workflow job")
    add_trailing_common(retry)
    retry.add_argument("--job-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    root = f"/api/projects/{project_id}/content/jobs"

    if args.command in list_commands:
        workflow_type = {
            "list-outline": "outline",
            "list-article": "article",
        }.get(args.command, getattr(args, "workflow_type", None))
        params = {
            "page": args.page,
            "limit": args.limit,
            "workflow_type": workflow_type,
            "topic_id": args.topic_id,
        }
        data = extract_data(api_get(root, key, base, params=params)) or {}
        _print_list(data, args, workflow_type)
        return

    if args.command.startswith("get"):
        data = extract_data(api_get(f"{root}/{args.job_id}", key, base)) or {}
        _print_detail(data, raw_json=args.json)
        return

    data = extract_data(api_post(f"{root}/{args.job_id}/retry", key, base)) or {}
    if args.json:
        print_json(data)
    else:
        print(f"Retried content task {_short(args.job_id)}")
        print(f"  Status   : {data.get('status') or '—'}")
        print(f"  Progress : {data.get('progress', 0)}%")


if __name__ == "__main__":
    main()
