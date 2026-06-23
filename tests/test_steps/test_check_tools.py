import pytest

from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.steps.check_tools import CheckToolsStep


def test_check_tools_passes_when_all_present(pipeline_context, monkeypatch):
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/usr/bin/{name}",
    )
    step = CheckToolsStep()
    step.run(pipeline_context)


def test_check_tools_missing_pdfinfo(pipeline_context, monkeypatch):
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: None if name == "pdfinfo" else f"/usr/bin/{name}",
    )
    step = CheckToolsStep()
    with pytest.raises(PdfTraError) as exc:
        step.run(pipeline_context)
    assert exc.value.exit_code is ExitCode.TOOL_NOT_FOUND
