from __future__ import annotations

from dataclasses import dataclass

from pdf_tra.adapters.subprocess import which_tool
from pdf_tra.core.constants import TOOL_GHOSTSCRIPT, TOOL_OCRMYPDF


@dataclass(frozen=True)
class OcrCapability:
    available: bool
    ocrmypdf: bool
    tesseract: bool
    ghostscript: bool
    install_hint: str | None = None


def _has_ghostscript() -> bool:
    if which_tool(TOOL_GHOSTSCRIPT) is not None:
        return True
    if which_tool("gswin32c") is not None:
        return True
    return which_tool("gs") is not None


def check_ocr_capability() -> OcrCapability:
    has_ocrmypdf = which_tool(TOOL_OCRMYPDF) is not None
    has_tesseract = which_tool("tesseract") is not None
    has_gs = _has_ghostscript()
    available = has_ocrmypdf and has_tesseract and has_gs
    hint = None
    if not available:
        missing = []
        if not has_ocrmypdf:
            missing.append("ocrmypdf")
        if not has_tesseract:
            missing.append("Tesseract")
        if not has_gs:
            missing.append("Ghostscript (gswin64c)")
        hint = f"未检测到 {' / '.join(missing)}，请运行 scripts/install-ghostscript.ps1 或查看安装指南 §7"
    return OcrCapability(
        available=available,
        ocrmypdf=has_ocrmypdf,
        tesseract=has_tesseract,
        ghostscript=has_gs,
        install_hint=hint,
    )
