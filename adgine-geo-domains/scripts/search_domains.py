#!/usr/bin/env python3
"""Search available domains by keyword.

Usage:
  python3 scripts/search_domains.py <keyword> [--limit 20] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json


REGISTER_URL = "https://platform.adgine.ai/domains/contact?domain={domain}"


def format_price(value, currency="USD"):
    if value is None:
        return "--"
    try:
        price = float(value)
        return f"${price:,.2f}"
    except (TypeError, ValueError):
        return str(value)


def main():
    parser = argparse.ArgumentParser(description="Search available domains by keyword")
    parser.add_argument("keyword", help="Search keyword (e.g. mybrand)")
    parser.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/domains/search", key, base, params={
        "keyword": args.keyword,
        "limit": args.limit,
    })
    data = extract_data(result) or {}
    domains = data.get("domains", [])

    if args.json:
        print_json(data)
        return

    if not domains:
        print(f'No domains found for "{args.keyword}".')
        return

    available = [d for d in domains if d.get("status") == "available"]
    taken = [d for d in domains if d.get("status") == "taken"]
    unsupported = [d for d in domains if d.get("status") == "unsupported"]

    # Sort: .com first, then by name
    available.sort(key=lambda d: ("" if d.get("name", "").endswith(".com") else d.get("name", "")))

    print(f"DOMAIN_SEARCH_RESULTS keyword={args.keyword}")
    print()

    if taken:
        print(f"TAKEN_DOMAINS count={len(taken)}")
        for d in taken:
            print(f"  TAKEN {d.get('name', '--')}")
        print()

    if available:
        print(f"AVAILABLE_DOMAINS count={len(available)}")
        for d in available:
            name = d.get("name", "--")
            price = format_price(d.get("price"), d.get("currency"))
            renewal = format_price(d.get("renewal_price"), d.get("currency"))
            reg_url = REGISTER_URL.format(domain=name)
            print(f"  AVAILABLE name={name} price={price} renewal={renewal} register_url={reg_url}")
        print()

    if unsupported:
        print(f"UNSUPPORTED_DOMAINS count={len(unsupported)}")
        for d in unsupported:
            print(f"  UNSUPPORTED {d.get('name', '--')}")
        print()


if __name__ == "__main__":
    main()
