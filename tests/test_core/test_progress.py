import pytest

from pdf_tra.core.progress import (
    ocr_progress_percent,
    parse_ocr_progress,
    parse_page_progress,
    translate_progress_percent,
)


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Processing page 3 of 12", (3, 12)),
        ("page 5 of 10", (5, 10)),
        ("  3/12  ", (3, 12)),
        ("no progress here", None),
    ],
)
def test_parse_page_progress(line, expected):
    assert parse_page_progress(line) == expected


def test_ocr_progress_percent():
    assert ocr_progress_percent(1, 10) == 9
    assert ocr_progress_percent(10, 10) == 50


def test_translate_progress_percent():
    assert translate_progress_percent(1, 10) == 54
    assert translate_progress_percent(10, 10) == 95


@pytest.mark.parametrize(
    "line,page_total,expected",
    [
        ("    3 [tesseract] read_params_file", 12, (3, 12)),
        ("Page 5", 57, (5, 57)),
        ("Postprocessing...", 12, None),
    ],
)
def test_parse_ocr_progress(line, page_total, expected):
    assert parse_ocr_progress(line, page_total) == expected
