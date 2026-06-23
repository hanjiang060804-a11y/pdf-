from pdf_tra.steps.base import Step
from pdf_tra.steps.check_tools import CheckToolsStep
from pdf_tra.steps.ocr import OcrStep
from pdf_tra.steps.pdf2zh import Pdf2zhStep
from pdf_tra.steps.pdfinfo import PdfinfoStep
from pdf_tra.steps.pdftotext import PdftotextStep
from pdf_tra.steps.pdftotext_post import PdftotextPostStep
from pdf_tra.steps.polish import PolishStep
from pdf_tra.steps.translate import TranslateStep

INSPECT_STEPS = ["check_tools", "pdfinfo", "pdftotext"]

TRANSLATE_STEPS = ["check_tools", "pdfinfo", "pdftotext", "translate", "polish"]

TRANSLATE_WITH_OCR = [
    "check_tools",
    "pdfinfo",
    "pdftotext",
    "ocr",
    "pdftotext_post",
    "translate",
    "polish",
]

_translate_step = TranslateStep()

STEP_REGISTRY: dict[str, Step] = {
    "check_tools": CheckToolsStep(),
    "pdfinfo": PdfinfoStep(),
    "pdftotext": PdftotextStep(),
    "pdftotext_post": PdftotextPostStep(),
    "ocr": OcrStep(),
    "translate": _translate_step,
    "pdf2zh": Pdf2zhStep(),
    "polish": PolishStep(),
}


def resolve_steps(names: list[str]) -> list[Step]:
    steps: list[Step] = []
    for name in names:
        step = STEP_REGISTRY.get(name)
        if step is None:
            raise KeyError(f"未知 pipeline step: {name}")
        steps.append(step)
    return steps
