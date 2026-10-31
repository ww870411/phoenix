# -*- coding: utf-8 -*-
"""
辽宁电力现货数据每日定时自动化获取与入库服务。

核心功能：
1. 配置管理：支持设置自动拉取开关、每日初次尝试时间点（默认 07:40）、未更新重试间隔（默认 20 分钟）；
2. 自动化调度引擎：后台守护线程实时检测时间，到达设定时间自动发起探测，若发改委数据尚未发布则自动按设定间隔持续重试直至入库成功；
3. 数据拉取与清洗：直接对接发改委底层 JSON 接口 (getLine)，校验 96 点位完整性与非空状态；
4. 原子幂等入库：基于 (trade_date, point_index) 唯一键进行 UPSERT，保护既有机组售电量业务数据；
5. 手动实时拉取：支持 Global_admin 手动拉取最新或指定某日历史数据补录。
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine

# 北京时区定义（固定 UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def get_beijing_now() -> datetime:
    """获取当前北京时间（无时区 naive datetime，已校准至 UTC+8）。"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


logger = logging.getLogger("spot_electricity_sync")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [spot_sync] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

# 发改委现货电价底层 API
GET_LINE_API_URL = "https://fgw.ln.gov.cn/indexview/api/getLine"
DEFAULT_TIMEOUT = 20.0

from backend.config import DATA_DIRECTORY

# 配置文件存储路径（统一挂载持久化）
_CONFIG_DIR = (
    DATA_DIRECTORY
    / "projects"
    / "daily_report_25_26"
    / "config"
)
CONFIG_FILE_PATH = _CONFIG_DIR / "spot_electricity_sync_config.json"

# 默认配置
DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,  # 自动拉取开关
    "cron_time": "07:40",  # 初次尝试时间点 (HH:MM)
    "retry_interval_minutes": 20,  # 未更新时的重试间隔 (分钟)
    "max_retries_per_day": 30,  # 单日最大重试次数 (覆盖整个工作时段)
    "target_date_rule": "yesterday",  # 默认抓取昨日（发改委发布前一日真实电价）
    "last_sync_date": None,  # 最近成功入库的交易日期 (YYYY-MM-DD)
    "last_run_time": None,  # 最近一次尝试/执行的时间戳
    "last_run_status": "IDLE",  # IDLE | WAITING | RETRYING | SUCCESS | FAILED
    "last_run_message": "系统初次就绪，等待执行",
    "next_run_time": None,  # 下一次计划探测的时间戳
}

UPSERT_SPOT_PRICE_SQL = text("""
INSERT INTO public.spot_electricity_15min_data (
    trade_date,
    point_index,
    time_label,
    period_start_time,
    period_end_time,
    day_ahead_price,
    real_time_price,
    status,
    updated_at
) VALUES (
    :trade_date,
    :point_index,
    :time_label,
    :period_start_time,
    :period_end_time,
    :day_ahead_price,
    :real_time_price,
    'published',
    CURRENT_TIMESTAMP
)
ON CONFLICT (trade_date, point_index)
DO UPDATE SET
    time_label = EXCLUDED.time_label,
    period_start_time = EXCLUDED.period_start_time,
    period_end_time = EXCLUDED.period_end_time,
    day_ahead_price = EXCLUDED.day_ahead_price,
    real_time_price = EXCLUDED.real_time_price,
    status = 'published',
    updated_at = CURRENT_TIMESTAMP;
""")


def _calculate_period_times(point_index: int) -> Tuple[str, str]:
    """根据时点序号 (1-96) 计算 15 分钟区间的起止时刻字符串。"""
    total_minutes_start = (point_index - 1) * 15
    start_hour = total_minutes_start // 60
    start_minute = total_minutes_start % 60
    start_str = f"{start_hour:02d}:{start_minute:02d}:00"

    total_minutes_end = point_index * 15
    if total_minutes_end >= 24 * 60:
        end_str = "24:00:00"
    else:
        end_hour = total_minutes_end // 60
        end_minute = total_minutes_end % 60
        end_str = f"{end_hour:02d}:{end_minute:02d}:00"

    return start_str, end_str


def _parse_time_str(time_str: str) -> Tuple[int, int]:
    """解析 HH:MM 格式时间字符串。"""
    parts = time_str.strip().split(":")
    hour = int(parts[0]) if len(parts) > 0 else 7
    minute = int(parts[1]) if len(parts) > 1 else 40
    return hour, minute


class SpotElectricitySyncService:
    """电力现货数据自动化同步与调度服务单例。"""

    _instance: Optional[SpotElectricitySyncService] = None
    _lock = threading.RLock()

    def __new__(cls) -> SpotElectricitySyncService:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._config_lock = threading.RLock()
        self._running_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._retry_count_today = 0
        self._current_tracking_date: Optional[str] = None
        self._last_tracking_day: Optional[str] = None
        self._config = self._load_config()
        self._bg_thread: Optional[threading.Thread] = None

    def _load_config(self) -> Dict[str, Any]:
        """从文件加载配置，若不存在则初始化默认配置。"""
        with self._config_lock:
            if not CONFIG_FILE_PATH.exists():
                _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                CONFIG_FILE_PATH.write_text(
                    json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return dict(DEFAULT_CONFIG)
            try:
                raw = CONFIG_FILE_PATH.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                merged = dict(DEFAULT_CONFIG)
                merged.update(loaded)
                return merged
            except Exception as e:
                logger.error("加载现货同步配置文件失败，使用默认配置: %s", e)
                return dict(DEFAULT_CONFIG)

    def _persist_config(self) -> None:
        """持久化当前配置到磁盘。"""
        with self._config_lock:
            try:
                _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                CONFIG_FILE_PATH.write_text(
                    json.dumps(self._config, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.error("保存现货同步配置失败: %s", e)

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置克隆。"""
        with self._config_lock:
            cfg = dict(self._config)
            cfg["retry_count_today"] = self._retry_count_today
            cfg["current_tracking_date"] = self._current_tracking_date
            return cfg

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置并即时唤醒调度器生效。"""
        with self._config_lock:
            for key in ["enabled", "cron_time", "retry_interval_minutes", "max_retries_per_day", "target_date_rule"]:
                if key in updates:
                    self._config[key] = updates[key]

            # 校验并规范时间格式
            if "cron_time" in updates:
                try:
                    h, m = _parse_time_str(str(updates["cron_time"]))
                    self._config["cron_time"] = f"{h:02d}:{m:02d}"
                except Exception:
                    self._config["cron_time"] = "07:40"

            if "retry_interval_minutes" in updates:
                try:
                    self._config["retry_interval_minutes"] = max(1, int(updates["retry_interval_minutes"]))
                except Exception:
                    self._config["retry_interval_minutes"] = 20

        self._persist_config()
        self._wake_event.set()  # 唤醒后台调度线程立即重新计算下一次执行时间
        return self.get_config()

    def fetch_from_fgw_api(self, target_date: str) -> Dict[str, Any]:
        """调用发改委底层 getLine 接口获取指定日期的现货电价数据。"""
        payload = json.dumps({"date": target_date}).encode("utf-8")
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        last_error = None
        for attempt in range(2):
            try:
                req = request.Request(GET_LINE_API_URL, data=payload, headers=headers, method="POST")
                with request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                    raw_body = resp.read().decode("utf-8")
                    data = json.loads(raw_body)
                    return data
            except Exception as e:
                last_error = e
                time.sleep(1.5)
        raise RuntimeError(f"发改委接口请求失败: {last_error}")

    def check_date_exists(self, target_date: str) -> Dict[str, Any]:
        """检查数据库中指定交易日期是否已存在电力现货电价数据。"""
        check_sql = text("""
            SELECT 
                COUNT(*) as total_points,
                COUNT(*) FILTER (WHERE day_ahead_price IS NOT NULL OR real_time_price IS NOT NULL) as price_points,
                COUNT(*) FILTER (WHERE beihai_unit1_sales IS NOT NULL OR beihai_unit2_sales IS NOT NULL OR beihai_unit3_sales IS NOT NULL OR xianghai_unit1_sales IS NOT NULL OR xianghai_unit2_sales IS NOT NULL OR xianghai_unit3_sales IS NOT NULL OR xianghai_unit4_sales IS NOT NULL) as sales_points
            FROM public.spot_electricity_15min_data
            WHERE trade_date = :trade_date;
        """)
        try:
            with engine.connect() as conn:
                row = conn.execute(check_sql, {"trade_date": target_date}).fetchone()
                if row and row.total_points > 0:
                    price_pts = int(row.price_points or 0)
                    return {
                        "exists": price_pts > 0,  # 仅当已存在非空电价数据时才触发覆盖警告
                        "has_records": True,
                        "total_points": int(row.total_points),
                        "price_points": price_pts,
                        "sales_points": int(row.sales_points or 0),
                    }
        except Exception as e:
            logger.warning("[现货同步] 检查数据库存在性失败: %s", e)
        return {
            "exists": False,
            "has_records": False,
            "total_points": 0,
            "price_points": 0,
            "sales_points": 0,
        }

    def sync_data(
        self,
        target_date: Optional[str] = None,
        is_manual: bool = False,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        核心执行逻辑：抓取指定日期或默认昨日的数据并幂等入库。

        返回格式：
        {
            "ok": bool,
            "status": "SUCCESS" | "ALREADY_EXISTS" | "NOT_PUBLISHED" | "FAILED",
            "target_date": "YYYY-MM-DD",
            "points_count": int,
            "message": str
        }
        """
        now = get_beijing_now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 确定目标日期：若未指定，默认为北京时间的昨日（发改委发布前一日真实电价）
        if not target_date:
            target_date = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 若是手动拉取且未显式指定覆盖，检查数据库中是否已存在该日期数据
        if is_manual and not overwrite:
            exists_info = self.check_date_exists(target_date)
            if exists_info.get("exists"):
                pts = exists_info.get("total_points", 0)
                price_pts = exists_info.get("price_points", 0)
                msg = f"数据库中已存在【{target_date}】的现货数据（已有 {pts} 个点位，其中 {price_pts} 个点位已含电价）。是否确认覆盖现有数据？"
                logger.info("[现货同步] %s", msg)
                return {
                    "ok": False,
                    "status": "ALREADY_EXISTS",
                    "target_date": target_date,
                    "points_count": pts,
                    "price_points": price_pts,
                    "sales_points": exists_info.get("sales_points", 0),
                    "message": msg,
                }

        logger.info("[现货同步] 开始获取 %s 数据 (手动触发: %s, 覆盖模式: %s)...", target_date, is_manual, overwrite)

        try:
            raw_res = self.fetch_from_fgw_api(target_date)
        except Exception as e:
            err_msg = f"连接发改委接口异常: {e}"
            logger.error("[现货同步] %s", err_msg)
            if not is_manual:
                with self._config_lock:
                    self._config["last_run_time"] = now_str
                    self._config["last_run_status"] = "FAILED"
                    self._config["last_run_message"] = err_msg
                    self._persist_config()
            return {
                "ok": False,
                "status": "FAILED",
                "target_date": target_date,
                "points_count": 0,
                "message": err_msg,
            }

        # 检查发改委响应状态
        if str(raw_res.get("CODE")) != "200" or not isinstance(raw_res.get("data"), dict):
            msg = f"发改委接口返回异常 (CODE={raw_res.get('CODE')}, MESSAGE={raw_res.get('MESSAGE')})"
            logger.warning("[现货同步] %s", msg)
            if not is_manual:
                with self._config_lock:
                    self._config["last_run_time"] = now_str
                    self._config["last_run_status"] = "RETRYING"
                    self._config["last_run_message"] = msg
                    self._persist_config()
            return {
                "ok": False,
                "status": "NOT_PUBLISHED",
                "target_date": target_date,
                "points_count": 0,
                "message": msg,
            }

        data_obj = raw_res.get("data") or {}
        real_time_list = data_obj.get("realTime") or []
        before_list = data_obj.get("before") or []
        x_data_list = data_obj.get("xData") or []

        # 校验 96 点有效性：如果数组长度不足或数据全为空，判定为“尚未发布”
        valid_rt = [x for x in real_time_list if x is not None and str(x).strip() != ""]
        valid_bf = [x for x in before_list if x is not None and str(x).strip() != ""]

        if len(valid_rt) == 0 and len(valid_bf) == 0:
            msg = f"{target_date} 发改委电价数据尚未发布 (数据点全空)"
            logger.info("[现货同步] %s", msg)
            if not is_manual:
                with self._config_lock:
                    self._config["last_run_time"] = now_str
                    self._config["last_run_status"] = "RETRYING"
                    self._config["last_run_message"] = msg
                    self._persist_config()
            return {
                "ok": False,
                "status": "NOT_PUBLISHED",
                "target_date": target_date,
                "points_count": 0,
                "message": msg,
            }

        # 解析并构建 96 个时序点位数据
        parsed_records: List[Dict[str, Any]] = []
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        for idx in range(1, 97):
            array_idx = idx - 1
            time_label = x_data_list[array_idx] if array_idx < len(x_data_list) else ""
            if not time_label:
                # 兼容兜底格式化
                h = (idx * 15) // 60
                m = (idx * 15) % 60
                time_label = f"{h:02d}:{m:02d}"

            p_start, p_end = _calculate_period_times(idx)

            raw_da = before_list[array_idx] if array_idx < len(before_list) else None
            raw_rt = real_time_list[array_idx] if array_idx < len(real_time_list) else None

            da_price: Optional[Decimal] = None
            rt_price: Optional[Decimal] = None

            if raw_da is not None and str(raw_da).strip() != "":
                try:
                    da_price = Decimal(str(raw_da).strip())
                except Exception:
                    da_price = None

            if raw_rt is not None and str(raw_rt).strip() != "":
                try:
                    rt_price = Decimal(str(raw_rt).strip())
                except Exception:
                    rt_price = None


            parsed_records.append({
                "trade_date": parsed_date,
                "point_index": idx,
                "time_label": time_label,
                "period_start_time": p_start,
                "period_end_time": p_end,
                "day_ahead_price": da_price,
                "real_time_price": rt_price,
            })

        # 执行数据库原子批量幂等入库
        try:
            with engine.begin() as conn:
                conn.execute(UPSERT_SPOT_PRICE_SQL, parsed_records)
        except Exception as e:
            err_msg = f"数据库入库失败: {e}"
            logger.error("[现货同步] %s", err_msg)
            if not is_manual:
                with self._config_lock:
                    self._config["last_run_time"] = now_str
                    self._config["last_run_status"] = "FAILED"
                    self._config["last_run_message"] = err_msg
                    self._persist_config()
            return {
                "ok": False,
                "status": "FAILED",
                "target_date": target_date,
                "points_count": 0,
                "message": err_msg,
            }

        if overwrite:
            success_msg = f"已成功覆盖更新【{target_date}】电力现货数据，共刷新 {len(parsed_records)} 个 15 分钟时点！"
        else:
            success_msg = f"成功入库【{target_date}】电力现货数据，共写入 {len(parsed_records)} 个 15 分钟时点！"
        logger.info("[现货同步] %s", success_msg)

        # 更新配置记录
        with self._config_lock:
            self._config["last_sync_date"] = target_date
            self._config["last_run_time"] = now_str
            self._config["last_run_status"] = "SUCCESS"
            self._config["last_run_message"] = success_msg
            self._persist_config()
        self._wake_event.set()

        return {
            "ok": True,
            "status": "SUCCESS",
            "target_date": target_date,
            "points_count": len(parsed_records),
            "message": success_msg,
        }

    def start_scheduler(self) -> None:
        """启动后台自动调度守护线程。"""
        with self._running_lock:
            if self._bg_thread and self._bg_thread.is_alive():
                return
            self._stop_event.clear()
            self._wake_event.clear()
            self._bg_thread = threading.Thread(
                target=self._scheduler_loop,
                name="SpotElectricitySyncScheduler",
                daemon=True,
            )
            self._bg_thread.start()
            logger.info("现货电价自动化同步后台守护线程已启动。")

    def stop_scheduler(self) -> None:
        """优雅停止后台调度线程。"""
        with self._running_lock:
            self._stop_event.set()
            self._wake_event.set()
            if self._bg_thread and self._bg_thread.is_alive():
                self._bg_thread.join(timeout=2.0)
            self._bg_thread = None

    def _scheduler_loop(self) -> None:
        """后台调度引擎主循环。"""
        logger.info("现货电价调度引擎循环已就绪。")
        while not self._stop_event.is_set():
            try:
                self._run_scheduler_step()
            except Exception as e:
                logger.error("调度引擎运行单步发生异常: %s", e)

            # 休眠 30 秒或被 wake_event 提前唤醒
            self._wake_event.wait(timeout=30.0)
            self._wake_event.clear()

    def _run_scheduler_step(self) -> None:
        """执行单次调度状态评估与触发检测（基于北京时间）。"""
        cfg = self.get_config()
        if not cfg.get("enabled", True):
            # 若自动拉取开关被关闭
            with self._config_lock:
                if self._config.get("next_run_time") != "已暂停自动拉取":
                    self._config["next_run_time"] = "已暂停自动拉取"
                    self._persist_config()
            return

        now = get_beijing_now()
        today_str = now.strftime("%Y-%m-%d")

        # 跨自然日重置当日重试计数器
        if self._last_tracking_day != today_str:
            self._retry_count_today = 0
            self._last_tracking_day = today_str

        cron_time_str = str(cfg.get("cron_time") or "07:40")
        target_h, target_m = _parse_time_str(cron_time_str)
        interval_mins = max(1, int(cfg.get("retry_interval_minutes") or 20))
        max_retries = int(cfg.get("max_retries_per_day") or 30)

        # 每日目标数据对应北京时间的昨日
        yesterday_date = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 检查昨日数据是否已经在数据库中完整存储
        if self._is_date_already_synced(yesterday_date):
            # 今日任务已圆满完成，计算明天的北京时间 07:40
            tomorrow = now.date() + timedelta(days=1)
            next_run_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, target_h, target_m, 0)
            next_str = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
            with self._config_lock:
                changed = False
                if self._config.get("next_run_time") != next_str:
                    self._config["next_run_time"] = next_str
                    changed = True
                if self._config.get("last_run_status") != "SUCCESS":
                    self._config["last_run_status"] = "SUCCESS"
                    self._config["last_run_message"] = f"【{yesterday_date}】现货电价数据已在库中完整存储，等待明日自动拉取"
                    changed = True
                if self._config.get("last_sync_date") != yesterday_date:
                    self._config["last_sync_date"] = yesterday_date
                    changed = True
                if changed:
                    self._persist_config()
                self._retry_count_today = 0
                self._current_tracking_date = None
            return

        # 尚未完成昨日数据入库
        # 计算今天设定的初次尝试时间（北京时间）
        today_trigger_dt = datetime(now.year, now.month, now.day, target_h, target_m, 0)

        if now < today_trigger_dt:
            # 尚未到达初次尝试时间 (如北京时间 07:40 之前)
            trigger_str = today_trigger_dt.strftime("%Y-%m-%d %H:%M:%S")
            with self._config_lock:
                changed = False
                if self._config.get("next_run_time") != trigger_str:
                    self._config["next_run_time"] = trigger_str
                    changed = True
                if self._config.get("last_run_status") not in ("SUCCESS", "RETRYING"):
                    self._config["last_run_status"] = "WAITING"
                    self._config["last_run_message"] = f"等待今日 {cron_time_str} 发起首次抓取探测"
                    changed = True
                if changed:
                    self._persist_config()
            return

        # 已到达或超过设定时间 (>= 07:40)
        # 检查是否处于重试等待冷却期
        last_run_str = cfg.get("last_run_time")
        if last_run_str:
            try:
                last_run_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
                elapsed_seconds = (now - last_run_dt).total_seconds()
                cooling_seconds = interval_mins * 60

                if elapsed_seconds < cooling_seconds:
                    # 仍在等待间隔冷却期内
                    next_attempt_dt = last_run_dt + timedelta(minutes=interval_mins)
                    next_str = next_attempt_dt.strftime("%Y-%m-%d %H:%M:%S")
                    with self._config_lock:
                        if self._config.get("next_run_time") != next_str:
                            self._config["next_run_time"] = next_str
                            self._persist_config()
                    return
            except Exception:
                pass

        # 达到重试次数上限保护
        if self._retry_count_today >= max_retries:
            logger.warning("[现货同步] 今日已达到最大重试次数 (%s次)，暂停重试。", max_retries)
            with self._config_lock:
                self._config["next_run_time"] = "已达今日最大重试次数"
                self._config["last_run_status"] = "FAILED"
                self._config["last_run_message"] = f"今日已重试 {max_retries} 次仍未检测到发改委发布最新数据，等待人工核实"
                self._persist_config()
            return

        # 触发执行抓取尝试！
        logger.info("[现货同步] 调度触发：发起对 %s 的第 %s 次抓取探测...", yesterday_date, self._retry_count_today + 1)
        res = self.sync_data(target_date=yesterday_date, is_manual=False)

        if res.get("ok"):
            self._retry_count_today = 0
            self._current_tracking_date = None
            # 计算明日执行时间（北京时间）
            tomorrow = now.date() + timedelta(days=1)
            next_run_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, target_h, target_m, 0)
            with self._config_lock:
                self._config["next_run_time"] = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
                self._persist_config()
        else:
            self._retry_count_today += 1
            self._current_tracking_date = yesterday_date
            next_attempt_dt = now + timedelta(minutes=interval_mins)
            with self._config_lock:
                self._config["next_run_time"] = next_attempt_dt.strftime("%Y-%m-%d %H:%M:%S")
                self._config["last_run_message"] = f"第 {self._retry_count_today} 次探测未就绪: {res.get('message')}，将在 {interval_mins} 分钟后重试"
                self._persist_config()

    def _is_date_already_synced(self, check_date: str) -> bool:
        """检查指定日期是否已经在数据库中拥有完整的 96 个现货电价点位。"""
        try:
            with engine.connect() as conn:
                res = conn.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM public.spot_electricity_15min_data 
                        WHERE trade_date = :d
                          AND (day_ahead_price IS NOT NULL OR real_time_price IS NOT NULL);
                    """),
                    {"d": check_date},
                ).scalar()
                return int(res or 0) >= 96
        except Exception as e:
            logger.error("检查日期数据库记录失败: %s", e)
            return False


# 全局单例服务
spot_sync_service = SpotElectricitySyncService()
