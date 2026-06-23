from __future__ import annotations

import logging

from pdf_tra.core.layout_options import apply_layout_defaults
from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step
from pdf_tra.steps.translate_babeldoc import run_babeldoc
from pdf_tra.steps.translate_classic import run_classic

logger = logging.getLogger(__name__)


class TranslateStep(Step):
    name = "translate"

    def should_run(self, ctx: PipelineContext) -> bool:
        return ctx.pipeline_name == "translate" and not ctx.options.dry_run

    def run(self, ctx: PipelineContext) -> None:
        apply_layout_defaults(ctx)
        engine = ctx.options.translate_engine or "babeldoc"
        fallback = bool(ctx.options.translate_fallback)

        if engine == "classic":
            ctx.translate_result = run_classic(ctx)
            return

        try:
            ctx.translate_result = run_babeldoc(ctx)
        except Exception as exc:
            if not fallback:
                raise
            logger.warning("BabelDOC 失败，回退经典引擎: %s", exc)
            ctx.report_progress(
                phase="translate",
                progress=55,
                message="BabelDOC 失败，正在使用经典引擎…",
            )
            ctx.translate_result = run_classic(ctx)
