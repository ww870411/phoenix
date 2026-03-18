"""数据看板缓存发布任务管理。"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from multiprocessing import Process
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Sequence, Tuple

from backend.services.dashboard_cache import resolve_cache_key, update_cache_entry
from backend.services.dashboard_expression import (
    evaluate_dashboard,
    load_dashboard_config,
    load_default_push_date,
    normalize_show_date,
)
from backend.services.project_data_paths import get_project_runtime_dir

EAST_8 = timezone(timedelta(hours=8))
STATE_FILENAME = "dashboard_cache_publish_state.json"
CANCEL_FILENAME = "dashboard_cache_publish_cancel.flag"
LOCK_FILENAME = "dashboard_cache_publish.lock"
LOG_DIRNAME = "dashboard_cache_publish_logs"
LOG_TAIL_LIMIT = 200
SECTION_GROUPS: List[Tuple[str, List[str]]] = [
    ("temperature", ["1"]),
    ("cumulative_cards", ["9"]),
    ("daily_trend", ["10"]),
    ("metrics_profit", ["2", "3", "5"]),
    ("metrics_operation", ["4", "6", "8"]),
    ("detail_tables", ["0.5", "7", "11"]),
]

GROUP_LABELS: Dict[str, str] = {
    "temperature": "日均气温",
    "cumulative_cards": "累计卡片",
    "daily_trend": "每日对比趋势",
    "metrics_profit": "利润收入与标煤",
    "metrics_operation": "单耗投诉与分中心",
    "detail_tables": "明细表格与设备状态",
}


def _now() -> str:
    return datetime.now(EAST_8).isoformat()


def _runtime_dir(project_key: str) -> Path:
    return get_project_runtime_dir(project_key).resolve()


def _state_file(project_key: str) -> Path:
    return _runtime_dir(project_key) / STATE_FILENAME


def _cancel_file(project_key: str) -> Path:
    return _runtime_dir(project_key) / CANCEL_FILENAME


def _lock_file(project_key: str) -> Path:
    return _runtime_dir(project_key) / LOCK_FILENAME


def _logs_dir(project_key: str) -> Path:
    return _runtime_dir(project_key) / LOG_DIRNAME


def _results_dir(project_key: str) -> Path:
    return _runtime_dir(project_key) / "dashboard_cache_publish_results"


def _result_file(project_key: str, group_name: str) -> Path:
    return _results_dir(project_key) / f"{group_name}.json"


def _log_file(project_key: str, pid: int | None) -> Path:
    label = str(pid) if isinstance(pid, int) and pid > 0 else "unknown"
    return _logs_dir(project_key) / f"{label}.jsonl"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _pid_is_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def _reset_logs(project_key: str) -> None:
    log_dir = _logs_dir(project_key)
    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)


def _reset_results(project_key: str) -> None:
    result_dir = _results_dir(project_key)
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)


def _append_log(
    project_key: str,
    text: str,
    pid: int | None = None,
    level: str = "info",
    group: str | None = None,
) -> None:
    message = str(text or "").strip()
    if not message:
        return
    _logs_dir(project_key).mkdir(parents=True, exist_ok=True)
    entry = {
        "time": _now(),
        "pid": pid if isinstance(pid, int) and pid > 0 else None,
        "level": level,
        "text": message,
        "group": group or None,
    }
    with _log_file(project_key, pid).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_logs(project_key: str, tail_limit: int = LOG_TAIL_LIMIT) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    log_dir = _logs_dir(project_key)
    if not log_dir.exists():
        return [], []

    grouped: List[Dict[str, Any]] = []
    merged: List[Dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.jsonl")):
        rows: List[Dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []
        for line in lines:
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            rows.append(payload)
            merged.append(payload)
        pid = None
        try:
            pid = int(path.stem)
        except ValueError:
            pid = None
        grouped.append({"pid": pid, "entries": rows[-tail_limit:]})

    merged.sort(key=lambda item: (str(item.get("time") or ""), str(item.get("pid") or "")))
    return merged[-tail_limit:], grouped


def _load_group_results(project_key: str) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for group_name, _section_indexes in SECTION_GROUPS:
        path = _result_file(project_key, group_name)
        if not path.exists():
            continue
        payload = _read_json(path)
        if isinstance(payload, dict):
            results[group_name] = payload
    return results


def _load_worker_groups(
    project_key: str,
    state: "CachePublishState",
    logs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    latest_by_group: Dict[str, Dict[str, Any]] = {}
    for entry in logs:
        group_name = entry.get("group")
        if isinstance(group_name, str) and group_name:
            latest_by_group[group_name] = entry

    result_by_group = _load_group_results(project_key)
    worker_groups: List[Dict[str, Any]] = []
    for group_name, section_indexes in SECTION_GROUPS:
        latest = latest_by_group.get(group_name)
        result = result_by_group.get(group_name)
        status = "pending"
        message = "等待开始"
        updated_at = None

        if isinstance(latest, dict):
            updated_at = latest.get("time")
            latest_text = str(latest.get("text") or "").strip()
            latest_level = str(latest.get("level") or "info")
            if latest_level == "error":
                status = "failed"
            elif latest_level == "warn" and "中止" in latest_text:
                status = "aborted"
            elif "完成" in latest_text:
                status = "completed"
            else:
                status = "running"
            if latest_text:
                message = latest_text

        if isinstance(result, dict):
            updated_at = result.get("updated_at") or updated_at
            if result.get("ok"):
                status = "completed"
                message = "本分块已完成"
            elif result.get("aborted"):
                status = "aborted"
                message = str(result.get("error") or "本分块已中止")
            else:
                status = "failed"
                message = str(result.get("error") or "本分块执行失败")

        if state.status == "idle" and group_name not in result_by_group:
            status = "pending"
            message = "暂无任务"
        elif state.status == "completed" and group_name not in result_by_group:
            status = "completed"
            message = "本轮任务已完成"
        elif state.status == "aborted" and status in {"pending", "running"}:
            status = "aborted"
            message = "本轮任务已中止"
        elif state.status == "failed" and status in {"pending", "running"}:
            status = "failed"
            message = state.error or "发布任务失败"

        worker_groups.append(
            {
                "key": group_name,
                "label": GROUP_LABELS.get(group_name, group_name),
                "sections": list(section_indexes),
                "status": status,
                "message": message,
                "updated_at": updated_at,
            }
        )
    return worker_groups


@dataclass
class CachePublishState:
    status: str = "idle"
    total: int = 0
    processed: int = 0
    current_label: str = ""
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    pid: int | None = None

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
            "pid": self.pid,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CachePublishState":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            status=str(payload.get("status") or "idle"),
            total=int(payload.get("total") or 0),
            processed=int(payload.get("processed") or 0),
            current_label=str(payload.get("current_label") or ""),
            error=payload.get("error"),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            updated_at=payload.get("updated_at"),
            pid=payload.get("pid") if isinstance(payload.get("pid"), int) else None,
        )


def _load_state(project_key: str) -> CachePublishState:
    return CachePublishState.from_dict(_read_json(_state_file(project_key)))


def _write_state(project_key: str, state: CachePublishState) -> None:
    _write_json(_state_file(project_key), state.snapshot())


def _update_state(project_key: str, **changes: Any) -> CachePublishState:
    state = _load_state(project_key)
    for key, value in changes.items():
        if hasattr(state, key):
            setattr(state, key, value)
    state.updated_at = _now()
    _write_state(project_key, state)
    return state


def _state_snapshot_with_logs(project_key: str, state: CachePublishState) -> Dict[str, Any]:
    payload = state.snapshot()
    logs, grouped_logs = _load_logs(project_key)
    payload["logs"] = logs
    payload["logs_by_pid"] = grouped_logs
    payload["worker_groups"] = _load_worker_groups(project_key, state, logs)
    return payload


def _acquire_lock(project_key: str) -> bool:
    path = _lock_file(project_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        os.write(fd, f"{os.getpid()}".encode("utf-8"))
    finally:
        os.close(fd)
    return True


def _release_lock(project_key: str) -> None:
    _safe_unlink(_lock_file(project_key))


def _request_cancel(project_key: str) -> None:
    path = _cancel_file(project_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_now(), encoding="utf-8")


def _cancel_requested(project_key: str) -> bool:
    return _cancel_file(project_key).exists()


def _clear_cancel(project_key: str) -> None:
    _safe_unlink(_cancel_file(project_key))


def _mark_stale_if_needed(project_key: str) -> CachePublishState:
    state = _load_state(project_key)
    if state.status != "running":
        return state
    if _pid_is_alive(state.pid):
        return state
    state.status = "failed"
    state.error = "缓存发布进程已退出"
    state.finished_at = _now()
    state.updated_at = state.finished_at
    stale_pid = state.pid
    state.pid = None
    _write_state(project_key, state)
    _append_log(project_key, "缓存发布进程已退出", pid=stale_pid, level="error")
    _release_lock(project_key)
    _clear_cancel(project_key)
    return state


def _build_base_payload(project_key: str, show_date: str) -> Dict[str, Any]:
    normalized_show_date = normalize_show_date(show_date)
    push_date = normalized_show_date or load_default_push_date(project_key)
    data = dict(load_dashboard_config(project_key))
    data["push_date"] = push_date
    data["展示日期"] = push_date
    return {
        "project_key": project_key,
        "show_date": normalized_show_date,
        "push_date": push_date,
        "generated_at": _now(),
        "source": "config/dashboard_expression_parallel",
        "data": data,
    }


def _merge_partial_data(base_data: Dict[str, Any], partial_data: Dict[str, Any]) -> None:
    for key, value in (partial_data or {}).items():
        base_data[key] = value


def _run_section_group(
    project_key: str,
    show_date: str,
    group_name: str,
    section_indexes: Sequence[str],
) -> None:
    pid = os.getpid()
    _append_log(
        project_key,
        f"开始计算 {GROUP_LABELS.get(group_name, group_name)}：{','.join(section_indexes)}",
        pid=pid,
        group=group_name,
    )
    try:
        result = evaluate_dashboard(
            project_key,
            show_date=show_date,
            check_abort=lambda: _cancel_requested(project_key),
            on_progress=None,
            shared_metrics_cache=None,
            only_section_indexes=section_indexes,
        )
        _write_json(
            _result_file(project_key, group_name),
            {
                "ok": True,
                "pid": pid,
                "group": group_name,
                "section_indexes": list(section_indexes),
                "data": result.data,
                "source": result.source,
                "updated_at": _now(),
            },
        )
        _append_log(project_key, f"{GROUP_LABELS.get(group_name, group_name)}已完成", pid=pid, group=group_name)
    except InterruptedError:
        _write_json(
            _result_file(project_key, group_name),
            {
                "ok": False,
                "pid": pid,
                "group": group_name,
                "aborted": True,
                "error": "任务已中止",
                "updated_at": _now(),
            },
        )
        _append_log(project_key, f"{GROUP_LABELS.get(group_name, group_name)}已中止", pid=pid, level="warn", group=group_name)
    except Exception as exc:  # pragma: no cover
        _write_json(
            _result_file(project_key, group_name),
            {"ok": False, "pid": pid, "group": group_name, "error": str(exc), "updated_at": _now()},
        )
        _append_log(
            project_key,
            f"{GROUP_LABELS.get(group_name, group_name)}失败：{exc}",
            pid=pid,
            level="error",
            group=group_name,
        )


def _build_parallel_payload(project_key: str, show_date: str) -> Dict[str, Any]:
    base_payload = _build_base_payload(project_key, show_date)
    workers: List[Tuple[str, Process]] = []
    _reset_results(project_key)

    for group_name, section_indexes in SECTION_GROUPS:
        process = Process(
            target=_run_section_group,
            args=(project_key, show_date, group_name, list(section_indexes)),
            daemon=False,
        )
        process.start()
        workers.append((group_name, process))
        _append_log(
            project_key,
            f"已启动{GROUP_LABELS.get(group_name, group_name)}任务",
            pid=process.pid,
            group=group_name,
        )

    pending = {group_name for group_name, _ in workers}
    sources: List[str] = []
    errors: List[str] = []
    aborted = False

    while pending:
        if _cancel_requested(project_key):
            aborted = True
            break
        finished_groups = []
        for group_name in list(pending):
            result_path = _result_file(project_key, group_name)
            if not result_path.exists():
                continue
            message = _read_json(result_path)
            finished_groups.append(group_name)
            if message.get("ok"):
                _merge_partial_data(base_payload["data"], message.get("data") or {})
                source = message.get("source")
                if isinstance(source, str) and source:
                    sources.append(source)
            else:
                if message.get("aborted"):
                    aborted = True
                else:
                    errors.append(str(message.get("error") or f"分组 {group_name} 失败"))
        for group_name in finished_groups:
            pending.discard(group_name)
        if pending and not aborted and not errors:
            import time
            time.sleep(0.1)

    for group_name, process in workers:
        if process.is_alive() and (aborted or errors):
            process.terminate()
        process.join(timeout=5)
        if group_name in pending and not aborted and not errors:
            errors.append(f"分组 {group_name} 未返回结果")

    if aborted:
        raise InterruptedError("Dashboard evaluation aborted by user")
    if errors:
        raise RuntimeError("；".join(errors))

    if sources:
        base_payload["source"] = sources[0]
    base_payload["generated_at"] = _now()
    return base_payload


def _build_serial_payload(project_key: str, show_date: str) -> Dict[str, Any]:
    result = evaluate_dashboard(
        project_key,
        show_date=show_date,
        check_abort=lambda: _cancel_requested(project_key),
        on_progress=None,
        shared_metrics_cache={},
    )
    return {"ok": True, **result.to_dict()}


def _build_publish_payload(project_key: str, show_date: str) -> Dict[str, Any]:
    if show_date:
        payload = _build_parallel_payload(project_key, show_date)
        payload["ok"] = True
        return payload
    return _build_serial_payload(project_key, show_date)


def _run_publish_job(project_key: str, schedule: List[str]) -> None:
    pid = os.getpid()
    _update_state(project_key, pid=pid)
    _append_log(project_key, f"发布子进程启动，共 {len(schedule)} 天", pid=pid)

    try:
        for index, show_date in enumerate(schedule, start=1):
            label = show_date or "默认"
            if _cancel_requested(project_key):
                _append_log(project_key, f"收到取消信号，停止于 {label}", pid=pid, level="warn")
                _update_state(project_key, status="aborted", current_label=label, finished_at=_now(), pid=None)
                return

            _update_state(project_key, current_label=label, pid=pid)
            _append_log(project_key, f"开始处理 {label}（{index}/{len(schedule)}）", pid=pid)

            try:
                payload = _build_publish_payload(project_key, show_date)
                cache_key = resolve_cache_key(show_date or "")
                update_cache_entry(project_key, cache_key, payload)
            except InterruptedError:
                _append_log(project_key, f"任务在 {label} 被中止", pid=pid, level="warn")
                _update_state(project_key, status="aborted", current_label=label, finished_at=_now(), pid=None)
                return
            except Exception as exc:  # pragma: no cover
                _append_log(project_key, f"{label} 失败：{exc}", pid=pid, level="error")
                _update_state(project_key, status="failed", current_label=label, error=str(exc), finished_at=_now(), pid=None)
                return

            _append_log(project_key, f"完成 {label}", pid=pid)
            _update_state(project_key, processed=index, current_label=label, pid=pid)

        _append_log(project_key, "缓存发布完成", pid=pid)
        _update_state(project_key, status="completed", finished_at=_now(), current_label="", pid=None)
    finally:
        _release_lock(project_key)
        _clear_cancel(project_key)


class CachePublishJobManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._process: Process | None = None

    def start(self, project_key: str, schedule: List[str]) -> Tuple[Dict[str, Any], bool]:
        with self._lock:
            state = _mark_stale_if_needed(project_key)
            if state.status == "running":
                return _state_snapshot_with_logs(project_key, state), False

            if not _acquire_lock(project_key):
                state = _mark_stale_if_needed(project_key)
                if state.status == "running":
                    return _state_snapshot_with_logs(project_key, state), False
                if not _acquire_lock(project_key):
                    return _state_snapshot_with_logs(project_key, state), False

            started_at = _now()
            state = CachePublishState(
                status="running",
                total=len(schedule),
                processed=0,
                current_label="",
                error=None,
                started_at=started_at,
                finished_at=None,
                updated_at=started_at,
                pid=os.getpid(),
            )
            _clear_cancel(project_key)
            _reset_logs(project_key)
            _reset_results(project_key)
            _append_log(project_key, f"收到发布请求，共 {len(schedule)} 天", pid=os.getpid())
            _write_state(project_key, state)

            process = Process(target=_run_publish_job, args=(project_key, list(schedule)), daemon=False)
            try:
                process.start()
            except Exception as exc:
                _append_log(project_key, f"启动发布子进程失败：{exc}", pid=os.getpid(), level="error")
                _release_lock(project_key)
                _clear_cancel(project_key)
                raise

            state.pid = process.pid
            state.updated_at = _now()
            _append_log(project_key, f"发布子进程已启动，pid={process.pid}", pid=process.pid)
            _write_state(project_key, state)
            self._process = process
            return _state_snapshot_with_logs(project_key, state), True

    def request_cancel(self, project_key: str) -> Dict[str, Any]:
        with self._lock:
            state = _mark_stale_if_needed(project_key)
            if state.status == "running":
                _request_cancel(project_key)
                state.updated_at = _now()
                _append_log(project_key, "收到停止任务请求", pid=state.pid, level="warn")
                _write_state(project_key, state)
            return _state_snapshot_with_logs(project_key, state)

    def snapshot(self, project_key: str) -> Dict[str, Any]:
        with self._lock:
            state = _mark_stale_if_needed(project_key)
            return _state_snapshot_with_logs(project_key, state)


cache_publish_job_manager = CachePublishJobManager()


__all__ = ["cache_publish_job_manager"]
