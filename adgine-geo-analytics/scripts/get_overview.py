#!/usr/bin/env python3
"""Fetch dashboard analytics overview for a GEO project.

Usage:
  python3 scripts/get_overview.py --project-id <id> [--period 30d] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, get_project_id, api_get, extract_data, print_json

parser = argparse.ArgumentParser(description="Fetch GEO analytics dashboard overview")
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
    params={"period": args.period}
)
data = extract_data(result)

if args.json:
    print_json(data)
    sys.exit(0)

# ── Human-readable output ─────────────────────────────────────────────────────
period     = data.get("period", args.period)
dr         = data.get("date_range", {})
integs     = data.get("integrations", {})
search     = data.get("search")
traffic    = data.get("traffic")
ai_impact  = data.get("ai_impact")
infra      = data.get("infrastructure")

print(f"Analytics Overview  —  {dr.get('start','?')} to {dr.get('end','?')}  ({period})")
print(f"Project: {pid}")
print()

# ── Integrations status ───────────────────────────────────────────────────────
statuses = []
for name, key_name in [("GSC", "gsc"), ("GA4", "ga4"), ("Cloudflare", "cloudflare")]:
    statuses.append(f"{name} {'✓' if integs.get(key_name) else '✗'}")
print("Integrations: " + "  |  ".join(statuses))
print()

def _metric(obj, key, default=0):
    """Extract .value from a MetricWithChange field, fallback to scalar."""
    v = obj.get(key, {})
    if isinstance(v, dict):
        return v.get("value", default)
    return v if v is not None else default

def _change(obj, key):
    """Extract .change from a MetricWithChange field (may be None)."""
    v = obj.get(key, {})
    if isinstance(v, dict):
        return v.get("change")
    return None

def _change_str(change):
    if change is None:
        return ""
    return f"  ({'+' if change >= 0 else ''}{change:,.0f} vs prev period)"

# ── Search (GSC) ──────────────────────────────────────────────────────────────
if search:
    print("── Search Performance (GSC) ─────────────────────────────────────────")
    clicks      = _metric(search, "clicks")
    impressions = _metric(search, "impressions")
    ctr         = _metric(search, "avg_ctr")
    position    = _metric(search, "avg_position")
    print(f"  Clicks      : {clicks:,.0f}{_change_str(_change(search, 'clicks'))}")
    print(f"  Impressions : {impressions:,.0f}{_change_str(_change(search, 'impressions'))}")
    print(f"  Avg CTR     : {ctr:.2%}")
    print(f"  Avg Position: {position:.1f}")
    top_q = search.get("top_queries", [])
    if top_q:
        print(f"\n  Top queries:")
        for q in top_q[:5]:
            print(f"    {q.get('name',''):<40}  {q.get('value',0):>8,.0f} clicks")
else:
    print("── Search Performance (GSC) ─────────────────────────────────────────")
    print("  Not connected. Connect GSC at: https://platform.adgine.ai")
print()

# ── Traffic (GA4) ─────────────────────────────────────────────────────────────
if traffic:
    print("── Website Traffic (GA4) ────────────────────────────────────────────")
    sessions = _metric(traffic, "sessions")
    users    = _metric(traffic, "active_users")
    print(f"  Sessions    : {sessions:,.0f}{_change_str(_change(traffic, 'sessions'))}")
    print(f"  Active users: {users:,.0f}{_change_str(_change(traffic, 'active_users'))}")
    top_src = traffic.get("top_sources", [])
    if top_src:
        print(f"\n  Top sources:")
        for s in top_src[:5]:
            print(f"    {s.get('name',''):<30}  {s.get('value',0):>8,.0f} sessions")
else:
    print("── Website Traffic (GA4) ────────────────────────────────────────────")
    print("  Not connected. Connect GA4 at: https://platform.adgine.ai")
print()

# ── AI Impact ─────────────────────────────────────────────────────────────────
if ai_impact:
    print("── AI Impact ────────────────────────────────────────────────────────")
    ai_sess = _metric(ai_impact, "ai_referral_sessions")
    ai_reqs = _metric(ai_impact, "ai_crawler_requests")
    print(f"  AI referral sessions : {ai_sess:,.0f}{_change_str(_change(ai_impact, 'ai_referral_sessions'))}")
    print(f"  AI crawler requests  : {ai_reqs:,.0f}{_change_str(_change(ai_impact, 'ai_crawler_requests'))}")
    top_bots = ai_impact.get("top_ai_bots", [])
    if top_bots:
        print(f"\n  Top AI crawlers:")
        for b in top_bots[:3]:
            print(f"    {b.get('name',''):<30}  {b.get('value',0):>10,.0f} requests")
    top_src = ai_impact.get("top_ai_sources", [])
    if top_src:
        print(f"\n  Top AI referral sources:")
        for s in top_src[:3]:
            print(f"    {s.get('name',''):<30}  {s.get('value',0):>8,.0f} sessions")
print()
