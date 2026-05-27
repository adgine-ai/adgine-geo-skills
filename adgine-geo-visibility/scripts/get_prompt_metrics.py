#!/usr/bin/env python3
"""Per-prompt visibility overview (Visibility Score + Avg Position with
trend, previous-period delta, and per-platform breakdown).

Usage:
  python3 scripts/get_prompt_metrics.py --prompt-id <prompt_id>
  python3 scripts/get_prompt_metrics.py --prompt-id <id> --start 2025-11-01 --end 2025-11-30
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get,
    extract_data, print_json, truncate,
    pad,
)


def _fmt(v):
    if v is None:
        return "--"
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)[:8]


def _fmt_change(c):
    if c is None:
        return "--"
    try:
        f = float(c)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f:.2f}"
    except (TypeError, ValueError):
        return str(c)


def main():
    parser = argparse.ArgumentParser(description="Per-prompt visibility overview")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    params = {}
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end

    result = api_get(
        f"/api/projects/{pid}/analytics/prompts/{args.prompt_id}/overview",
        key, base, params=params or None,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    vs = data.get("visibility_score") or {}
    ap = data.get("average_position") or {}

    print(f"Prompt overview — {args.prompt_id}")
    if data.get("prompt_text"):
        print(f"  text: {truncate(data['prompt_text'], 80)}")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┬──────────────┐")
    print("│ Metric             │      Current │     Previous │       Change │")
    print("├────────────────────┼──────────────┼──────────────┼──────────────┤")
    print(f"│ {pad('Visibility Score', 18)} │ {_fmt(vs.get('current')):>12} │ {_fmt(vs.get('previous')):>12} │ {_fmt_change(vs.get('change')):>12} │")
    print(f"│ {pad('Average Position', 18)} │ {_fmt(ap.get('current')):>12} │ {_fmt(ap.get('previous')):>12} │ {_fmt_change(ap.get('change')):>12} │")
    print("└────────────────────┴──────────────┴──────────────┴──────────────┘")
    print("```")

    by_platform = data.get("by_platform") or data.get("platforms") or []
    if by_platform:
        print()
        print("By platform:")
        print("```")
        print("┌────────────────────┬──────────┬──────────┐")
        print("│ Platform           │   Vis(%) │  AvgPos  │")
        print("├────────────────────┼──────────┼──────────┤")
        for p in by_platform:
            name = truncate(p.get("name") or p.get("platform") or p.get("code"), 18)
            v = _fmt(p.get("visibility_score") or p.get("visibility"))
            a = _fmt(p.get("average_position") or p.get("avg_position"))
            print(f"│ {pad(name, 18)} │ {v:>8} │ {a:>8} │")
        print("└────────────────────┴──────────┴──────────┘")
        print("```")


if __name__ == "__main__":
    main()
