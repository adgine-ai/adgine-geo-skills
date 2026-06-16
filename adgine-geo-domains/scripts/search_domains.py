#!/usr/bin/env python3
"""Search available domains by keyword.

Usage:
  python3 scripts/search_domains.py <keyword> [--limit 20] [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json, pad


REGISTER_URL = "https://platform.adgine.ai/domains/contact?domain={domain}"

STATUS_MAP = {
    "available": "✅ 可注册",
    "taken": "❌ 已注册",
    "unsupported": "⚠️ 不支持",
}


def format_price(value, currency="USD"):
    """Format a price value for display."""
    if value is None:
        return "--"
    try:
        price = float(value)
        return f"${price:,.2f} {currency}"
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

    print(f'\n🔍 搜索: **{args.keyword}**\n')
    print("```")
    # Table header
    C1, C2, C3, C4, C5 = 4, 20, 10, 22, 14
    sep = f"┌{'─' * C1}┬{'─' * C2}┬{'─' * C3}┬{'─' * C4}┬{'─' * C5}┐"
    print(sep)
    print(f"│ {'#':<2} │ {pad('Domain', C2)} │ {pad('Status', C3)} │ {pad('Price / Renewal', C4)} │ {pad('', C5)} │")
    mid = f"├{'─' * C1}┼{'─' * C2}┼{'─' * C3}┼{'─' * C4}┼{'─' * C5}┤"
    print(mid)

    available_domains = []
    for i, d in enumerate(domains, 1):
        name = d.get("name", "--")
        status_label = STATUS_MAP.get(d.get("status"), d.get("status", "--"))
        price = format_price(d.get("price"), d.get("currency"))
        renewal = format_price(d.get("renewal_price"), d.get("currency"))
        renewal_str = f"{renewal}/yr" if renewal != "--" else "--"
        price_col = f"{price} / {renewal_str}"
        action = "" if d.get("status") != "available" else "马上注册 →"

        print(f"│ {i:<2} │ {pad(name, C2)} │ {pad(status_label, C3)} │ {pad(price_col, C4)} │ {pad(action, C5)} │")

        if d.get("status") == "available":
            available_domains.append(name)

    bot = f"└{'─' * C1}┴{'─' * C2}┴{'─' * C3}┴{'─' * C4}┴{'─' * C5}┘"
    print(bot)
    print("```")

    # Print clickable registration links below the table
    if available_domains:
        print()
        print("> 💡 找到想注册的域名？点击下方链接跳转到网页填写注册信息：")
        print(">")
        for domain in available_domains:
            url = REGISTER_URL.format(domain=domain)
            print(f"> - [注册 **{domain}**]({url})")
        print()


if __name__ == "__main__":
    main()
