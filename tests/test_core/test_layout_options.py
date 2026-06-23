from pdf_tra.core.layout_options import apply_layout_defaults
from pdf_tra.core.models import TranslateOptions


def test_apply_layout_defaults_from_config(pipeline_context):
    pipeline_context.options = TranslateOptions()
    pipeline_context.config["translate_engine"] = "classic"
    pipeline_context.config["layout_polish"] = False
    apply_layout_defaults(pipeline_context)
    assert pipeline_context.options.translate_engine == "classic"
    assert pipeline_context.options.layout_polish is False
    assert pipeline_context.options.translate_fallback is True


def test_apply_layout_defaults_respects_explicit_options(pipeline_context):
    pipeline_context.options = TranslateOptions(
        translate_engine="babeldoc",
        layout_polish=True,
        translate_fallback=False,
    )
    pipeline_context.config["translate_engine"] = "classic"
    apply_layout_defaults(pipeline_context)
    assert pipeline_context.options.translate_engine == "babeldoc"
    assert pipeline_context.options.layout_polish is True
    assert pipeline_context.options.translate_fallback is False
