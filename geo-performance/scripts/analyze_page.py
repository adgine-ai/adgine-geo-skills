#!/usr/bin/env python3
"""Fetch the AI-agent page health report for a specific URL path.

Retrieves GEO platform health metrics (crawlability, AI optimization score,
indexing status, content issues) for a page within a project.

Usage:
  python3 scripts/analyze_page.py --path /blog/my-article [--project-id <id>] [--json]
  python3 scripts/analyze_page.py --path /                          # homepage
  python3 scripts/analyze_page.py --path /pricing --refresh         # force re-analysis
  python3 scripts/analyze_page.py --path /pricing --strategy desktop
"""
import sys
import os
import argparse
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, api_post, extract_data, print_json

parser = argparse.ArgumentParser(description="GEO AI-agent page health analysis")
parser.add_argument("--path",       required=True,
                    help="URL path to analyze, e.g. /blog/my-article or https://example.com/path")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--strategy",   default="mobile", choices=["mobile", "desktop"],
                    help="Device strategy for health check: mobile (default) or desktop")
parser.add_argument("--refresh",    action="store_true",
                    help="Force a fresh health analysis (POST refresh instead of GET cached)")
parser.add_argument("--json",       action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

# Accept either a full URL (https://example.com/path) or just the path (/path)
page_path = args.path
parsed = urllib.parse.urlparse(args.path)
if parsed.scheme in ("http", "https"):
    page_path = parsed.path or "/"

query_params = {"path": page_path, "strategy": args.strategy}

if args.refresh:
    print(f"Refreshing page health for: {page_path}  (strategy: {args.strategy}, project: {pid})")
    result = api_post(
        f"/api/projects/{pid}/ai-agent/pages/by-path/health/refresh",
        key, base,
        params=query_params,
    )
else:
    print(f"Fetching page health for: {page_path}  (strategy: {args.strategy}, project: {pid})")
    result = api_get(
        f"/api/projects/{pid}/ai-agent/pages/by-path/health",
        key, base,
        params=query_params,
    )

data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

# ── Human-readable output ─────────────────────────────────────────────────────
print(f"\nPage Health Report")
print(f"  Path    : {page_path}")
print(f"  Project : {pid}")
print()

if not data:
    print("  No data returned. The page may not be indexed yet.")
    sys.exit(0)

# Support both a list of metrics and a single report object
metrics = data if isinstance(data, list) else data.get("metrics") or [data]

for metric in metrics:
    check   = metric.get("check") or metric.get("name") or metric.get("type") or ""
    status  = metric.get("status") or metric.get("result") or ""
    score   = metric.get("score")
    message = metric.get("message") or metric.get("description") or ""
    rec     = metric.get("recommendation") or metric.get("fix") or ""

    icon = {"pass": "✓", "fail": "✗", "warning": "⚠", "info": "ℹ"}.get(
        status.lower() if status else "", "·"
    )

    line = f"  {icon} {check:<40}"
    if score is not None:
        line += f"  score: {score}"
    if status:
        line += f"  [{status}]"
    print(line)

    if message:
        print(f"      {message[:120]}")
    if rec:
        print(f"      → {rec[:120]}")

print()
