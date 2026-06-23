from __future__ import annotations

from pathlib import Path

from pdf_tra.core.models import PipelineContext, TranslateOptions

VALID_ENGINES = frozenset({"babeldoc", "classic"})


def resolve_translate_engine(options: TranslateOptions, config: dict) -> str:
    engine = options.translate_engine or config.get("translate_engine", "babeldoc")
    if engine not in VALID_ENGINES:
        raise ValueError(f"未知翻译引擎: {engine}")
    return engine


def resolve_translate_fallback(options: TranslateOptions, config: dict) -> bool:
    if options.translate_fallback is not None:
        return options.translate_fallback
    return bool(config.get("translate_fallback", True))


def resolve_layout_polish(options: TranslateOptions, config: dict) -> bool:
    if options.layout_polish is not None:
        return options.layout_polish
    return bool(config.get("layout_polish", True))


def resolve_layout_prompt_path(options: TranslateOptions, config: dict) -> Path | None:
    if options.layout_prompt_path is not None:
        return options.layout_prompt_path if options.layout_prompt_path.exists() else None
    raw = config.get("layout_prompt_path")
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path if path.exists() else None


def apply_layout_defaults(ctx: PipelineContext) -> None:
    opts = ctx.options
    config = ctx.config
    if opts.translate_engine is None:
        opts.translate_engine = resolve_translate_engine(opts, config)
    if opts.translate_fallback is None:
        opts.translate_fallback = resolve_translate_fallback(opts, config)
    if opts.layout_polish is None:
        opts.layout_polish = resolve_layout_polish(opts, config)
    if opts.layout_prompt_path is None:
        opts.layout_prompt_path = resolve_layout_prompt_path(opts, config)
