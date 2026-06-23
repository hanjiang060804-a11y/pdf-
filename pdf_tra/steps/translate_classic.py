from __future__ import annotations

import time
from pathlib import Path

from pdf_tra.adapters.subprocess import run_command_streaming
from pdf_tra.config.schema import clamp_threads
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext, TranslateResult
from pdf_tra.core.progress import parse_page_progress, translate_progress_percent
from pdf_tra.steps.translate_outputs import build_pdf2zh_argv, locate_outputs


def run_classic(ctx: PipelineContext) -> TranslateResult:
    from pdf_tra.config.loader import validate_config

    validate_config(ctx.config)
    input_path = ctx.effective_input
    page_total = ctx.pdf_info.pages if ctx.pdf_info else None
    if page_total:
        translate_msg = f"正在翻译 0/{page_total} 页"
        page_current = 0
    else:
        translate_msg = "正在翻译…"
        page_current = None
    ctx.report_progress(
        phase="translate",
        progress=55,
        message=translate_msg,
        page_current=page_current,
        page_total=page_total,
    )
    threads = clamp_threads(
        ctx.options.threads,
        int(ctx.config.get("max_threads", 8)),
    )
    argv = build_pdf2zh_argv(ctx, input_path, threads)
    started = time.perf_counter()
    latest_page = 0

    def on_output_line(line: str) -> None:
        nonlocal latest_page
        if page_total is None:
            return
        parsed = parse_page_progress(line)
        if parsed is None:
            return
        current, total = parsed
        latest_page = max(latest_page, current)
        ctx.report_progress(
            phase="translate",
            progress=translate_progress_percent(latest_page, total),
            message=f"正在翻译 {latest_page}/{total} 页",
            page_current=latest_page,
            page_total=total,
        )

    result = run_command_streaming(
        argv,
        on_stderr_line=on_output_line,
        on_stdout_line=on_output_line,
        cwd=ctx.output_dir,
    )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise PdfTraError(
            f"pdf2zh 翻译失败: {result.stderr.strip() or result.stdout.strip()}",
            ExitCode.EXTERNAL_CMD_FAILED,
        )
    mono, dual = locate_outputs(input_path, ctx.output_dir)
    return TranslateResult(mono_pdf=mono, dual_pdf=dual, elapsed_seconds=elapsed)
