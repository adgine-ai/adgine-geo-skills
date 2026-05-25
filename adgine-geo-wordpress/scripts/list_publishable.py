#!/usr/bin/env python3
"""List articles that are ready to publish to WordPress.

Returns content items with completed full_content (max 50). Use the IDs from
this list with publish.py --content-id <id>.

Usage:
  python3 scripts/list_publishable.py [--project-id <id>] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, extract_data, print_json, truncate,
)


def main():
    parser = argparse.ArgumentParser(description="List publishable content for WordPress")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    result = api_get(
        f"/api/projects/{pid}/integrations/wordpress/publishable-content",
        key, base,
    )
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("items") or (data or {}).get("content", [])

    if args.json:
        print_json(items)
        return

    if not items:
        print("No publishable content yet. Generate articles first (see adgine-geo-content).")
        return

    print(f"Publishable content ({len(items)})")
    print()
    print("```")
    print("┌────┬──────────────────────────────────────┬──────────────────────────────────────┐")
    print("│  # │ Content ID                           │ Title                                │")
    print("├────┼──────────────────────────────────────┼──────────────────────────────────────┤")
    for i, c in enumerate(items, 1):
        cid = truncate(c.get("id") or c.get("content_id"), 36)
        title = truncate(c.get("title") or "(untitled)", 36)
        print(f"│ {i:>2} │ {cid:<36} │ {title:<36} │")
    print("└────┴──────────────────────────────────────┴──────────────────────────────────────┘")
    print("```")


if __name__ == "__main__":
    main()
