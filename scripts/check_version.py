#!/usr/bin/env python3
"""
Check whether a newer version of adgine-geo-skills is available on GitHub.

The canonical VERSION source of truth is:
  https://github.com/adgine-ai/adgine-geo-skills/blob/main/VERSION
fetched via the raw endpoint.

Two output modes:
  (default)   Print a JSON object describing the version state.
  --notice    Print a single `_notice: {...}` line IF (and only if) an update
              is available. Prints nothing otherwise. This is what scripts emit
              at startup so the AI agent sees it in the tool output and prompts
              the user to update.
  --footer    Print a human-readable `---` / ⚠️ footer IF an update is available.

Exits 0 always — any error (network, parse, etc.) is silently suppressed so the
calling skill's main flow is never blocked.

Debug (opt-in, does not change exit code):
  GEO_VERSION_CHECK_DEBUG=1   Log failures to stderr.
  --verbose                 Same, with default or --notice mode.

JSON schema (default mode):
  {
    "current": "1.1.0",
    "latest": "1.2.0",
    "update_available": true,
    "install_type": "git" | "package",
    "update_command": "git -C /path/to/dir pull",   // git only
    "release_url": "https://github.com/..."
  }
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(REPO_ROOT, "VERSION")
REMOTE_VERSION_URL = (
    "https://raw.githubusercontent.com/adgine-ai/adgine-geo-skills/main/VERSION"
)
RELEASE_URL = "https://github.com/adgine-ai/adgine-geo-skills/releases/latest"
TIMEOUT = 5
# Cache the remote version lookup so a conversation that runs several scripts
# in one turn does not hammer GitHub. A fresh conversation later still re-checks
# once the cache expires.
CACHE_TTL = 120  # 2 minutes — dedupes a burst of scripts in one turn while
# still surfacing a freshly-pushed version within ~2 min.
CACHE_FILE = os.path.join(tempfile.gettempdir(), "adgine_geo_skills_version.json")


def _debug_enabled():
    return os.environ.get("GEO_VERSION_CHECK_DEBUG") == "1" or "--verbose" in sys.argv


def _debug(msg):
    if _debug_enabled():
        print(f"[check_version] {msg}", file=sys.stderr)


def _read_version_from_skill_md():
    """Fallback when installers (e.g. WorkBuddy) omit the root VERSION file."""
    skill_md = os.path.join(REPO_ROOT, "SKILL.md")
    if not os.path.isfile(skill_md):
        return None
    in_frontmatter = False
    with open(skill_md, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "---":
                in_frontmatter = not in_frontmatter
                if not in_frontmatter:
                    break
                continue
            if in_frontmatter:
                m = re.match(r'^version:\s*["\']?([^"\'#\s]+)', line)
                if m:
                    return m.group(1).strip()
    return None


def _read_local_version():
    if os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return f.read().strip()
    fallback = _read_version_from_skill_md()
    if fallback:
        _debug(f"VERSION file missing; using SKILL.md frontmatter ({fallback})")
        return fallback
    raise FileNotFoundError(VERSION_FILE)


def _fetch_remote_version():
    """Return the latest version string from GitHub, using a short-lived cache."""
    # Serve from cache if fresh
    try:
        with open(CACHE_FILE) as f:
            cached = json.load(f)
        if time.time() - cached.get("ts", 0) < CACHE_TTL and cached.get("latest"):
            return cached["latest"]
    except Exception:
        pass

    req = urllib.request.Request(
        REMOTE_VERSION_URL,
        headers={"User-Agent": "adgine-geo-skills-version-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        latest = resp.read().decode().strip()

    try:
        with open(CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "latest": latest}, f)
    except Exception:
        pass
    return latest


def _parse_version(v):
    """Return tuple of ints for semver comparison, e.g. 'v1.2.3' → (1, 2, 3)."""
    return tuple(int(x) for x in v.strip().lstrip("v").split("."))


def _is_git_repo(path):
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--git-dir"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_state():
    """Return the full version-state dict, or None on any error."""
    try:
        current = _read_local_version()
        latest = _fetch_remote_version()
        update_available = _parse_version(latest) > _parse_version(current)
        is_git = _is_git_repo(REPO_ROOT)
        return {
            "current": current,
            "latest": latest,
            "update_available": update_available,
            "install_type": "git" if is_git else "package",
            "update_command": f"git -C {REPO_ROOT} pull" if is_git else "",
            "release_url": RELEASE_URL,
        }
    except Exception as exc:
        _debug(f"check failed: {exc}")
        return None


def format_user_footer(state):
    """Human-readable update block for stdout (WorkBuddy and similar agents).

    Printed at the end of script output so agents that rewrite tool results
    still surface the message when they quote trailing lines.
    """
    if not state or not state.get("update_available"):
        return ""
    cur, lat = state["current"], state["latest"]
    if state.get("install_type") == "git":
        body = (
            f"⚠️ adgine-geo-skills v{lat} 已发布（当前 v{cur}）。"
            "跟我说「请帮我更新 adgine-geo-skills 到最新版本」即可升级。"
        )
    else:
        url = state.get("release_url", "")
        body = (
            f"⚠️ adgine-geo-skills v{lat} 已发布（当前 v{cur}）。"
            f"请前往 {url} 下载最新版并重新安装。"
        )
    return f"---\n{body}"


def emit_footer(stream=None):
    """Print the human-readable footer if an update is available."""
    stream = stream or sys.stdout
    footer = format_user_footer(get_state())
    if not footer:
        return
    try:
        stream.write(footer + "\n")
        stream.flush()
    except Exception:
        pass


def emit_notice(stream=None):
    """Print a single `_notice:` line to `stream` if an update is available.

    Writes to STDOUT by default so the agent harness reliably surfaces it in the
    tool result (some harnesses only feed stdout to the model). The `_notice:`
    prefix lets agents parse it before JSON on the same stream.

    Silent when up to date or on any error. Safe to call at the top of any
    skill script — never raises, never blocks.
    """
    stream = stream or sys.stdout
    state = get_state()
    if not state or not state.get("update_available"):
        return
    cur, lat = state["current"], state["latest"]
    if state.get("install_type") == "git":
        msg = (f"adgine-geo-skills {lat} available (current {cur}). "
               "Tell me: 请帮我更新 adgine-geo-skills 到最新版本")
    else:
        msg = (f"adgine-geo-skills {lat} available (current {cur}). "
               f"Download: {state.get('release_url', '')}")
    notice = {"update": {"current": cur, "latest": lat, "message": msg}}
    try:
        stream.write(f"_notice: {json.dumps(notice, ensure_ascii=False)}\n\n")
        stream.flush()
    except Exception:
        pass


def main():
    if "--notice" in sys.argv:
        emit_notice()
        sys.exit(0)
    if "--footer" in sys.argv:
        emit_footer()
        sys.exit(0)
    state = get_state()
    if state is not None:
        print(json.dumps(state, ensure_ascii=False))
    elif _debug_enabled():
        _debug("no state returned (see errors above)")
    sys.exit(0)


if __name__ == "__main__":
    main()
