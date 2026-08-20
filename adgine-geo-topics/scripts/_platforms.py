"""Normalize user-facing AI platform names to GEO-Api platform IDs."""


SUPPORTED_PLATFORMS = (
    "openai",
    "perplexity",
    "google_aio",
    "deepseek",
    "yuanbao",
    "qwen",
    "doubao",
    "baidu",
)

_ALIASES = {
    "openai": "openai",
    "open ai": "openai",
    "chatgpt": "openai",
    "chat gpt": "openai",
    "perplexity": "perplexity",
    "perplexity ai": "perplexity",
    "google_aio": "google_aio",
    "google aio": "google_aio",
    "google ai overview": "google_aio",
    "google ai overviews": "google_aio",
    "deepseek": "deepseek",
    "deep seek": "deepseek",
    "深度求索": "deepseek",
    "yuanbao": "yuanbao",
    "tencent yuanbao": "yuanbao",
    "腾讯元宝": "yuanbao",
    "騰訊元寶": "yuanbao",
    "qwen": "qwen",
    "tongyi qianwen": "qwen",
    "通义千问": "qwen",
    "通義千問": "qwen",
    "doubao": "doubao",
    "豆包": "doubao",
    "baidu": "baidu",
    "ernie bot": "baidu",
    "文心一言": "baidu",
}


def normalize_platform(value):
    """Return one canonical GEO-Api platform ID."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("platform cannot be empty")
    key = " ".join(raw.casefold().replace("-", " ").split())
    canonical = _ALIASES.get(key)
    if canonical:
        return canonical
    if raw.casefold() == "gemini":
        raise ValueError(
            "unsupported platform 'gemini'; GEO-Api treats Google AI Overviews "
            "as google_aio and does not expose Gemini as a platform ID"
        )
    raise ValueError(
        f"unsupported platform {value!r}; use one of: "
        + ", ".join(SUPPORTED_PLATFORMS)
    )


def normalize_platforms(values):
    """Normalize comma-separated or repeated platform values and de-duplicate."""
    if values is None:
        return []
    raw_values = [values] if isinstance(values, str) else values
    output = []
    for raw in raw_values:
        for part in str(raw).split(","):
            if not part.strip():
                continue
            canonical = normalize_platform(part)
            if canonical not in output:
                output.append(canonical)
    return output
