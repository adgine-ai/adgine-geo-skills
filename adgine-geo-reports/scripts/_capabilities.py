"""Capability discovery with a credential-free disk cache."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from _client import ApiError


SCHEMA_VERSION = "1.0"
DEFAULT_CACHE_TTL_SECONDS = 2 * 60 * 60


def _cache_ttl_seconds():
    """Return the capability-cache TTL; zero forces a fresh probe."""
    raw = os.environ.get("GEO_REPORT_CAPABILITY_CACHE_TTL_SECONDS")
    if raw is None:
        return DEFAULT_CACHE_TTL_SECONDS
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_CACHE_TTL_SECONDS


def _cache_dir():
    configured = os.environ.get("GEO_REPORT_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "adgine-geo-reports"


def _cache_path(base, project_id):
    # Only the API origin and project ID participate; credentials are never persisted.
    identity = f"{str(base).rstrip('/')}\n{project_id}".encode("utf-8")
    return _cache_dir() / f"capabilities-{hashlib.sha256(identity).hexdigest()[:24]}.json"


def _read_cache(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
            return None
        return value
    except (OSError, ValueError, TypeError):
        return None


def _write_cache(path, data, saved_at=None):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"saved_at": time.time() if saved_at is None else saved_at, "data": data}
        fd, temporary = tempfile.mkstemp(prefix="capabilities-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
    except OSError:
        # A read-only home directory must not prevent report generation.
        return


def _legacy(reason, warning):
    return {
        "schema_version": SCHEMA_VERSION,
        "features": {},
        "legacy": True,
        "reason": reason,
    }, warning


def discover_capabilities(client, now=None):
    """Return ``(capabilities, warning)`` using a two-hour disk cache by default.

    Authentication/authorization failures are always raised. A discovery outage may
    use stale cache, or legacy mode with an explicit warning when no cache exists.
    """
    now = time.time() if now is None else now
    path = _cache_path(getattr(client, "base", "injected-client"), client.project_id)
    cached = _read_cache(path)
    if cached and now - float(cached.get("saved_at", 0)) <= _cache_ttl_seconds():
        return cached["data"], None

    endpoint = f"/api/projects/{client.project_id}/report-data/capabilities"
    try:
        data = client.get(endpoint) or {}
    except ApiError as exc:
        if exc.status_code in (401, 403):
            raise
        if exc.status_code in (404, 501):
            return _legacy(
                "capability_endpoint_unavailable",
                "Report-data capability endpoint is unavailable; legacy API workflow used.",
            )
        if cached:
            return cached["data"], "Capability discovery failed; stale cached capabilities used."
        return _legacy(
            "capability_discovery_failed",
            "Capability discovery failed with no cache; legacy API workflow used.",
        )

    if data.get("schema_version") != SCHEMA_VERSION:
        return _legacy(
            "unsupported_schema_version",
            f"Unsupported report-data schema {data.get('schema_version')!r}; legacy API workflow used.",
        )
    if not isinstance(data.get("features"), dict):
        return _legacy(
            "invalid_capability_response",
            "Invalid capability response; legacy API workflow used.",
        )
    _write_cache(path, data, saved_at=now)
    return data, None


def supports(capabilities, feature):
    return not capabilities.get("legacy") and capabilities.get("features", {}).get(feature) is True
