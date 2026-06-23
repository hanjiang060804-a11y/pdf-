from __future__ import annotations

from pdf_tra.adapters.subprocess import run_command
from pdf_tra.core.constants import MIN_EXTRACTABLE_TEXT_CHARS, TOOL_PDFTOTEXT
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step


class PdftotextStep(Step):
    name = "pdftotext"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

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
        ctx.pdf_type = "text" if has_text else "scanned"

        if ctx.pipeline_name == "translate" and not has_text and ctx.options.ocr_mode != "auto":
            raise PdfTraError(
                "检测到扫描版 PDF（无可提取文字）。"
                "请使用 --ocr auto（Phase 3）或先用 OCR 工具生成可搜索 PDF。",
                ExitCode.SCANNED_PDF,
            )


def build_inspect_suggestion(pdf_type: str, *, ocr_available: bool = False) -> str:
    if pdf_type == "text":
        return "可直接翻译"
    if ocr_available:
        return "扫描版 PDF，将先 OCR 识别文字再翻译（进度实时显示）"
    return "扫描版 PDF，需安装 ocrmypdf 与 Tesseract 后才能翻译"
