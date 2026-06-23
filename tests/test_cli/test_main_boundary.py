from pathlib import Path

import pytest

from pdf_tra.cli.main import main
from pdf_tra.core.errors import ExitCode


def test_main_unknown_subcommand():
    with pytest.raises(SystemExit):
        main(["unknown-cmd"])


def test_inspect_missing_file(tmp_path):
    missing = tmp_path / "gone.pdf"
    code = main(["inspect", str(missing)])
    assert code == ExitCode.FILE_NOT_FOUND


def test_translate_not_pdf(tmp_path):
    f = tmp_path / "fake.pdf"
    f.write_text("not a pdf", encoding="utf-8")
    code = main(["translate", str(f)])
    assert code == ExitCode.NOT_PDF


def test_translate_dry_run_e2e(
    tmp_path,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
    fixtures_dir,
):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    config = fixtures_dir / "config_valid.json"

    mock_run_command(
        {
            ("pdfinfo",): __import__(
                "pdf_tra.adapters.subprocess", fromlist=["CommandResult"]
            ).CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): __import__(
                "pdf_tra.adapters.subprocess", fromlist=["CommandResult"]
            ).CommandResult(0, "sample extractable text", "", ["pdftotext"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )

    code = main(
        [
            "translate",
            str(pdf),
            "--dry-run",
            "--config",
            str(config),
        ]
    )
    assert code == 0


def test_translate_threads_cli_override(
    tmp_path,
    monkeypatch,
    fixtures_dir,
    capsys,
):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    config = fixtures_dir / "config_valid.json"

    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )

    from pdf_tra.adapters.subprocess import CommandResult

    def fake_run(argv, **kwargs):
        if argv[0] == "pdfinfo":
            return CommandResult(0, "Pages: 1\nEncrypted: no\n", "", argv)
        if argv[0] == "pdftotext":
            return CommandResult(0, "hello world text", "", argv)
        if "pdf2zh" in Path(argv[0]).name.lower():
            return CommandResult(0, "ok", "", argv)
        raise AssertionError(argv)

    monkeypatch.setattr("pdf_tra.steps.pdfinfo.run_command", fake_run)
    monkeypatch.setattr("pdf_tra.steps.pdftotext.run_command", fake_run)
    monkeypatch.setattr("pdf_tra.steps.translate_classic.run_command_streaming", fake_run)
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda c: None)

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    (out_dir / "paper-mono.pdf").write_bytes(b"%PDF")
    (out_dir / "paper-dual.pdf").write_bytes(b"%PDF")

    code = main(
        [
            "translate",
            str(pdf),
            "-o",
            str(out_dir),
            "-t",
            "2",
            "--config",
            str(config),
        ]
    )
    assert code == 0


def test_pdf_tra_error_printed_to_stderr(capsys):
    code = main(["translate", "/nonexistent/path/file.pdf"])
    assert code == ExitCode.FILE_NOT_FOUND
    err = capsys.readouterr().err
    assert "错误" in err
