from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_tra.config.loader import load_config
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext, TranslateOptions
from pdf_tra.core.ocr import check_ocr_capability
from pdf_tra.pipeline.registry import INSPECT_STEPS
from pdf_tra.pipeline.runner import run_pipeline
from pdf_tra.steps.pdfinfo import is_pdf_file
from pdf_tra.steps.pdftotext import build_inspect_suggestion


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("inspect", help="检测 PDF 类型与是否可翻译")
    parser.add_argument("input_pdf", type=Path, help="PDF 文件路径")
    parser.add_argument("--config", type=Path, default=Path("config.json"))
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    path = args.input_pdf.resolve()
    _validate_input(path)
    config = load_config(args.config if args.config.exists() else None)
    ctx = PipelineContext(
        input_path=path,
        output_dir=path.parent,
        config=config,
        options=TranslateOptions(config_path=args.config if args.config.exists() else None),
        pipeline_name="inspect",
    )
    run_pipeline(ctx, INSPECT_STEPS)
    assert ctx.pdf_info is not None
    assert ctx.pdf_type is not None
    ocr_cap = check_ocr_capability()
    needs_ocr = ctx.pdf_type == "scanned"
    print(f"文件: {path.name}")
    print(f"页数: {ctx.pdf_info.pages}")
    print(f"类型: {ctx.pdf_type}")
    print(f"加密: {'是' if ctx.pdf_info.encrypted else '否'}")
    print(f"估计字符数: {ctx.char_count}")
    print(f"需要 OCR: {'是' if needs_ocr else '否'}")
    print(f"OCR 可用: {'是' if ocr_cap.available else '否'}")
    print(f"建议: {build_inspect_suggestion(ctx.pdf_type, ocr_available=ocr_cap.available)}")
    return 0


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise PdfTraError(f"文件不存在: {path}", ExitCode.FILE_NOT_FOUND)
    if not is_pdf_file(path):
        raise PdfTraError(f"不是有效的 PDF 文件: {path}", ExitCode.NOT_PDF)
