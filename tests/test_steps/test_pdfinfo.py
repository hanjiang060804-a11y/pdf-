import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdfinfo import PdfinfoStep, is_pdf_file, parse_pdfinfo_output


def test_parse_pdfinfo_output(pdfinfo_output):
    info = parse_pdfinfo_output(pdfinfo_output)
    assert info.pages == 12
    assert info.encrypted is False
    assert info.title == "Sample Paper"


def test_is_pdf_file(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert is_pdf_file(pdf) is True
    txt = tmp_path / "a.txt"
    txt.write_text("hello", encoding="utf-8")
    assert is_pdf_file(txt) is False


def test_pdfinfo_step_sets_context(pipeline_context, pdfinfo_output, mock_run_command):
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo", "x"]),
        }
    )
    PdfinfoStep().run(pipeline_context)
    assert pipeline_context.pdf_info is not None
    assert pipeline_context.pdf_info.pages == 12


def test_pdfinfo_encrypted_raises(pipeline_context, mock_run_command):
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(
                0,
                "Pages: 1\nEncrypted: yes\n",
                "",
                ["pdfinfo"],
            ),
        }
    )
    with pytest.raises(PdfTraError) as exc:
        PdfinfoStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.PDF_ENCRYPTED


def test_pdfinfo_large_file_requires_confirm(pipeline_context, mock_run_command):
    pipeline_context.options = TranslateOptions(threads=4, confirm=False)
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(
                0,
                "Pages: 501\nEncrypted: no\n",
                "",
                ["pdfinfo"],
            ),
        }
    )
    with pytest.raises(PdfTraError) as exc:
        PdfinfoStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.CONFIRMATION_REQUIRED
