# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 后台定时采集调度引擎。

策略：
1. 每 15 分钟（或配置为 30/60 分钟）在刻度时刻触发批量快照采集（整点 `:00` 附带 `/jumin/`）；
2. 每隔 `table_bottom_sync_hours` 小时错峰（整点后第 18 分钟）触发 `/hrz_ls_zb/` 表底校准；
3. 每日 08:30 采集前一日 464 户商业用户日耗量。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from backend.projects.smart_heating_platform.services.cleaning_engine import EAST_8, floor_to_15min
from backend.projects.smart_heating_platform.services.collector_config_service import _read_raw_config
from backend.projects.smart_heating_platform.services.collector_engine import (
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

    def start_scheduler(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
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

    def _tick(self) -> None:
        cfg = _read_raw_config()
        if not cfg.get("scheduler_enabled", False):
            return

        now_e8 = datetime.now(EAST_8)
        snap_interval = int(cfg.get("snapshot_interval_minutes", 15))
        offset_min = int(cfg.get("hourly_offset_minutes", 0))
        calib_hours = max(1, int(cfg.get("table_bottom_sync_hours", 6)))

        # 1. 15/30/60 分钟批量断面采集
        if snap_interval == 60:
            due_min = offset_min % 60
            if now_e8.minute == due_min:
                slot = now_e8.strftime("%Y-%m-%d %H")
                if slot != self._last_snapshot_slot:
                    self._last_snapshot_slot = slot
                    run_snapshot_cycle(include_jumin=True, trigger="AUTO")
        else:
            bucket = floor_to_15min(now_e8)
            if snap_interval == 30 and bucket.minute not in (0, 30):
                pass
            else:
                target_trigger = bucket + timedelta(minutes=offset_min if bucket.minute == 0 else 0)
                if now_e8 >= target_trigger:
                    slot = bucket.strftime("%Y-%m-%d %H:%M")
                    if slot != self._last_snapshot_slot:
                        self._last_snapshot_slot = slot
                        run_snapshot_cycle(include_jumin=(bucket.minute == 0), trigger="AUTO")

        # 2. 错峰表底校准 (整点后 18 分触发，避免与整点采样冲突)
        if now_e8.hour % calib_hours == 0 and now_e8.minute == 18:
            calib_slot = now_e8.strftime("%Y-%m-%d %H")
            if calib_slot != self._last_calib_slot:
                self._last_calib_slot = calib_slot
                target_day = (now_e8.date() - timedelta(days=1)).isoformat() if now_e8.hour == 0 else now_e8.date().isoformat()
                run_table_bottom_calibration(target_date_str=target_day, trigger="AUTO")

        # 3. 每日 08:30 采集前一日商业用户耗量
        if now_e8.hour == 8 and now_e8.minute == 30:
            day_str = (now_e8.date() - timedelta(days=1)).isoformat()
            if day_str != self._last_merchant_date:
                self._last_merchant_date = day_str
                run_merchant_daily_cycle(target_date_str=day_str, trigger="AUTO")


smart_heating_scheduler = SmartHeatingSchedulerService()
