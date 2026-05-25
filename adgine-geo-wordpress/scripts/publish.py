#!/usr/bin/env python3
"""Publish a GEO content item (or raw markdown) to WordPress.

Two modes:
  --content-id <uuid>           — publish an existing system article by ID
  --title <t> --content-body <md>
                                — publish raw title + markdown body

Optional:
  --category-ids 1,2,3          — WP category IDs (omitted → Uncategorized)
  --status publish|draft        — publish state (default: publish)

Examples:
  python3 scripts/publish.py --content-id <uuid> --category-ids 2,5
  python3 scripts/publish.py --title "My Post" --content-body "# Hello..." --status draft

Run list_publishable.py first to find content_id candidates.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_post, extract_data, print_json,
)


def main():
    parser = argparse.ArgumentParser(description="Publish content to WordPress")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--content-id", help="System article UUID (content_id mode)")
    parser.add_argument("--title", help="Article title (direct mode)")
    parser.add_argument("--content-body", help="Markdown body (direct mode)")
    parser.add_argument("--category-ids", help="Comma-separated WP category IDs")
    parser.add_argument("--status", default="publish",
                        choices=["publish", "draft"],
                        help="Publish state (default: publish)")
    args = parser.parse_args()

    if not args.content_id and not (args.title and args.content_body):
        print("ERROR: provide either --content-id OR both --title and --content-body.")
        sys.exit(1)

    body = {"status": args.status}
    if args.content_id:
        body["content_id"] = args.content_id
    else:
        body["title"] = args.title
        body["content_body"] = args.content_body
    if args.category_ids:
        body["category_ids"] = [
            int(c.strip()) for c in args.category_ids.split(",") if c.strip()
        ]

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    result = api_post(
        f"/api/projects/{pid}/integrations/wordpress/publish",
        key, base, body=body,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    print("Published to WordPress.")
    for k in ("record_id", "wp_post_id", "wp_post_url", "status",
              "published_at"):
        if k in data:
            print(f"  {k}: {data.get(k)}")


if __name__ == "__main__":
    main()
