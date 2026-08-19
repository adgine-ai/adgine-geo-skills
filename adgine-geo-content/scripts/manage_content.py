#!/usr/bin/env python3
"""Inspect and partially update GEO content and article versions.

Omitted edit fields are not sent, so GEO-Api retains their current values. For
version-level edits and publish status changes, the current selected/latest
version is resolved automatically when ``--version-id`` is omitted.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import (  # noqa: E402
    api_delete,
    api_get,
    api_patch,
    extract_data,
    get_api_config,
    get_project_id,
    print_json,
)
from _content_helpers import read_text, selected_version_id, short_id  # noqa: E402


def _get_content(root, content_id, key, base, version_id=None):
    params = {"version_id": version_id} if version_id else None
    return extract_data(api_get(f"{root}/{content_id}", key, base, params=params)) or {}


def _version_for(content, explicit_version_id, parser):
    version_id = explicit_version_id or selected_version_id(content)
    if not version_id:
        parser.error("this content has no article version yet")
    return version_id


def _print_content(item):
    print(f"Content: {item.get('article_title') or '(untitled)'}")
    print(f"  Stage          : {item.get('status') or '—'}")
    print(f"  Publish status : {item.get('publish_status') or '—'}")
    print(f"  Selected ver.  : {short_id(item.get('selected_version_id'))}")
    print(f"  Language       : {(item.get('versions') or [{}])[0].get('language') or '—'}")
    print(f"  Words          : {item.get('word_count', 0)}")
    print(f"  Meta title     : {item.get('meta_title') or '—'}")
    print(f"  Meta desc      : {item.get('meta_description') or '—'}")
    print(f"  Slug           : {item.get('meta_slug') or '—'}")
    print(f"  Cover URL      : {item.get('cover_image_url') or '—'}")
    body = item.get("full_content") or item.get("article_body") or ""
    if body:
        print("\n  --- article preview ---")
        for line in body[:600].splitlines():
            print(f"  {line}")
        if len(body) > 600:
            print(f"  [... truncated, {len(body)} chars total ...]")


def main():
    parser = argparse.ArgumentParser(description="Manage GEO content and article versions")
    parser.add_argument(
        "action",
        choices=[
            "get", "edit", "publish-status", "versions", "get-version",
            "delete-version", "delete",
        ],
    )
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--content-id", required=True, help="Content ID")
    parser.add_argument("--version-id", help="Article version ID; latest is selected automatically")
    parser.add_argument("--title", help="New article title")
    parser.add_argument("--outline-file", help="Markdown file containing a replacement page outline")
    parser.add_argument("--body-file", help="Markdown file containing replacement full_content")
    parser.add_argument("--meta-title", help="Replacement SEO title")
    parser.add_argument("--meta-description", help="Replacement meta description")
    parser.add_argument("--meta-slug", help="Replacement shared URL slug")
    parser.add_argument("--schema-file", help="JSON file containing replacement schema.org markup")
    parser.add_argument("--cover-image-url", help="Replacement cover image URL")
    parser.add_argument("--cover-image-alt", help="Replacement cover image alt text")
    parser.add_argument("--status", choices=["unpublished", "published"],
                        help="Publish status for the publish-status action")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    root = f"/api/projects/{project_id}/content"

    if args.action == "get":
        item = _get_content(root, args.content_id, key, base, args.version_id)
        if args.json:
            print_json(item)
        else:
            _print_content(item)
        return

    if args.action == "versions":
        data = extract_data(api_get(f"{root}/{args.content_id}/versions", key, base)) or {}
        if args.json:
            print_json(data)
            return
        items = data.get("items") or []
        print(f"Article versions ({len(items)}):")
        for index, version in enumerate(items, 1):
            print(
                f"  {index:>2}. v{version.get('version_no') or '?'}  "
                f"{version.get('language') or '—'}  {version.get('word_count', 0)} words  "
                f"{version.get('publish_status') or '—'}"
            )
        return

    current = _get_content(root, args.content_id, key, base)

    if args.action == "get-version":
        version_id = _version_for(current, args.version_id, parser)
        data = extract_data(api_get(
            f"{root}/{args.content_id}/versions/{version_id}", key, base
        )) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Article version v{data.get('version_no') or '?'} ({data.get('language') or '—'})")
            print(f"  Status : {data.get('publish_status') or '—'}")
            print(f"  Words  : {data.get('word_count', 0)}")
            print(f"  Cover  : {data.get('cover_image_url') or '—'}")
            body = data.get("full_content") or data.get("article_body") or ""
            if body:
                print(f"\n{body}")
        return

    if args.action == "edit":
        body = {}
        if args.title is not None:
            body["article_title"] = args.title
        if args.outline_file:
            try:
                body["page_outline"] = read_text(args.outline_file, "outline file")
            except ValueError as exc:
                parser.error(str(exc))
        if args.body_file:
            try:
                body["full_content"] = read_text(args.body_file, "body file")
            except ValueError as exc:
                parser.error(str(exc))
        for argument, field in (
            (args.meta_title, "meta_title"),
            (args.meta_description, "meta_description"),
            (args.meta_slug, "meta_slug"),
            (args.cover_image_url, "cover_image_url"),
            (args.cover_image_alt, "cover_image_alt"),
        ):
            if argument is not None:
                body[field] = argument
        if args.schema_file:
            try:
                schema_text = read_text(args.schema_file, "schema file")
                schema = json.loads(schema_text)
            except (ValueError, json.JSONDecodeError) as exc:
                parser.error(f"--schema-file must contain valid JSON — {exc}")
            body["schema_markup"] = json.dumps(schema, ensure_ascii=False)
        version_fields = {
            "full_content", "meta_title", "meta_description", "schema_markup",
            "cover_image_url", "cover_image_alt",
        }
        if version_fields.intersection(body):
            body["version_id"] = _version_for(current, args.version_id, parser)
        elif args.version_id:
            parser.error("--version-id only applies to version-level edit fields")
        if not body:
            parser.error("provide at least one edit field; omitted fields retain their current values")
        updated = extract_data(api_patch(
            f"{root}/{args.content_id}", key, base, body
        )) or {}
        if args.json:
            print_json(updated)
        else:
            print(f"Updated content: {updated.get('article_title') or current.get('article_title') or '(untitled)'}")
            if body.get("version_id"):
                print(f"  Version: {short_id(body['version_id'])} (selected automatically if omitted)")
            print("  All omitted fields were retained unchanged.")
        return

    if args.action == "publish-status":
        if not args.status:
            parser.error("--status unpublished|published is required for publish-status")
        version_id = _version_for(current, args.version_id, parser)
        data = extract_data(api_patch(
            f"{root}/{args.content_id}/publish-status",
            key,
            base,
            {"publish_status": args.status, "version_id": version_id},
        )) or {}
        if args.json:
            print_json(data)
        else:
            print(f"Set {current.get('article_title') or '(untitled)'} to {args.status}.")
            print(f"  Version: {short_id(version_id)} (selected automatically if omitted)")
        return

    if args.action == "delete-version":
        version_id = _version_for(current, args.version_id, parser)
        if not args.yes:
            print(f"About to delete article version {short_id(version_id)}. Re-run with --yes to confirm.")
            return
        api_delete(f"{root}/{args.content_id}/versions/{version_id}", key, base)
        print(f"Deleted article version {short_id(version_id)}.")
        return

    if not args.yes:
        print(f"About to delete content {current.get('article_title') or short_id(args.content_id)}. Re-run with --yes to confirm.")
        return
    api_delete(f"{root}/{args.content_id}", key, base)
    print(f"Deleted content: {current.get('article_title') or short_id(args.content_id)}")


if __name__ == "__main__":
    main()
