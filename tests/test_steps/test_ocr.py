import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.ocr import OcrStep, _build_ocr_argv


def test_ocr_should_not_run_for_text_pdf(pipeline_context):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = True
    assert OcrStep().should_run(pipeline_context) is False


def test_ocr_should_not_run_without_auto_mode(pipeline_context):
    pipeline_context.has_extractable_text = False
    assert OcrStep().should_run(pipeline_context) is False


def test_ocr_should_run_for_scanned_with_auto(pipeline_context):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = False
    assert OcrStep().should_run(pipeline_context) is True


def test_ocr_missing_tool_raises(pipeline_context, monkeypatch):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = False
    monkeypatch.setattr("pdf_tra.adapters.subprocess.which_tool", lambda n: None)
    with pytest.raises(PdfTraError) as exc:
        OcrStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.TOOL_NOT_FOUND


def test_ocr_success_sets_working_path(pipeline_context, monkeypatch, tmp_path):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = False
    pipeline_context.output_dir = tmp_path / "out"
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.which_tool",
        lambda n: "/usr/bin/ocrmypdf",
    )

    def fake_run(argv, **kwargs):
        from pathlib import Path

        out = argv[2]
        Path(out).write_bytes(b"%PDF-ocr-out")
        return CommandResult(0, "", "", argv)

    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.run_command",
        fake_run,
    )
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.run_command_streaming",
        fake_run,
    )
    OcrStep().run(pipeline_context)
    assert pipeline_context.working_pdf_path is not None
    assert pipeline_context.working_pdf_path.exists()


def test_ocr_reports_progress_on_stderr(pipeline_context, monkeypatch, tmp_path):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = False
    pipeline_context.output_dir = tmp_path / "out"
    pipeline_context.pdf_info = type("I", (), {"pages": 12})()
    updates = []

    pipeline_context.progress_callback = updates.append
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.which_tool",
        lambda n: "/usr/bin/ocrmypdf",
    )

    def fake_stream(argv, on_stderr_line=None, on_stdout_line=None, **kwargs):
        handler = on_stderr_line or on_stdout_line
        if handler:
            handler("    2 [tesseract] running OCR")
        from pathlib import Path

        Path(argv[2]).write_bytes(b"%PDF")
        return CommandResult(0, "", "", argv)

    monkeypatch.setattr("pdf_tra.adapters.subprocess.run_command_streaming", fake_stream)
    OcrStep().run(pipeline_context)
    assert any(u.page_current == 2 and u.page_total == 12 for u in updates)


def test_ocr_command_failure(pipeline_context, monkeypatch, tmp_path):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    pipeline_context.has_extractable_text = False
    pipeline_context.output_dir = tmp_path / "out"
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.which_tool",
        lambda n: "/usr/bin/ocrmypdf",
    )
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.run_command",
        lambda argv, **kw: CommandResult(1, "", "ocr failed", argv),
    )
    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.run_command_streaming",
        lambda argv, **kw: CommandResult(1, "", "ocr failed", argv),
    )
    with pytest.raises(PdfTraError) as exc:
        OcrStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.EXTERNAL_CMD_FAILED


def test_build_ocr_argv_uses_fast_flags(tmp_path):
    argv = _build_ocr_argv(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert "--output-type" in argv and "pdf" in argv
    assert "-O" in argv and "0" in argv
    assert "-j" in argv
