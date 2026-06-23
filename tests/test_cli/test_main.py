from pathlib import Path

import pytest

from pdf_tra.cli.main import build_parser, main
from pdf_tra.core.errors import ExitCode


def test_version_command(capsys):
    code = main(["version"])
    assert code == 0
    captured = capsys.readouterr()
    assert "pdf_tra" in captured.out


def test_build_parser_has_subcommands():
    parser = build_parser()
    args = parser.parse_args(["translate", "paper.pdf"])
    assert args.command == "translate"
    assert args.input_pdf == Path("paper.pdf")


def test_translate_missing_file(tmp_path):
    missing = tmp_path / "missing.pdf"
    code = main(["translate", str(missing)])
    assert code == ExitCode.FILE_NOT_FOUND


def test_inspect_non_pdf(tmp_path):
    txt = tmp_path / "note.txt"
    txt.write_text("not pdf", encoding="utf-8")
    code = main(["inspect", str(txt)])
    assert code == ExitCode.NOT_PDF
