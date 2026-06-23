from pathlib import Path

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.models import TranslateOptions
from pdf_tra.steps.pdf2zh import Pdf2zhStep, _build_pdf2zh_argv


def test_pdf2zh_skipped_on_dry_run(pipeline_context):
    pipeline_context.options = TranslateOptions(dry_run=True)
    step = Pdf2zhStep()
    assert step.should_run(pipeline_context) is False


def test_build_pdf2zh_argv(pipeline_context, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    pipeline_context.options = TranslateOptions(
        threads=4,
        pages="1-3",
        lang_in="en",
        lang_out="zh",
        config_path=config_path,
        service="deepseek",
    )
    argv = _build_pdf2zh_argv(pipeline_context, pipeline_context.input_path, 4)
    assert Path(argv[0]).name.lower().startswith("pdf2zh")
    assert "-t" in argv and "4" in argv
    assert "-p" in argv and "1-3" in argv
    assert "--config" in argv


def test_pdf2zh_step_records_outputs(pipeline_context, mock_run_command, monkeypatch, tmp_path):
    out_dir = pipeline_context.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pipeline_context.input_path.stem
    (out_dir / f"{stem}-mono.pdf").write_bytes(b"%PDF-mono")
    (out_dir / f"{stem}-dual.pdf").write_bytes(b"%PDF-dual")

    mock_run_command({("pdf2zh",): CommandResult(0, "done", "", ["pdf2zh"])})
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda cfg: None)

    Pdf2zhStep().run(pipeline_context)
    assert pipeline_context.translate_result is not None
    assert pipeline_context.translate_result.mono_pdf is not None
    assert pipeline_context.translate_result.dual_pdf is not None
