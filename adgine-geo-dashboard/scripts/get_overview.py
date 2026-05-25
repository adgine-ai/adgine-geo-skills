#!/usr/bin/env python3
"""Fetch the project dashboard overview snapshot.

Returns the aggregate dashboard metrics for a project (visibility, prompts,
topics, test counts, etc.) for the requested period.

Usage:
  python3 scripts/get_overview.py [--project-id <id>] [--period 30d] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id, api_get, extract_data, print_json, fmt_change,
)


def _scalar(obj, key, default=None):
    """Extract a scalar that may be wrapped in {value, change} or returned plain."""
    if not isinstance(obj, dict):
        return default
    v = obj.get(key)
    if isinstance(v, dict) and "value" in v:
        return v.get("value", default)
    return v if v is not None else default


def _delta(obj, key):
    """Extract the change delta from a {value, change} wrapper, or return None."""
    if not isinstance(obj, dict):
        return None
    v = obj.get(key)
    if isinstance(v, dict):
        return v.get("change")
    return None


def _fmt_num(n):
    if n is None:
        return "--"
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    if f == int(f):
        return f"{int(f):,}"
    return f"{f:,.1f}"


def main():
    parser = argparse.ArgumentParser(description="Fetch GEO project dashboard overview")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--period", default="30d", choices=["7d", "14d", "30d", "90d"],
                        help="Time period (default: 30d)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    result = api_get(
        f"/api/projects/{pid}/dashboard/overview",
        key, base,
        params={"period": args.period},
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    period = data.get("period", args.period)
    dr = data.get("date_range") or {}
    start = dr.get("start", "--")
    end = dr.get("end", "--")

    print(f"Dashboard Overview  —  {start} to {end}  ({period})")
    print(f"Project: {pid}")
    print()

    # ── Snapshot metrics ──────────────────────────────────────────────────
    # The dashboard/overview payload aggregates several top-level metric
    # groups. We render whichever ones are present, with graceful fallback.
    metric_keys = [
        ("visibility_score", "Visibility Score"),
        ("prompts_total",    "Prompts (total)"),
        ("prompts_tested",   "Prompts tested"),
        ("topics_total",     "Topics"),
        ("tests_total",      "Tests run"),
        ("citations_total",  "Citations"),
        ("articles_total",   "Articles"),
        ("ai_referrals",     "AI referrals"),
    ]
    rows = []
    for k, label in metric_keys:
        if k in data:
            rows.append((label, _scalar(data, k), _delta(data, k)))

    if rows:
        print("Snapshot")
        print("```")
        print("┌────────────────────────┬──────────┬──────────┐")
        print("│ Metric                 │    Value │ vs Prev  │")
        print("├────────────────────────┼──────────┼──────────┤")
        for label, val, change in rows:
            print(f"│ {label:<22} │ {_fmt_num(val):>8} │ {fmt_change(change):>8} │")
        print("└────────────────────────┴──────────┴──────────┘")
        print("```")
        print()

    # ── Top lists (if present) ────────────────────────────────────────────
    for list_key, title, name_field, value_field, value_label in [
        ("top_topics",   "Top Topics",       "name",    "score",     "Score"),
        ("top_prompts",  "Top Prompts",      "text",    "score",     "Score"),
        ("recent_tests", "Recent Tests",     "prompt",  "platform",  "Platform"),
    ]:
        items = data.get(list_key) or []
        if not items:
            continue
        print(f"{title}")
        print("```")
        print("┌────┬────────────────────────────────────────┬──────────┐")
        print(f"│  # │ {'Name':<38} │ {value_label:<8} │")
        print("├────┼────────────────────────────────────────┼──────────┤")
        for idx, item in enumerate(items[:5], 1):
            name = str(item.get(name_field, ""))
            value = str(item.get(value_field, ""))
            if len(name) > 38:
                name = name[:37] + "…"
            print(f"│ {idx:>2} │ {name:<38} │ {value:<8} │")
        print("└────┴────────────────────────────────────────┴──────────┘")
        print("```")
        print()

    # ── Fallback: dump unknown top-level keys ─────────────────────────────
    if not rows:
        print("Raw snapshot keys:")
        for k, v in data.items():
            if k in ("period", "date_range"):
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                print(f"  {k}: {v}")
            elif isinstance(v, list):
                print(f"  {k}: list[{len(v)}]")
            elif isinstance(v, dict):
                print(f"  {k}: dict({', '.join(v.keys())})")
        print()
        print("Tip: rerun with --json to see the full payload.")


if __name__ == "__main__":
    main()
