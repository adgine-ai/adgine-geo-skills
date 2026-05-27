#!/usr/bin/env python3
"""List, inspect and retry content generation jobs (outline + article workflows).

Subcommands:
  list-outline                          — list outline-generation jobs
  list-article                          — list article-generation jobs
  list-workflow                         — list combined workflow jobs (jobs)
  get-outline   --job-id <id>           — outline-jobs/{id}
  get-article   --job-id <id>           — article-jobs/{id}
  get-workflow  --job-id <id>           — jobs/{id}  (overall workflow)
  retry         --job-id <id>           — retry a failed workflow job

Usage examples:
  python3 scripts/manage_jobs.py list-outline
  python3 scripts/manage_jobs.py get-article --job-id <id>
  python3 scripts/manage_jobs.py retry --job-id <id>
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
    extract_data, print_json, truncate,
    pad,
)


def _norm_status(s):
    s = (s or "").lower()
    if s in ("completed", "complete", "success", "done"):
        return "Completed"
    if s in ("failed", "error"):
        return "Failed"
    if s in ("running", "generating", "in_progress"):
        return "Generating"
    if s in ("pending", "queued", "created"):
        return "Pending"
    return s.title() if s else "--"


def _print_list(items, args, title):
    if args.json:
        print_json(items)
        return
    print(f"{title}  (page {args.page}, limit {args.limit})")
    print()
    if not items:
        print("No jobs found.")
        return
    print("```")
    print("┌──────────────────────────────────────┬──────────────┬──────────────────────┐")
    print("│ Job ID                               │ Status       │ Created at           │")
    print("├──────────────────────────────────────┼──────────────┼──────────────────────┤")
    for j in items:
        jid = truncate(j.get("id") or j.get("job_id"), 36)
        st = _norm_status(j.get("status"))
        created = truncate(j.get("created_at") or "--", 20)
        print(f"│ {pad(jid, 36)} │ {pad(st, 12)} │ {pad(created, 20)} │")
    print("└──────────────────────────────────────┴──────────────┴──────────────────────┘")
    print("```")


def _print_detail(data, args, title):
    if args.json:
        print_json(data)
        return
    print(f"{title}: {args.job_id}")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────────────┐")
    print("│ Field              │ Value                                │")
    print("├────────────────────┼──────────────────────────────────────┤")
    for k in ("status", "current_phase", "progress", "content_id",
              "topic_id", "created_at", "started_at", "completed_at",
              "error_message"):
        if k in data:
            val = data.get(k)
            if k == "status":
                val = _norm_status(val)
            print(f"│ {pad(k, 18)} │ {pad(truncate(val, 36), 36)} │")
    print("└────────────────────┴──────────────────────────────────────┘")
    print("```")


def cmd_list_outline(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/outline-jobs", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("jobs") or (data or {}).get("items", [])
    _print_list(items, args, "Outline jobs")


def cmd_list_article(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/article-jobs", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("jobs") or (data or {}).get("items", [])
    _print_list(items, args, "Article jobs")


def cmd_list_workflow(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/jobs", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("jobs") or (data or {}).get("items", [])
    _print_list(items, args, "Workflow jobs")


def cmd_get_outline(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/outline-jobs/{args.job_id}", key, base)
    data = extract_data(result) or {}
    _print_detail(data, args, "Outline job")


def cmd_get_article(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/article-jobs/{args.job_id}", key, base)
    data = extract_data(result) or {}
    _print_detail(data, args, "Article job")


def cmd_get_workflow(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/content/jobs/{args.job_id}", key, base)
    data = extract_data(result) or {}
    _print_detail(data, args, "Workflow job")


def cmd_retry(args, key, base, pid):
    result = api_post(f"/api/projects/{pid}/content/jobs/{args.job_id}/retry", key, base)
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Retried job: {args.job_id}")
    if isinstance(data, dict) and data.get("status"):
        print(f"  Status: {_norm_status(data.get('status'))}")


def main():
    parser = argparse.ArgumentParser(description="Manage content generation jobs")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for sub_name, _path, _title in [
        ("list-outline",  "/content/outline-jobs", "Outline jobs"),
        ("list-article",  "/content/article-jobs", "Article jobs"),
        ("list-workflow", "/content/jobs",         "Workflow jobs"),
    ]:
        p = sub.add_parser(sub_name)
        p.add_argument("--page", type=int, default=1)
        p.add_argument("--limit", type=int, default=20)

    for sub_name, _path, _title in [
        ("get-outline",  "/content/outline-jobs", "Outline job"),
        ("get-article",  "/content/article-jobs", "Article job"),
        ("get-workflow", "/content/jobs",         "Workflow job"),
    ]:
        p = sub.add_parser(sub_name)
        p.add_argument("--job-id", required=True)

    p_retry = sub.add_parser("retry", help="Retry a failed workflow job")
    p_retry.add_argument("--job-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "list-outline": cmd_list_outline,
        "list-article": cmd_list_article,
        "list-workflow": cmd_list_workflow,
        "get-outline": cmd_get_outline,
        "get-article": cmd_get_article,
        "get-workflow": cmd_get_workflow,
        "retry": cmd_retry,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
