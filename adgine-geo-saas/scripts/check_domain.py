#!/usr/bin/env python3
"""Check whether a SaaS subdomain is available.

Usage:
  python3 scripts/check_domain.py --subdomain mysite [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json


def main():
    parser = argparse.ArgumentParser(description="Check SaaS subdomain availability")
    parser.add_argument("--subdomain", required=True, help="Subdomain to check (without dots)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/saas/domain/check", key, base,
                     params={"subdomain": args.subdomain})
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    available = data.get("available")
    if available is True:
        print(f"Available: {args.subdomain}")
    elif available is False:
        reason = data.get("reason") or data.get("message") or "already in use"
        print(f"Unavailable: {args.subdomain} ({reason})")
    else:
        print(f"Result for {args.subdomain}:")
        for k, v in data.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
