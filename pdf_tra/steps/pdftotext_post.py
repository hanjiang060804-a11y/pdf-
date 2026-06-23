from __future__ import annotations

from pdf_tra.adapters.subprocess import run_command
from pdf_tra.core.constants import MIN_EXTRACTABLE_TEXT_CHARS, TOOL_PDFTOTEXT
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.lang import detect_language
from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step


class PdftotextPostStep(Step):
    """Re-extract text after OCR and detect source language."""

    name = "pdftotext_post"
    required = False

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.ocr_output_path is not None

    def run(self, ctx: PipelineContext) -> None:
        path = ctx.effective_input
        result = run_command([TOOL_PDFTOTEXT, str(path), "-"])
        if result.returncode != 0:
            raise PdfTraError(
                f"pdftotext 失败: {result.stderr.strip()}",
                ExitCode.EXTERNAL_CMD_FAILED,
            )
        text = result.stdout.strip()
        char_count = len(text)
        ctx.char_count = char_count
        ctx.text_sample = text[:8000]
        has_text = char_count >= MIN_EXTRACTABLE_TEXT_CHARS
        ctx.has_extractable_text = has_text

        if not has_text:
            raise PdfTraError(
                "OCR 后仍无法提取足够文字，可能是空白页或 OCR 语言包缺失。",
                ExitCode.SCANNED_PDF,
            )

        lang_in, _, _ = detect_language(text)
        ctx.options.lang_in = lang_in
        ctx.report_progress(
            phase="translate",
            progress=50,
            message="文字识别完成，正在翻译…",
        )
