#!/usr/bin/env python3
"""Shared HTTP client utilities for geo-skills scripts.

Used by all scripts in this skill. Uses Python stdlib only — no external dependencies.

This file is the canonical source. It must be copied verbatim into every
adgine-geo-* skill folder's scripts/ directory. The sync linter at
scripts/sync-skills/sync-skills.sh (in the GEOAgent repo) flags any drift.
"""
import os
import sys
import json
import time
import unicodedata
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


def _print_version_notice():
    """Check for a newer version of adgine-geo-skills and print _notice if found.

    Runs once per process. Silent on any error or timeout.
    """
    import subprocess
    _check = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts", "check_version.py",
    )
    if not os.path.isfile(_check):
        return
    try:
        import json as _json
        _out = subprocess.run(
            [sys.executable, _check], capture_output=True, text=True, timeout=5
        )
        if not _out.stdout.strip():
            return
        _v = _json.loads(_out.stdout)
        if not _v.get("update_available"):
            return
        cur, lat = _v["current"], _v["latest"]
        if _v.get("install_type") == "git":
            msg = (f"adgine-geo-skills {lat} available (current {cur}). "
                   "Tell me: 请帮我更新 adgine-geo-skills 到最新版本")
        else:
            msg = (f"adgine-geo-skills {lat} available (current {cur}). "
                   f"Download: {_v.get('release_url', '')}")
        print(f'_notice: {{"update": {{"current": "{cur}", "latest": "{lat}", "message": "{msg}"}}}}')
        print()
    except Exception:
        pass


_print_version_notice()


def get_api_config():
    """Read GEO_API_KEY and GEO_API_BASE_URL from environment.

    Exits with a helpful message if GEO_API_KEY is not set.
    Returns (key, base_url).
    """
    key = os.environ.get("GEO_API_KEY", "")
    base = os.environ.get("GEO_API_BASE_URL", "https://platform.adgine.ai").rstrip("/")
    if not key:
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        env_path = os.path.join(repo_root, ".env")
        example_path = os.path.join(repo_root, ".env.example")
        setup_path = os.path.join(repo_root, "setup.py")
        print("ERROR: GEO_API_KEY is not set.")
        print(f"  Expected location: {env_path}")
        print()
        print("  One-shot fix (recommended):")
        print(f"    python3 {setup_path} <YOUR_KEY>")
        print()
        print("  Or set it manually:")
        if not os.path.isfile(env_path):
            print(f"    cp {example_path} {env_path}")
        print(f"    edit {env_path} and set GEO_API_KEY=geo_sk_live_xxx")
        print()
        print("  Get your key at: https://platform.adgine.ai")
        print("  The .env file is gitignored — your key stays local and private.")
        print()
        print("  NOTE: adgine-geo-site-audit does NOT require an API key.")
        print("    Run directly: python3 adgine-geo-site-audit/scripts/geo_collect.py <url>")
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
        print("  Run list_projects.py from the adgine-geo-projects skill to see your available projects.")
        sys.exit(1)
    return pid


def _do_request(method, url, key, body=None, timeout=30):
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
        with _req.urlopen(request, timeout=timeout) as resp:
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


def api_get(path, key, base, params=None, timeout=30):
    url = f"{base}{path}"
    if params:
        clean = {k: str(v) for k, v in params.items() if v is not None}
        if clean:
            url += "?" + _up.urlencode(clean)
    return _do_request("GET", url, key, timeout=timeout)


def api_post(path, key, base, body=None, timeout=30):
    return _do_request("POST", f"{base}{path}", key, body, timeout=timeout)


def api_patch(path, key, base, body=None, timeout=30):
    return _do_request("PATCH", f"{base}{path}", key, body, timeout=timeout)


def api_put(path, key, base, body=None, timeout=30):
    return _do_request("PUT", f"{base}{path}", key, body, timeout=timeout)


def api_delete(path, key, base, timeout=30):
    return _do_request("DELETE", f"{base}{path}", key, timeout=timeout)


def extract_data(result):
    """Extract the .data field from a standard geo-api envelope response.

    On success the API returns {"code": 0, "data": <payload>, "message": "ok"}.
    On non-zero code, this prints the message and exits(1).
    """
    if not isinstance(result, dict):
        return result
    if "code" in result and result.get("code") not in (0, None):
        msg = result.get("message") or result.get("detail") or "request failed"
        print(f"ERROR: API returned code={result.get('code')} — {msg}")
        sys.exit(1)
    return result.get("data", result)


def poll_job(status_path, key, base, interval=3, max_wait=300,
             terminal=("completed", "failed", "done", "success", "error")):
    """Poll a job/task endpoint until it reaches a terminal state.

    Prints an inline spinner with the current phase. Returns the final job dict.
    """
    elapsed = 0
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    last_job = {}
    while elapsed < max_wait:
        result = api_get(status_path, key, base)
        last_job = extract_data(result) or {}
        status = (last_job.get("status") or "").lower()
        phase = last_job.get("current_phase") or last_job.get("phase") or status or "pending"
        print(f"\r  {frames[idx % len(frames)]} {phase}... ({elapsed}s)", end="", flush=True)
        idx += 1
        if status in terminal:
            print()  # newline after spinner
            return last_job
        time.sleep(interval)
        elapsed += interval
    print()
    print(f"WARNING: Job is still running after {max_wait}s. Check status manually.")
    return last_job


def print_json(data):
    """Print data as formatted JSON (UTF-8 safe)."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def fmt_change(value):
    """Format a numeric change indicator per CONVENTIONS.md §4.

    Returns: '+N' / '-N' / '0' / '--' (None becomes '--').
    """
    if value is None:
        return "--"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "--"
    if n == 0:
        return "0"
    sign = "+" if n > 0 else ""
    if n == int(n):
        return f"{sign}{int(n):,}"
    return f"{sign}{n:,.1f}"


def truncate(text, n=60, ellipsis="…"):
    """Truncate text to n characters, adding ellipsis if cut. ASCII-safe for tables."""
    if text is None:
        return "--"
    s = str(text)
    if len(s) <= n:
        return s
    return s[: max(0, n - len(ellipsis))] + ellipsis

def display_width(s):
    """Return the display width of a string (CJK chars count as 2 columns)."""
    w = 0
    for c in str(s):
        eaw = unicodedata.east_asian_width(c)
        w += 2 if eaw in ('W', 'F') else 1
    return w


def pad(s, width, align='left'):
    """Pad string to display width for CJK-aware table alignment.
    Replaces f'{s:<N}' (align='left') and f'{s:>N}' (align='right').
    """
    s = str(s)
    dw = display_width(s)
    spaces = max(0, width - dw) * ' '
    return spaces + s if align == 'right' else s + spaces
