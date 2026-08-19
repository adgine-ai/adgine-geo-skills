#!/usr/bin/env python3
"""Generate an AI cover for the selected/latest article version."""
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
from _content_helpers import selected_version_id, short_id  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Generate an AI article cover image")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--content-id", required=True, help="Content ID")
    parser.add_argument("--version-id", help="Version ID; latest is selected automatically")
    parser.add_argument("--prompt", help="Optional custom image prompt")
    parser.add_argument("--include-title", action="store_true", help="Include the article title in image context")
    parser.add_argument("--include-summary", action="store_true", help="Include the meta summary in image context")
    parser.add_argument("--include-body", action="store_true", help="Include article body in image context")
    parser.add_argument("--json", action="store_true", help="Output final job JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    root = f"/api/projects/{project_id}/content"
    content = extract_data(api_get(f"{root}/{args.content_id}", key, base)) or {}
    version_id = args.version_id or selected_version_id(content)
    if not version_id:
        parser.error("this content has no article version for a cover image")

    body = {
        "include_title": args.include_title,
        "include_summary": args.include_summary,
        "include_body": args.include_body,
    }
    if args.prompt:
        body["custom_prompt"] = args.prompt
    print(f"Generating an AI cover for {content.get('article_title') or short_id(args.content_id)}...")
    result = api_post(
        f"{root}/{args.content_id}/versions/{version_id}/generate-cover",
        key,
        base,
        body,
    )
    job = extract_data(result) or {}
    job_id = job.get("id") or job.get("job_id")
    if not job_id:
        print("ERROR: generate-cover did not return a job ID")
        print_json(job)
        sys.exit(1)
    final_job = poll_job(f"{root}/jobs/{job_id}", key, base, interval=10, max_wait=900)
    if args.json:
        print_json(final_job)
        return
    if final_job.get("status") == "failed":
        print(f"ERROR: cover generation failed — {final_job.get('error') or 'unknown error'}")
        sys.exit(1)
    print("AI cover generated and attached to the article version.")
    print(f"  Version : {short_id(version_id)}")
    print(f"  URL     : {final_job.get('cover_image_url') or '—'}")
    print(f"  Alt     : {final_job.get('cover_image_alt') or '—'}")


if __name__ == "__main__":
    main()
