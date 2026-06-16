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

    # Split domains by status
    available = [d for d in domains if d.get("status") == "available"]
    taken = [d for d in domains if d.get("status") == "taken"]
    unsupported = [d for d in domains if d.get("status") == "unsupported"]

    # Sort available: .com first, then alphabetically
    available.sort(key=lambda d: ("" if d.get("name", "").endswith(".com") else d.get("name", "")))

    print(f'\n🔍 搜索: **{args.keyword}**\n')

    # ===== Section 1: 推荐首选 (.com or first available) =====
    top_pick = None
    remaining = list(available)
    for d in available:
        if d.get("name", "").endswith(".com"):
            top_pick = d
            remaining.remove(d)
            break
    if top_pick is None and available:
        top_pick = available[0]
        remaining = available[1:]

    if top_pick:
        name = top_pick.get("name", "--")
        price = format_price(top_pick.get("price"), top_pick.get("currency"))
        renewal = format_price(top_pick.get("renewal_price"), top_pick.get("currency"))
        renewal_str = f"{renewal}/yr" if renewal != "--" else "--"
        reg_url = REGISTER_URL.format(domain=name)

        print("> 🏆 **推荐首选**\n>")
        print(f"> | 域名 | 年费 | 续费 | |")
        print(f"> |------|------|------|---|")
        print(f"> | **{name}** | {price} | {renewal_str} | [现在注册 →]({reg_url}) |")
        print(">")

    # ===== Section 2: 其他可注册域名 =====
    if remaining:
        print("> 📋 **其他可注册域名**\n>")
        print(f"> | # | 域名 | 年费 | 续费 | |")
        print(f"> |---|------|------|------|---|")
        for i, d in enumerate(remaining, 2):
            name = d.get("name", "--")
            price = format_price(d.get("price"), d.get("currency"))
            renewal = format_price(d.get("renewal_price"), d.get("currency"))
            renewal_str = f"{renewal}/yr" if renewal != "--" else "--"
            reg_url = REGISTER_URL.format(domain=name)
            print(f"> | {i} | {name} | {price} | {renewal_str} | [现在注册 →]({reg_url}) |")
        print(">")

    # ===== Section 3: 已注册域名 =====
    if taken:
        print("> ⚠️ **已注册域名**\n>")
        print(f"> | # | 域名 | 状态 |")
        print(f"> |---|------|------|")
        for i, d in enumerate(taken, 1):
            name = d.get("name", "--")
            print(f"> | {i} | {name} | ❌ 已注册 |")
        print(">")

    # ===== Section 4: 不支持的域名 =====
    if unsupported:
        print("> ⚠️ **不支持的域名**\n>")
        print(f"> | # | 域名 | 状态 |")
        print(f"> |---|------|------|")
        for i, d in enumerate(unsupported, 1):
            name = d.get("name", "--")
            reason = d.get("reason") or "不支持注册"
            print(f"> | {i} | {name} | ⚠️ {reason} |")
        print(">")

    # ===== Section 5: 建议 =====
    all_available = [d for d in domains if d.get("status") == "available"]
    if all_available:
        print("> 💡 **建议**: 推荐优先注册 `.com`，若预算有限可选择 `.org`。以下为注册链接：\n>")
        for d in all_available:
            name = d.get("name", "--")
            reg_url = REGISTER_URL.format(domain=name)
            print(f"> - [注册 **{name}**]({reg_url})")
        print()


if __name__ == "__main__":
    main()
