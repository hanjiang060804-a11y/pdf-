from __future__ import annotations

import shutil
from pathlib import Path

from pdf_tra.adapters.subprocess import CommandResult, which_tool
from pdf_tra.core.constants import TOOL_PDF2ZH
from pdf_tra.core.models import PipelineContext


def build_pdf2zh_argv(ctx: PipelineContext, input_path: Path, threads: int) -> list[str]:
    pdf2zh = which_tool(TOOL_PDF2ZH)
    argv = [
        str(pdf2zh) if pdf2zh is not None else TOOL_PDF2ZH,
        str(input_path),
        "-s",
        ctx.options.service,
        "-t",
        str(threads),
    ]
    if ctx.options.pages:
        argv.extend(["-p", ctx.options.pages])
    if ctx.options.lang_in:
        argv.extend(["-li", ctx.options.lang_in])
    if ctx.options.lang_out:
        argv.extend(["-lo", ctx.options.lang_out])
    config_path = ctx.options.config_path
    if config_path and config_path.exists():
        argv.extend(["--config", str(config_path)])
    prompt_path = ctx.options.layout_prompt_path
    if prompt_path and prompt_path.exists():
        argv.extend(["--prompt", str(prompt_path)])
    return argv


def locate_outputs(input_path: Path, output_dir: Path) -> tuple[Path | None, Path | None]:
    stem = input_path.stem
    mono_name = f"{stem}-mono.pdf"
    dual_name = f"{stem}-dual.pdf"
    mono = output_dir / mono_name
    dual = output_dir / dual_name
    if not mono.exists():
        mono = input_path.parent / mono_name
    if not dual.exists():
        dual = input_path.parent / dual_name
    if mono.exists() and mono.parent != output_dir:
        target = output_dir / mono.name
        shutil.move(str(mono), str(target))
        mono = target
    if dual.exists() and dual.parent != output_dir:
        target = output_dir / dual.name
        shutil.move(str(dual), str(target))
        dual = target
    return (mono if mono.exists() else None, dual if dual.exists() else None)
