#!/usr/bin/env python3
"""Single-metric visibility queries (granular, for AI-agent fine-grained Q&A).

Three subcommands map 1:1 to the analytics single-metric endpoints. Each
returns the metric value plus previous-period delta. Score and average position
also request trend points; Share of Voice currently has no trend series.

Subcommands:
  score              — Visibility Score
  share-of-voice     — Share of Voice
  average-position   — Average Position

Common options:
  --start <YYYY-MM-DD>  --end <YYYY-MM-DD>     time window
  --platform <code>    GEO-Api ID or display name (for example ChatGPT)

Usage:
  python3 scripts/get_visibility.py score
  python3 scripts/get_visibility.py share-of-voice --platform openai
  python3 scripts/get_visibility.py average-position --start 2025-11-01 --end 2025-11-30
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get,
    extract_data, print_json,
    pad,
)
from _platforms import normalize_platform


def _fmt_metric(v):
    if v is None:
        return "--"
    try:
        f = float(v)
        return f"{f:.2f}" if abs(f) < 1000 else f"{f:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_change(c):
    if c is None:
        return "--"
    try:
        f = float(c)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f:.2f}"
    except (TypeError, ValueError):
        return str(c)


def _common_params(args, include_trend=False):
    p = {}
    if args.start:
        p["date_from"] = args.start
    if args.end:
        p["date_to"] = args.end
    if args.platform:
        p["platform"] = [normalize_platform(args.platform)]
    if include_trend:
        p["include_trend"] = True
    return p or None


def _print_metric(label, unit, data, suffix=""):
    cur = data.get("current") if isinstance(data, dict) else None
    if cur is None and isinstance(data, dict):
        cur = data.get("value") or data.get(label.lower().replace(" ", "_"))
    prev = data.get("previous") if isinstance(data, dict) else None
    change = data.get("change") if isinstance(data, dict) else None
    print(f"{label}")
    print()
    print("```")
    print("┌────────────────────┬──────────────┐")
    print("│ Field              │        Value │")
    print("├────────────────────┼──────────────┤")
    print(f"│ {pad('current', 18)} │ {(_fmt_metric(cur) + unit):>12} │")
    if prev is not None:
        print(f"│ {pad('previous', 18)} │ {(_fmt_metric(prev) + unit):>12} │")
    if change is not None:
        print(f"│ {pad('change', 18)} │ {_fmt_change(change):>12} │")
    print("└────────────────────┴──────────────┘")
    print("```")
    if suffix:
        print()
        print(suffix)


def _show_trend(data, unit):
    trend = data.get("trend") or data.get("series")
    if isinstance(trend, list) and trend:
        print()
        print(f"Trend ({len(trend)} points):")
        for pt in trend[-10:]:
            d = pt.get("date") or pt.get("day") or ""
            v = pt.get("value") or pt.get("score") or pt.get("metric")
            print(f"  {d}  {_fmt_metric(v)}{unit}")


def cmd_score(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/visibility/score",
        key, base, params=_common_params(args, include_trend=True),
    )
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    _print_metric("Visibility Score", "%", data)
    _show_trend(data, "%")


def cmd_sov(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/visibility/share-of-voice",
        key, base, params=_common_params(args),
    )
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    _print_metric("Share of Voice", "%", data)


def cmd_avg(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/visibility/average-position",
        key, base, params=_common_params(args, include_trend=True),
    )
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    _print_metric("Average Position", "", data)
    _show_trend(data, "")


def main():
    parser = argparse.ArgumentParser(description="Single-metric visibility queries")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("score", "share-of-voice", "average-position"):
        p = sub.add_parser(name)
        p.add_argument("--start", help="Start date YYYY-MM-DD")
        p.add_argument("--end", help="End date YYYY-MM-DD")
        p.add_argument("--platform", help="GEO-Api platform ID or display name")

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "score": cmd_score,
        "share-of-voice": cmd_sov,
        "average-position": cmd_avg,
    }
    try:
        handlers[args.command](args, key, base, pid)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
