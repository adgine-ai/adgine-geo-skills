#!/usr/bin/env python3
"""Get detailed information about a specific domain registration.

Usage:
  python3 scripts/get_domain.py <domain_id> [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json, truncate, pad


def format_date(value):
    """Format a datetime string to YYYY-MM-DD."""
    if not value:
        return "--"
    return str(value)[:10]


def main():
    parser = argparse.ArgumentParser(description="Get domain registration details")
    parser.add_argument("domain_id", help="Domain registration ID (UUID)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get(f"/api/domains/{args.domain_id}", key, base)
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    if not data:
        print("Domain not found.")
        return

    domain = data.get("domain", "--")

    print(f'\n🌐 **Domain: {domain}**\n')
    print("```")

    fields = [
        ("Status", data.get("status")),
        ("Cloudflare State", data.get("cf_state")),
        ("Zone ID", truncate(data.get("zone_id"), 34) if data.get("zone_id") else "--"),
        ("Price", f"{data.get('total_price')} {data.get('currency', 'USD')}" if data.get("total_price") else "--"),
        ("Expires", format_date(data.get("expires_at"))),
        ("Auto Renew", "Yes" if data.get("auto_renew") else "No"),
        ("DNS Status", data.get("dns_status") or "--"),
        ("Error", data.get("error_msg") or "--"),
        ("Created", format_date(data.get("created_at"))),
        ("Updated", format_date(data.get("updated_at"))),
    ]

    C1, C2 = 20, 36
    sep = f"┌{'─' * C1}┬{'─' * C2}┐"
    print(sep)
    print(f"│ {pad('Field', C1)} │ {pad('Value', C2)} │")
    mid = f"├{'─' * C1}┼{'─' * C2}┤"
    print(mid)

    for label, value in fields:
        print(f"│ {pad(label, C1)} │ {pad(str(value), C2)} │")

    bot = f"└{'─' * C1}┴{'─' * C2}┘"
    print(bot)
    print("```")
    print()


if __name__ == "__main__":
    main()
