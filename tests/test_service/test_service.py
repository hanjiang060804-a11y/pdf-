import json
from pathlib import Path

import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import ProgressUpdate, TranslateOptions
from pdf_tra.service import inspect_pdf, translate_pdf


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    p = tmp_path / "paper.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


@pytest.fixture
def stub_tools(monkeypatch):
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/usr/bin/{name}",
    )


@pytest.fixture
def inspect_mocks(mock_run_command, pdfinfo_output, stub_tools):
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(
                0,
                "Introduction to machine learning systems and applications.",
                "",
                ["pdftotext"],
            ),
        }
    )


def test_inspect_pdf_returns_language_fields(pdf_path, inspect_mocks):
    result = inspect_pdf(pdf_path)
    assert result.pdf_type == "text"
    assert result.detected_lang == "English"
    assert result.detected_lang_label == "英语"
    assert result.target_lang == "Simplified Chinese"
    assert result.can_translate is True
    assert result.lang_detect_fallback is False


def test_inspect_pdf_scanned_not_translatable(
    pdf_path, mock_run_command, pdfinfo_output, stub_tools, monkeypatch
):
    from pdf_tra.core.ocr import OcrCapability

    monkeypatch.setattr(
        "pdf_tra.service.check_ocr_capability",
        lambda: OcrCapability(False, False, False, False, "missing"),
    )
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    result = inspect_pdf(pdf_path)
    assert result.pdf_type == "scanned"
    assert result.needs_ocr is True
    assert result.can_translate is False


def test_inspect_pdf_scanned_ocr_available(
    pdf_path, mock_run_command, pdfinfo_output, stub_tools, monkeypatch
):
    from pdf_tra.core.ocr import OcrCapability

    monkeypatch.setattr(
        "pdf_tra.service.check_ocr_capability",
        lambda: OcrCapability(True, True, True, True, None),
    )
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    result = inspect_pdf(pdf_path)
    assert result.needs_ocr is True
    assert result.ocr_available is True
    assert result.can_translate is True
    assert "OCR" in result.suggestion


def test_inspect_pdf_missing_file(tmp_path: Path):
    with pytest.raises(PdfTraError) as exc:
        inspect_pdf(tmp_path / "missing.pdf")
    assert exc.value.exit_code is ExitCode.FILE_NOT_FOUND


def test_translate_pdf_success(
    pdf_path,
    tmp_path: Path,
    mock_run_command,
    pdfinfo_output,
    sample_config,
    stub_tools,
    monkeypatch,
):
    out = tmp_path / "output"
    out.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")
    stem = pdf_path.stem
    (out / f"{stem}-mono.pdf").write_bytes(b"%PDF")
    (out / f"{stem}-dual.pdf").write_bytes(b"%PDF")

    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(
                0,
                "Sample extractable document text for translation.",
                "",
                ["pdftotext"],
            ),
            ("pdf2zh",): CommandResult(0, "done", "", ["pdf2zh"]),
        }
    )
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda cfg: None)

    result = translate_pdf(pdf_path, out, config_path=config_path)
    assert result.mono_pdf is not None
    assert result.dual_pdf is not None


def test_translate_pdf_scanned_raises_without_ocr_flag(
    pdf_path, tmp_path: Path, mock_run_command, pdfinfo_output, stub_tools, monkeypatch
):
    from pdf_tra.core.ocr import OcrCapability

    monkeypatch.setattr(
        "pdf_tra.service.check_ocr_capability",
        lambda: OcrCapability(True, True, True, True, None),
    )
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    with pytest.raises(PdfTraError) as exc:
        translate_pdf(pdf_path, tmp_path / "out")
    assert exc.value.exit_code is ExitCode.SCANNED_PDF


def test_translate_pdf_scanned_with_ocr_auto(
    pdf_path,
    tmp_path: Path,
    pdfinfo_output,
    sample_config,
    stub_tools,
    monkeypatch,
):
    from pdf_tra.core.ocr import OcrCapability

    monkeypatch.setattr(
        "pdf_tra.service.check_ocr_capability",
        lambda: OcrCapability(True, True, True, True, None),
    )
    out = tmp_path / "output"
    out.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config), encoding="utf-8")
    stem = pdf_path.stem
    (out / f"{stem}-mono.pdf").write_bytes(b"%PDF")
    (out / f"{stem}-dual.pdf").write_bytes(b"%PDF")

    pdftotext_calls = {"n": 0}

    def side_effect(argv, **kwargs):
        if argv[0] == "pdftotext":
            pdftotext_calls["n"] += 1
            if pdftotext_calls["n"] == 1:
                return CommandResult(0, "", "", argv)
            return CommandResult(
                0,
                "Sample extractable document text for translation.",
                "",
                argv,
            )
        if argv[0] == "pdfinfo":
            return CommandResult(0, pdfinfo_output, "", argv)
        if argv[0] == "ocrmypdf":
            ocr_path = Path(argv[2])
            ocr_path.write_bytes(b"%PDF-ocr")
            return CommandResult(0, "", "", argv)
        if "pdf2zh" in Path(argv[0]).name.lower():
            ocr_stem = Path(argv[1]).stem
            (out / f"{ocr_stem}-mono.pdf").write_bytes(b"%PDF")
            (out / f"{ocr_stem}-dual.pdf").write_bytes(b"%PDF")
            return CommandResult(0, "done", "", argv)
        raise AssertionError(argv)

    for target in (
        "pdf_tra.adapters.subprocess.run_command",
        "pdf_tra.adapters.subprocess.run_command_streaming",
        "pdf_tra.steps.pdfinfo.run_command",
        "pdf_tra.steps.pdftotext.run_command",
        "pdf_tra.steps.pdftotext_post.run_command",
        "pdf_tra.steps.translate_classic.run_command_streaming",
    ):
        monkeypatch.setattr(target, side_effect)
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda cfg: None)

    updates: list[ProgressUpdate] = []
    result = translate_pdf(
        pdf_path,
        out,
        config_path=config_path,
        options=TranslateOptions(ocr_mode="auto"),
        progress_callback=updates.append,
    )
    assert result.mono_pdf is not None
    assert any(u.phase == "done" for u in updates)
