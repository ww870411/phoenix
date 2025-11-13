# -*- coding: utf-8 -*-
"""
数据看板缓存发布后台任务管理。

提供启动、状态查询与取消控制，避免长耗时任务阻塞请求线程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from threading import Lock, Thread
from typing import Any, Dict, List, Tuple

from backend.services.dashboard_cache import (
    DEFAULT_CACHE_KEY,
    resolve_cache_key,
    update_cache_entry,
)
from backend.services.dashboard_expression import evaluate_dashboard

EAST_8 = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(EAST_8).isoformat()


@dataclass
class CachePublishState:
    status: str = "idle"  # idle / running / completed / failed / aborted
    total: int = 0
    processed: int = 0
    current_label: str = ""
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "total": self.total,
            "processed": self.processed,
            "current_label": self.current_label,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated_at": self.updated_at,
        }


class CachePublishJobManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state = CachePublishState()
        self._thread: Thread | None = None
        self._abort_requested = False

    def start(self, project_key: str, schedule: List[str]) -> Tuple[Dict[str, Any], bool]:
        with self._lock:
            if self._state.status == "running":
                return self._state.snapshot(), False
            self._state = CachePublishState(
                status="running",
                total=len(schedule),
                processed=0,
                current_label="",
                started_at=_now(),
                updated_at=_now(),
            )
            self._abort_requested = False
            self._thread = Thread(
                target=self._run, args=(project_key, schedule), daemon=True
            )
            self._thread.start()
            return self._state.snapshot(), True

    def request_cancel(self) -> Dict[str, Any]:
        with self._lock:
            if self._state.status == "running":
                self._abort_requested = True
            return self._state.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._state.snapshot()

    def _run(self, project_key: str, schedule: List[str]) -> None:
        for index, show_date in enumerate(schedule, start=1):
            with self._lock:
                if self._abort_requested:
                    self._state.status = "aborted"
                    self._state.finished_at = _now()
                    self._state.updated_at = _now()
                    return
                label = show_date or "默认"
                self._state.current_label = label
                self._state.updated_at = _now()

            try:
                result = evaluate_dashboard(project_key, show_date=show_date)
                payload = {"ok": True, **result.to_dict()}
                cache_key = resolve_cache_key(show_date or "")
                update_cache_entry(project_key, cache_key, payload)
            except Exception as exc:  # pragma: no cover
                with self._lock:
                    self._state.status = "failed"
                    self._state.error = str(exc)
                    self._state.finished_at = _now()
                    self._state.updated_at = _now()
                return

            with self._lock:
                self._state.processed = index
                self._state.updated_at = _now()

        with self._lock:
            self._state.status = "completed"
            self._state.finished_at = _now()
            self._state.updated_at = _now()


cache_publish_job_manager = CachePublishJobManager()


__all__ = ["cache_publish_job_manager"]
