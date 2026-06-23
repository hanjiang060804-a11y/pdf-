from __future__ import annotations

from pdf_tra.core.constants import MIN_EXTRACTABLE_TEXT_CHARS

TARGET_LANG = "Simplified Chinese"
TARGET_LANG_LABEL = "简体中文"
DEFAULT_LANG_IN = "English"
DEFAULT_LANG_IN_LABEL = "英语"

_LANG_LABELS: dict[str, str] = {
    "English": "英语",
    "Simplified Chinese": "简体中文",
    "Traditional Chinese": "繁体中文",
    "Japanese": "日语",
    "Korean": "韩语",
    "French": "法语",
    "German": "德语",
    "Spanish": "西班牙语",
    "Russian": "俄语",
}

_ISO_TO_PDF2ZH: dict[str, str] = {
    "en": "English",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "zh": "Simplified Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
}


def lang_label(pdf2zh_lang: str) -> str:
    return _LANG_LABELS.get(pdf2zh_lang, pdf2zh_lang)


def detect_language(text: str) -> tuple[str, str, bool]:
    """Return (pdf2zh lang code, Chinese label, used_fallback)."""
    cleaned = text.strip()
    if len(cleaned) < MIN_EXTRACTABLE_TEXT_CHARS:
        return DEFAULT_LANG_IN, DEFAULT_LANG_IN_LABEL, True

    try:
        from langdetect import LangDetectException, detect
    except ImportError:
        return _heuristic(cleaned)

    try:
        code = detect(cleaned).lower()
    except LangDetectException:
        return _heuristic(cleaned)
    except Exception:
        return _heuristic(cleaned)

    mapped = _ISO_TO_PDF2ZH.get(code) or _ISO_TO_PDF2ZH.get(code.split("-", 1)[0])
    if mapped is None:
        return DEFAULT_LANG_IN, DEFAULT_LANG_IN_LABEL, True
    return mapped, lang_label(mapped), False


def _heuristic(text: str) -> tuple[str, str, bool]:
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    if cjk / max(len(text), 1) > 0.15:
        return "Simplified Chinese", "简体中文", False
    return DEFAULT_LANG_IN, DEFAULT_LANG_IN_LABEL, True
