from __future__ import annotations

import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pdf_tra.config.loader import load_config, read_settings, save_user_settings
from pdf_tra.core.errors import ExitCode, PdfTraError, http_status_for_exit_code
from pdf_tra.core.models import InspectResult
from pdf_tra.service import get_capabilities, inspect_pdf, translate_pdf, validate_pdf_path
from pdf_tra.web.jobs import JobStore

STATIC_DIR = Path(__file__).resolve().parent / "static"


class PathPayload(BaseModel):
    path: str


class TranslatePayload(BaseModel):
    path: str
    ocr: bool = False
    engine: str | None = None
    polish: bool | None = None


class SettingsPayload(BaseModel):
    api_key: str | None = Field(default=None, min_length=8)
    translate_engine: str | None = None
    layout_polish: bool | None = None


def create_app(
    *,
    config_path: Path | None = None,
    upload_dir: Path | None = None,
) -> FastAPI:
    cfg_path = (config_path or Path("config.json")).resolve()
    uploads = (upload_dir or Path("output") / "uploads").resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    jobs = JobStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        jobs.shutdown()

    app = FastAPI(title="pdf-tra", version="0.1.0", lifespan=lifespan)

    @app.post("/api/v1/inspect")
    async def api_inspect_upload(file: UploadFile = File(...)) -> dict[str, Any]:
        filename = _safe_pdf_filename(file.filename)
        dest = uploads / filename
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            result = inspect_pdf(dest, config_path=cfg_path if cfg_path.exists() else None)
        except PdfTraError as err:
            dest.unlink(missing_ok=True)
            raise _http_error(err) from err
        return _inspect_to_dict(result)

    @app.post("/api/v1/inspect/path")
    def api_inspect_path(payload: PathPayload) -> dict[str, Any]:
        path = Path(payload.path).resolve()
        try:
            result = inspect_pdf(path, config_path=cfg_path if cfg_path.exists() else None)
        except PdfTraError as err:
            raise _http_error(err) from err
        return _inspect_to_dict(result)

    @app.get("/api/v1/capabilities")
    def api_capabilities() -> dict:
        return get_capabilities()

    @app.post("/api/v1/translate")
    def api_translate(payload: TranslatePayload) -> dict[str, str]:
        path = Path(payload.path).resolve()
        try:
            validate_pdf_path(path)
        except PdfTraError as err:
            raise _http_error(err) from err
        out_dir = uploads / "translated" / path.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        job = jobs.create()

        from pdf_tra.core.models import TranslateOptions

        options = TranslateOptions(ocr_mode="auto" if payload.ocr else None)
        if payload.engine is not None:
            if payload.engine not in {"babeldoc", "classic"}:
                raise HTTPException(status_code=400, detail="engine 必须是 babeldoc 或 classic")
            options.translate_engine = payload.engine
        if payload.polish is not None:
            options.layout_polish = payload.polish
        if options.translate_engine is None or options.layout_polish is None:
            cfg = load_config(cfg_path if cfg_path.exists() else None)
            if options.translate_engine is None:
                options.translate_engine = cfg.get("translate_engine", "babeldoc")
            if options.layout_polish is None:
                options.layout_polish = bool(cfg.get("layout_polish", True))

        def _on_progress(update):
            jobs.update(
                job.id,
                phase=update.phase,
                progress=update.progress,
                message=update.message,
                page_current=update.page_current,
                page_total=update.page_total,
            )

        def _task():
            return translate_pdf(
                path,
                out_dir,
                config_path=cfg_path if cfg_path.exists() else None,
                options=options,
                progress_callback=_on_progress,
            )

        jobs.submit(job.id, _task)
        return {"job_id": job.id}

    @app.get("/api/v1/jobs/{job_id}")
    def api_job_status(job_id: str) -> dict[str, Any]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "id": job.id,
            "status": job.status,
            "phase": job.phase,
            "progress": job.progress,
            "message": job.message,
            "error": job.error,
            "page_current": job.page_current,
            "page_total": job.page_total,
            "has_mono": job.mono_path is not None and job.mono_path.exists(),
            "has_dual": job.dual_path is not None and job.dual_path.exists(),
        }

    @app.get("/api/v1/jobs/{job_id}/download/{kind}")
    def api_job_download(job_id: str, kind: str) -> FileResponse:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        path = job.mono_path if kind == "mono" else job.dual_path if kind == "dual" else None
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="文件尚未就绪")
        return FileResponse(path, filename=path.name, media_type="application/pdf")

    @app.get("/api/v1/settings")
    def api_get_settings() -> dict[str, Any]:
        return read_settings(cfg_path)

    @app.put("/api/v1/settings")
    def api_put_settings(payload: SettingsPayload) -> dict[str, Any]:
        try:
            save_user_settings(
                cfg_path,
                api_key=payload.api_key,
                translate_engine=payload.translate_engine,
                layout_polish=payload.layout_polish,
            )
        except PdfTraError as err:
            raise _http_error(err) from err
        return read_settings(cfg_path)

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/")
        def spa_home() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


def _safe_pdf_filename(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="请上传 PDF 文件")
    name = Path(filename).name
    if not name or not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 文件")
    return name


def _inspect_to_dict(result: InspectResult) -> dict[str, Any]:
    return {
        "filename": result.input_path.name,
        "path": str(result.input_path),
        "pages": result.pdf_info.pages,
        "encrypted": result.pdf_info.encrypted,
        "pdf_type": result.pdf_type,
        "char_count": result.char_count,
        "suggestion": result.suggestion,
        "detected_lang": result.detected_lang,
        "detected_lang_label": result.detected_lang_label,
        "target_lang": result.target_lang,
        "target_lang_label": result.target_lang_label,
        "lang_detect_fallback": result.lang_detect_fallback,
        "can_translate": result.can_translate,
        "needs_ocr": result.needs_ocr,
        "ocr_available": result.ocr_available,
    }


def _http_error(err: PdfTraError) -> HTTPException:
    return HTTPException(status_code=http_status_for_exit_code(err.exit_code), detail=err.message)
