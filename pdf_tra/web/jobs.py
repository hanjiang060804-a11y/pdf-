from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

JobStatus = Literal["pending", "running", "done", "error"]
JobPhase = Literal["preparing", "ocr", "translate", "polish", "done", "error"]


@dataclass
class Job:
    id: str
    owner_openid: str | None = None
    status: JobStatus = "pending"
    phase: JobPhase = "preparing"
    progress: int = 0
    message: str = "等待开始"
    error: str | None = None
    page_current: int | None = None
    page_total: int | None = None
    mono_path: Path | None = None
    dual_path: Path | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdf-tra-job")

    def create(self, *, owner_openid: str | None = None) -> Job:
        job = Job(id=uuid.uuid4().hex, owner_openid=owner_openid)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)

    def submit(self, job_id: str, fn, *args, **kwargs) -> None:
        def _run() -> None:
            self.update(
                job_id,
                status="running",
                phase="preparing",
                progress=2,
                message="正在准备…",
            )
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                self.update(
                    job_id,
                    status="error",
                    phase="error",
                    progress=0,
                    error=str(exc),
                    message="翻译失败",
                )
                return
            mono = getattr(result, "mono_pdf", None)
            dual = getattr(result, "dual_pdf", None)
            self.update(
                job_id,
                status="done",
                phase="done",
                progress=100,
                message="翻译完成",
                mono_path=mono,
                dual_path=dual,
            )

        self._executor.submit(_run)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
