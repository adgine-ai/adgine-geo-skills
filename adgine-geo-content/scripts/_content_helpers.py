"""Small helpers shared by GEO content lifecycle scripts."""
import os


def short_id(value):
    text = str(value or "")
    return f"{text[:8]}…" if len(text) > 8 else (text or "—")


def selected_version_id(content):
    """Resolve the API-selected/latest version without asking the user for an ID."""
    selected = content.get("selected_version_id")
    if selected:
        return str(selected)
    versions = content.get("versions") or []
    if not versions:
        return None
    latest = max(versions, key=lambda item: item.get("version_no") or 0)
    return str(latest.get("id")) if latest.get("id") else None


def read_text(path, label):
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise ValueError(f"could not read {label} {path!r} — {exc}") from exc
