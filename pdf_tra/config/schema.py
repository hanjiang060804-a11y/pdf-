from pdf_tra.core.constants import DEFAULT_THREADS, MAX_THREADS

DEFAULT_CONFIG: dict = {
    "PDF2ZH_LANG_FROM": "English",
    "PDF2ZH_LANG_TO": "Simplified Chinese",
    "threads": DEFAULT_THREADS,
    "max_threads": MAX_THREADS,
    "translate_engine": "babeldoc",
    "translate_fallback": True,
    "layout_polish": True,
    "NOTO_FONT_PATH": "",
    "layout_prompt_path": "prompts/layout_concise.txt",
    "translators": [],
}


def clamp_threads(value: int, max_threads: int) -> int:
    if value < 1:
        raise ValueError("threads must be >= 1")
    return min(value, max_threads)
