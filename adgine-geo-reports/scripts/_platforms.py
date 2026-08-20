"""Normalize GEO analytics platform filters without constraining traffic IDs."""


SUPPORTED_PLATFORMS = (
    "openai", "perplexity", "google_aio", "deepseek",
    "yuanbao", "qwen", "doubao", "baidu",
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


def normalize_platforms(values):
    """Return de-duplicated GEO-Api platform IDs from repeated/CSV values."""
    output = []
    for raw in values or []:
        for part in str(raw).split(","):
            value = part.strip()
            if not value:
                continue
            key = " ".join(value.casefold().replace("-", " ").split())
            canonical = _ALIASES.get(key)
            if canonical is None:
                if value.casefold() == "gemini":
                    raise ValueError(
                        "unsupported platform 'gemini'; use google_aio only for "
                        "Google AI Overviews"
                    )
                raise ValueError(
                    f"unsupported GEO analytics platform {value!r}; use one of: "
                    + ", ".join(SUPPORTED_PLATFORMS)
                )
            if canonical not in output:
                output.append(canonical)
    return output
