import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdf2zh import Pdf2zhStep, _build_pdf2zh_argv, _locate_outputs


def test_pdf2zh_not_run_for_inspect_pipeline(pipeline_context):
    pipeline_context.pipeline_name = "inspect"
    assert Pdf2zhStep().should_run(pipeline_context) is False


def test_pdf2zh_failure_raises(pipeline_context, mock_run_command, monkeypatch):
    mock_run_command({("pdf2zh",): CommandResult(1, "", "API error", ["pdf2zh"])})
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda c: None)
    with pytest.raises(PdfTraError) as exc:
        Pdf2zhStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.EXTERNAL_CMD_FAILED
    assert "API error" in exc.value.message


def test_pdf2zh_missing_api_key_raises(pipeline_context, mock_run_command, sample_config):
    bad_config = dict(sample_config)
    bad_config["translators"] = []
    pipeline_context.config = bad_config
    mock_run_command({("pdf2zh",): CommandResult(0, "ok", "", ["pdf2zh"])})
    with pytest.raises(PdfTraError) as exc:
        Pdf2zhStep().run(pipeline_context)
    assert exc.value.exit_code is ExitCode.CONFIG_ERROR


def test_build_pdf2zh_argv_without_optional_fields(pipeline_context):
    pipeline_context.options = TranslateOptions(service="deepseek", threads=4)
    argv = _build_pdf2zh_argv(pipeline_context, pipeline_context.input_path, 4)
    assert "-p" not in argv
    assert "-li" not in argv
    assert "--config" not in argv


def test_build_pdf2zh_skips_missing_config_path(pipeline_context, tmp_path):
    pipeline_context.options.config_path = tmp_path / "missing.json"
    argv = _build_pdf2zh_argv(pipeline_context, pipeline_context.input_path, 4)
    assert "--config" not in argv


def test_locate_outputs_in_output_dir(tmp_path):
    input_pdf = tmp_path / "doc.pdf"
    input_pdf.write_bytes(b"%PDF")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "doc-mono.pdf").write_bytes(b"m")
    (out_dir / "doc-dual.pdf").write_bytes(b"d")
    mono, dual = _locate_outputs(input_pdf, out_dir)
    assert mono == out_dir / "doc-mono.pdf"
    assert dual == out_dir / "doc-dual.pdf"


def test_locate_outputs_moves_from_input_parent(tmp_path):
    input_pdf = tmp_path / "doc.pdf"
    input_pdf.write_bytes(b"%PDF")
    (tmp_path / "doc-mono.pdf").write_bytes(b"m")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    mono, dual = _locate_outputs(input_pdf, out_dir)
    assert mono == out_dir / "doc-mono.pdf"
    assert mono.exists()


def test_locate_outputs_none_when_missing(tmp_path):
    input_pdf = tmp_path / "doc.pdf"
    input_pdf.write_bytes(b"%PDF")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    mono, dual = _locate_outputs(input_pdf, out_dir)
    assert mono is None
    assert dual is None


def test_pdf2zh_clamps_threads_in_argv(pipeline_context, mock_run_command, monkeypatch):
    pipeline_context.options = TranslateOptions(threads=99)
    pipeline_context.config["max_threads"] = 8
    captured: list[list[str]] = []

    def side_effect(argv, **kwargs):
        captured.append(list(argv))
        return CommandResult(0, "ok", "", argv)

    monkeypatch.setattr("pdf_tra.steps.translate_classic.run_command_streaming", side_effect)
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda c: None)
    (pipeline_context.output_dir).mkdir(parents=True, exist_ok=True)
    Pdf2zhStep().run(pipeline_context)
    t_index = captured[0].index("-t")
    assert captured[0][t_index + 1] == "8"
