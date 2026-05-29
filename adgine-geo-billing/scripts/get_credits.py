#!/usr/bin/env python3
"""Query the current user's credits balance (subscription + purchased pools).

Usage:
  python3 scripts/get_credits.py [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json


def main():
    parser = argparse.ArgumentParser(description="Get current credits balance")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/payments/credits/me", key, base)
    data = extract_data(result)

    if args.json:
        print_json(data)
        return

    if not data:
        print("Credits information unavailable (service may be offline).")
        return

    sub_bal = data.get("subscription_balance", 0)
    pur_bal = data.get("purchased_balance", 0)
    total = sub_bal + pur_bal

    print("Credits Balance")
    print()
    print("```")
    print("┌──────────────────────┬──────────────┐")
    print("│ Pool                 │      Balance │")
    print("├──────────────────────┼──────────────┤")
    print(f"│ Subscription Credits │ {sub_bal:>12,} │")
    print(f"│ Purchased Credits    │ {pur_bal:>12,} │")
    print("├──────────────────────┼──────────────┤")
    print(f"│ Total                │ {total:>12,} │")
    print("└──────────────────────┴──────────────┘")
    print("```")


if __name__ == "__main__":
    main()
