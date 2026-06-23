import pytest

from pdf_tra.pipeline.registry import (
    INSPECT_STEPS,
    STEP_REGISTRY,
    TRANSLATE_STEPS,
    TRANSLATE_WITH_OCR,
    resolve_steps,
)


def test_all_registered_steps_resolve():
    for name in STEP_REGISTRY:
        steps = resolve_steps([name])
        assert len(steps) == 1
        assert steps[0].name == name


def test_translate_steps_order():
    steps = resolve_steps(TRANSLATE_STEPS)
    names = [s.name for s in steps]
    assert names == ["check_tools", "pdfinfo", "pdftotext", "translate", "polish"]


def test_translate_with_ocr_inserts_ocr():
    steps = resolve_steps(TRANSLATE_WITH_OCR)
    names = [s.name for s in steps]
    assert names.index("ocr") == 3
    assert names.index("pdftotext_post") == 4
    assert names.index("translate") == 5
    assert names.index("polish") == 6


def test_inspect_steps_exclude_translate():
    steps = resolve_steps(INSPECT_STEPS)
    names = [s.name for s in steps]
    assert "translate" not in names
    assert "pdf2zh" not in names


def test_resolve_empty_list():
    assert resolve_steps([]) == []


@pytest.mark.parametrize("invalid", ["", "unknown", "pdf2zh_extra"])
def test_resolve_unknown_step(invalid):
    with pytest.raises(KeyError):
        resolve_steps([invalid])
