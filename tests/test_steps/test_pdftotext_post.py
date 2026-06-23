import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import ProgressUpdate
from pdf_tra.steps.pdftotext_post import PdftotextPostStep


def test_pdftotext_post_should_not_run_without_ocr(pipeline_context):
    assert PdftotextPostStep().should_run(pipeline_context) is False


def test_pdftotext_post_should_run_after_ocr(pipeline_context, tmp_path):
    pipeline_context.ocr_output_path = tmp_path / "x_ocr.pdf"
    pipeline_context.working_pdf_path = pipeline_context.ocr_output_path
    assert PdftotextPostStep().should_run(pipeline_context) is True


def test_pdftotext_post_sets_lang_in(pipeline_context, tmp_path, monkeypatch):
    ocr_pdf = tmp_path / "sample_ocr.pdf"
    ocr_pdf.write_bytes(b"%PDF")
    pipeline_context.ocr_output_path = ocr_pdf
    pipeline_context.working_pdf_path = ocr_pdf

    monkeypatch.setattr(
        "pdf_tra.steps.pdftotext_post.run_command",
        lambda argv, **kw: CommandResult(
            0,
            "Introduction to machine learning systems and applications.",
            "",
            argv,
        ),
    )
    updates: list[ProgressUpdate] = []
    pipeline_context.progress_callback = updates.append

    PdftotextPostStep().run(pipeline_context)
    assert pipeline_context.options.lang_in == "English"
    assert pipeline_context.has_extractable_text is True
    assert updates[-1].phase == "translate"


def test_pdftotext_post_fails_when_still_no_text(pipeline_context, tmp_path, monkeypatch):
    ocr_pdf = tmp_path / "sample_ocr.pdf"
    ocr_pdf.write_bytes(b"%PDF")
    pipeline_context.ocr_output_path = ocr_pdf
    pipeline_context.working_pdf_path = ocr_pdf
    monkeypatch.setattr(
        "pdf_tra.steps.pdftotext_post.run_command",
        lambda argv, **kw: CommandResult(0, "", "", argv),
    )
    with pytest.raises(PdfTraError) as exc:
        PdftotextPostStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.SCANNED_PDF
