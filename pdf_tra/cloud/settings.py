from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CloudSettings:
    wechat_app_id: str
    wechat_app_secret: str
    jwt_secret: str
    jwt_expire_days: int = 7
    max_file_bytes: int = 20 * 1024 * 1024
    max_pages_per_job: int = 100
    daily_pages_per_user: int = 50
    dev_mode: bool = False

    @classmethod
    def from_env(cls) -> CloudSettings:
        app_id = os.environ.get("WECHAT_APP_ID", "")
        secret = os.environ.get("WECHAT_APP_SECRET", "")
        jwt_secret = os.environ.get("JWT_SECRET", "")
        dev = os.environ.get("PDF_TRA_CLOUD_DEV", "").lower() in {"1", "true", "yes"}
        if not dev and (not app_id or not secret or not jwt_secret):
            raise RuntimeError(
                "云模式需要环境变量 WECHAT_APP_ID、WECHAT_APP_SECRET、JWT_SECRET"
                "（本地开发可设 PDF_TRA_CLOUD_DEV=true）"
            )
        return cls(
            wechat_app_id=app_id,
            wechat_app_secret=secret,
            jwt_secret=jwt_secret or "dev-jwt-secret-change-me",
            jwt_expire_days=int(os.environ.get("JWT_EXPIRE_DAYS", "7")),
            max_file_bytes=int(os.environ.get("MAX_FILE_BYTES", str(20 * 1024 * 1024))),
            max_pages_per_job=int(os.environ.get("MAX_PAGES_PER_JOB", "100")),
            daily_pages_per_user=int(os.environ.get("DAILY_PAGES_PER_USER", "50")),
            dev_mode=dev,
        )
