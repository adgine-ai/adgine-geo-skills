#!/usr/bin/env python3
"""Prompt execution history & full single-execution detail.

Subcommands:
  list   --prompt-id <id>                    — recent executions of this prompt
        [--platform <code>] [--start <>] [--end <>]
        [--limit 20]
  get    --prompt-id <id> --execution-id <eid>  — full AI response, brand
                                                  mentions (rank/sentiment),
                                                  citations & matches

Usage:
  python3 scripts/get_execution.py list --prompt-id <pid>
  python3 scripts/get_execution.py list --prompt-id <pid> --platform openai
  python3 scripts/get_execution.py get --prompt-id <pid> --execution-id <eid>
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


def cmd_list(args, key, base, pid):
    params = {"limit": args.limit}
    if args.platform:
        params["platform"] = args.platform
    if args.start:
        params["start_date"] = args.start
    if args.end:
        params["end_date"] = args.end

    result = api_get(
        f"/api/projects/{pid}/analytics/prompts/{args.prompt_id}/executions",
        key, base, params=params,
    )
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("executions", [])

    if args.json:
        print_json(items)
        return

    if not items:
        print(f"No executions for prompt {args.prompt_id} in this window.")
        return

    print(f"Executions for prompt {args.prompt_id} ({len(items)})")
    print()
    print("```")
    print("┌──────────────────────────────────────┬────────────┬────────────┬────────────┐")
    print("│ Execution ID                         │ Platform   │ Date       │ Brand?     │")
    print("├──────────────────────────────────────┼────────────┼────────────┼────────────┤")
    for e in items:
        eid = truncate(e.get("id") or e.get("execution_id"), 36)
        plat = truncate(e.get("platform") or "--", 10)
        date = truncate((e.get("executed_at") or e.get("created_at") or "--")[:10], 10)
        mentioned = e.get("brand_mentioned")
        if mentioned is None:
            mentioned = bool(e.get("brand_mentions") or e.get("self_mentioned"))
        bm = "Yes" if mentioned else "No"
        print(f"│ {eid:<36} │ {plat:<10} │ {date:<10} │ {bm:<10} │")
    print("└──────────────────────────────────────┴────────────┴────────────┴────────────┘")
    print("```")


def cmd_get(args, key, base, pid):
    result = api_get(
        f"/api/projects/{pid}/analytics/prompts/{args.prompt_id}/executions/{args.execution_id}",
        key, base,
    )
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    print(f"Execution {args.execution_id}")
    print(f"  prompt:    {args.prompt_id}")
    print(f"  platform:  {data.get('platform')}")
    print(f"  date:      {(data.get('executed_at') or data.get('created_at') or '')[:19]}")
    print()
    response = data.get("response") or data.get("ai_response") or data.get("answer")
    if response:
        print("AI Response:")
        print("---")
        print(response)
        print("---")
        print()

    mentions = data.get("brand_mentions") or data.get("mentions") or []
    if mentions:
        print(f"Brand mentions ({len(mentions)}):")
        print()
        print("```")
        print("┌──────────────────────────────┬────────┬────────────┬────────────┐")
        print("│ Brand                        │  Rank  │ Sentiment  │ Is yours?  │")
        print("├──────────────────────────────┼────────┼────────────┼────────────┤")
        for m in mentions:
            name = truncate(m.get("brand") or m.get("name"), 28)
            rank = m.get("rank") or m.get("position") or "--"
            sent = truncate(m.get("sentiment") or "--", 10)
            mine = "Yes" if (m.get("is_self") or m.get("self")) else "No"
            print(f"│ {name:<28} │ {str(rank):>6} │ {sent:<10} │ {mine:<10} │")
        print("└──────────────────────────────┴────────┴────────────┴────────────┘")
        print("```")
        print()

    citations = data.get("citations") or data.get("links") or []
    if citations:
        print(f"Citations ({len(citations)}):")
        for c in citations[:10]:
            url = c.get("url") or c.get("link")
            title = truncate(c.get("title") or "", 60)
            print(f"  • {title}")
            print(f"    {url}")


def main():
    parser = argparse.ArgumentParser(description="Prompt execution history & detail")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_l = sub.add_parser("list", help="List recent executions")
    p_l.add_argument("--prompt-id", required=True)
    p_l.add_argument("--platform", choices=["openai", "google_aio", "perplexity", "gemini"])
    p_l.add_argument("--start", help="Start date YYYY-MM-DD")
    p_l.add_argument("--end", help="End date YYYY-MM-DD")
    p_l.add_argument("--limit", type=int, default=20)

    p_g = sub.add_parser("get", help="Full execution detail")
    p_g.add_argument("--prompt-id", required=True)
    p_g.add_argument("--execution-id", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {"list": cmd_list, "get": cmd_get}
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
