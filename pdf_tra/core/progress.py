from __future__ import annotations

import re

_PAGE_OF_RE = re.compile(r"page\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_FRACTION_RE = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")
_OCRMYPDF_LOG_PAGE_RE = re.compile(r"^\s*(\d+)\s+\S")
_GS_PAGE_RE = re.compile(r"^Page\s+(\d+)\b", re.IGNORECASE)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(line: str) -> str:
    return _ANSI_RE.sub("", line)


def parse_page_progress(line: str) -> tuple[int, int] | None:
    """Extract (current, total) page numbers from a subprocess log line."""
    for pattern in (_PAGE_OF_RE, _FRACTION_RE):
        match = pattern.search(line)
        if match:
            current, total = int(match.group(1)), int(match.group(2))
            if total > 0 and 0 < current <= total:
                return current, total
    return None


def parse_ocr_progress(line: str, page_total: int | None) -> tuple[int, int] | None:
    """Parse OCR progress from ocrmypdf / Ghostscript stderr lines."""
    cleaned = _strip_ansi(line).strip()
    if not cleaned:
        return None

    parsed = parse_page_progress(cleaned)
    if parsed is not None:
        return parsed

    if page_total and page_total > 0:
        match = _OCRMYPDF_LOG_PAGE_RE.match(cleaned)
        if match:
            current = int(match.group(1))
            if 0 < current <= page_total:
                return current, page_total

        gs_match = _GS_PAGE_RE.match(cleaned)
        if gs_match:
            current = int(gs_match.group(1))
            if 0 < current <= page_total:
                return current, page_total

    return None


def ocr_progress_percent(page_current: int, page_total: int) -> int:
    if page_total <= 0:
        return 10
    return 5 + int(45 * page_current / page_total)


def translate_progress_percent(page_current: int, page_total: int) -> int:
    if page_total <= 0:
        return 70
    return 50 + int(45 * page_current / page_total)
