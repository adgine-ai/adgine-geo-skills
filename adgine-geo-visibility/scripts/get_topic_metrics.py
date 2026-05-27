#!/usr/bin/env python3
"""Topic-level AI visibility metrics.

Subcommands:
  list                              — full Topic dimension (Visibility / SoV /
                                       Avg Position + previous-period delta)
  visibility                        — lightweight list (id + name + score)
                                       used for content-creation topic picker
  prompts --topic-id <id>           — prompts under a topic (full metrics)
  prompts-visibility --topic-id <id>  — prompts under a topic (lightweight)

Time-window options on `list`:
  --start <YYYY-MM-DD>  --end <YYYY-MM-DD>

Usage:
  python3 scripts/get_topic_metrics.py list
  python3 scripts/get_topic_metrics.py visibility            # for picker UI
  python3 scripts/get_topic_metrics.py prompts --topic-id <topic_id>
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
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return str(v)[:6]


def _fmt_change(c):
    if c is None:
        return "--"
    try:
        f = float(c)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f:.1f}"
    except (TypeError, ValueError):
        return str(c)


def cmd_list(args, key, base, pid):
    params = {}
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end
    result = api_get(f"/api/projects/{pid}/analytics/topics", key, base,
                     params=params or None)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("topics", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No topic data.")
        return
    print(f"Topic Visibility ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│ Topic                        │   Vis(%) │   SoV(%) │  AvgPos  │   ΔVis   │")
    print("├──────────────────────────────┼──────────┼──────────┼──────────┼──────────┤")
    for t in items:
        name = truncate(t.get("name") or t.get("topic"), 28)
        vis = _fmt(t.get("visibility_score") or t.get("visibility"))
        sov = _fmt(t.get("share_of_voice") or t.get("sov"))
        ap = _fmt(t.get("average_position") or t.get("avg_position"))
        ch = _fmt_change(t.get("visibility_change") or t.get("change"))
        print(f"│ {pad(name, 28)} │ {vis:>8} │ {sov:>8} │ {ap:>8} │ {ch:>8} │")
    print("└──────────────────────────────┴──────────┴──────────┴──────────┴──────────┘")
    print("```")


def cmd_visibility(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/analytics/topics/visibility",
                     key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("topics", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print("No topics.")
        return
    print(f"Topics ({len(items)}) — sorted by visibility, last 30 days")
    print()
    print("```")
    print("┌──────────────────────────────────────┬──────────────────────────────┬──────────┐")
    print("│ Topic ID                             │ Name                         │   Vis(%) │")
    print("├──────────────────────────────────────┼──────────────────────────────┼──────────┤")
    for t in items:
        tid = truncate(t.get("id") or t.get("topic_id"), 36)
        name = truncate(t.get("name") or t.get("topic"), 28)
        vis = _fmt(t.get("visibility_score") or t.get("score") or t.get("visibility"))
        print(f"│ {pad(tid, 36)} │ {pad(name, 28)} │ {vis:>8} │")
    print("└──────────────────────────────────────┴──────────────────────────────┴──────────┘")
    print("```")


def cmd_prompts(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/topics/{args.topic_id}/prompts",
        key, base,
    )
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("prompts", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print(f"No prompts under topic {args.topic_id}.")
        return
    print(f"Prompt Visibility — topic {args.topic_id} ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────────────────┬──────────┬──────────┬──────────┐")
    print("│ Prompt                                   │   Vis(%) │   SoV(%) │  AvgPos  │")
    print("├──────────────────────────────────────────┼──────────┼──────────┼──────────┤")
    for p in items:
        text = truncate(p.get("text") or p.get("prompt") or p.get("name"), 40)
        vis = _fmt(p.get("visibility_score") or p.get("visibility"))
        sov = _fmt(p.get("share_of_voice") or p.get("sov"))
        ap = _fmt(p.get("average_position") or p.get("avg_position"))
        print(f"│ {pad(text, 40)} │ {vis:>8} │ {sov:>8} │ {ap:>8} │")
    print("└──────────────────────────────────────────┴──────────┴──────────┴──────────┘")
    print("```")


def cmd_prompts_visibility(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/topics/{args.topic_id}/prompts/visibility",
        key, base,
    )
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("prompts", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print(f"No prompts under topic {args.topic_id}.")
        return
    print(f"Prompts under topic {args.topic_id} — sorted by visibility")
    print()
    print("```")
    print("┌──────────────────────────────────────┬──────────────────────────────┬──────────┐")
    print("│ Prompt ID                            │ Text                         │   Vis(%) │")
    print("├──────────────────────────────────────┼──────────────────────────────┼──────────┤")
    for p in items:
        pid_ = truncate(p.get("id") or p.get("prompt_id"), 36)
        text = truncate(p.get("text") or p.get("prompt"), 28)
        vis = _fmt(p.get("visibility_score") or p.get("score") or p.get("visibility"))
        print(f"│ {pad(pid_, 36)} │ {pad(text, 28)} │ {vis:>8} │")
    print("└──────────────────────────────────────┴──────────────────────────────┴──────────┘")
    print("```")


def main():
    parser = argparse.ArgumentParser(description="Topic-level AI visibility metrics")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_l = sub.add_parser("list", help="Full Topic dimension metrics")
    p_l.add_argument("--start", help="Start date YYYY-MM-DD")
    p_l.add_argument("--end", help="End date YYYY-MM-DD")

    sub.add_parser("visibility", help="Lightweight topic list for pickers")

    p_p = sub.add_parser("prompts", help="Prompts under topic (full)")
    p_p.add_argument("--topic-id", required=True)

    p_pv = sub.add_parser("prompts-visibility", help="Prompts under topic (light)")
    p_pv.add_argument("--topic-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "list": cmd_list,
        "visibility": cmd_visibility,
        "prompts": cmd_prompts,
        "prompts-visibility": cmd_prompts_visibility,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
