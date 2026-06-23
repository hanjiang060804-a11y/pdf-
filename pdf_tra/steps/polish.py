from __future__ import annotations

import logging
import re

from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step

logger = logging.getLogger(__name__)

_FORMULA_FONT_RE = re.compile(r"(mono|math|symbol|code|cmr|cmsy|msam|msbm)", re.I)
_MAX_SHRINK_PASSES = 6
_SHRINK_FACTOR = 0.92


class PolishStep(Step):
    name = "polish"

    def should_run(self, ctx: PipelineContext) -> bool:
        return (
            ctx.pipeline_name == "translate"
            and not ctx.options.dry_run
            and bool(ctx.options.layout_polish)
            and ctx.translate_result is not None
            and ctx.translate_result.mono_pdf is not None
        )

    def run(self, ctx: PipelineContext) -> None:
        mono = ctx.translate_result.mono_pdf
        assert mono is not None
        page_total = ctx.pdf_info.pages if ctx.pdf_info else None
        ctx.report_progress(
            phase="polish",
            progress=96,
            message="正在优化排版…",
            page_current=page_total,
            page_total=page_total,
        )
        try:
            adjusted = polish_mono_pdf(mono)
            logger.info("排版优化完成，调整 %s 处文本块", adjusted)
        except Exception as exc:
            logger.warning("排版优化跳过: %s", exc)
            ctx.report_progress(
                phase="polish",
                progress=98,
                message="排版优化已跳过",
                page_current=page_total,
                page_total=page_total,
            )
            return
        ctx.report_progress(
            phase="polish",
            progress=98,
            message=f"排版优化完成（调整 {adjusted} 处）",
            page_current=page_total,
            page_total=page_total,
        )


def polish_mono_pdf(path) -> int:
    import fitz

    doc = fitz.open(path)
    adjusted = 0
    try:
        for page in doc:
            adjusted += _polish_page(page)
        if adjusted:
            doc.save(path, deflate=True, garbage=3)
    finally:
        doc.close()
    return adjusted


def _polish_page(page) -> int:
    import fitz

    data = page.get_text("dict")
    adjusted = 0
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                font = span.get("font", "")
                if _FORMULA_FONT_RE.search(font):
                    continue
                size = float(span.get("size", 12))
                bbox = fitz.Rect(span["bbox"])
                if bbox.width <= 0:
                    continue
                needed = fitz.get_text_length(text, fontsize=size)
                if needed <= bbox.width * 1.02:
                    continue
                new_size = size
                for _ in range(_MAX_SHRINK_PASSES):
                    new_size *= _SHRINK_FACTOR
                    if fitz.get_text_length(text, fontsize=new_size) <= bbox.width * 1.02:
                        break
                if new_size >= size * 0.99:
                    continue
                page.add_redact_annot(bbox, fill=(1, 1, 1))
                page.apply_redactions()
                try:
                    page.insert_text(
                        (bbox.x0, bbox.y1 - new_size * 0.15),
                        text,
                        fontsize=new_size,
                        fontname="china-s",
                    )
                except Exception:
                    page.insert_text(
                        (bbox.x0, bbox.y1 - new_size * 0.15),
                        text,
                        fontsize=new_size,
                    )
                adjusted += 1
    return adjusted
