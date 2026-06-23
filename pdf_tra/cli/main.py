from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_tra import __version__
from pdf_tra.cli.commands import inspect as inspect_cmd
from pdf_tra.cli.commands import translate as translate_cmd
from pdf_tra.core.errors import PdfTraError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf_tra",
        description="PDF 翻译编排工具（pdf2zh + DeepSeek + poppler）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    translate_cmd.register(subparsers)
    inspect_cmd.register(subparsers)

    version_parser = subparsers.add_parser("version", help="显示版本")
    version_parser.set_defaults(handler=_handle_version)
    return parser


def _handle_version(_args: argparse.Namespace) -> int:
    print(f"pdf_tra {__version__}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except PdfTraError as exc:
        print(f"错误: {exc.message}", file=sys.stderr)
        return int(exc.exit_code)


def run() -> None:
    raise SystemExit(main())
