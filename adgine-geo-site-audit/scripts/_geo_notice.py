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
            # Forward to stdout so every harness surfaces it — EXCEPT the one
            # case that emits pure JSON on stdout: geo_collect without --output.
            script = os.path.basename(sys.argv[0]) if sys.argv else ""
            json_to_stdout = (
                script.startswith("geo_collect")
                and not ({"--output", "-o"} & set(sys.argv))
            )
            dest = sys.stderr if json_to_stdout else sys.stdout
            dest.write(notice if notice.endswith("\n") else notice + "\n")
    except Exception:
        pass
