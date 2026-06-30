#!/usr/bin/env python3
"""
Check whether a newer version of adgine-geo-skills is available on GitHub.

Outputs JSON to stdout. Exits 0 always — errors are silently suppressed
so the calling agent's main flow is never blocked.

Output schema:
  {
    "current": "1.1.0",
    "latest": "1.2.0",
    "update_available": true,
    "install_type": "git" | "package",
    "update_command": "git -C /path/to/dir pull",   // git only
    "release_url": "https://github.com/..."
  }

On any error (network, parse, etc.): exits 0 with no output.
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(REPO_ROOT, "VERSION")
REMOTE_VERSION_URL = (
    "https://raw.githubusercontent.com/adgine-ai/adgine-geo-skills/main/VERSION"
)
RELEASE_URL = "https://github.com/adgine-ai/adgine-geo-skills/releases/latest"
TIMEOUT = 5


def _read_local_version():
    with open(VERSION_FILE) as f:
        return f.read().strip()


def _fetch_remote_version():
    req = urllib.request.Request(
        REMOTE_VERSION_URL,
        headers={"User-Agent": "adgine-geo-skills-version-check/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode().strip()


def _parse_version(v):
    """Return tuple of ints for semver comparison, e.g. '1.2.3' → (1, 2, 3)."""
    return tuple(int(x) for x in v.lstrip("v").split("."))


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


def main():
    try:
        current = _read_local_version()
        latest = _fetch_remote_version()
        update_available = _parse_version(latest) > _parse_version(current)

        is_git = _is_git_repo(REPO_ROOT)
        install_type = "git" if is_git else "package"
        update_command = f"git -C {REPO_ROOT} pull" if is_git else ""

        print(json.dumps({
            "current": current,
            "latest": latest,
            "update_available": update_available,
            "install_type": install_type,
            "update_command": update_command,
            "release_url": RELEASE_URL,
        }, ensure_ascii=False))
    except Exception:
        # Silent failure — never block the agent's main task
        sys.exit(0)


if __name__ == "__main__":
    main()
