from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.models import TranslateOptions
from pdf_tra.pipeline.registry import INSPECT_STEPS, resolve_steps
from pdf_tra.pipeline.runner import run_pipeline


def test_resolve_steps_unknown_raises():
    import pytest

    with pytest.raises(KeyError):
        resolve_steps(["not_a_step"])


def test_inspect_pipeline_runs_without_pdf2zh(
    pipeline_context,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
):
    pipeline_context.pipeline_name = "inspect"
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "extractable text content", "", ["pdftotext"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/usr/bin/{name}",
    )
    ctx = run_pipeline(pipeline_context, INSPECT_STEPS)
    assert ctx.pdf_info is not None
    assert ctx.pdf_type == "text"
    assert ctx.translate_result is None


def test_translate_pipeline_dry_run_skips_pdf2zh(
    pipeline_context,
    mock_run_command,
    pdfinfo_output,
    monkeypatch,
):
    pipeline_context.options = TranslateOptions(dry_run=True)
    mock_run_command(
        {
            ("pdfinfo",): CommandResult(0, pdfinfo_output, "", ["pdfinfo"]),
            ("pdftotext",): CommandResult(0, "extractable text content", "", ["pdftotext"]),
        }
    )
    monkeypatch.setattr(
        "pdf_tra.steps.check_tools.which_tool",
        lambda name: f"/usr/bin/{name}",
    )
    ctx = run_pipeline(pipeline_context, ["check_tools", "pdfinfo", "pdftotext", "pdf2zh"])
    assert ctx.translate_result is None
