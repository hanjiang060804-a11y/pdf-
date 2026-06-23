import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.constants import MIN_EXTRACTABLE_TEXT_CHARS
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdftotext import PdftotextStep


def test_pdftotext_exactly_min_chars_is_text(pipeline_context, mock_run_command):
    text = "x" * MIN_EXTRACTABLE_TEXT_CHARS
    mock_run_command(
        {("pdftotext",): CommandResult(0, text, "", ["pdftotext", "-"])}
    )
    PdftotextStep().run(pipeline_context)
    assert pipeline_context.has_extractable_text is True


def test_pdftotext_one_below_min_is_scanned(pipeline_context, mock_run_command):
    text = "x" * (MIN_EXTRACTABLE_TEXT_CHARS - 1)
    mock_run_command(
        {("pdftotext",): CommandResult(0, text, "", ["pdftotext", "-"])}
    )
    with pytest.raises(PdfTraError) as exc:
        PdftotextStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.SCANNED_PDF


def test_pdftotext_whitespace_only_counts_as_scanned(pipeline_context, mock_run_command):
    mock_run_command(
        {("pdftotext",): CommandResult(0, "   \n\t  ", "", ["pdftotext", "-"])}
    )
    with pytest.raises(PdfTraError):
        PdftotextStep().run(pipeline_context)


def test_pdftotext_command_failure(pipeline_context, mock_run_command):
    mock_run_command(
        {("pdftotext",): CommandResult(1, "", "error", ["pdftotext", "-"])}
    )
    with pytest.raises(PdfTraError) as exc:
        PdftotextStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.EXTERNAL_CMD_FAILED


def test_pdftotext_uses_effective_input_after_ocr(pipeline_context, tmp_path, monkeypatch):
    ocr_path = tmp_path / "ocr.pdf"
    ocr_path.write_bytes(b"%PDF")
    pipeline_context.working_pdf_path = ocr_path
    captured: list[list[str]] = []

    def side_effect(argv, **kwargs):
        captured.append(list(argv))
        return CommandResult(0, "a" * 20, "", argv)

    monkeypatch.setattr("pdf_tra.steps.pdftotext.run_command", side_effect)
    PdftotextStep().run(pipeline_context)
    assert str(ocr_path) in captured[0]
