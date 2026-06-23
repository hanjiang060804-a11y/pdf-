from __future__ import annotations

from pathlib import Path

from pdf_tra.config.loader import load_config
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.lang import TARGET_LANG, TARGET_LANG_LABEL, detect_language
from pdf_tra.core.models import (
    InspectResult,
    PipelineContext,
    ProgressCallback,
    TranslateOptions,
    TranslateResult,
)
from pdf_tra.core.ocr import check_ocr_capability
from pdf_tra.pipeline.registry import INSPECT_STEPS, TRANSLATE_STEPS, TRANSLATE_WITH_OCR
from pdf_tra.pipeline.runner import run_pipeline
from pdf_tra.steps.pdfinfo import is_pdf_file
from pdf_tra.steps.pdftotext import build_inspect_suggestion


def inspect_pdf(path: Path, *, config_path: Path | None = None) -> InspectResult:
    resolved = path.resolve()
    _validate_pdf(resolved)
    cfg_path = config_path or Path("config.json")
    config = load_config(cfg_path if cfg_path.exists() else None)
    ctx = PipelineContext(
        input_path=resolved,
        output_dir=resolved.parent,
        config=config,
        options=TranslateOptions(config_path=cfg_path if cfg_path.exists() else None),
        pipeline_name="inspect",
    )
    run_pipeline(ctx, INSPECT_STEPS)
    assert ctx.pdf_info is not None
    assert ctx.pdf_type is not None

    ocr_cap = check_ocr_capability()
    needs_ocr = ctx.pdf_type == "scanned"
    encrypted = ctx.pdf_info.encrypted

    lang_in, detected_label, fallback = detect_language(ctx.text_sample)
    if needs_ocr:
        lang_in, detected_label, fallback = "English", "OCR 后自动识别", False

    can_translate = (ctx.pdf_type == "text" and not encrypted) or (
        needs_ocr and ocr_cap.available and not encrypted
    )

    return InspectResult(
        input_path=resolved,
        pdf_info=ctx.pdf_info,
        pdf_type=ctx.pdf_type,
        char_count=ctx.char_count,
        suggestion=build_inspect_suggestion(ctx.pdf_type, ocr_available=ocr_cap.available),
        detected_lang=lang_in,
        detected_lang_label=detected_label,
        target_lang=TARGET_LANG,
        target_lang_label=TARGET_LANG_LABEL,
        lang_detect_fallback=fallback,
        can_translate=can_translate,
        needs_ocr=needs_ocr,
        ocr_available=ocr_cap.available,
    )


def translate_pdf(
    path: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    options: TranslateOptions | None = None,
    progress_callback: ProgressCallback | None = None,
) -> TranslateResult:
    resolved = path.resolve()
    _validate_pdf(resolved)
    out = output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    inspection = inspect_pdf(resolved, config_path=config_path)
    opts = options or TranslateOptions()

    if inspection.pdf_info.encrypted:
        raise PdfTraError("该 PDF 已加密，请先解密", ExitCode.PDF_ENCRYPTED)

    if inspection.needs_ocr:
        if opts.ocr_mode != "auto":
            raise PdfTraError(
                "检测到扫描版 PDF（无可提取文字）。请启用 OCR 后再翻译。",
                ExitCode.SCANNED_PDF,
            )
        if not inspection.ocr_available:
            ocr_cap = check_ocr_capability()
            hint = ocr_cap.install_hint or "未安装 OCR 工具"
            raise PdfTraError(hint, ExitCode.TOOL_NOT_FOUND)
    elif not inspection.can_translate:
        raise PdfTraError(
            "检测到扫描版 PDF（无可提取文字）。",
            ExitCode.SCANNED_PDF,
        )

    cfg_path = config_path or Path("config.json")
    config = load_config(cfg_path if cfg_path.exists() else None)

    if inspection.needs_ocr:
        opts.lang_in = None
    elif opts.lang_in is None:
        opts.lang_in = inspection.detected_lang
    if opts.lang_out is None:
        opts.lang_out = inspection.target_lang
    if opts.config_path is None and cfg_path.exists():
        opts.config_path = cfg_path
    threads = opts.threads or int(config.get("threads", 4))
    opts.threads = threads

    ctx = PipelineContext(
        input_path=resolved,
        output_dir=out,
        config=config,
        options=opts,
        pipeline_name="translate",
        progress_callback=progress_callback,
    )
    use_ocr = opts.ocr_mode == "auto" and inspection.needs_ocr
    steps = TRANSLATE_WITH_OCR if use_ocr else TRANSLATE_STEPS

    if progress_callback is not None:
        ctx.report_progress(phase="preparing", progress=2, message="正在准备…")

    run_pipeline(ctx, steps)

    if opts.dry_run:
        return TranslateResult(mono_pdf=None, dual_pdf=None, elapsed_seconds=0.0)

    if ctx.translate_result is None:
        raise PdfTraError("翻译未产生结果", ExitCode.EXTERNAL_CMD_FAILED)

    if progress_callback is not None:
        ctx.report_progress(phase="done", progress=100, message="翻译完成")

    return ctx.translate_result


def get_capabilities() -> dict:
    from pdf_tra.adapters.subprocess import which_tool
    from pdf_tra.core.constants import TOOL_OCRMYPDF, TOOL_PDF2ZH, TOOL_PDFINFO

    ocr_cap = check_ocr_capability()
    config = load_config(Path("config.json") if Path("config.json").exists() else None)
    return {
        "ocr": {
            "available": ocr_cap.available,
            "ocrmypdf": ocr_cap.ocrmypdf,
            "tesseract": ocr_cap.tesseract,
            "ghostscript": ocr_cap.ghostscript,
            "install_hint": ocr_cap.install_hint,
        },
        "poppler": which_tool(TOOL_PDFINFO) is not None,
        "pdf2zh": which_tool(TOOL_PDF2ZH) is not None,
        "translate_engines": ["babeldoc", "classic"],
        "default_translate_engine": config.get("translate_engine", "babeldoc"),
        "layout_polish_available": True,
        "default_layout_polish": bool(config.get("layout_polish", True)),
    }


def _validate_pdf(path: Path) -> None:
    if not path.exists():
        raise PdfTraError(f"文件不存在: {path}", ExitCode.FILE_NOT_FOUND)
    if not is_pdf_file(path):
        raise PdfTraError(f"不是有效的 PDF 文件: {path}", ExitCode.NOT_PDF)


def validate_pdf_path(path: Path) -> None:
    """Validate path exists and is a PDF (for Web/CLI preflight)."""
    _validate_pdf(path.resolve())
