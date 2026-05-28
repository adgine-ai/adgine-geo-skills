#!/usr/bin/env python3
"""Query the status of a SaaS deployment task.

With --poll, this will block and poll every few seconds until the task reaches
a terminal state (completed / failed / success / error).

Usage:
  python3 scripts/get_task.py --task-id <id> [--poll] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, api_get, extract_data, print_json, poll_job, truncate,
    pad,
)


def _norm_status(s):
    s = (s or "").lower()
    if s in ("completed", "complete", "success", "done"):
        return "Completed"
    if s in ("failed", "error"):
        return "Failed"
    if s in ("running", "in_progress", "generating", "deploying"):
        return "Generating"
    if s in ("pending", "queued", "created"):
        return "Pending"
    return s.title() if s else "--"


def main():
    parser = argparse.ArgumentParser(description="Query SaaS deployment task status")
    parser.add_argument("--task-id", required=True, help="Task ID returned by create_website.py")
    parser.add_argument("--poll", action="store_true", help="Block and poll until terminal")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()

    if args.poll:
        data = poll_job(f"/api/saas/task/{args.task_id}", key, base) or {}
    else:
        result = api_get(f"/api/saas/task/{args.task_id}", key, base)
        data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    norm_status = _norm_status(data.get('status'))

    print(f"SaaS task: {args.task_id}")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────┐")
    print("│ Field              │ Value                        │")
    print("├────────────────────┼──────────────────────────────┤")
    print(f"│ {pad('status', 18)} │ {pad(norm_status, 28)} │")
    for k in ("phase", "current_phase", "progress", "url", "subdomain",
              "started_at", "completed_at", "error_message"):
        if k in data:
            print(f"│ {pad(k, 18)} │ {pad(truncate(data.get(k), 28), 28)} │")
    print("└────────────────────┴──────────────────────────────┘")
    print("```")

    # When deployment succeeds, show WordPress login credentials
    if norm_status == "Completed":
        domain = data.get("domain", "")
        wp_user = data.get("wp_username", "")
        wp_pass = data.get("wp_password", "")
        if domain and (wp_user or wp_pass):
            wp_login_url = f"https://{domain}/wp-login.php"
            print()
            print("🎉 Your website is live! WordPress login details:")
            print()
            print("```")
            print("┌────────────────────┬──────────────────────────────┐")
            print("│ WordPress          │ Info                         │")
            print("├────────────────────┼──────────────────────────────┤")
            print(f"│ {pad('login URL', 18)} │ {pad(truncate(wp_login_url, 28), 28)} │")
            if wp_user:
                print(f"│ {pad('username', 18)} │ {pad(truncate(wp_user, 28), 28)} │")
            if wp_pass:
                print(f"│ {pad('password', 18)} │ {pad(truncate(wp_pass, 28), 28)} │")
            print("└────────────────────┴──────────────────────────────┘")
            print("```")


if __name__ == "__main__":
    main()
