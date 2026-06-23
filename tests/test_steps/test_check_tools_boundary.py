import pytest

from pdf_tra.core.constants import MIN_EXTRACTABLE_TEXT_CHARS
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.check_tools import CheckToolsStep, _required_tools


def test_required_tools_inspect_pipeline(pipeline_context):
    pipeline_context.pipeline_name = "inspect"
    tools = _required_tools(pipeline_context)
    assert tools == ["pdfinfo", "pdftotext"]
    assert "pdf2zh" not in tools


def test_required_tools_translate_pipeline(pipeline_context):
    tools = _required_tools(pipeline_context)
    assert "pdf2zh" in tools


def test_required_tools_ocr_auto_adds_ocrmypdf(pipeline_context):
    pipeline_context.options = TranslateOptions(ocr_mode="auto")
    tools = _required_tools(pipeline_context)
    assert "ocrmypdf" in tools


def test_check_tools_missing_pdf2zh(pipeline_context, monkeypatch):
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: None if name == "pdf2zh" else f"/bin/{name}",
    )
    with pytest.raises(PdfTraError) as exc:
        CheckToolsStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.TOOL_NOT_FOUND
    assert "pdf2zh" in exc.value.message


def test_check_tools_inspect_does_not_require_pdf2zh(pipeline_context, monkeypatch):
    pipeline_context.pipeline_name = "inspect"
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/bin/{name}",
    )
    CheckToolsStep().run(pipeline_context)
