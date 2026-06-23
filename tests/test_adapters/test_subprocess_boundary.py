import pytest

from pdf_tra.adapters.subprocess import CommandResult, run_command


def test_run_command_returns_stderr_on_failure(tmp_path, monkeypatch):
    class FakeCompleted:
        returncode = 1
        stdout = ""
        stderr = "command failed"

    monkeypatch.setattr(
        "pdf_tra.adapters.subprocess.subprocess.run",
        lambda *a, **k: FakeCompleted(),
    )
    result = run_command(["pdfinfo", "missing.pdf"])
    assert result.returncode == 1
    assert result.stderr == "command failed"


def test_run_command_preserves_argv():
    result = CommandResult(0, "ok", "", ["pdfinfo", "a.pdf"])
    assert result.argv == ["pdfinfo", "a.pdf"]


def test_which_tool_nonexistent():
    from pdf_tra.adapters.subprocess import which_tool

    assert which_tool("definitely-not-a-real-tool-xyz123") is None
