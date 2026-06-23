import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdftotext import PdftotextStep, build_inspect_suggestion


def test_build_inspect_suggestion():
    assert "可直接翻译" in build_inspect_suggestion("text")
    assert "OCR" in build_inspect_suggestion("scanned", ocr_available=True)
    assert "ocrmypdf" in build_inspect_suggestion("scanned", ocr_available=False)


def test_pdftotext_marks_text_pdf(pipeline_context, mock_run_command):
    mock_run_command(
        {
            ("pdftotext",): CommandResult(
                0,
                "A" * 20,
                "",
                ["pdftotext", "x", "-"],
            ),
        }
    )
    PdftotextStep().run(pipeline_context)
    assert pipeline_context.has_extractable_text is True
    assert pipeline_context.pdf_type == "text"


def test_pdftotext_scanned_raises_on_translate(pipeline_context, mock_run_command):
    mock_run_command(
        {
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    with pytest.raises(PdfTraError) as exc:
        PdftotextStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.SCANNED_PDF


def test_pdftotext_scanned_allowed_with_ocr_auto(pipeline_context, mock_run_command):
    pipeline_context.options = TranslateOptions(threads=4, ocr_mode="auto")
    mock_run_command(
        {
            ("pdftotext",): CommandResult(0, "", "", ["pdftotext"]),
        }
    )
    PdftotextStep().run(pipeline_context)
    assert pipeline_context.pdf_type == "scanned"
