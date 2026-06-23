"""Backward-compatible exports; implementation lives in translate_* modules."""

from __future__ import annotations

from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step
from pdf_tra.steps.translate import TranslateStep
from pdf_tra.steps.translate_outputs import build_pdf2zh_argv, locate_outputs

_build_pdf2zh_argv = build_pdf2zh_argv
_locate_outputs = locate_outputs


class Pdf2zhStep(Step):
    """Alias for TranslateStep (registry name ``pdf2zh``)."""

    name = "pdf2zh"

    def should_run(self, ctx: PipelineContext) -> bool:
        return TranslateStep().should_run(ctx)

    def run(self, ctx: PipelineContext) -> None:
        TranslateStep().run(ctx)
