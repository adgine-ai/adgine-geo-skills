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
        notice = (out.stdout or "") + (out.stderr or "")
        if notice.strip():
            # Always stdout — distinct _notice: prefix before JSON (see _client.py).
            sys.stdout.write(notice if notice.endswith("\n") else notice + "\n")
            sys.stdout.flush()
    except Exception:
        pass
