"""Validate AI Agent traffic-type filters against GEO-Api."""


TRAFFIC_TYPES = (
    "ai_search",
    "ai_training",
    "ai_assistant",
    "ai_agent",
    "ai_human_referral",
    "utm_ai",
)

_GROUPS = {
    "bot": ("ai_search", "ai_training", "ai_assistant", "ai_agent"),
    "bots": ("ai_search", "ai_training", "ai_assistant", "ai_agent"),
    "human": ("ai_human_referral", "utm_ai"),
    "humans": ("ai_human_referral", "utm_ai"),
}


def normalize_traffic_types(value):
    """Return a comma-separated backend filter, or ``None`` for all traffic."""
    raw = str(value or "").strip()
    if not raw or raw.casefold() == "all":
        return None
    output = []
    for part in raw.split(","):
        key = part.strip().casefold().replace("-", "_")
        if not key:
            continue
        expanded = _GROUPS.get(key, (key,))
        invalid = [item for item in expanded if item not in TRAFFIC_TYPES]
        if invalid:
            raise ValueError(
                f"unsupported traffic type {part.strip()!r}; use bot, human, all, or: "
                + ", ".join(TRAFFIC_TYPES)
            )
        for item in expanded:
            if item not in output:
                output.append(item)
    return ",".join(output) or None
