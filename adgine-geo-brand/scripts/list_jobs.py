#!/usr/bin/env python3
"""List, inspect or manually start brand generation jobs.

Subcommands:
  list                                  — list brand jobs (latest first)
  get  --job-id <id>                    — show one job's full status
  start --job-id <id>                   — manually trigger a job that was created with auto_start=false

Usage examples:
  python3 scripts/list_jobs.py list
  python3 scripts/list_jobs.py get --job-id <id>
  python3 scripts/list_jobs.py start --job-id <id>
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
    extract_data, print_json, truncate,
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


def cmd_list(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/brand/jobs", key, base,
                     params={"page": args.page, "limit": args.limit})
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("jobs") or (data or {}).get("items", [])

    if args.json:
        print_json(items)
        return

    print(f"Brand jobs for project {pid}")
    print()
    if not items:
        print("No brand generation jobs yet.")
        return

    print("```")
    print("┌──────────────────────────────────────┬──────────────┬──────────────────────┐")
    print("│ Job ID                               │ Status       │ Created at           │")
    print("├──────────────────────────────────────┼──────────────┼──────────────────────┤")
    for j in items:
        jid = truncate(j.get("id") or j.get("job_id"), 36)
        st = _norm_status(j.get("status"))
        created = truncate(j.get("created_at") or j.get("started_at") or "--", 20)
        print(f"│ {jid:<36} │ {st:<12} │ {created:<20} │")
    print("└──────────────────────────────────────┴──────────────┴──────────────────────┘")
    print("```")


def cmd_get(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/brand/jobs/{args.job_id}", key, base)
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    print(f"Brand job: {args.job_id}")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────────────┐")
    print("│ Field              │ Value                                │")
    print("├────────────────────┼──────────────────────────────────────┤")
    for k in ("status", "current_phase", "progress", "created_at",
              "started_at", "completed_at", "error_message", "url",
              "language", "region"):
        if k in data:
            val = data.get(k)
            if k == "status":
                val = _norm_status(val)
            print(f"│ {k:<18} │ {truncate(val, 36):<36} │")
    print("└────────────────────┴──────────────────────────────────────┘")
    print("```")

    phases = data.get("phases") or []
    if phases:
        print()
        print("Phases")
        print("```")
        print("┌────────────────────────────────┬──────────────┐")
        print("│ Phase                          │ Status       │")
        print("├────────────────────────────────┼──────────────┤")
        for p in phases:
            name = truncate(p.get("name") or p.get("phase"), 30)
            st = _norm_status(p.get("status"))
            print(f"│ {name:<30} │ {st:<12} │")
        print("└────────────────────────────────┴──────────────┘")
        print("```")


def cmd_start(args, key, base, pid):
    result = api_post(
        f"/api/projects/{pid}/brand/jobs/{args.job_id}/start",
        key, base,
    )
    data = extract_data(result)
    if args.json:
        print_json(data if data is not None else {"ok": True})
        return
    print(f"Started brand job: {args.job_id}")
    if isinstance(data, dict) and data.get("status"):
        print(f"  Status: {_norm_status(data.get('status'))}")


def main():
    parser = argparse.ArgumentParser(description="Manage brand generation jobs")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List brand jobs")
    p_list.add_argument("--page", type=int, default=1)
    p_list.add_argument("--limit", type=int, default=20)

    p_get = sub.add_parser("get", help="Get one job's details")
    p_get.add_argument("--job-id", required=True)

    p_start = sub.add_parser("start", help="Manually start a queued job")
    p_start.add_argument("--job-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    if args.command == "list":
        cmd_list(args, key, base, pid)
    elif args.command == "get":
        cmd_get(args, key, base, pid)
    elif args.command == "start":
        cmd_start(args, key, base, pid)


if __name__ == "__main__":
    main()
