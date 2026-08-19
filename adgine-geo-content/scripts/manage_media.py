#!/usr/bin/env python3
"""List project media or upload an image and optionally set it as a cover."""
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from _client import (  # noqa: E402
    api_get,
    api_patch,
    extract_data,
    get_api_config,
    get_project_id,
    print_json,
)
from _content_helpers import selected_version_id, short_id  # noqa: E402

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_BYTES = 5 * 1024 * 1024


def _upload_image(path, key, base):
    expanded = os.path.expanduser(path)
    extension = os.path.splitext(expanded)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("image must be JPG, JPEG, PNG, WebP, or GIF")
    try:
        size = os.path.getsize(expanded)
        with open(expanded, "rb") as fh:
            content = fh.read()
    except OSError as exc:
        raise ValueError(f"could not read image {path!r} — {exc}") from exc
    if size > MAX_BYTES:
        raise ValueError("image exceeds GEO-Api's 5 MB upload limit")

    boundary = f"geo-skills-{uuid.uuid4().hex}"
    filename = os.path.basename(expanded).replace('"', "_").replace("\r", "_").replace("\n", "_")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        f"{base}/api/uploads/images",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "geo-skills/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"upload failed with HTTP {exc.code} — {detail}") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ValueError(f"upload failed — {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description="Manage GEO article images")
    parser.add_argument("action", choices=["list", "upload"])
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID)")
    parser.add_argument("--file", help="Local image file for upload")
    parser.add_argument("--content-id", help="Attach uploaded image as this content's cover")
    parser.add_argument("--version-id", help="Target version; latest is selected automatically")
    parser.add_argument("--alt", help="Cover image alt text; defaults to article title or filename")
    parser.add_argument("--q", help="Search media by related content title")
    parser.add_argument("--source", help="Filter media source (e.g. content)")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    project_id = get_project_id(args.project_id)
    if args.action == "list":
        data = extract_data(api_get(
            f"/api/projects/{project_id}/media",
            key,
            base,
            params={"q": args.q, "source": args.source, "page": args.page, "limit": args.limit},
        )) or {}
        if args.json:
            print_json(data)
            return
        items = data.get("items") or []
        print(f"Media images ({len(items)} of {data.get('total', len(items))}):")
        for index, item in enumerate(items, 1):
            print(f"  {index:>2}. {item.get('content_title') or '(unattached image)'}")
            print(f"      URL: {item.get('image_url') or '—'}")
            print(f"      Alt: {item.get('alt_text') or '—'}")
        return

    if not args.file:
        parser.error("--file is required for upload")
    if not args.content_id and (args.version_id or args.alt):
        parser.error("--version-id and --alt require --content-id")
    target_content = None
    target_version_id = None
    target_alt = None
    if args.content_id:
        content_root = f"/api/projects/{project_id}/content/{args.content_id}"
        target_content = extract_data(api_get(content_root, key, base)) or {}
        target_version_id = args.version_id or selected_version_id(target_content)
        if not target_version_id:
            parser.error("the target content has no article version for a cover")
        target_alt = (
            args.alt
            or target_content.get("article_title")
            or os.path.splitext(os.path.basename(args.file))[0]
        )
    try:
        uploaded = extract_data(_upload_image(args.file, key, base)) or {}
    except ValueError as exc:
        parser.error(str(exc))
    image_url = uploaded.get("url")
    if not image_url:
        print("ERROR: upload endpoint did not return an image URL")
        print_json(uploaded)
        sys.exit(1)

    result = {"url": image_url}
    if args.content_id:
        updated = extract_data(api_patch(
            content_root,
            key,
            base,
            {
                "version_id": target_version_id,
                "cover_image_url": image_url,
                "cover_image_alt": target_alt,
            },
        )) or {}
        result.update({"content": updated, "version_id": target_version_id, "alt": target_alt})

    if args.json:
        print_json(result)
        return
    print(f"Uploaded image: {image_url}")
    if args.content_id:
        print(f"  Attached as cover to version {short_id(result['version_id'])}.")
        print(f"  Alt: {result['alt']}")
    else:
        print("  Supply --content-id to attach it as an article cover and add it to project media.")


if __name__ == "__main__":
    main()
