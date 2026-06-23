import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode
from pdf_tra.core.models import TranslateOptions
from pdf_tra.pipeline.registry import TRANSLATE_STEPS, TRANSLATE_WITH_OCR
from pdf_tra.pipeline.runner import run_pipeline


def test_full_translate_pipeline_success(
    pipeline_context,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
    tmp_path,
):
    out_dir = pipeline_context.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pipeline_context.input_path.stem
    (out_dir / f"{stem}-mono.pdf").write_bytes(b"%PDF-m")
    (out_dir / f"{stem}-dual.pdf").write_bytes(b"%PDF-d")

    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "enough text here", "", ["pdftotext"]),
            ("pdf2zh",): CommandResult(0, "ok", "", ["pdf2zh"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda c: None)

    ctx = run_pipeline(pipeline_context, TRANSLATE_STEPS)
    assert ctx.translate_result is not None
    assert ctx.translate_result.mono_pdf is not None


def test_pipeline_stops_on_scanned_pdf(
    pipeline_context,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
):
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )
    from pdf_tra.core.errors import PdfTraError

    with pytest.raises(PdfTraError) as exc:
        run_pipeline(pipeline_context, TRANSLATE_STEPS)
    assert exc.value.exit_code is ExitCode.SCANNED_PDF


def test_pipeline_skips_steps_when_should_run_false(
    pipeline_context,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
):
    pipeline_context.options = TranslateOptions(dry_run=True)
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "text content enough", "", ["pdftotext"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )
    ctx = run_pipeline(pipeline_context, TRANSLATE_WITH_OCR)
    assert ctx.translate_result is None
    assert ctx.ocr_output_path is None
