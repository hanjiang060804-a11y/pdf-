from __future__ import annotations

import os
from pathlib import Path

from pdf_tra.core.models import PipelineContext
from pdf_tra.core.progress import ocr_progress_percent, parse_ocr_progress
from pdf_tra.steps.base import Step


class OcrStep(Step):
    """Phase 3: ocrmypdf preprocessing."""

    name = "ocr"
    required = False

    def should_run(self, ctx: PipelineContext) -> bool:
        return (
            ctx.pipeline_name == "translate"
            and ctx.options.ocr_mode == "auto"
            and ctx.has_extractable_text is False
        )

    def run(self, ctx: PipelineContext) -> None:
        from pdf_tra.adapters.subprocess import run_command_streaming, which_tool
        from pdf_tra.core.constants import TOOL_OCRMYPDF
        from pdf_tra.core.errors import ExitCode, PdfTraError

        if which_tool(TOOL_OCRMYPDF) is None:
            raise PdfTraError(
                "未安装 ocrmypdf，无法处理扫描件",
                ExitCode.TOOL_NOT_FOUND,
            )

        page_total = ctx.pdf_info.pages if ctx.pdf_info else None
        latest_page = 0
        if page_total:
            start_msg = f"正在识别文字 0/{page_total} 页"
        else:
            start_msg = "正在 OCR 识别文字…"
        ctx.report_progress(
            phase="ocr",
            progress=5,
            message=start_msg,
            page_current=0 if page_total else None,
            page_total=page_total,
        )

        def on_output_line(line: str) -> None:
            nonlocal latest_page
            parsed = parse_ocr_progress(line, page_total)
            if parsed is None:
                return
            current, total = parsed
            latest_page = max(latest_page, current)
            ctx.report_progress(
                phase="ocr",
                progress=ocr_progress_percent(latest_page, total),
                message=f"正在识别文字 {latest_page}/{total} 页",
                page_current=latest_page,
                page_total=total,
            )

        output_path = ctx.output_dir / f"{ctx.input_path.stem}_ocr.pdf"
        ctx.output_dir.mkdir(parents=True, exist_ok=True)
        argv = _build_ocr_argv(ctx.input_path, output_path)
        result = run_command_streaming(
            argv,
            on_stderr_line=on_output_line,
            on_stdout_line=on_output_line,
        )
        if result.returncode != 0:
            raise PdfTraError(
                f"ocrmypdf 失败: {result.stderr.strip()}",
                ExitCode.EXTERNAL_CMD_FAILED,
            )
        ctx.ocr_output_path = output_path
        ctx.working_pdf_path = output_path
        ctx.report_progress(
            phase="ocr",
            progress=50,
            message="文字识别完成，正在翻译…",
            page_current=page_total,
            page_total=page_total,
        )


def _build_ocr_argv(input_path: Path, output_path: Path) -> list[str]:
    from pdf_tra.core.constants import TOOL_OCRMYPDF

    jobs = max(1, os.cpu_count() or 4)
    return [
        TOOL_OCRMYPDF,
        str(input_path),
        str(output_path),
        "--skip-text",
        "--output-type",
        "pdf",
        "-O",
        "0",
        "-j",
        str(jobs),
    ]
