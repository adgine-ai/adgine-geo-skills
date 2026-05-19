#!/usr/bin/env python3
"""Verify GEO_API_KEY is set and valid.

Run this once before using any other geo-skills scripts.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_api_config, api_get, extract_data

key, base = get_api_config()

if not key.startswith("geo_sk_"):
    print(f"WARNING: Unexpected key format: {key[:14]}...")
    print("  Expected: geo_sk_live_xxx or geo_sk_test_xxx")

# Verify by fetching projects list
print(f"Verifying API key...")
result = api_get("/api/projects", key, base, params={"limit": 1})
data = extract_data(result)

total = data.get("total", "?") if isinstance(data, dict) else "?"

print(f"✓ Authentication successful")
print(f"  Key prefix : {key[:18]}...")
print(f"  API base   : {base}")
print(f"  Projects   : {total} project(s) found")
print()

project_id = os.environ.get("GEO_PROJECT_ID", "")
if project_id:
    print(f"  Active project: {project_id}  (from GEO_PROJECT_ID env var)")
else:
    print("  No active project set. Run list_projects.py to select one.")
    print("  Then: export GEO_PROJECT_ID=<project-id>")
