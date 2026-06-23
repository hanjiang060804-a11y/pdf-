from pdf_tra.adapters.subprocess import CommandResult, which_tool


def test_command_result_fields():
    result = CommandResult(0, "out", "err", ["pdfinfo", "a.pdf"])
    assert result.returncode == 0
    assert result.stdout == "out"
    assert result.argv[0] == "pdfinfo"


def test_which_tool_returns_path_or_none():
    found = which_tool("python")
    assert found is None or found.name.lower().startswith("python")
