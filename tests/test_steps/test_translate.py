from pdf_tra.core.models import TranslateOptions, TranslateResult
from pdf_tra.steps.polish import PolishStep
from pdf_tra.steps.translate import TranslateStep


def test_translate_step_routes_classic(pipeline_context, mock_run_command, monkeypatch):
    out_dir = pipeline_context.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pipeline_context.input_path.stem
    (out_dir / f"{stem}-mono.pdf").write_bytes(b"%PDF-mono")

    from pdf_tra.adapters.subprocess import CommandResult

    mock_run_command({("pdf2zh",): CommandResult(0, "done", "", ["pdf2zh"])})
    monkeypatch.setattr("pdf_tra.config.loader.validate_config", lambda cfg: None)
    pipeline_context.options.translate_engine = "classic"

    TranslateStep().run(pipeline_context)
    assert pipeline_context.translate_result is not None
    assert pipeline_context.translate_result.mono_pdf is not None


def test_translate_step_babeldoc_fallback(pipeline_context, monkeypatch):
    out_dir = pipeline_context.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pipeline_context.input_path.stem
    (out_dir / f"{stem}-mono.pdf").write_bytes(b"%PDF-mono")

    from pdf_tra.adapters.subprocess import CommandResult

    def fail_babeldoc(ctx):
        raise RuntimeError("babeldoc down")

    def ok_classic(ctx):
        mono = out_dir / f"{stem}-mono.pdf"
        return TranslateResult(mono_pdf=mono, dual_pdf=None, elapsed_seconds=1.0)

    monkeypatch.setattr("pdf_tra.steps.translate.run_babeldoc", fail_babeldoc)
    monkeypatch.setattr("pdf_tra.steps.translate.run_classic", ok_classic)
    pipeline_context.options.translate_engine = "babeldoc"
    pipeline_context.options.translate_fallback = True

    TranslateStep().run(pipeline_context)
    assert pipeline_context.translate_result is not None


def test_polish_step_skipped_when_disabled(pipeline_context):
    pipeline_context.translate_result = TranslateResult(
        mono_pdf=pipeline_context.output_dir / "x-mono.pdf",
        dual_pdf=None,
    )
    pipeline_context.options.layout_polish = False
    assert PolishStep().should_run(pipeline_context) is False


def test_polish_step_runs_when_enabled(pipeline_context, tmp_path):
    mono = tmp_path / "doc-mono.pdf"
    mono.write_bytes(b"%PDF")
    pipeline_context.translate_result = TranslateResult(mono_pdf=mono, dual_pdf=None)
    pipeline_context.options.layout_polish = True
    assert PolishStep().should_run(pipeline_context) is True
