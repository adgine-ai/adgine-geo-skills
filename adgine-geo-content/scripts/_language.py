"""Normalize user-facing language names to the current GEO-Api contract."""


SUPPORTED_LANGUAGES = (
    "English",
    "Chinese (Simplified)",
    "Chinese (Traditional)",
    "Spanish",
    "French",
    "German",
    "Japanese",
    "Korean",
    "Portuguese",
    "Russian",
    "Arabic",
    "Hindi",
    "Italian",
    "Dutch",
    "Swedish",
    "Turkish",
    "Thai",
    "Vietnamese",
    "Indonesian",
    "Malay",
    "Polish",
    "Danish",
    "Norwegian",
    "Finnish",
    "Czech",
    "Romanian",
    "Hebrew",
    "Bengali",
    "Urdu",
    "Filipino",
)

_CANONICAL = {value.casefold(): value for value in SUPPORTED_LANGUAGES}

_ALIASES = {
    "en": "English",
    "en-us": "English",
    "en-gb": "English",
    "english (en-us)": "English",
    "english (en-gb)": "English",
    "英文": "English",
    "英语": "English",
    "英語": "English",
    "zh": "Chinese (Simplified)",
    "zh-cn": "Chinese (Simplified)",
    "zh-hans": "Chinese (Simplified)",
    "chinese": "Chinese (Simplified)",
    "chinese simplified": "Chinese (Simplified)",
    "chinese (zh-cn)": "Chinese (Simplified)",
    "中文": "Chinese (Simplified)",
    "汉语": "Chinese (Simplified)",
    "漢語": "Chinese (Simplified)",
    "简体中文": "Chinese (Simplified)",
    "簡體中文": "Chinese (Simplified)",
    "中文简体": "Chinese (Simplified)",
    "中文簡體": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "zh-hant": "Chinese (Traditional)",
    "traditional chinese": "Chinese (Traditional)",
    "chinese traditional": "Chinese (Traditional)",
    "chinese (zh-tw)": "Chinese (Traditional)",
    "繁体中文": "Chinese (Traditional)",
    "繁體中文": "Chinese (Traditional)",
    "正体中文": "Chinese (Traditional)",
    "正體中文": "Chinese (Traditional)",
    "中文繁体": "Chinese (Traditional)",
    "中文繁體": "Chinese (Traditional)",
    "es": "Spanish",
    "es-es": "Spanish",
    "spanish (es-es)": "Spanish",
    "fr": "French",
    "fr-fr": "French",
    "french (fr-fr)": "French",
    "de": "German",
    "de-de": "German",
    "german (de-de)": "German",
    "ja": "Japanese",
    "ja-jp": "Japanese",
    "japanese (ja-jp)": "Japanese",
    "日语": "Japanese",
    "日語": "Japanese",
    "日文": "Japanese",
    "ko": "Korean",
    "ko-kr": "Korean",
    "korean (ko-kr)": "Korean",
    "韩语": "Korean",
    "韓語": "Korean",
    "韩文": "Korean",
    "韓文": "Korean",
    "pt": "Portuguese",
    "pt-br": "Portuguese",
    "portuguese (pt-br)": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "it": "Italian",
    "nl": "Dutch",
    "sv": "Swedish",
    "tr": "Turkish",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "pl": "Polish",
    "da": "Danish",
    "no": "Norwegian",
    "nb": "Norwegian",
    "nn": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "ro": "Romanian",
    "he": "Hebrew",
    "iw": "Hebrew",
    "bn": "Bengali",
    "ur": "Urdu",
    "fil": "Filipino",
    "tl": "Filipino",
}


def normalize_language(value):
    """Return a GEO-Api canonical language, preserving ``None`` inheritance."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    canonical = _CANONICAL.get(raw.casefold())
    if canonical:
        return canonical
    key = raw.casefold().replace("_", "-")
    canonical = _ALIASES.get(key)
    if canonical:
        return canonical
    raise ValueError(
        f"unsupported language {value!r}; use a GEO-Api language such as "
        "English, Chinese (Simplified), Chinese (Traditional), zh-CN, or zh-TW"
    )
