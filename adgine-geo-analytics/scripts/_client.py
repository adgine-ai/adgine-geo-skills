#!/usr/bin/env python3
"""Shared HTTP client utilities for geo-skills scripts.

Used by all scripts in this skill. Uses Python stdlib only — no external dependencies.
"""
import os
import sys
import json
import time
import urllib.request as _req
import urllib.error as _uerr
import urllib.parse as _up

def _load_dot_env():
    """Load .env from the repo root (adgine-geo-skills/) into os.environ.

    Resolved relative to this file's location, so it works regardless of the
    agent's working directory (e.g. Hermes, OpenClaw, or any other runtime).
    Existing environment variables are never overwritten.
    """
    if os.environ.get("GEO_API_KEY"):
        return
    # _client.py is at <repo_root>/adgine-geo-<skill>/scripts/_client.py
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    env_path = os.path.join(repo_root, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip()
            if _k and _k not in os.environ:
                os.environ[_k] = _v


_load_dot_env()



def get_api_config():
    """Read GEO_API_KEY and GEO_API_BASE_URL from environment.

    Exits with a helpful message if GEO_API_KEY is not set.
    Returns (key, base_url).
    """
    key = os.environ.get("GEO_API_KEY", "")
    base = os.environ.get("GEO_API_BASE_URL", "https://platform.adgine.ai").rstrip("/")
    if not key:
        print("ERROR: GEO_API_KEY is not set.")
        print("  1. Get your API key: https://platform.adgine.ai")
        print("  2. Run: export GEO_API_KEY=geo_sk_live_xxx")
        print("  3. To persist: add the export line to ~/.zshrc or ~/.bashrc")
        sys.exit(1)
    return key, base


def get_project_id(arg_value=None):
    """Resolve project ID from argument or GEO_PROJECT_ID env var.

    Exits with instructions if neither is set.
    """
    pid = arg_value or os.environ.get("GEO_PROJECT_ID", "")
    if not pid:
        print("ERROR: Project ID is required but not set.")
        print("  Option 1: export GEO_PROJECT_ID=<project-id>")
        print("  Option 2: pass --project-id <id> to this script")
        print("  Run list_projects.py to see your available projects.")
        sys.exit(1)
    return pid


def _do_request(method, url, key, body=None):
    """Execute an HTTP request and return parsed JSON.

    Exits with an error message on HTTP errors or network failures.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "geo-skills/1.0",
    }
    request = _req.Request(url, data=data, headers=headers, method=method)
    try:
        with _req.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except _uerr.HTTPError as e:
        raw = e.read().decode("utf-8")[:400]
        try:
            err_data = json.loads(raw)
            msg = err_data.get("message") or err_data.get("detail") or raw
        except Exception:
            msg = raw
        if e.code == 401:
            print("ERROR: Unauthorized — API key is invalid or revoked.")
            print("  Generate a new key: https://platform.adgine.ai")
        elif e.code == 403:
            print("ERROR: Forbidden — insufficient permissions for this operation.")
        elif e.code == 404:
            print(f"ERROR: Not found — {msg}")
        else:
            print(f"ERROR: HTTP {e.code} — {msg}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Request failed — {e}")
        sys.exit(1)


def api_get(path, key, base, params=None):
    url = f"{base}{path}"
    if params:
        clean = {k: str(v) for k, v in params.items() if v is not None}
        if clean:
            url += "?" + _up.urlencode(clean)
    return _do_request("GET", url, key)


def api_post(path, key, base, body=None):
    return _do_request("POST", f"{base}{path}", key, body)


def api_patch(path, key, base, body=None):
    return _do_request("PATCH", f"{base}{path}", key, body)


def api_put(path, key, base, body=None):
    return _do_request("PUT", f"{base}{path}", key, body)


def api_delete(path, key, base):
    return _do_request("DELETE", f"{base}{path}", key)


def extract_data(response):
    """Extract the data payload from a standard ApiResponse wrapper."""
    if isinstance(response, dict):
        return response.get("data", response)
    return response


def print_json(data):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def poll_job(path, key, base, interval=5, max_wait=300):
    """Poll a job/task endpoint until it reaches a terminal state.

    Returns the final job data dict.
    """
    elapsed = 0
    while elapsed < max_wait:
        result = api_get(path, key, base)
        data = extract_data(result)
        status = data.get("status", "")
        if status in ("completed", "failed", "done", "success", "error"):
            print()
            return data
        print(f"  Status: {status or 'pending'} ({elapsed}s elapsed)...   ", end="\r")
        time.sleep(interval)
        elapsed += interval
    print(f"\nWARNING: Job did not complete within {max_wait}s.")
    return extract_data(api_get(path, key, base))


def api_put(path, key, base, body=None):
    return _do_request("PUT", f"{base}{path}", key, body)


def api_delete(path, key, base):
    return _do_request("DELETE", f"{base}{path}", key)


def extract_data(result):
    """Extract the .data field from a standard geo-api envelope response."""
    if isinstance(result, dict):
        return result.get("data", result)
    return result


def poll_job(status_path, key, base, interval=3, max_wait=300,
             terminal=("completed", "failed", "done", "success", "error")):
    """Poll a job endpoint until it reaches a terminal state.

    Prints a spinner with the current phase. Returns the final job dict.
    """
    elapsed = 0
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    while elapsed < max_wait:
        result = api_get(status_path, key, base)
        job = extract_data(result)
        status = job.get("status", "")
        phase = job.get("current_phase") or job.get("phase") or status
        print(f"\r  {frames[idx % len(frames)]} {phase}...", end="", flush=True)
        idx += 1
        if status in terminal:
            print()  # newline after spinner
            return job
        time.sleep(interval)
        elapsed += interval
    print()
    print(f"WARNING: Job is still running after {max_wait}s. Check status manually.")
    return api_get(status_path, key, base).get("data", {})


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))
