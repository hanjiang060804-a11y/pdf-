from __future__ import annotations

from pdf_tra.adapters.subprocess import run_command
from pdf_tra.core.constants import MAX_PAGES_WITHOUT_CONFIRM, TOOL_PDFINFO
from pdf_tra.core.errors import ExitCode, PdfTraError
from pdf_tra.core.models import PdfInfo, PipelineContext
from pdf_tra.steps.base import Step


class PdfinfoStep(Step):
    name = "pdfinfo"

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    def run(self, ctx: PipelineContext) -> None:
        path = ctx.input_path
        result = run_command([TOOL_PDFINFO, str(path)])
        if result.returncode != 0:
            raise PdfTraError(
                f"无法读取 PDF（pdfinfo 失败）: {result.stderr.strip()}",
                ExitCode.PDF_CORRUPT,
            )
        pdf_info = parse_pdfinfo_output(result.stdout)
        if pdf_info.encrypted:
            raise PdfTraError("不支持加密 PDF", ExitCode.PDF_ENCRYPTED)
        if pdf_info.pages <= 0:
            raise PdfTraError("PDF 页数为 0", ExitCode.PDF_CORRUPT)
        if (
            ctx.pipeline_name == "translate"
            and pdf_info.pages > MAX_PAGES_WITHOUT_CONFIRM
            and not ctx.options.confirm
        ):
            raise PdfTraError(
                f"PDF 共 {pdf_info.pages} 页，超过 {MAX_PAGES_WITHOUT_CONFIRM} 页，"
                "请添加 --confirm 后继续",
                ExitCode.CONFIRMATION_REQUIRED,
            )
        ctx.pdf_info = pdf_info


def parse_pdfinfo_output(stdout: str) -> PdfInfo:
    pages = 0
    encrypted = False
    title = ""
    for line in stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1].strip())
        elif line.startswith("Encrypted:"):
            encrypted = line.split(":", 1)[1].strip().lower() == "yes"
        elif line.startswith("Title:"):
            title = line.split(":", 1)[1].strip()
    return PdfInfo(pages=pages, encrypted=encrypted, title=title)


def is_pdf_file(path) -> bool:
    from pdf_tra.core.constants import PDF_MAGIC

    try:
        with open(path, "rb") as f:
            header = f.read(4)
        return header.startswith(PDF_MAGIC)
    except OSError:
        return False
