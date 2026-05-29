#!/usr/bin/env python3
"""Retrieve project-level citation aggregate metrics.

Returns citation count, citation share, and global citation ranking
for a given time window, with automatic previous-period comparison.

Usage:
  python3 scripts/get_aggregate.py [--start-date 2025-02-22] [--end-date 2025-03-14]
  python3 scripts/get_aggregate.py --platform chatgpt,perplexity
  python3 scripts/get_aggregate.py --json
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json

parser = argparse.ArgumentParser(description="View project-level citation aggregate metrics")
parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
parser.add_argument("--start-date", help="Start date (YYYY-MM-DD), default: 7 days ago")
parser.add_argument("--end-date",   help="End date (YYYY-MM-DD), default: today")
parser.add_argument("--platform",   help="Comma-separated platform filter (e.g. chatgpt,perplexity)")
parser.add_argument("--json", action="store_true", help="Output raw JSON")
args = parser.parse_args()

key, base = get_api_config()
pid = get_project_id(args.project_id)

# Build query params
params = {}
if args.start_date:
    params["date_from"] = args.start_date
if args.end_date:
    params["date_to"] = args.end_date
if args.platform:
    params["platform"] = args.platform

result = api_get(
    f"/api/projects/{pid}/analytics/citation/aggregate",
    key, base, params=params,
)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

# Formatted output
date_range = data.get("date_range") or {}
print(f"Citation Aggregate Metrics")
print(f"  Period: {date_range.get('from', '?')} → {date_range.get('to', '?')}")
if date_range.get("platform"):
    print(f"  Platforms: {', '.join(date_range['platform'])}")
print()

# Main metrics
citation_count = data.get("citation_count") or {}
citation_share = data.get("citation_share") or {}
citation_rank  = data.get("citation_rank") or {}
total_citations = data.get("total_citations") or {}


def fmt_change(val):
    if val is None:
        return ""
    if isinstance(val, float):
        sign = "+" if val > 0 else ""
        return f" ({sign}{val:.1f})"
    sign = "+" if val > 0 else ""
    return f" ({sign}{val})"


def fmt_pct(val):
    if val is None:
        return "--"
    return f"{val:.2f}%"


print(f"  Citation Count : {citation_count.get('current', 0)}{fmt_change(citation_count.get('change'))}")
print(f"  Citation Share : {fmt_pct(citation_share.get('current'))}{fmt_change(citation_share.get('change'))}")
print(f"  Citation Rank  : #{citation_rank.get('current', '--')}{fmt_change(citation_rank.get('change'))}")
print(f"  Total (all brands): {total_citations.get('current', 0)}{fmt_change(total_citations.get('change'))}")
print()

# Platform breakdown
by_platform = data.get("by_platform") or []
if by_platform:
    print("  By Platform:")
    for p in by_platform:
        plat = p.get("platform", "?")
        count = p.get("citation_count", 0)
        share = p.get("citation_share")
        share_str = f"{share:.1f}%" if share is not None else "--"
        print(f"    {plat:<16} {count:>5} citations  ({share_str} share)")
    print()

# Competitor ranking
competitors = data.get("competitors") or []
if competitors:
    print("  Brand Citation Ranking:")
    for i, c in enumerate(competitors[:10], 1):
        name = c.get("name", "?")
        count = c.get("citation_count", 0)
        share = c.get("citation_share")
        share_str = f"{share:.1f}%" if share is not None else "--"
        marker = " ← you" if c.get("is_our_brand") else ""
        print(f"    #{i:<2} {name:<20} {count:>5} ({share_str}){marker}")
