#!/usr/bin/env python3
"""Fetch the lightweight 7-day brand visibility snapshot.

Returns current visibility score, 7-day daily trend and period-over-period change.

Usage:
  python3 scripts/get_visibility_overview.py [--project-id <id>] \\
      [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id, api_get, extract_data, print_json, fmt_change,
    pad,
)


def _fmt_score(n):
    if n is None:
        return "--"
    try:
        return f"{float(n):.1f}"
    except (TypeError, ValueError):
        return str(n)


def main():
    parser = argparse.ArgumentParser(description="Fetch GEO visibility overview")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--start-date", help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", help="End date YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    params = {}
    if args.start_date:
        params["start_date"] = args.start_date
    if args.end_date:
        params["end_date"] = args.end_date

    result = api_get(
        f"/api/projects/{pid}/dashboard/visibility",
        key, base,
        params=params or None,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    current = data.get("current_score")
    change = data.get("change") or data.get("score_change")
    trend = data.get("daily_scores") or data.get("trend") or []

    print(f"Visibility Overview")
    print(f"Project: {pid}")
    print()

    print("```")
    print("┌────────────────────────┬──────────┐")
    print("│ Metric                 │    Value │")
    print("├────────────────────────┼──────────┤")
    print(f"│ Current Score          │ {_fmt_score(current):>8} │")
    print(f"│ Change vs Prev         │ {fmt_change(change):>8} │")
    print("└────────────────────────┴──────────┘")
    print("```")
    print()

    if trend:
        print("7-Day Trend")
        print("```")
        print("┌────────────┬──────────┐")
        print("│ Date       │    Score │")
        print("├────────────┼──────────┤")
        for point in trend[:14]:
            date = str(point.get("date", "--"))[:10]
            score = _fmt_score(point.get("score"))
            print(f"│ {pad(date, 10)} │ {score:>8} │")
        print("└────────────┴──────────┘")
        print("```")
    else:
        print("No daily trend data available for the requested range.")


if __name__ == "__main__":
    main()
