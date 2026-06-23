from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from pdf_tra.cloud.auth import (
    AuthError,
    create_token,
    exchange_wechat_code,
    mask_openid,
    verify_token,
)
from pdf_tra.cloud.files import FileRegistry, UsageTracker
from pdf_tra.cloud.settings import CloudSettings
from pdf_tra.config.loader import load_config
from pdf_tra.core.errors import PdfTraError
from pdf_tra.core.models import TranslateOptions
from pdf_tra.service import get_capabilities, inspect_pdf, translate_pdf
from pdf_tra.web.jobs import JobStore
from pdf_tra.web.server import _http_error, _inspect_to_dict, _safe_pdf_filename


class WechatAuthPayload(BaseModel):
    code: str = Field(min_length=1)


class TranslateCloudPayload(BaseModel):
    file_id: str = Field(min_length=8)
    ocr: bool = False
    engine: str | None = None
    polish: bool | None = None


def create_cloud_app(
    *,
    config_path: Path | None = None,
    upload_dir: Path | None = None,
    settings: CloudSettings | None = None,
) -> FastAPI:
    cfg_path = (config_path or Path(os.environ.get("PDF_TRA_CONFIG", "config.json"))).resolve()
    uploads = (
        upload_dir or Path(os.environ.get("PDF_TRA_UPLOAD_DIR", "output/cloud-uploads"))
    ).resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    cloud_settings = settings or CloudSettings.from_env()
    jobs = JobStore()
    files = FileRegistry()
    usage = UsageTracker(cloud_settings.daily_pages_per_user)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.cloud_settings = cloud_settings
        app.state.files = files
        app.state.usage = usage
        yield
        jobs.shutdown()

    app = FastAPI(title="pdf-tra-cloud", version="2.0.0-alpha", lifespan=lifespan)
    bearer = HTTPBearer(auto_error=False)

    def get_openid(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> str:
        if credentials is None:
            raise HTTPException(status_code=401, detail="请先登录")
        try:
            return verify_token(cloud_settings, credentials.credentials)
        except AuthError as err:
            raise HTTPException(status_code=401, detail=str(err)) from err

    def get_job_for_user(job_id: str, openid: str):
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        if job.owner_openid != openid:
            raise HTTPException(status_code=404, detail="任务不存在")
        return job

    @app.post("/api/v2/auth/wechat")
    def api_wechat_auth(payload: WechatAuthPayload) -> dict[str, str]:
        try:
            openid = exchange_wechat_code(cloud_settings, payload.code)
            token = create_token(cloud_settings, openid)
        except AuthError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except httpx.HTTPError as err:
            raise HTTPException(status_code=502, detail="微信服务暂不可用") from err
        return {
            "token": token,
            "openid_masked": mask_openid(openid),
        }

    @app.get("/api/v2/me")
    def api_me(openid: str = Depends(get_openid)) -> dict[str, Any]:
        used = usage.pages_used(openid)
        return {
            "openid_masked": mask_openid(openid),
            "pages_used_today": used,
            "pages_limit_today": cloud_settings.daily_pages_per_user,
            "pages_remaining_today": max(0, cloud_settings.daily_pages_per_user - used),
        }

    @app.get("/api/v1/capabilities")
    def api_capabilities() -> dict:
        return get_capabilities()

    @app.post("/api/v1/inspect")
    async def api_inspect_upload(
        openid: str = Depends(get_openid),
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        filename = _safe_pdf_filename(file.filename)
        user_dir = uploads / openid
        user_dir.mkdir(parents=True, exist_ok=True)
        dest = user_dir / f"{uuid.uuid4().hex}_{filename}"
        size = 0
        with dest.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > cloud_settings.max_file_bytes:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="文件过大，请压缩后重试")
                out.write(chunk)
        try:
            result = inspect_pdf(dest, config_path=cfg_path if cfg_path.exists() else None)
        except PdfTraError as err:
            dest.unlink(missing_ok=True)
            raise _http_error(err) from err

        if result.pdf_info.pages > cloud_settings.max_pages_per_job:
            dest.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail=f"超过单文件页数上限（{cloud_settings.max_pages_per_job} 页）",
            )

        file_id = files.register(
            openid, dest, filename, pages=result.pdf_info.pages
        )
        body = _inspect_to_dict(result)
        body.pop("path", None)
        body["file_id"] = file_id
        return body

    @app.post("/api/v1/translate")
    def api_translate(
        payload: TranslateCloudPayload,
        openid: str = Depends(get_openid),
    ) -> dict[str, str]:
        entry = files.resolve(openid, payload.file_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="文件不存在或已过期")

        try:
            usage.check_and_add(openid, entry.pages)
        except ValueError as err:
            raise HTTPException(status_code=429, detail=str(err)) from err

        path = entry.path
        out_dir = uploads / openid / "translated" / entry.file_id
        out_dir.mkdir(parents=True, exist_ok=True)
        job = jobs.create(owner_openid=openid)

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
    def api_job_status(
        job_id: str,
        openid: str = Depends(get_openid),
    ) -> dict[str, Any]:
        job = get_job_for_user(job_id, openid)
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
    def api_job_download(
        job_id: str,
        kind: str,
        openid: str = Depends(get_openid),
    ) -> FileResponse:
        job = get_job_for_user(job_id, openid)
        path = job.mono_path if kind == "mono" else job.dual_path if kind == "dual" else None
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="文件尚未就绪")
        return FileResponse(path, filename=path.name, media_type="application/pdf")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pdf-tra-cloud"}

    return app
