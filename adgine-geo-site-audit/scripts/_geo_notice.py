"""Version-update notice for site-audit scripts.

site-audit scripts are self-contained and do NOT import _client.py, so they
call this helper at startup to emit the same `_notice:` line the API skills do.

Delegates to <repo_root>/scripts/check_version.py --notice (single source of
truth). Silent on any error, timeout, or when check_version.py is absent (e.g.
a standalone site-audit export).
"""
import os
import subprocess
import sys


def emit():
    check = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts", "check_version.py",
    )
    if not os.path.isfile(check):
        return
    try:
        out = subprocess.run(
            [sys.executable, check, "--notice"],
            capture_output=True, text=True, timeout=8,
        )
        # notice is emitted on stderr to keep stdout clean (may be pure JSON)
        if out.stderr.strip():
            sys.stderr.write(out.stderr)
    except Exception:
        pass
