from pathlib import Path

from pdf_tra.adapters.subprocess import which_tool


def test_which_tool_finds_venv_script(tmp_path, monkeypatch):
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    tool = scripts / "pdf2zh.exe"
    tool.write_bytes(b"")

    fake_python = scripts / "python.exe"
    fake_python.write_bytes(b"")

    monkeypatch.setattr("pdf_tra.adapters.subprocess.sys.executable", str(fake_python))
    monkeypatch.setattr("pdf_tra.adapters.subprocess.shutil.which", lambda name: None)

    found = which_tool("pdf2zh")
    assert found == tool
