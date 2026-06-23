from __future__ import annotations

from pdf_tra.adapters.subprocess import which_tool
from pdf_tra.core.constants import (
    TOOL_GHOSTSCRIPT,
    TOOL_OCRMYPDF,
    TOOL_PDF2ZH,
    TOOL_PDFINFO,
    TOOL_PDFTOTEXT,
)
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PipelineContext
from pdf_tra.steps.base import Step


class CheckToolsStep(Step):
    name = "check_tools"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        tools = _required_tools(ctx)
        missing = [tool for tool in tools if which_tool(tool) is None]
        if missing:
            joined = ", ".join(missing)
            raise PdfTraError(
                f"缺少外部工具: {joined}。请先安装 poppler 与 pdf2zh。",
                ExitCode.TOOL_NOT_FOUND,
            )


def _required_tools(ctx: PipelineContext) -> list[str]:
    if ctx.pipeline_name == "inspect":
        return [TOOL_PDFINFO, TOOL_PDFTOTEXT]
    tools = [TOOL_PDFINFO, TOOL_PDFTOTEXT, TOOL_PDF2ZH]
    if ctx.options.ocr_mode == "auto":
        tools.insert(-1, TOOL_OCRMYPDF)
        if which_tool(TOOL_GHOSTSCRIPT) is None and which_tool("gs") is None:
            tools.insert(-1, TOOL_GHOSTSCRIPT)
    return tools
