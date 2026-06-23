from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pdf_tra.adapters.subprocess import CommandResult
from pdf_tra.core.models import PipelineContext, TranslateOptions


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(fixtures_dir: Path) -> dict:
    import json

    with (fixtures_dir / "config_valid.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pdfinfo_output(fixtures_dir: Path) -> str:
    return (fixtures_dir / "pdfinfo_sample.txt").read_text(encoding="utf-8")


@pytest.fixture
def translate_options() -> TranslateOptions:
    return TranslateOptions(threads=4, confirm=False, translate_engine="classic")


@pytest.fixture
def pipeline_context(tmp_path: Path, sample_config: dict, translate_options: TranslateOptions) -> PipelineContext:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% mock")
    return PipelineContext(
        input_path=pdf_path,
        output_dir=tmp_path / "out",
        config=sample_config,
        options=translate_options,
        pipeline_name="translate",
    )


@dataclass
class MockCommandMap:
    mapping: dict[tuple[str, ...], CommandResult]

    def __call__(self, argv: list[str], **kwargs) -> CommandResult:
        tool = Path(argv[0]).name.lower() if argv else ""
        key = ("pdf2zh",) if "pdf2zh" in tool else tuple(argv[:1])
        if key in self.mapping:
            return self.mapping[key]
        joined = " ".join(argv)
        if argv and argv[0] == "pdfinfo":
            return self.mapping.get(("pdfinfo",), CommandResult(1, "", "missing", argv))
        if argv and argv[0] == "pdftotext":
            return self.mapping.get(("pdftotext",), CommandResult(0, "hello world text", "", argv))
        if argv and "pdf2zh" in tool:
            return self.mapping.get(("pdf2zh",), CommandResult(0, "ok", "", argv))
        raise AssertionError(f"unexpected argv: {joined}")


@pytest.fixture
def mock_run_command(monkeypatch):
    holder: dict[str, MockCommandMap | None] = {"impl": None}

    def _install(mapping: dict[tuple[str, ...], CommandResult]):
        impl = MockCommandMap(mapping)
        holder["impl"] = impl
        targets = [
            "pdf_tra.adapters.subprocess.run_command",
            "pdf_tra.adapters.subprocess.run_command_streaming",
            "pdf_tra.steps.pdfinfo.run_command",
            "pdf_tra.steps.pdftotext.run_command",
            "pdf_tra.steps.translate_classic.run_command_streaming",
        ]
        for target in targets:
            monkeypatch.setattr(target, impl)
        return impl

    yield _install
