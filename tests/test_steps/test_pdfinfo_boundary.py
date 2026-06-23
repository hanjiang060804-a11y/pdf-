import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdfinfo import PdfinfoStep, is_pdf_file, parse_pdfinfo_output


def test_parse_pdfinfo_missing_pages_defaults_zero():
    info = parse_pdfinfo_output("Title: x\nEncrypted: no\n")
    assert info.pages == 0


def test_parse_pdfinfo_empty_stdout():
    info = parse_pdfinfo_output("")
    assert info.pages == 0
    assert info.encrypted is False


def test_pdfinfo_zero_pages_raises(pipeline_context, mock_run_command):
    mock_run_command(
        {("pdfinfo",): CommandResult(0, "Pages: 0\nEncrypted: no\n", "", ["pdfinfo"])}
    )
    with pytest.raises(PdfTraError) as exc:
        PdfinfoStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.PDF_CORRUPT


def test_pdfinfo_command_failure(pipeline_context, mock_run_command):
    mock_run_command(
        {("pdfinfo",): CommandResult(1, "", "Syntax Error", ["pdfinfo"])}
    )
    with pytest.raises(PdfTraError) as exc:
        PdfinfoStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.PDF_CORRUPT


def test_pdfinfo_exactly_500_pages_ok_without_confirm(pipeline_context, mock_run_command):
    pipeline_context.options = TranslateOptions(confirm=False)
    mock_run_command(
        {("pdfinfo",): CommandResult(0, "Pages: 500\nEncrypted: no\n", "", ["pdfinfo"])}
    )
    PdfinfoStep().run(pipeline_context)
    assert pipeline_context.pdf_info.pages == 500


def test_pdfinfo_500_pages_with_confirm(pipeline_context, mock_run_command):
    pipeline_context.options = TranslateOptions(confirm=True)
    mock_run_command(
        {("pdfinfo",): CommandResult(0, "Pages: 501\nEncrypted: no\n", "", ["pdfinfo"])}
    )
    PdfinfoStep().run(pipeline_context)
    assert pipeline_context.pdf_info.pages == 501


def test_is_pdf_file_empty_file(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    assert is_pdf_file(empty) is False


def test_is_pdf_file_missing_file(tmp_path):
    assert is_pdf_file(tmp_path / "nope.pdf") is False


def test_is_pdf_file_pdf_prefix_only(tmp_path):
    f = tmp_path / "minimal.pdf"
    f.write_bytes(b"%PDF")
    assert is_pdf_file(f) is True
