from pathlib import Path

from pdf_tra.core.constants import (
    MAX_PAGES_WITHOUT_CONFIRM,
    MIN_EXTRACTABLE_TEXT_CHARS,
    PDF_MAGIC,
)
from pdf_tra.core.models import PipelineContext, TranslateOptions, TranslateResult


def test_pdf_magic_constant():
    assert PDF_MAGIC == b"%PDF"


def test_threshold_constants():
    assert MIN_EXTRACTABLE_TEXT_CHARS == 10
    assert MAX_PAGES_WITHOUT_CONFIRM == 500


def test_pipeline_context_effective_input_defaults(pipeline_context):
    assert pipeline_context.effective_input == pipeline_context.input_path


def test_pipeline_context_effective_input_uses_ocr_output(pipeline_context, tmp_path):
    ocr_pdf = tmp_path / "sample_ocr.pdf"
    ocr_pdf.write_bytes(b"%PDF-ocr")
    pipeline_context.working_pdf_path = ocr_pdf
    assert pipeline_context.effective_input == ocr_pdf


def test_translate_options_defaults():
    opts = TranslateOptions()
    assert opts.threads == 4
    assert opts.dry_run is False
    assert opts.confirm is False
    assert opts.ocr_mode is None


def test_translate_result_optional_paths():
    result = TranslateResult(mono_pdf=None, dual_pdf=None)
    assert result.mono_pdf is None
    assert result.elapsed_seconds == 0.0
