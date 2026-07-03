"""Version-update notice for site-audit scripts.

site-audit scripts are self-contained and do NOT import _client.py, so they
call this helper at startup to emit the same `_notice:` line the API skills do.

Delegates to <repo_root>/scripts/check_version.py (single source of truth).
Silent on any error, timeout, or when check_version.py is absent (e.g.
a standalone site-audit export).
"""
import atexit
import importlib.util
import os
import sys

_FOOTER_REGISTERED = False


def _repo_root():
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


def _load_check_version_module():
    path = os.path.join(_repo_root(), "scripts", "check_version.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("geo_check_version", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _print_footer():
    try:
        mod = _load_check_version_module()
        if mod is not None:
            mod.emit_footer()
    except Exception:
        pass


def emit():
    global _FOOTER_REGISTERED
    mod = _load_check_version_module()
    if mod is None:
        return
    try:
        mod.emit_human()
        mod.emit_notice()
    except Exception:
        pass
    if not _FOOTER_REGISTERED:
        atexit.register(_print_footer)
        _FOOTER_REGISTERED = True
