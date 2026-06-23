from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class StoredFile:
    file_id: str
    openid: str
    path: Path
    filename: str
    pages: int
    created_at: str


class FileRegistry:
    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}
        self._lock = threading.Lock()

    def register(self, openid: str, path: Path, filename: str, *, pages: int) -> str:
        file_id = uuid.uuid4().hex
        entry = StoredFile(
            file_id=file_id,
            openid=openid,
            path=path,
            filename=filename,
            pages=pages,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._files[file_id] = entry
        return file_id

    def resolve(self, openid: str, file_id: str) -> StoredFile | None:
        with self._lock:
            entry = self._files.get(file_id)
        if entry is None or entry.openid != openid:
            return None
        return entry


class UsageTracker:
    def __init__(self, daily_pages_limit: int) -> None:
        self._daily_pages_limit = daily_pages_limit
        self._pages: dict[str, int] = {}
        self._day: str = self._today()
        self._lock = threading.Lock()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_if_new_day(self) -> None:
        today = self._today()
        if today != self._day:
            self._pages.clear()
            self._day = today

    def pages_used(self, openid: str) -> int:
        with self._lock:
            self._reset_if_new_day()
            return self._pages.get(openid, 0)

    def check_and_add(self, openid: str, pages: int) -> None:
        with self._lock:
            self._reset_if_new_day()
            used = self._pages.get(openid, 0)
            if used + pages > self._daily_pages_limit:
                raise ValueError(
                    f"今日翻译页数已达上限（{self._daily_pages_limit} 页），请明天再试"
                )
            self._pages[openid] = used + pages
