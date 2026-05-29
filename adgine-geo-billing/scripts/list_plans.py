#!/usr/bin/env python3
"""List all GEO platform subscription plans.

Public endpoint — works without project context but still requires GEO_API_KEY.

Usage:
  python3 scripts/list_plans.py [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json, truncate, pad


def _fmt_price(p):
    if p is None:
        return "--"
    try:
        f = float(p)
        if f == int(f):
            return f"{int(f):,}"
        return f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(p)


def main():
    parser = argparse.ArgumentParser(description="List GEO subscription plans")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/payments/plans", key, base)
    data = extract_data(result)
    items = data if isinstance(data, list) else (data or {}).get("plans", [])

    if args.json:
        print_json(items)
        return

    if not items:
        print("No plans available.")
        return

    print("Available Plans")
    print()
    print("```")
    print("┌────────────────────┬──────────┬──────────┬──────────────────────────┐")
    print("│ Plan               │    Price │ Interval │ Notes                    │")
    print("├────────────────────┼──────────┼──────────┼──────────────────────────┤")
    for p in items:
        name = truncate(p.get("name") or p.get("display_name"), 18)
        price = _fmt_price(p.get("price") or p.get("amount"))
        currency = p.get("currency") or ""
        price_str = f"{price} {currency}".strip()
        interval = truncate(p.get("interval") or p.get("billing_cycle") or "--", 8)
        note = truncate(p.get("description") or "", 24)
        print(f"│ {pad(name, 18)} │ {price_str:>8} │ {pad(interval, 8)} │ {pad(note, 24)} │")
    print("└────────────────────┴──────────┴──────────┴──────────────────────────┘")
    print("```")


if __name__ == "__main__":
    main()
