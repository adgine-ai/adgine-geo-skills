#!/usr/bin/env python3
"""Competitor × AI-platform matrix (Visibility Score or Share of Voice).

Shows a grid of competitor brands (rows) × AI platforms (cols), with the
chosen metric in each cell. Useful for "我的品牌在 ChatGPT/Perplexity 上
跟竞争对手相比怎么样" / "竞品矩阵".

Options:
  --metric visibility|sov           — which metric to plot (default: visibility)
  --start <YYYY-MM-DD>  --end <>    time window

Usage:
  python3 scripts/get_matrix.py
  python3 scripts/get_matrix.py --metric sov --start 2025-11-01
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get,
    extract_data, print_json, truncate,
)


def _fmt(v):
    if v is None:
        return "--"
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return str(v)[:6]


def main():
    parser = argparse.ArgumentParser(description="Competitor × AI-platform matrix")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--metric", choices=["visibility", "sov"], default="visibility")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    params = {"metric": args.metric}
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end

    result = api_get(
        f"/api/projects/{pid}/analytics/platforms/matrix",
        key, base, params=params,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    platforms = data.get("platforms") or data.get("columns") or []
    rows = data.get("rows") or data.get("brands") or data.get("competitors") or []

    if not rows or not platforms:
        print("No matrix data available.")
        return

    label = "Visibility Score (%)" if args.metric == "visibility" else "Share of Voice (%)"
    print(f"Competitor × Platform Matrix — {label}")
    print()
    print("```")
    # Header
    head = "│ {:<20} │".format("Brand")
    sep_top = "┌" + "─" * 22 + "┬"
    sep_mid = "├" + "─" * 22 + "┼"
    sep_bot = "└" + "─" * 22 + "┴"
    for p in platforms:
        name = truncate(p.get("name") or p.get("code") or str(p), 8)
        head += " {:>8} │".format(name)
        sep_top += "─" * 10 + "┬"
        sep_mid += "─" * 10 + "┼"
        sep_bot += "─" * 10 + "┴"
    print(sep_top[:-1] + "┐")
    print(head)
    print(sep_mid[:-1] + "┤")
    for r in rows:
        bname = truncate(r.get("brand") or r.get("name") or "?", 20)
        is_self = r.get("is_self") or r.get("self")
        prefix = "★ " if is_self else "  "
        row = "│ {:<20} │".format(prefix + bname)[:24]  # safety
        row = "│ {:<20} │".format(prefix + bname)
        values = r.get("values") or r.get("scores") or {}
        for p in platforms:
            code = p.get("code") or p.get("name") or str(p)
            v = values.get(code) if isinstance(values, dict) else None
            row += " {:>8} │".format(_fmt(v))
        print(row)
    print(sep_bot[:-1] + "┘")
    print("```")
    print()
    print("★ = your brand")


if __name__ == "__main__":
    main()
