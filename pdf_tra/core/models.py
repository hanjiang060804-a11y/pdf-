from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal


@dataclass
class ProgressUpdate:
    phase: str
    progress: int
    message: str
    page_current: int | None = None
    page_total: int | None = None


ProgressCallback = Callable[[ProgressUpdate], None]


@dataclass
class PdfInfo:
    pages: int
    encrypted: bool
    title: str = ""


PdfType = Literal["text", "scanned", "mixed"]


@dataclass
class TranslateOptions:
    threads: int = 4
    pages: str | None = None
    ocr_mode: str | None = None
    dry_run: bool = False
    confirm: bool = False
    service: str = "deepseek"
    lang_in: str | None = None
    lang_out: str | None = None
    config_path: Path | None = None
    verbose: bool = False
    translate_engine: str | None = None
    translate_fallback: bool | None = None
    layout_polish: bool | None = None
    layout_prompt_path: Path | None = None


@dataclass
class InspectResult:
    input_path: Path
    pdf_info: PdfInfo
    pdf_type: PdfType
    char_count: int
    suggestion: str
    detected_lang: str = "English"
    detected_lang_label: str = "英语"
    target_lang: str = "Simplified Chinese"
    target_lang_label: str = "简体中文"
    lang_detect_fallback: bool = False
    can_translate: bool = True
    needs_ocr: bool = False
    ocr_available: bool = False


@dataclass
class TranslateResult:
    mono_pdf: Path | None
    dual_pdf: Path | None
    elapsed_seconds: float = 0.0


@dataclass
class PipelineContext:
    input_path: Path
    output_dir: Path
    config: dict
    options: TranslateOptions
    pipeline_name: str = "translate"

    pdf_info: PdfInfo | None = None
    char_count: int = 0
    pdf_type: PdfType | None = None
    has_extractable_text: bool | None = None
    text_sample: str = ""
    working_pdf_path: Path | None = None
    ocr_output_path: Path | None = None
    translate_result: TranslateResult | None = None
    required_tools: list[str] = field(default_factory=list)
    progress_callback: ProgressCallback | None = None

    def report_progress(
        self,
        *,
        phase: str,
        progress: int,
        message: str,
        page_current: int | None = None,
        page_total: int | None = None,
    ) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            ProgressUpdate(
                phase=phase,
                progress=progress,
                message=message,
                page_current=page_current,
                page_total=page_total,
            )
        )

    @property
    def effective_input(self) -> Path:
        return self.working_pdf_path or self.input_path
