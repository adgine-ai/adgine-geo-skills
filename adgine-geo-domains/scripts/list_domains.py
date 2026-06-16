#!/usr/bin/env python3
"""List the current user's registered domains.

Usage:
  python3 scripts/list_domains.py [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json, pad


def format_date(value):
    """Format a datetime string to YYYY-MM-DD."""
    if not value:
        return "--"
    return str(value)[:10]


def main():
    parser = argparse.ArgumentParser(description="List my registered domains")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/domains", key, base)
    data = extract_data(result)

    if args.json:
        print_json(data)
        return

    domains = data if isinstance(data, list) else []
    if not domains:
        print("No registered domains.")
        return

    print("\n🌐 **我的域名**\n")
    print("```")
    C1, C2, C3, C4, C5, C6 = 4, 22, 12, 22, 10, 12
    sep = f"┌{'─' * C1}┬{'─' * C2}┬{'─' * C3}┬{'─' * C4}┬{'─' * C5}┬{'─' * C6}┐"
    print(sep)
    print(f"│ {'#':<2} │ {pad('Domain', C2)} │ {pad('Status', C3)} │ {pad('Expires', C4)} │ {pad('Renew', C5)} │ {pad('DNS', C6)} │")
    mid = f"├{'─' * C1}┼{'─' * C2}┼{'─' * C3}┼{'─' * C4}┼{'─' * C5}┼{'─' * C6}┤"
    print(mid)

    for i, d in enumerate(domains, 1):
        domain = d.get("domain", "--")
        status = d.get("status", "--")
        expires = format_date(d.get("expires_at"))
        auto_renew = "Auto" if d.get("auto_renew") else "Manual"
        dns = d.get("dns_status") or "--"

        print(f"│ {i:<2} │ {pad(domain, C2)} │ {pad(status, C3)} │ {pad(expires, C4)} │ {pad(auto_renew, C5)} │ {pad(dns, C6)} │")

    bot = f"└{'─' * C1}┴{'─' * C2}┴{'─' * C3}┴{'─' * C4}┴{'─' * C5}┴{'─' * C6}┘"
    print(bot)
    print("```")
    print()
    print()


if __name__ == "__main__":
    main()
