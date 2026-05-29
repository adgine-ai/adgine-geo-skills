#!/usr/bin/env python3
"""Query the current user's active GEO subscription.

Usage:
  python3 scripts/get_subscription.py [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json, truncate, pad


def main():
    parser = argparse.ArgumentParser(description="Get current GEO subscription")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/payments/subscription", key, base)
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    if not data or (isinstance(data, dict) and not data):
        print("No active subscription.")
        return

    print("Current Subscription")
    print()
    print("```")
    print("┌────────────────────┬──────────────────────────────┐")
    print("│ Field              │ Value                        │")
    print("├────────────────────┼──────────────────────────────┤")
    for k in ("plan", "plan_name", "status", "interval", "current_period_start",
              "current_period_end", "renews_at", "cancel_at_period_end",
              "trial_end", "credits_remaining", "credits_total"):
        if k in data:
            print(f"│ {pad(k, 18)} │ {pad(truncate(data.get(k), 28), 28)} │")
    print("└────────────────────┴──────────────────────────────┘")
    print("```")


if __name__ == "__main__":
    main()
