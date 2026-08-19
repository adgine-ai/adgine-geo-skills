#!/usr/bin/env python3
"""Refine the selected/latest article version with custom instructions."""
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
    poll_job,
    print_json,
)
from _content_helpers import read_text, selected_version_id, short_id  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Refine an existing GEO article version")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--content-id", help="Content ID; used to auto-select its latest version")
    parser.add_argument("--version-id", help="Explicit article version ID")
    instructions = parser.add_mutually_exclusive_group(required=True)
    instructions.add_argument("--instructions", help="Refinement instructions")
    instructions.add_argument("--instructions-file", help="Text file containing refinement instructions")
    parser.add_argument("--show-article", action="store_true", help="Print the refined full article")
    parser.add_argument("--json", action="store_true", help="Output final job JSON")
    args = parser.parse_args()

    if not args.content_id and not args.version_id:
        parser.error("provide --content-id or --version-id")

    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    root = f"/api/projects/{project_id}/content"
    version_id = args.version_id
    if not version_id:
        content = extract_data(api_get(f"{root}/{args.content_id}", key, base)) or {}
        version_id = selected_version_id(content)
        if not version_id:
            parser.error("this content has no article version to refine")

    if args.instructions_file:
        try:
            custom_instructions = read_text(args.instructions_file, "instructions file")
        except ValueError as exc:
            parser.error(str(exc))
    else:
        custom_instructions = args.instructions

    print(f"Starting article refinement for version {short_id(version_id)}...")
    result = api_post(
        f"{root}/refine-article",
        key,
        base,
        {"version_id": version_id, "custom_instructions": custom_instructions},
    )
    job = extract_data(result) or {}
    job_id = job.get("id") or job.get("job_id")
    if not job_id:
        print("ERROR: refine-article did not return a job ID")
        print_json(job)
        sys.exit(1)
    final_job = poll_job(f"{root}/jobs/{job_id}", key, base, interval=10, max_wait=900)
    if args.json:
        print_json(final_job)
        return
    if final_job.get("status") == "failed":
        print(f"ERROR: article refinement failed — {final_job.get('error') or 'unknown error'}")
        sys.exit(1)
    content_id = final_job.get("content_id") or args.content_id
    print("Article refinement completed.")
    print(f"  Version : {short_id(version_id)}")
    if content_id and args.show_article:
        content = extract_data(api_get(
            f"{root}/{content_id}", key, base, params={"version_id": version_id}
        )) or {}
        full_content = content.get("full_content") or content.get("article_body") or ""
        if full_content:
            print(f"\n{full_content}")


if __name__ == "__main__":
    main()
