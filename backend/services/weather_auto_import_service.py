# -*- coding: utf-8 -*-
"""
气温数据自动定时获取与入库调度服务（双模块独立实例）。

支持两个独立工作的气象模块：
1. `weather_auto_import_service`：近端逐小时实况与近 3 天预报（`type='near'`），对应数据看板“导入气温”；
2. `ensemble_weather_auto_import_service`：未来 35 天集合气温预报（`type='far'`），对应计划情景分解模型“导入35天预报”。

核心能力：
- 各自独立的 API URL 与多时段定时时间点（HH:MM，北京时间）配置；
- 各自独立的守护线程巡检，到点即尝试一次获取并入库；
- 各自持久化记录上次成功时间、上次失败时间、最近尝试状态及近 30 条尝试历史（UTF-8 无 BOM 原子写入）。
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services import ensemble_weather_service, weather_importer
from backend.services.auth_manager import EAST_8
from backend.services.project_settings import (
    DEFAULT_PROJECT_KEY,
    atomic_write_json,
    get_settings_section,
    has_settings_section,
    update_settings_section,
)

logger = logging.getLogger("weather_auto_import")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [weather_auto] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

MAX_SCHEDULE_TIMES = 48
MAX_HISTORY_RECORDS = 30
SCHEDULER_POLL_SECONDS = 15.0
SLOT_TRIGGER_WINDOW_SECONDS = 90.0


def _now_east8() -> datetime:
    """获取当前北京时间（带 UTC+8 时区信息）。"""
    return datetime.now(EAST_8)


def _format_dt(dt: datetime) -> str:
    """统一格式化东八区时间为 YYYY-MM-DD HH:MM:SS。"""
    return dt.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S")


def _auto_config_path() -> Path:
    """旧近端实况/预报自动获取配置文件（仅用于历史迁移兼容读取）。"""
    return weather_importer._weather_config_path().parent / "weather_auto_import_config.json"


def _auto_state_path() -> Path:
    """近端实况/预报运行态与历史记录文件（存于 runtime/）。"""
    return weather_importer._weather_config_path().parent / "weather_auto_import_state.json"


def _ensemble_auto_config_path() -> Path:
    """旧35天集合气温预报自动获取配置文件（仅用于历史迁移兼容读取）。"""
    return ensemble_weather_service._ensemble_config_path().parent / "ensemble_weather_auto_import_config.json"


def _ensemble_state_path() -> Path:
    """35天集合气温预报运行态与历史记录文件（存于 runtime/）。"""
    return ensemble_weather_service._ensemble_config_path().parent / "ensemble_weather_auto_import_state.json"


RUNTIME_STATE_KEYS = (
    "last_attempt_time",
    "last_attempt_status",
    "last_attempt_trigger",
    "last_attempt_message",
    "last_success_time",
    "last_success_trigger",
    "last_success_message",
    "last_success_summary",
    "last_failure_time",
    "last_failure_trigger",
    "last_failure_message",
    "executed_slots_date",
    "executed_slots_today",
    "history",
)


def _default_state(initial_idle_message: str = "尚未执行过气温自动或手动导入") -> Dict[str, Any]:
    return {
        "enabled": True,
        "schedule_times": [],
        "last_attempt_time": None,
        "last_attempt_status": "IDLE",
        "last_attempt_trigger": None,
        "last_attempt_message": initial_idle_message,
        "last_success_time": None,
        "last_success_trigger": None,
        "last_success_message": None,
        "last_success_summary": None,
        "last_failure_time": None,
        "last_failure_trigger": None,
        "last_failure_message": None,
        "executed_slots_date": None,
        "executed_slots_today": {},
        "history": [],
    }


def normalize_schedule_times(raw_times: Sequence[Any]) -> List[str]:
    """校验并规范化每日定时时间列表，返回去重且升序排列的 HH:MM 字符串列表。"""
    if raw_times is None:
        return []
    if isinstance(raw_times, str) or not isinstance(raw_times, Sequence):
        raise ValueError("自动获取时间设置必须为时间列表。")

    normalized: List[str] = []
    seen = set()
    for item in raw_times:
        text = str(item or "").strip()
        if not text:
            continue
        parts = text.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"无效的时间格式“{text}”，请使用 HH:MM（24 小时制）。")
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"时间“{text}”超出有效范围（00:00 ~ 23:59）。")
        formatted = f"{hour:02d}:{minute:02d}"
        if formatted not in seen:
            seen.add(formatted)
            normalized.append(formatted)

    if len(normalized) > MAX_SCHEDULE_TIMES:
        raise ValueError(f"每日最多允许设置 {MAX_SCHEDULE_TIMES} 个自动获取时间点。")

    normalized.sort()
    return normalized


def _parse_hhmm(slot: str) -> Tuple[int, int]:
    hour_str, minute_str = slot.split(":")
    return int(hour_str), int(minute_str)


def _compute_next_run_time(
    enabled: bool,
    schedule_times: Sequence[str],
    executed_slots_date: Optional[str],
    executed_slots_today: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Optional[str]:
    """根据启用状态、时间列表与当日已执行情况，计算下一次计划尝试时间。"""
    if not enabled or not schedule_times:
        return None

    current = (now or _now_east8()).astimezone(EAST_8)
    today_str = current.strftime("%Y-%m-%d")
    executed_today = executed_slots_today if executed_slots_date == today_str and isinstance(executed_slots_today, dict) else {}

    for slot in sorted(schedule_times):
        try:
            hour, minute = _parse_hhmm(slot)
        except Exception:
            continue
        slot_dt = datetime(current.year, current.month, current.day, hour, minute, 0, tzinfo=EAST_8)
        if slot in executed_today:
            continue
        if current < slot_dt + timedelta(seconds=SLOT_TRIGGER_WINDOW_SECONDS):
            return _format_dt(slot_dt)

    tomorrow = current.date() + timedelta(days=1)
    first_hour, first_minute = _parse_hhmm(sorted(schedule_times)[0])
    tomorrow_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, first_hour, first_minute, 0, tzinfo=EAST_8)
    return _format_dt(tomorrow_dt)


def _format_trigger_label(trigger: str, scheduled_slot: Optional[str] = None) -> str:
    if trigger == "auto":
        return f"定时自动 ({scheduled_slot})" if scheduled_slot else "定时自动"
    if trigger == "manual_admin":
        return "管理中心手动"
    if trigger == "manual_dashboard":
        return "数据看板手动"
    if trigger == "manual_dynamic_plan":
        return "计划情景页面手动"
    return trigger or "未知来源"


def _execute_near_weather_import() -> Dict[str, Any]:
    """执行一次近端逐小时气温拉取与入库。"""
    db_session = SessionLocal()
    try:
        result = weather_importer.fetch_hourly_temperatures()
        tz_name = (result.get("source") or {}).get("timezone")
        hourly_items = result.get("hourly", [])
        dates = list(result.get("dates") or [])
        total_hours = int((result.get("summary") or {}).get("total_hours") or len(hourly_items))

        persist_result = weather_importer.persist_hourly_temperatures(db_session, hourly_items, tz_name)
        inserted = int(persist_result.get("inserted") or 0)
        replaced = int(persist_result.get("replaced") or 0)
        date_span = f"{dates[0]} ~ {dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "—")
        success_msg = (
            f"气温获取并入库成功：共拉取 {total_hours} 小时，"
            f"写入 {inserted} 条、覆盖 {replaced} 条（日期范围：{date_span}）。"
        )
        return {
            "ok": True,
            "message": success_msg,
            "source": result.get("source"),
            "summary": {
                "total_hours": total_hours,
                "inserted": inserted,
                "replaced": replaced,
                "start": persist_result.get("start"),
                "end": persist_result.get("end"),
                "dates": dates,
            },
            "raw_summary": result.get("summary"),
            "dates": dates,
            "write_result": persist_result,
        }
    except Exception:
        try:
            db_session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            db_session.close()
        except Exception:
            pass


def _execute_ensemble_weather_import() -> Dict[str, Any]:
    """执行一次 35 天集合气温预报拉取、均值清洗与入库。"""
    res = ensemble_weather_service.fetch_and_import_ensemble_weather()
    if not res.get("ok"):
        raise RuntimeError(str(res.get("message") or "35 天集合气温预报入库失败"))

    inserted_or_updated = int(res.get("inserted_or_updated") or 0)
    skipped_near = int(res.get("skipped_near") or 0)
    start_time = str(res.get("start_time") or "")
    end_time = str(res.get("end_time") or "")
    members_count = int(res.get("members_count") or 0)
    start_date = start_time[:10] if start_time else ""
    end_date = end_time[:10] if end_time else ""
    date_span = f"{start_date} ~ {end_date}" if start_date and end_date else "—"
    success_msg = (
        f"35天集合预报获取并入库成功：写入/更新 {inserted_or_updated} 条，"
        f"跳过已有近端 near 记录 {skipped_near} 条（成员数：{members_count}，范围：{date_span}）。"
    )
    dates = [d for d in (start_date, end_date) if d]
    return {
        "ok": True,
        "message": success_msg,
        "summary": {
            "inserted_or_updated": inserted_or_updated,
            "skipped_near": skipped_near,
            "start_time": start_time,
            "end_time": end_time,
            "truncated_at": res.get("truncated_at"),
            "members_count": members_count,
            "dates": dates,
        },
        "dates": dates,
        "write_result": res,
        "inserted_or_updated": inserted_or_updated,
        "skipped_near": skipped_near,
        "start_time": start_time,
        "end_time": end_time,
        "truncated_at": res.get("truncated_at"),
        "members_count": members_count,
    }


class WeatherAutoImportService:
    """参数化气温自动定时获取与状态追踪服务，供近端与 35 天预报模块各自独立运行。"""

    def __init__(
        self,
        *,
        service_name: str = "near_weather",
        thread_name: str = "WeatherAutoImportScheduler",
        settings_section: str = "weather_near",
        config_path_getter: Optional[Callable[[], Path]] = None,
        legacy_state_path_getter: Optional[Callable[[], Path]] = None,
        import_executor: Optional[Callable[[], Dict[str, Any]]] = None,
        audit_resource_prefix: str = "weather",
        initial_idle_message: str = "尚未执行过气温自动或手动导入",
    ) -> None:
        self._service_name = service_name
        self._thread_name = thread_name
        self._settings_section = settings_section
        self._config_path_getter = config_path_getter or (lambda: _auto_state_path())
        self._legacy_state_path_getter = legacy_state_path_getter or (lambda: _auto_config_path())
        self._import_executor = import_executor or _execute_near_weather_import
        self._audit_resource_prefix = audit_resource_prefix
        self._initial_idle_message = initial_idle_message

        self._state_lock = threading.RLock()
        self._run_lock = threading.Lock()
        self._scheduler_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    def _get_config_path(self) -> Path:
        return self._config_path_getter()

    def _read_raw_state_file(self) -> Dict[str, Any]:
        """读取 runtime 运行态文件，不存在时兼容读取旧 auto_import_config.json。"""
        state_path = self._get_config_path()
        target_path = state_path
        if not target_path.exists():
            legacy_path = self._legacy_state_path_getter()
            if legacy_path and legacy_path != state_path and legacy_path.exists():
                target_path = legacy_path
            else:
                return {}
        try:
            raw = json.loads(target_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception as exc:
            logger.warning("[%s] 读取气温自动获取状态文件失败，回退默认配置: %s", self._service_name, exc)
            return {}

    def _read_state(self) -> Dict[str, Any]:
        """合并读取综合配置中的定时设置与 runtime 中的执行状态/历史。"""
        state = _default_state(self._initial_idle_message)
        raw_state = self._read_raw_state_file()

        # 1. 从 runtime 状态文件填充运行历史与今日槽位执行记录
        for key in (
            "last_attempt_time",
            "last_attempt_status",
            "last_attempt_trigger",
            "last_attempt_message",
            "last_success_time",
            "last_success_trigger",
            "last_success_message",
            "last_success_summary",
            "last_failure_time",
            "last_failure_trigger",
            "last_failure_message",
            "executed_slots_date",
        ):
            if key in raw_state and raw_state[key] is not None:
                state[key] = raw_state[key]

        if isinstance(raw_state.get("executed_slots_today"), dict):
            state["executed_slots_today"] = dict(raw_state["executed_slots_today"])
        if isinstance(raw_state.get("history"), list):
            state["history"] = [item for item in raw_state["history"] if isinstance(item, dict)][:MAX_HISTORY_RECORDS]

        # 2. 从综合配置文件读取 enabled 与 schedule_times（若尚未保存则回退旧文件）
        cfg_node: Dict[str, Any] = {}
        try:
            if has_settings_section(self._settings_section, project_key=DEFAULT_PROJECT_KEY):
                cfg_node = get_settings_section(self._settings_section, project_key=DEFAULT_PROJECT_KEY)
        except Exception as exc:
            logger.warning("[%s] 读取综合配置节 %s 失败: %s", self._service_name, self._settings_section, exc)

        if "enabled" in cfg_node:
            state["enabled"] = bool(cfg_node.get("enabled", True))
        elif "enabled" in raw_state:
            state["enabled"] = bool(raw_state.get("enabled", True))

        raw_times = cfg_node["schedule_times"] if "schedule_times" in cfg_node else raw_state.get("schedule_times")
        try:
            state["schedule_times"] = normalize_schedule_times(raw_times or [])
        except ValueError:
            state["schedule_times"] = []

        return state

    def _write_state(self, state: Dict[str, Any]) -> None:
        """仅将运行态与历史字段原子写入 runtime/*_state.json（不污染业务配置）。"""
        state_path = self._get_config_path()
        runtime_payload = {key: state.get(key) for key in RUNTIME_STATE_KEYS}
        atomic_write_json(state_path, runtime_payload)

    def _build_status_payload(self, state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
        current = (now or _now_east8()).astimezone(EAST_8)
        today_str = current.strftime("%Y-%m-%d")
        executed_today = (
            dict(state.get("executed_slots_today") or {})
            if state.get("executed_slots_date") == today_str
            else {}
        )
        payload = copy.deepcopy(state)
        payload["executed_slots_today"] = executed_today
        payload["is_running"] = self._run_lock.locked()
        payload["next_run_time"] = _compute_next_run_time(
            enabled=bool(payload.get("enabled", True)),
            schedule_times=payload.get("schedule_times") or [],
            executed_slots_date=today_str,
            executed_slots_today=executed_today,
            now=current,
        )
        return payload

    def get_status(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """获取自动导入配置与最近成功/失败状态快照。"""
        with self._state_lock:
            state = self._read_state()
            return self._build_status_payload(state, now=now)

    def update_config(
        self,
        enabled: Optional[bool] = None,
        schedule_times: Optional[Sequence[Any]] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """保存自动获取开关与多个定时时间点，并立即唤醒调度器。"""
        current = (now or _now_east8()).astimezone(EAST_8)
        today_str = current.strftime("%Y-%m-%d")

        with self._state_lock:
            state = self._read_state()
            config_updates: Dict[str, Any] = {}
            if enabled is not None:
                state["enabled"] = bool(enabled)
                config_updates["enabled"] = state["enabled"]
            else:
                config_updates["enabled"] = bool(state.get("enabled", True))

            if schedule_times is not None:
                normalized_times = normalize_schedule_times(schedule_times)
                state["schedule_times"] = normalized_times
                config_updates["schedule_times"] = normalized_times

                existing_executed = (
                    dict(state.get("executed_slots_today") or {})
                    if state.get("executed_slots_date") == today_str
                    else {}
                )
                updated_executed: Dict[str, str] = {}
                for slot in normalized_times:
                    if slot in existing_executed:
                        updated_executed[slot] = existing_executed[slot]
                        continue
                    hour, minute = _parse_hhmm(slot)
                    slot_dt = datetime(current.year, current.month, current.day, hour, minute, 0, tzinfo=EAST_8)
                    if slot_dt <= current:
                        updated_executed[slot] = f"跳过（{slot} 早于本次保存时刻）"
                state["executed_slots_date"] = today_str
                state["executed_slots_today"] = updated_executed
            else:
                config_updates["schedule_times"] = list(state.get("schedule_times") or [])

            update_settings_section(
                self._settings_section,
                config_updates,
                project_key=DEFAULT_PROJECT_KEY,
            )
            self._write_state(state)
            snapshot = self._build_status_payload(state, now=current)

        self._wake_event.set()
        return snapshot

    def _append_history(self, state: Dict[str, Any], entry: Dict[str, Any]) -> None:
        history = list(state.get("history") or [])
        history.insert(0, entry)
        state["history"] = history[:MAX_HISTORY_RECORDS]

    def _record_outcome(
        self,
        *,
        ok: bool,
        timestamp: datetime,
        trigger: str,
        message: str,
        scheduled_slot: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ts_str = _format_dt(timestamp)
        trigger_label = _format_trigger_label(trigger, scheduled_slot)

        with self._state_lock:
            state = self._read_state()
            state["last_attempt_time"] = ts_str
            state["last_attempt_status"] = "SUCCESS" if ok else "FAILED"
            state["last_attempt_trigger"] = trigger_label
            state["last_attempt_message"] = message

            if ok:
                state["last_success_time"] = ts_str
                state["last_success_trigger"] = trigger_label
                state["last_success_message"] = message
                state["last_success_summary"] = summary
            else:
                state["last_failure_time"] = ts_str
                state["last_failure_trigger"] = trigger_label
                state["last_failure_message"] = message

            self._append_history(
                state,
                {
                    "time": ts_str,
                    "status": "SUCCESS" if ok else "FAILED",
                    "trigger": trigger,
                    "trigger_label": trigger_label,
                    "scheduled_slot": scheduled_slot,
                    "message": message,
                    "summary": summary if ok else None,
                },
            )
            self._write_state(state)
            return self._build_status_payload(state, now=timestamp)

    def record_external_import_outcome(
        self,
        *,
        ok: bool,
        message: str,
        trigger: str = "manual_dashboard",
        summary: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """同步记录来自数据看板或计划情景分解页面的导入结果，使管理中心展示保持一致。"""
        return self._record_outcome(
            ok=ok,
            timestamp=(timestamp or _now_east8()).astimezone(EAST_8),
            trigger=trigger,
            message=message,
            summary=summary,
        )

    def _write_audit_log(self, trigger: str, message: str, operator: Optional[str], dates: Sequence[str]) -> None:
        """在真实运行环境中同步写入业务操作审计日志；失败时仅记录告警，不阻断主流程。"""
        try:
            from backend.projects.daily_report_25_26.services.audit_log_service import save_operation_log

            resource_date = dates[-1] if dates else _now_east8().strftime("%Y-%m-%d")
            op_name = operator or ("weather_scheduler" if trigger == "auto" else "global_admin")
            op_group = "System_scheduler" if trigger == "auto" else "Global_admin"
            save_operation_log(
                operator=op_name,
                operator_group=op_group,
                unit="集团生产调度中心",
                action_type="IMPORT_TEMPERATURE",
                action_desc=message,
                resource_id=f"{self._audit_resource_prefix}:{resource_date}",
            )
        except Exception as exc:
            logger.warning("[%s] 记录气温导入审计日志失败（已忽略）: %s", self._service_name, exc)

    def run_import_once(
        self,
        trigger: str = "auto",
        scheduled_slot: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行一次气温数据拉取与入库，并持久化记录成功或失败时间。"""
        if not self._run_lock.acquire(blocking=False):
            return {
                "ok": False,
                "busy": True,
                "status": "BUSY",
                "message": "当前已有气温导入任务正在执行，请稍候。",
                "data": self.get_status(),
            }

        try:
            exec_res = self._import_executor()
            finished_at = _now_east8()
            success_msg = str(exec_res.get("message") or "气温获取并入库成功。")
            dates = list(exec_res.get("dates") or [])
            summary = exec_res.get("summary")
            snapshot = self._record_outcome(
                ok=True,
                timestamp=finished_at,
                trigger=trigger,
                scheduled_slot=scheduled_slot,
                message=success_msg,
                summary=summary,
            )
            self._write_audit_log(trigger, success_msg, operator, dates)
            logger.info("[%s][%s] %s", self._service_name, _format_trigger_label(trigger, scheduled_slot), success_msg)
            payload: Dict[str, Any] = {
                "ok": True,
                "busy": False,
                "status": "SUCCESS",
                "fetched_at": finished_at.isoformat(),
                "message": success_msg,
                "source": exec_res.get("source"),
                "summary": exec_res.get("raw_summary") or summary,
                "dates": dates,
                "write_result": exec_res.get("write_result"),
                "data": snapshot,
            }
            for extra_key in (
                "inserted_or_updated",
                "skipped_near",
                "start_time",
                "end_time",
                "truncated_at",
                "members_count",
            ):
                if extra_key in exec_res:
                    payload[extra_key] = exec_res[extra_key]
            return payload
        except Exception as exc:
            finished_at = _now_east8()
            err_detail = str(exc).strip() or exc.__class__.__name__
            fail_msg = f"气温获取或入库失败：{err_detail}"
            snapshot = self._record_outcome(
                ok=False,
                timestamp=finished_at,
                trigger=trigger,
                scheduled_slot=scheduled_slot,
                message=fail_msg,
            )
            logger.warning("[%s][%s] %s", self._service_name, _format_trigger_label(trigger, scheduled_slot), fail_msg)
            return {
                "ok": False,
                "busy": False,
                "status": "FAILED",
                "fetched_at": finished_at.isoformat(),
                "message": fail_msg,
                "data": snapshot,
            }
        finally:
            self._run_lock.release()

    def _scheduler_step(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """执行单步时间检测；若命中待执行的设定时间点则触发一次获取并入库。"""
        current = (now or _now_east8()).astimezone(EAST_8)
        today_str = current.strftime("%Y-%m-%d")

        due_slots: List[str] = []
        with self._state_lock:
            state = self._read_state()
            changed = False

            if state.get("executed_slots_date") != today_str:
                state["executed_slots_date"] = today_str
                state["executed_slots_today"] = {}
                changed = True

            enabled = bool(state.get("enabled", True))
            schedule_times = list(state.get("schedule_times") or [])
            executed_today = dict(state.get("executed_slots_today") or {})

            if enabled and schedule_times:
                for slot in schedule_times:
                    if slot in executed_today:
                        continue
                    hour, minute = _parse_hhmm(slot)
                    slot_dt = datetime(current.year, current.month, current.day, hour, minute, 0, tzinfo=EAST_8)
                    delta = (current - slot_dt).total_seconds()
                    if 0 <= delta < SLOT_TRIGGER_WINDOW_SECONDS:
                        due_slots.append(slot)
                        executed_today[slot] = _format_dt(current)
                        changed = True

            if changed:
                state["executed_slots_today"] = executed_today
                self._write_state(state)

        results: List[Dict[str, Any]] = []
        for slot in due_slots:
            logger.info("[%s] 触发定时气温自动获取时间点：%s", self._service_name, slot)
            results.append(self.run_import_once(trigger="auto", scheduled_slot=slot))
        return results

    def _scheduler_loop(self) -> None:
        logger.info("[%s] 气温自动获取后台调度循环已启动。", self._service_name)
        while not self._stop_event.is_set():
            try:
                self._scheduler_step()
            except Exception as exc:
                logger.error("[%s] 气温自动获取调度单步执行异常: %s", self._service_name, exc)
            self._wake_event.wait(timeout=SCHEDULER_POLL_SECONDS)
            self._wake_event.clear()

    def start_scheduler(self) -> None:
        """启动后台定时调度守护线程。"""
        with self._scheduler_lock:
            if self._bg_thread and self._bg_thread.is_alive():
                return
            self._stop_event.clear()
            self._wake_event.clear()
            self._bg_thread = threading.Thread(
                target=self._scheduler_loop,
                name=self._thread_name,
                daemon=True,
            )
            self._bg_thread.start()
            logger.info("[%s] 气温自动获取后台调度线程已启动。", self._service_name)

    def stop_scheduler(self) -> None:
        """停止后台定时调度守护线程。"""
        with self._scheduler_lock:
            self._stop_event.set()
            self._wake_event.set()
            if self._bg_thread and self._bg_thread.is_alive():
                self._bg_thread.join(timeout=2.0)
            self._bg_thread = None


weather_auto_import_service = WeatherAutoImportService(
    service_name="near_weather",
    thread_name="WeatherAutoImportScheduler",
    settings_section="weather_near",
    config_path_getter=lambda: _auto_state_path(),
    legacy_state_path_getter=lambda: _auto_config_path(),
    import_executor=_execute_near_weather_import,
    audit_resource_prefix="weather",
    initial_idle_message="尚未执行过近端实况气温自动或手动导入",
)

ensemble_weather_auto_import_service = WeatherAutoImportService(
    service_name="ensemble_weather",
    thread_name="EnsembleWeatherAutoImportScheduler",
    settings_section="weather_ensemble",
    config_path_getter=lambda: _ensemble_state_path(),
    legacy_state_path_getter=lambda: _ensemble_auto_config_path(),
    import_executor=_execute_ensemble_weather_import,
    audit_resource_prefix="weather_ensemble",
    initial_idle_message="尚未执行过 35 天集合气温预报自动或手动导入",
)

__all__ = [
    "WeatherAutoImportService",
    "ensemble_weather_auto_import_service",
    "normalize_schedule_times",
    "weather_auto_import_service",
]
