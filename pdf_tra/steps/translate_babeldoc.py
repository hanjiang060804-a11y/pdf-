from __future__ import annotations

import asyncio
import time
from pathlib import Path
from string import Template

from pdf_tra.config.schema import clamp_threads
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext, TranslateResult
from pdf_tra.core.progress import translate_progress_percent
from pdf_tra.steps.translate_outputs import locate_outputs


def run_babeldoc(ctx: PipelineContext) -> TranslateResult:
    from pdf_tra.config.loader import validate_config

    validate_config(ctx.config)
    _ensure_pdf2zh_config(ctx)

    from babeldoc.high_level import async_translate
    from babeldoc.high_level import init as yadt_init
    from babeldoc.main import create_progress_handler
    from babeldoc.translation_config import TranslationConfig
    from pdf2zh.high_level import download_remote_fonts

    yadt_init()
    input_path = ctx.effective_input
    lang_out = ctx.options.lang_out or ctx.config.get("PDF2ZH_LANG_TO", "Simplified Chinese")
    lang_in = ctx.options.lang_in or ctx.config.get("PDF2ZH_LANG_FROM", "English")
    page_total = ctx.pdf_info.pages if ctx.pdf_info else None

    ctx.report_progress(
        phase="translate",
        progress=55,
        message="正在翻译（BabelDOC）…",
        page_current=0 if page_total else None,
        page_total=page_total,
    )

    threads = clamp_threads(
        ctx.options.threads,
        int(ctx.config.get("max_threads", 8)),
    )
    prompt_template = _load_prompt_template(ctx)
    translator = _build_translator(ctx, lang_in, lang_out, prompt_template)
    download_remote_fonts(lang_out.lower())

    yadt_config = TranslationConfig(
        translator=translator,
        input_file=str(input_path),
        lang_in=lang_in,
        lang_out=lang_out,
        output_dir=str(ctx.output_dir),
        doc_layout_model=None,
        pages=ctx.options.pages,
        qps=threads,
        use_rich_pbar=False,
        skip_scanned_detection=True,
    )

    started = time.perf_counter()
    translate_result = _run_async_translate(ctx, yadt_config, page_total)
    elapsed = time.perf_counter() - started

    mono = (
        Path(translate_result.mono_pdf_path)
        if translate_result.mono_pdf_path
        else None
    )
    dual = (
        Path(translate_result.dual_pdf_path)
        if translate_result.dual_pdf_path
        else None
    )
    if mono is None or not mono.exists():
        mono, dual = locate_outputs(input_path, ctx.output_dir)
    return TranslateResult(mono_pdf=mono, dual_pdf=dual, elapsed_seconds=elapsed)


def _run_async_translate(ctx: PipelineContext, yadt_config, page_total: int | None):
    holder: dict = {}

    async def _coro() -> None:
        from babeldoc.main import create_progress_handler

        progress_context, progress_handler = create_progress_handler(yadt_config)

        def combined_handler(event: dict) -> None:
            progress_handler(event)
            _map_babeldoc_event(ctx, event, page_total)

        with progress_context:
            async for event in async_translate(yadt_config):
                combined_handler(event)
                if event["type"] == "finish":
                    holder["result"] = event["translate_result"]
                    break
                if event["type"] == "error":
                    error = event.get("error")
                    raise PdfTraError(
                        f"BabelDOC 翻译失败: {error}",
                        ExitCode.EXTERNAL_CMD_FAILED,
                    )

    asyncio.run(_coro())
    result = holder.get("result")
    if result is None:
        raise PdfTraError("BabelDOC 未返回翻译结果", ExitCode.EXTERNAL_CMD_FAILED)
    return result


def _map_babeldoc_event(
    ctx: PipelineContext,
    event: dict,
    page_total: int | None,
) -> None:
    if event.get("type") != "progress_update":
        return
    overall = float(event.get("overall_progress", 0))
    progress = 55 + int(40 * overall / 100)
    stage = event.get("stage", "translate")
    stage_current = int(event.get("stage_current", 0))
    stage_total = int(event.get("stage_total", 0))
    if page_total and stage_total == page_total:
        current, total = stage_current, stage_total
        message = f"正在翻译 {current}/{total} 页"
    elif stage_total > 0:
        current, total = stage_current, stage_total
        message = f"正在翻译 {stage} {current}/{total}"
    else:
        current, total = None, page_total
        message = f"正在翻译（BabelDOC）{int(overall)}%"
    ctx.report_progress(
        phase="translate",
        progress=min(progress, 95),
        message=message,
        page_current=current,
        page_total=total or page_total,
    )


def _ensure_pdf2zh_config(ctx: PipelineContext) -> None:
    if ctx.options.config_path and ctx.options.config_path.exists():
        from pdf2zh.config import ConfigManager

        ConfigManager.custome_config(str(ctx.options.config_path))


def _load_prompt_template(ctx: PipelineContext) -> Template | None:
    path = ctx.options.layout_prompt_path
    if path is None or not path.exists():
        return None
    return Template(path.read_text(encoding="utf-8"))


def _build_translator(
    ctx: PipelineContext,
    lang_in: str,
    lang_out: str,
    prompt: Template | None,
):
    from pdf2zh.translator import DeepseekTranslator

    service = ctx.options.service
    param = service.split(":", 1)
    service_name = param[0]
    service_model = param[1] if len(param) > 1 else None
    if service_name != DeepseekTranslator.name:
        raise PdfTraError(
            f"BabelDOC 暂不支持翻译服务: {service_name}",
            ExitCode.CONFIG_ERROR,
        )
    envs = _deepseek_envs(ctx.config)
    return DeepseekTranslator(
        lang_in,
        lang_out,
        service_model,
        envs=envs,
        prompt=prompt,
    )


def _deepseek_envs(config: dict) -> dict:
    for item in config.get("translators", []):
        if isinstance(item, dict) and item.get("name") == "deepseek":
            envs = item.get("envs", {})
            return dict(envs) if isinstance(envs, dict) else {}
    return {}
