#!/usr/bin/env python3
"""Query credits pricing information (unit price, min/max, presets).

Usage:
  python3 scripts/get_credits_pricing.py [--json]
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data, print_json


def main():
    parser = argparse.ArgumentParser(description="Get credits pricing info")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    key, base = get_api_config()
    result = api_get("/api/payments/credits/pricing", key, base)
    data = extract_data(result) or {}

    if args.json:
        print_json(data)
        return

    if not data:
        print("Credits pricing information unavailable.")
        return

    unit = data.get("unit_price_cents_per_credit", 1)
    min_c = data.get("min_credits", 1000)
    step = data.get("step", 100)
    max_c = data.get("max_credits", 100000)
    presets = data.get("presets", [])

    print("Credits Pricing")
    print()
    print(f"  Unit price: ${unit / 100:.2f} per credit ({unit} cent)")
    print(f"  Minimum purchase: {min_c:,} credits (${min_c * unit / 100:.2f})")
    print(f"  Maximum purchase: {max_c:,} credits (${max_c * unit / 100:.2f})")
    print(f"  Step: {step:,} credits")
    print()
    if presets:
        print("  Preset options:")
        for p in presets:
            print(f"    - {p:,} credits = ${p * unit / 100:.2f}")


if __name__ == "__main__":
    main()
