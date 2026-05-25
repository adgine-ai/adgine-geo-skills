#!/usr/bin/env python3
"""Deep-dive analytics for a specific page path.

All subcommands require --path (URL path on the project's website).

Subcommands:
  kpi --path <p>          — 5 KPI cards for this page (citation/index/training/
                            agent/total bots) with delta + daily trend
  logs --path <p>         — recent AI access events on this exact path
        [--limit 50] [--traffic-type bot|human]
  platforms --path <p>    — per-platform 4-AI + human-referral + share table
  related --path <p>      — sibling pages under the same parent path, with
                            5-metric comparison
  health --path <p>       — PageSpeed Insights report (cached). Returns
                            report=null if never analyzed.
  health-refresh --path <p>  — synchronously refresh PSI report (15–60s blocking)

Common opts: --start --end

Usage:
  python3 scripts/page_detail.py kpi --path /blog/my-article
  python3 scripts/page_detail.py logs --path /blog/my-article --limit 20
  python3 scripts/page_detail.py health --path /blog/my-article
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import (
    get_api_config, get_project_id,
    api_get, api_post,
    extract_data, print_json, truncate,
)


def _fmt_num(n):
    if n is None:
        return "--"
    try:
        f = float(n)
        if f == int(f):
            return f"{int(f):,}"
        return f"{f:,.1f}"
    except (TypeError, ValueError):
        return str(n)


def _fmt_change(c):
    if c is None:
        return "--"
    try:
        f = float(c)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f:.1f}%"
    except (TypeError, ValueError):
        return str(c)


def _base_params(args):
    p = {"path": args.path}
    if args.start:
        p["start_date"] = args.start
    if args.end:
        p["end_date"] = args.end
    return p


def cmd_kpi(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/pages/by-path/kpi",
                     key, base, params=_base_params(args))
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    kpis = data.get("kpis") or data
    print(f"Page KPIs — {args.path}")
    print()
    print("```")
    print("┌────────────────────┬──────────────┬──────────────┐")
    print("│ KPI                │      Current │       Change │")
    print("├────────────────────┼──────────────┼──────────────┤")
    for k, label in [
        ("ai_citation", "AI Citation"),
        ("ai_index", "AI Index"),
        ("ai_training", "AI Training"),
        ("ai_agent", "AI Agent"),
        ("total_bots", "All bots"),
    ]:
        v = kpis.get(k) if isinstance(kpis, dict) else None
        if isinstance(v, dict):
            cur, ch = v.get("current"), v.get("change")
        else:
            cur, ch = v, None
        print(f"│ {label:<18} │ {_fmt_num(cur):>12} │ {_fmt_change(ch):>12} │")
    print("└────────────────────┴──────────────┴──────────────┘")
    print("```")


def cmd_logs(args, key, base, pid):
    params = _base_params(args)
    params["limit"] = args.limit
    if args.traffic_type:
        params["traffic_type"] = args.traffic_type
    result = api_get(f"/api/projects/{pid}/ai-agent/pages/by-path/logs",
                     key, base, params=params)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("logs") or (data or {}).get("events", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print(f"No log events for {args.path}.")
        return
    print(f"Logs for {args.path} ({len(items)})")
    print()
    print("```")
    print("┌────────────────────┬────────────────────┬────────────┐")
    print("│ Time               │ Bot / UA           │ Platform   │")
    print("├────────────────────┼────────────────────┼────────────┤")
    for e in items:
        t = truncate((e.get("timestamp") or e.get("created_at") or "")[:19], 18)
        bot = truncate(e.get("bot_name") or e.get("user_agent") or "(human)", 18)
        plat = truncate(e.get("platform") or "--", 10)
        print(f"│ {t:<18} │ {bot:<18} │ {plat:<10} │")
    print("└────────────────────┴────────────────────┴────────────┘")
    print("```")


def cmd_platforms(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/pages/by-path/platforms",
                     key, base, params=_base_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("platforms", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print(f"No platform breakdown for {args.path}.")
        return
    print(f"Per-platform metrics for {args.path} ({len(items)})")
    print()
    print("```")
    print("┌────────────────────┬──────┬──────┬──────┬──────┬────────┬────────┐")
    print("│ Platform           │ Cite │ Indx │ Trn  │ Agnt │ Human  │   %    │")
    print("├────────────────────┼──────┼──────┼──────┼──────┼────────┼────────┤")
    for p in items:
        name = truncate(p.get("name") or p.get("platform"), 18)
        c = _fmt_num(p.get("ai_citation"))
        i = _fmt_num(p.get("ai_index"))
        t = _fmt_num(p.get("ai_training"))
        a = _fmt_num(p.get("ai_agent"))
        h = _fmt_num(p.get("human_referral") or p.get("human"))
        pct = p.get("share") or p.get("percentage")
        pct_s = (f"{float(pct):.1f}%" if pct is not None else "--")
        print(f"│ {name:<18} │ {c:>4} │ {i:>4} │ {t:>4} │ {a:>4} │ {h:>6} │ {pct_s:>6} │")
    print("└────────────────────┴──────┴──────┴──────┴──────┴────────┴────────┘")
    print("```")


def cmd_related(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/pages/by-path/related",
                     key, base, params=_base_params(args))
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("pages", [])
    if args.json:
        print_json(items)
        return
    if not items:
        print(f"No sibling pages under parent of {args.path}.")
        return
    print(f"Sibling pages of {args.path} ({len(items)})")
    print()
    print("```")
    print("┌────────────────────────────────┬──────┬──────┬──────┬──────┬──────┐")
    print("│ Page                           │ Cite │ Indx │ Trn  │ Agnt │ Cit% │")
    print("├────────────────────────────────┼──────┼──────┼──────┼──────┼──────┤")
    for p in items:
        path = truncate(p.get("path") or p.get("url"), 30)
        c = _fmt_num(p.get("ai_citation"))
        i = _fmt_num(p.get("ai_index"))
        t = _fmt_num(p.get("ai_training"))
        a = _fmt_num(p.get("ai_agent"))
        cp = p.get("ai_citation_pct")
        cp_s = (f"{float(cp):.1f}" if cp is not None else "--")
        print(f"│ {path:<30} │ {c:>4} │ {i:>4} │ {t:>4} │ {a:>4} │ {cp_s:>4} │")
    print("└────────────────────────────────┴──────┴──────┴──────┴──────┴──────┘")
    print("```")


def cmd_health(args, key, base, pid):
    result = api_get(f"/api/projects/{pid}/ai-agent/pages/by-path/health",
                     key, base, params={"path": args.path})
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    report = data.get("report") or data
    if not report or report == {}:
        print(f"No PageSpeed report cached for {args.path}.")
        print("Run `python3 scripts/page_detail.py health-refresh --path ...` to generate one.")
        return
    print(f"PageSpeed Insights — {args.path}")
    print()
    perf = report.get("performance_score") or report.get("performance")
    print(f"  Performance score: {perf}")
    cwv = report.get("core_web_vitals") or report.get("cwv") or {}
    if cwv:
        print("  Core Web Vitals:")
        for k, v in cwv.items():
            print(f"    {k}: {v}")
    fetched = report.get("fetched_at") or report.get("updated_at")
    if fetched:
        print(f"  Fetched at: {fetched}")


def cmd_health_refresh(args, key, base, pid):
    print(f"Refreshing PageSpeed report for {args.path} (15–60s blocking)...")
    result = api_post(f"/api/projects/{pid}/ai-agent/pages/by-path/health/refresh",
                      key, base, body={"path": args.path})
    data = extract_data(result) or {}
    if args.json:
        print_json(data)
        return
    print("Refresh completed.")
    perf = data.get("performance_score") or data.get("performance")
    if perf is not None:
        print(f"  Performance score: {perf}")


def main():
    parser = argparse.ArgumentParser(description="Page-level deep-dive AI analytics")
    parser.add_argument("--project-id", help="Project ID (or set GEO_PROJECT_ID env var)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("kpi", "platforms", "related"):
        p = sub.add_parser(name)
        p.add_argument("--path", required=True)
        p.add_argument("--start")
        p.add_argument("--end")

    p_lg = sub.add_parser("logs")
    p_lg.add_argument("--path", required=True)
    p_lg.add_argument("--start")
    p_lg.add_argument("--end")
    p_lg.add_argument("--limit", type=int, default=50)
    p_lg.add_argument("--traffic-type", choices=["bot", "human"])

    p_h = sub.add_parser("health")
    p_h.add_argument("--path", required=True)

    p_hr = sub.add_parser("health-refresh")
    p_hr.add_argument("--path", required=True)

    args = parser.parse_args()
    key, base = get_api_config()
    pid = get_project_id(args.project_id)

    handlers = {
        "kpi": cmd_kpi,
        "logs": cmd_logs,
        "platforms": cmd_platforms,
        "related": cmd_related,
        "health": cmd_health,
        "health-refresh": cmd_health_refresh,
    }
    handlers[args.command](args, key, base, pid)


if __name__ == "__main__":
    main()
