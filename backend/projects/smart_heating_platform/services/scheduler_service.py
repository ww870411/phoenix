# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 后台定时采集调度引擎（并发解耦版）。

策略：
1. 每 5 分钟（或配置为 15/30/60 分钟）触发上游点位与商业用户高频并行采样，整点 `:00` 附带 `/jumin/`；
2. 每小时整点后第 5 分钟（或配置间隔 `table_bottom_sync_hours`）并行执行 `/hrz_ls_zb/` 表底校准产出换热站上一小时精算；
3. 每日 08:30 采集前一日 464 户商业用户日耗量；
4. 各调度任务在独立守护线程中运行，互不阻塞。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.projects.smart_heating_platform.services.cleaning_engine import EAST_8, floor_to_bucket
from backend.projects.smart_heating_platform.services.collector_config_service import _read_raw_config
from backend.projects.smart_heating_platform.services.collector_engine import (
    detect_data_gaps,
    run_daily_heat_audit_and_fix,
    run_gap_recovery,
    run_merchant_daily_cycle,
    run_snapshot_cycle,
    run_table_bottom_calibration,
)

logger = logging.getLogger(__name__)


class SmartHeatingSchedulerService:
    """单例后台定时调度服务。"""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._last_snapshot_slot: Optional[str] = None
        self._last_calib_slot: Optional[str] = None
        self._last_merchant_date: Optional[str] = None
        self._last_gap_watch_slot: Optional[str] = None
        self._last_heat_audit_date: Optional[str] = None
        self._startup_gap_checked: bool = False
        self._started_at_monotonic: float = 0.0
        self._last_tick_e8: Optional[datetime] = None

    def start_scheduler(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._startup_gap_checked = False
            self._started_at_monotonic = time.monotonic()
            self._last_tick_e8 = None
            self._thread = threading.Thread(
                target=self._run_loop,
                name="SmartHeatingCollectorScheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info("SmartHeatingSchedulerService 后台调度线程已启动。")

    def stop_scheduler(self) -> None:
        self._stop_event.set()
        with self._lock:
            t = self._thread
        if t and t.is_alive():
            t.join(timeout=3.0)
        logger.info("SmartHeatingSchedulerService 后台调度线程已停止。")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.exception("SmartHeatingSchedulerService 巡检异常: %s", exc)
            self._stop_event.wait(20.0)

    def _spawn_job(self, name: str, fn: Callable[[], None]) -> None:
        """在独立守护线程中异步触发定时作业，防止耗时校准延迟调度心跳。"""
        def _runner() -> None:
            try:
                fn()
            except Exception as exc:
                logger.exception("SmartHeatingSchedulerService 异步作业 %s 失败: %s", name, exc)

        threading.Thread(target=_runner, name=f"SmartHeatingJob-{name}", daemon=True).start()

    def _tick(self) -> None:
        cfg = _read_raw_config()
        if not cfg.get("scheduler_enabled", False):
            return

        now_e8 = datetime.now(EAST_8)
        snap_interval = int(cfg.get("snapshot_interval_minutes", 5))
        offset_min = int(cfg.get("hourly_offset_minutes", 0))
        calib_hours = max(1, int(cfg.get("table_bottom_sync_hours", 1)))

        # 1. 5/15/30/60 分钟上游与商户并行断面采集（整点 :00 附带 /jumin/）
        if snap_interval == 60:
            due_min = offset_min % 60
            if now_e8.minute == due_min:
                slot = now_e8.strftime("%Y-%m-%d %H")
                if slot != self._last_snapshot_slot:
                    self._last_snapshot_slot = slot
                    self._spawn_job("snapshot", lambda: run_snapshot_cycle(include_jumin=True, trigger="AUTO"))
        else:
            bucket = floor_to_bucket(now_e8, snap_interval)
            target_trigger = bucket + timedelta(minutes=offset_min if bucket.minute == 0 else 0)
            if now_e8 >= target_trigger:
                slot = bucket.strftime("%Y-%m-%d %H:%M")
                if slot != self._last_snapshot_slot:
                    self._last_snapshot_slot = slot
                    inc_jm = bucket.minute == 0
                    self._spawn_job("snapshot", lambda: run_snapshot_cycle(include_jumin=inc_jm, trigger="AUTO"))

        # 2. 每小时整点后第 5 分钟触发换热站表底并行校准（路线 B：计算上一已完成小时）
        if now_e8.hour % calib_hours == 0 and now_e8.minute >= 5 and now_e8.minute < 15:
            calib_slot = now_e8.strftime("%Y-%m-%d %H")
            if calib_slot != self._last_calib_slot:
                self._last_calib_slot = calib_slot
                target_day = (now_e8.date() - timedelta(days=1)).isoformat() if now_e8.hour == 0 else now_e8.date().isoformat()
                self._spawn_job("calib", lambda: run_table_bottom_calibration(target_date_str=target_day, trigger="AUTO"))

        # 3. 每日 08:30 采集前一日商业用户耗量
        if now_e8.hour == 8 and now_e8.minute == 30:
            day_str = (now_e8.date() - timedelta(days=1)).isoformat()
            if day_str != self._last_merchant_date:
                self._last_merchant_date = day_str
                self._spawn_job("merchant_daily", lambda: run_merchant_daily_cycle(target_date_str=day_str, trigger="AUTO"))

        # 4. 停机真空期自动巡检与补足（启动 10 秒宽限期后执行 + 每小时 :15 或休眠恢复跳变后巡检）
        if cfg.get("auto_gap_recovery", True):
            elapsed = time.monotonic() - self._started_at_monotonic
            tick_jump = (
                self._last_tick_e8 is not None
                and (now_e8 - self._last_tick_e8).total_seconds() > 20 * 60
            )
            if not self._startup_gap_checked and elapsed >= 10.0:
                self._startup_gap_checked = True
                self._spawn_job("gap_recovery_startup", lambda: run_gap_recovery(trigger="AUTO_STARTUP"))
            elif tick_jump:
                logger.warning("检测到系统时间跃变超过 20 分钟（疑似休眠/挂起恢复），触发真空期补采巡检。")
                self._spawn_job("gap_recovery_wake", lambda: run_gap_recovery(trigger="AUTO_WAKE"))
            elif now_e8.minute == 15:
                watch_slot = now_e8.strftime("%Y-%m-%d %H")
                if watch_slot != self._last_gap_watch_slot:
                    self._last_gap_watch_slot = watch_slot
                    self._spawn_job("gap_recovery_watchdog", self._run_watchdog_gap_check)

        # 5. 每日定时数据异常回看检测与自动修正（默认 00:00，可在设置页自定义）
        if cfg.get("auto_heat_audit_fix", True):
            raw_time = str(cfg.get("heat_audit_time") or "00:00").strip()
            try:
                hh_str, mm_str = raw_time.split(":", 1)
                audit_hh, audit_mm = int(hh_str), int(mm_str)
            except Exception:
                audit_hh, audit_mm = 0, 0
            cur_min_of_day = now_e8.hour * 60 + now_e8.minute
            target_min_of_day = audit_hh * 60 + audit_mm
            if target_min_of_day <= cur_min_of_day < target_min_of_day + 15:
                audit_day_str = now_e8.date().isoformat()
                if audit_day_str != self._last_heat_audit_date:
                    self._last_heat_audit_date = audit_day_str
                    lb_days = int(cfg.get("heat_audit_lookback_days", 3))
                    self._spawn_job(
                        "daily_heat_audit_fix",
                        lambda: run_daily_heat_audit_and_fix(lookback_days=lb_days, trigger="AUTO_DAILY_AUDIT"),
                    )

        self._last_tick_e8 = now_e8

    def _run_watchdog_gap_check(self) -> None:
        """每小时整点 15 分快速只读巡检一次缺失整点，仅存在非冷却缺口时才执行自动补采。"""
        gap_info = detect_data_gaps(respect_cooldown=True)
        if gap_info.get("has_gaps"):
            run_gap_recovery(trigger="AUTO_WATCHDOG")


smart_heating_scheduler = SmartHeatingSchedulerService()
