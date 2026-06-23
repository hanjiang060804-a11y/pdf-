from __future__ import annotations

import argparse
from pathlib import Path

from pdf_tra.config.loader import load_config
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext, TranslateOptions
from pdf_tra.pipeline.registry import TRANSLATE_STEPS, TRANSLATE_WITH_OCR
from pdf_tra.pipeline.runner import run_pipeline
from pdf_tra.steps.pdfinfo import is_pdf_file


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("translate", help="翻译 PDF")
    parser.add_argument("input_pdf", type=Path, help="PDF 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出目录")
    parser.add_argument("-s", "--service", default="deepseek")
    parser.add_argument("-li", "--lang-in")
    parser.add_argument("-lo", "--lang-out")
    parser.add_argument("-p", "--pages")
    parser.add_argument("-t", "--threads", type=int)
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.add_argument("--ocr", dest="ocr_mode", choices=["auto"])
    parser.add_argument(
        "--engine",
        choices=["babeldoc", "classic"],
        help="翻译引擎（默认读 config.json）",
    )
    parser.add_argument("--no-polish", action="store_true", help="跳过译后排版优化")
    parser.add_argument("--no-fallback", action="store_true", help="BabelDOC 失败时不回退经典引擎")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    path = args.input_pdf.resolve()
    _validate_input(path)
    output_dir = (args.output or path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = args.config if args.config.exists() else None
    config = load_config(config_path)
    threads = args.threads if args.threads is not None else int(config.get("threads", 4))

    options = TranslateOptions(
        threads=threads,
        pages=args.pages,
        ocr_mode=args.ocr_mode,
        dry_run=args.dry_run,
        confirm=args.confirm,
        service=args.service,
        lang_in=args.lang_in,
        lang_out=args.lang_out,
        config_path=config_path,
        verbose=args.verbose,
        translate_engine=args.engine,
        translate_fallback=False if args.no_fallback else None,
        layout_polish=False if args.no_polish else None,
    )
    ctx = PipelineContext(
        input_path=path,
        output_dir=output_dir,
        config=config,
        options=options,
        pipeline_name="translate",
    )
    steps = TRANSLATE_WITH_OCR if options.ocr_mode == "auto" else TRANSLATE_STEPS
    run_pipeline(ctx, steps)

    if options.dry_run:
        print("dry-run 完成：未调用 pdf2zh")
        if ctx.pdf_info:
            print(f"页数: {ctx.pdf_info.pages}")
        return 0

    result = ctx.translate_result
    if result is None:
        raise PdfTraError("翻译未产生结果", ExitCode.EXTERNAL_CMD_FAILED)
    if result.mono_pdf:
        print(f"单语: {result.mono_pdf}")
    if result.dual_pdf:
        print(f"双语: {result.dual_pdf}")
    print(f"耗时: {result.elapsed_seconds:.1f}s")
    return 0


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise PdfTraError(f"文件不存在: {path}", ExitCode.FILE_NOT_FOUND)
    if not is_pdf_file(path):
        raise PdfTraError(f"不是有效的 PDF 文件: {path}", ExitCode.NOT_PDF)
