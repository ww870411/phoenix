# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 核心旁路采集引擎与入库聚合服务。

支持三类受控并发采集作业（多线程受控并发 + Connection: close + 失败退避重试）：
1. `run_snapshot_cycle()`：每 5 分钟（可配 5/15/30/60）并发拉取上游（/gk_get_data/）与商业用户
   （/get_sh_data/），整点 `:00` 附带 /jumin/；对已结束小时执行时间加权梯形积分定格，
   并对采样明细执行 2 小时滚动算完即清（仅保留当前小时 + 上一小时）；
2. `run_table_bottom_calibration()`：路线 B 专责换热站每小时整点后（默认 `:05`）受控并行拉取
   /hrz_ls_zb/（isdownload=1），整点线性插值计算表底差值（METER_DIFF）与代表断面写入
   fact_station_hourly（坏表底自动降级为历史 f222 积分）；彻底不再拉取换热站实时与二次分区；
3. `run_merchant_daily_cycle()`：每日 08:30 拉取 /getall_bb_shrb/ 写入商业用户日耗表。
"""

from __future__ import annotations

import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import (
    EAST_8,
    FAULT_METER_JUMP,
    FAULT_SENSOR_RANGE,
    FAULT_SOFTWARE_DEFECT,
    OWNER_RESEARCH,
    OWNER_SHARED,
    OWNER_UNIVERSITY,
    SRC_FALLBACK_INTEGRAL,
    SRC_INTEGRAL_15M,
    SRC_MASKED_PREV,
    SRC_METER_DIFF,
    SRC_REAL,
    SRC_SOURCE_EMPTY,
    STATION_METER_SCALE_FACTORS,
    UPSTREAM_MAX_HEAT_GJH,
    clean_merchant_point,
    clean_station_history_point,
    clean_temp_device,
    clean_upstream_point,
    floor_to_bucket,
    floor_to_hour,
    interpolate_meter_at_hour,
    is_meter_sequence_oscillating,
    parse_dt_east8,
    station_max_hourly_elec_kwh,
    station_max_hourly_heat_gj,
    station_max_hourly_water_t,
    to_float,
    trapezoidal_hour_integral,
    validate_meter_delta,
)
from backend.projects.smart_heating_platform.services.collector_config_service import (
    DEFAULT_GAP_RECOVERY_START_DATE,
    _read_raw_config,
    normalize_cookie_input,
    resolve_effective_base_url,
)
from backend.projects.smart_heating_platform.services.db_schema import ensure_smart_heating_fact_tables

logger = logging.getLogger(__name__)

# 按作业类型拆锁：表底校准与 5 分钟快照采集互不阻塞
_SNAPSHOT_LOCK = threading.RLock()
_CALIB_LOCK = threading.RLock()
_MERCHANT_DAILY_LOCK = threading.RLock()
_MERCHANT_BACKFILL_LOCK = threading.RLock()
_UPSTREAM_BACKFILL_LOCK = threading.RLock()
_GAP_RECOVERY_LOCK = threading.RLock()
_GAP_STATE_LOCK = threading.Lock()
_GAP_RUNTIME_STATE: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "last_heartbeat_at": None,
    "trigger": None,
    "current_step_index": 0,
    "total_steps": 0,
    "current_date": None,
    "current_track": None,
    "current_step_label": "",
    "sub_done": 0,
    "sub_total": 0,
    "sub_item": "",
    "recovered_counts": {
        "station_hours": 0,
        "upstream_hours": 0,
        "merchant_hours": 0,
        "merchant_daily_days": 0,
    },
    "recent_logs": [],
    "errors": [],
}
_GAP_COOLDOWN_UNTIL: Dict[Tuple[str, str], datetime] = {}


def _append_gap_log(level: str, message: str) -> None:
    """线程安全地追加真空期补采实时进度日志并刷新最近心跳时间（最多保留 50 条）。"""
    ts = datetime.now(EAST_8).strftime("%H:%M:%S")
    with _GAP_STATE_LOCK:
        _GAP_RUNTIME_STATE["last_heartbeat_at"] = datetime.now(EAST_8).strftime("%Y-%m-%d %H:%M:%S")
        logs = _GAP_RUNTIME_STATE.setdefault("recent_logs", [])
        logs.append({"time": ts, "level": level, "message": message})
        if len(logs) > 50:
            del logs[:-50]


def _update_gap_progress(**kwargs: Any) -> None:
    """线程安全地更新真空期补采进度字段并刷新心跳时间。"""
    with _GAP_STATE_LOCK:
        _GAP_RUNTIME_STATE["last_heartbeat_at"] = datetime.now(EAST_8).strftime("%Y-%m-%d %H:%M:%S")
        _GAP_RUNTIME_STATE.update(kwargs)

TEMP_RETENTION_HOURS = 48
SAMPLING_KEEP_HOURS = 2


def prune_old_temp_hourly(
    conn: Any,
    reference_time: Optional[datetime] = None,
    retention_hours: int = TEMP_RETENTION_HOURS,
) -> int:
    """自动清理 `fact_temp_hourly` 中早于 `reference_time - retention_hours`（默认 48 小时）的历史室温记录。"""
    ref_e8 = floor_to_hour(reference_time or datetime.now(EAST_8))
    cutoff = ref_e8 - timedelta(hours=max(1, int(retention_hours)))
    res = conn.execute(
        text("DELETE FROM smart_heating_platform.fact_temp_hourly WHERE biz_hour < :cutoff"),
        {"cutoff": cutoff},
    )
    return int(res.rowcount or 0)


def prune_old_sampling_rows(
    conn: Any,
    reference_time: Optional[datetime] = None,
    keep_hours: int = SAMPLING_KEEP_HOURS,
) -> Dict[str, int]:
    """
    算完即清：清理高频采样明细表中早于保留窗口的记录。

    默认 `keep_hours=2` 时，仅保留当前正在进行的小时与刚结束的上一小时
    （即 `cutoff = floor_to_hour(ref) - 1h`，删除 `biz_hour < cutoff` 的明细）。
    """
    ref_e8 = floor_to_hour(reference_time or datetime.now(EAST_8))
    cutoff = ref_e8 - timedelta(hours=max(1, int(keep_hours)) - 1)
    tables = (
        "fact_upstream_15min",
        "fact_merchant_15min",
        "fact_station_15min",
        "fact_zone_15min",
    )
    counts: Dict[str, int] = {}
    total = 0
    for tbl in tables:
        res = conn.execute(
            text(f"DELETE FROM smart_heating_platform.{tbl} WHERE biz_hour < :cutoff"),
            {"cutoff": cutoff},
        )
        deleted = int(res.rowcount or 0)
        counts[tbl] = deleted
        total += deleted
    counts["total"] = total
    return counts


def _post_with_retry(
    client: httpx.Client,
    url: str,
    data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    retries: int = 2,
) -> httpx.Response:
    """对源站 Werkzeug 接口发起单线程重试请求（兼容偶发 502/连接抖动）。"""
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = client.post(url, data=data, headers=headers)
            if resp.status_code in (502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return resp
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"请求失败: {url}")


def _load_dict_caches() -> Dict[str, Any]:
    """从数据库加载八大主体字典索引供高速内存关联。"""
    with engine.connect() as conn:
        stations = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT station_id, center_id, branch_network_id, name, name_raw, rd_code, covered_area, rdfz "
                    "FROM smart_heating_platform.dict_heating_station"
                )
            ).fetchall()
        ]
        zones = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT secondary_zone_id, station_id, zone_name, is_online "
                    "FROM smart_heating_platform.dict_secondary_zone"
                )
            ).fetchall()
        ]
        devices = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT temp_device_id, station_id, name, station_name, station_name_raw "
                    "FROM smart_heating_platform.dict_temp_device"
                )
            ).fetchall()
        ]
        upstream_pts = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT point_id, data_zone, source_name, name, category, sub_category "
                    "FROM smart_heating_platform.dict_upstream_point"
                )
            ).fetchall()
        ]
        merchants = [
            dict(r._mapping)
            for r in conn.execute(
                text("SELECT merchant_id, name, name_raw, rdry FROM smart_heating_platform.dict_merchant")
            ).fetchall()
        ]
        main_network_ids = [
            int(r[0])
            for r in conn.execute(
                text("SELECT main_network_id FROM smart_heating_platform.dict_main_network ORDER BY main_network_id")
            ).fetchall()
        ]

    station_by_id = {s["station_id"]: s for s in stations}
    station_by_name = {s["name"]: s for s in stations}

    zones_by_station: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for z in zones:
        zones_by_station.setdefault(z["station_id"], {})[z["zone_name"]] = z

    device_by_id = {d["temp_device_id"]: d for d in devices}
    alias_station_map: Dict[str, str] = {}
    for s in stations:
        alias_station_map[s["name"]] = s["station_id"]
        alias_station_map[s["name_raw"]] = s["station_id"]
    for d in devices:
        alias_station_map[d["station_name_raw"]] = d["station_id"]

    upstream_by_key = {(p["data_zone"], p["source_name"]): p for p in upstream_pts}
    merchant_by_id = {m["merchant_id"]: m for m in merchants}
    merchant_by_name: Dict[str, Dict[str, Any]] = {}
    for m in merchants:
        merchant_by_name[m["name"]] = m
        if m.get("name_raw"):
            merchant_by_name[m["name_raw"]] = m

    return {
        "stations": stations,
        "station_by_id": station_by_id,
        "station_by_name": station_by_name,
        "zones_by_station": zones_by_station,
        "device_by_id": device_by_id,
        "alias_station_map": alias_station_map,
        "upstream_by_key": upstream_by_key,
        "merchants": merchants,
        "merchant_by_id": merchant_by_id,
        "merchant_by_name": merchant_by_name,
        "main_network_ids": main_network_ids,
    }


def _load_prev_valid_snapshots(biz_hour: datetime) -> Dict[str, Any]:
    """读取最近前序有效断面，用于临时离线/传感器断路时平滑回退。"""
    prev_start = biz_hour - timedelta(hours=6)
    with engine.connect() as conn:
        up_rows = conn.execute(
            text(
                "SELECT DISTINCT ON (data_zone, source_name) data_zone, source_name, "
                "temp_clean, pressure_clean, flow_clean, heat_clean "
                "FROM smart_heating_platform.fact_upstream_hourly "
                "WHERE biz_hour >= :prev_start AND biz_hour < :biz_hour AND temp_clean IS NOT NULL "
                "ORDER BY data_zone, source_name, biz_hour DESC"
            ),
            {"prev_start": prev_start, "biz_hour": biz_hour},
        ).fetchall()

        st_rows = conn.execute(
            text(
                "SELECT DISTINCT ON (station_id) station_id, e1_clean, e3_clean, e4_clean, "
                "e7_clean, e8_clean, e11_clean, e14_clean "
                "FROM smart_heating_platform.fact_station_hourly "
                "WHERE biz_hour >= :prev_start AND biz_hour < :biz_hour AND online IS TRUE "
                "ORDER BY station_id, biz_hour DESC"
            ),
            {"prev_start": prev_start, "biz_hour": biz_hour},
        ).fetchall()

        mc_rows = conn.execute(
            text(
                "SELECT DISTINCT ON (source_name) source_name, flow_clean, temp_sup_clean, temp_ret_clean, "
                "pres_sup_clean, pres_ret_clean, heat_clean "
                "FROM smart_heating_platform.fact_merchant_hourly "
                "WHERE biz_hour >= :prev_start AND biz_hour < :biz_hour AND online IS TRUE "
                "ORDER BY source_name, biz_hour DESC"
            ),
            {"prev_start": prev_start, "biz_hour": biz_hour},
        ).fetchall()

    return {
        "upstream": {(r.data_zone, r.source_name): dict(r._mapping) for r in up_rows},
        "station": {r.station_id: dict(r._mapping) for r in st_rows},
        "merchant": {r.source_name: dict(r._mapping) for r in mc_rows},
    }


def _upsert_batch(
    conn: Any,
    table_name: str,
    columns: Sequence[str],
    conflict_cols: Sequence[str],
    update_cols: Sequence[str],
    rows: List[Dict[str, Any]],
    extra_set_clauses: Optional[List[str]] = None,
    do_nothing_on_conflict: bool = False,
) -> None:
    """在当前数据库事务内执行批量幂等 UPSERT（支持空值占位行仅在缺行时插入而不覆盖已有实测记录）。"""
    if not rows:
        return
    col_str = ", ".join(columns)
    val_str = ", ".join(f":{c}" for c in columns)
    conf_str = ", ".join(conflict_cols)
    if do_nothing_on_conflict:
        conflict_clause = f"ON CONFLICT ({conf_str}) DO NOTHING"
    else:
        sets = [f"{c} = EXCLUDED.{c}" for c in update_cols]
        if extra_set_clauses:
            sets.extend(extra_set_clauses)
        conflict_clause = f"ON CONFLICT ({conf_str}) DO UPDATE SET {', '.join(sets)}"
    sql = (
        f"INSERT INTO smart_heating_platform.{table_name} ({col_str}) "
        f"VALUES ({val_str}) "
        f"{conflict_clause}"
    )
    conn.execute(text(sql), rows)


def _insert_run_log(biz_hour: datetime, run_type: str, source_mode: str) -> int:
    """创建采集运行批次记录并返回 run_id。"""
    with engine.begin() as conn:
        run_id = conn.execute(
            text(
                "INSERT INTO smart_heating_platform.fact_collector_run "
                "(biz_hour, run_type, source_mode, status) "
                "VALUES (:biz_hour, :run_type, :source_mode, 'RUNNING') "
                "RETURNING run_id"
            ),
            {"biz_hour": biz_hour, "run_type": run_type, "source_mode": source_mode},
        ).scalar_one()
    return int(run_id)


def _finish_run_log(
    run_id: int,
    started_perf: float,
    status: str,
    cookie_valid: Optional[bool],
    summary: Dict[str, Any],
    error_message: Optional[str] = None,
) -> None:
    """回写采集批次完成状态与摘要。"""
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE smart_heating_platform.fact_collector_run "
                "SET finished_at = NOW(), duration_ms = :dur, status = :st, "
                "cookie_valid = :cv, summary_json = CAST(:sj AS JSONB), error_message = :err "
                "WHERE run_id = :rid"
            ),
            {
                "dur": duration_ms,
                "st": status,
                "cv": cookie_valid,
                "sj": json.dumps(summary, ensure_ascii=False),
                "err": error_message,
                "rid": run_id,
            },
        )


def _aggregate_upstream_hourly(conn: Any, biz_hour: datetime, finalize: bool = True) -> int:
    """
    从 fact_upstream_15min 对指定小时汇总代表断面与梯形积分。

    - `finalize=False`（当前尚未结束的小时）：仅更新瞬时代表断面，`hour_heat_gj`/`hour_flow_t` 保持为空；
    - `finalize=True`（已结束整点小时）：计算 5/15 分钟时间加权梯形积分并定格。
    """
    rows = conn.execute(
        text(
            "SELECT sample_bucket, point_id, data_zone, source_name, display_name, category, sub_category, "
            "source_time, temp_raw, temp_clean, pressure_raw, pressure_clean, flow_raw, flow_clean, "
            "heat_raw, heat_clean, value_source, fault_tag "
            "FROM smart_heating_platform.fact_upstream_15min "
            "WHERE biz_hour = :biz_hour "
            "ORDER BY data_zone, source_name, sample_bucket ASC"
        ),
        {"biz_hour": biz_hour},
    ).fetchall()

    grouped: Dict[Tuple[str, str], List[Any]] = {}
    for r in rows:
        grouped.setdefault((r.data_zone, r.source_name), []).append(r)

    hourly_rows: List[Dict[str, Any]] = []
    for (dz, sname), items in grouped.items():
        latest = items[-1]
        heat_raw_samples = [(it.sample_bucket, float(it.heat_raw) if it.heat_raw is not None else None) for it in items]
        heat_samples = [(it.sample_bucket, float(it.heat_clean) if it.heat_clean is not None else None) for it in items]
        flow_samples = [(it.sample_bucket, float(it.flow_clean) if it.flow_clean is not None else None) for it in items]
        hourly_rows.append({
            "biz_hour": biz_hour,
            "point_id": latest.point_id,
            "data_zone": dz,
            "source_name": sname,
            "display_name": latest.display_name,
            "category": latest.category,
            "sub_category": latest.sub_category,
            "is_core_gk": latest.point_id is not None,
            "sample_count": len(items),
            "source_time": latest.source_time,
            "temp_raw": latest.temp_raw,
            "temp_clean": latest.temp_clean,
            "pressure_raw": latest.pressure_raw,
            "pressure_clean": latest.pressure_clean,
            "flow_raw": latest.flow_raw,
            "flow_clean": latest.flow_clean,
            "heat_raw": latest.heat_raw,
            "heat_clean": latest.heat_clean,
            "hour_heat_raw_gj": trapezoidal_hour_integral(heat_raw_samples) if finalize else None,
            "hour_heat_gj": trapezoidal_hour_integral(heat_samples) if finalize else None,
            "hour_flow_t": trapezoidal_hour_integral(flow_samples) if finalize else None,
            "value_source": latest.value_source,
            "fault_tag": latest.fault_tag,
        })

    _upsert_batch(
        conn,
        "fact_upstream_hourly",
        [
            "biz_hour", "point_id", "data_zone", "source_name", "display_name", "category", "sub_category",
            "is_core_gk", "sample_count", "source_time", "temp_raw", "temp_clean", "pressure_raw",
            "pressure_clean", "flow_raw", "flow_clean", "heat_raw", "heat_clean", "hour_heat_raw_gj", "hour_heat_gj",
            "hour_flow_t", "value_source", "fault_tag",
        ],
        ["biz_hour", "data_zone", "source_name"],
        [
            "point_id", "display_name", "category", "sub_category", "is_core_gk", "sample_count",
            "source_time", "temp_raw", "temp_clean", "pressure_raw", "pressure_clean", "flow_raw",
            "flow_clean", "heat_raw", "heat_clean", "hour_heat_raw_gj", "hour_heat_gj", "hour_flow_t", "value_source", "fault_tag",
        ],
        hourly_rows,
        extra_set_clauses=["updated_at = NOW()"],
    )
    return len(hourly_rows)


def _aggregate_merchant_hourly(conn: Any, biz_hour: datetime, finalize: bool = True) -> int:
    """
    从 fact_merchant_15min 汇总商业用户小时代表断面与梯形积分（热量 GJ 与流量 t）。

    - `finalize=False`（当前尚未结束的小时）：仅更新瞬时代表断面，`hour_heat_gj`/`hour_flow_t` 保持为空；
    - `finalize=True`（已结束整点小时）：计算 5/15 分钟时间加权梯形积分并定格。
    """
    rows = conn.execute(
        text(
            "SELECT sample_bucket, merchant_id, source_name, is_registered, online, "
            "flow_raw, flow_clean, return_flow_raw, temp_sup_raw, temp_sup_clean, "
            "temp_ret_raw, temp_ret_clean, pres_sup_raw, pres_sup_clean, "
            "pres_ret_raw, pres_ret_clean, heat_raw, heat_clean, valve_open, valve_set, "
            "value_source, fault_tag "
            "FROM smart_heating_platform.fact_merchant_15min "
            "WHERE biz_hour = :biz_hour "
            "ORDER BY source_name, sample_bucket ASC"
        ),
        {"biz_hour": biz_hour},
    ).fetchall()

    grouped: Dict[str, List[Any]] = {}
    for r in rows:
        grouped.setdefault(r.source_name, []).append(r)

    hourly_rows: List[Dict[str, Any]] = []
    for sname, items in grouped.items():
        latest = items[-1]
        heat_samples = [(it.sample_bucket, float(it.heat_clean) if it.heat_clean is not None else None) for it in items]
        flow_samples = [(it.sample_bucket, float(it.flow_clean) if it.flow_clean is not None else None) for it in items]
        hour_heat = trapezoidal_hour_integral(heat_samples) if (finalize and latest.is_registered) else None
        hour_flow = trapezoidal_hour_integral(flow_samples) if (finalize and latest.is_registered) else None

        hourly_rows.append({
            "biz_hour": biz_hour,
            "merchant_id": latest.merchant_id,
            "source_name": sname,
            "is_registered": latest.is_registered,
            "sample_count": len(items),
            "online": latest.online,
            "flow_raw": latest.flow_raw,
            "flow_clean": latest.flow_clean,
            "return_flow_raw": latest.return_flow_raw,
            "temp_sup_raw": latest.temp_sup_raw,
            "temp_sup_clean": latest.temp_sup_clean,
            "temp_ret_raw": latest.temp_ret_raw,
            "temp_ret_clean": latest.temp_ret_clean,
            "pres_sup_raw": latest.pres_sup_raw,
            "pres_sup_clean": latest.pres_sup_clean,
            "pres_ret_raw": latest.pres_ret_raw,
            "pres_ret_clean": latest.pres_ret_clean,
            "heat_raw": latest.heat_raw,
            "heat_clean": latest.heat_clean,
            "valve_open": latest.valve_open,
            "valve_set": latest.valve_set,
            "hour_heat_gj": hour_heat,
            "hour_heat_source": SRC_INTEGRAL_15M if finalize else "PENDING",
            "hour_flow_t": hour_flow,
            "hour_flow_source": SRC_INTEGRAL_15M if finalize else "PENDING",
            "value_source": latest.value_source,
            "fault_tag": latest.fault_tag,
        })

    _upsert_batch(
        conn,
        "fact_merchant_hourly",
        [
            "biz_hour", "merchant_id", "source_name", "is_registered", "sample_count", "online",
            "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
            "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
            "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
            "hour_heat_gj", "hour_heat_source", "hour_flow_t", "hour_flow_source",
            "value_source", "fault_tag",
        ],
        ["biz_hour", "source_name"],
        [
            "merchant_id", "is_registered", "sample_count", "online",
            "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
            "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
            "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
            "hour_heat_gj", "hour_heat_source", "hour_flow_t", "hour_flow_source",
            "value_source", "fault_tag",
        ],
        hourly_rows,
        extra_set_clauses=["updated_at = NOW()"],
    )
    return len(hourly_rows)


def _fetch_merchant_realtime_items(
    base_url: str,
    headers: Dict[str, str],
    main_network_ids: Sequence[int],
    timeout: float,
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """
    免 Cookie 并行获取商业用户全网实时运行参数（含瞬时热量与流量）。

    优先尝试单次调用 `/get_sh_data/0`（sh_selected=0）；若大包被源站 NAT 中断，
    则自动降级使用受控线程池按主干网 ID（2..16）并发拉取 `/get_sh_data/{mn_id}` 合并去重。
    """
    req_headers = {**headers, "Connection": "close"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            r0 = _post_with_retry(
                client,
                f"{base_url}/get_sh_data/0",
                data={"sh_selected": "0"},
                headers=req_headers,
                retries=1,
            )
            if r0.status_code == 200:
                arr = r0.json()
                if isinstance(arr, list) and arr:
                    return [x for x in arr if isinstance(x, dict) and x.get("name")]
    except Exception as exc:
        logger.info("全量 /get_sh_data/0 遇到截断抖动，切换主干网并发分片采集: %s", exc)

    def _fetch_shard(mid: int) -> List[Dict[str, Any]]:
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            rm = _post_with_retry(
                client,
                f"{base_url}/get_sh_data/{mid}",
                data={"sh_selected": str(mid)},
                headers=req_headers,
                retries=2,
            )
            if rm.status_code != 200:
                return []
            arr = rm.json() or []
            return [x for x in arr if isinstance(x, dict) and x.get("name")] if isinstance(arr, list) else []

    seen: Dict[str, Dict[str, Any]] = {}
    workers = max(1, min(int(max_workers), len(main_network_ids) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_shard, mid) for mid in main_network_ids]
        for fut in as_completed(futures):
            try:
                for x in fut.result():
                    seen[str(x["name"]).strip()] = x
            except Exception as exc:
                logger.warning("商户主干网分片采集失败: %s", exc)
    return list(seen.values())


def run_snapshot_cycle(
    include_jumin: Optional[bool] = None,
    trigger: str = "AUTO",
) -> Dict[str, Any]:
    """
    执行单轮高频（默认 5 分钟）受控并行快照采集、清洗、整点后积分定格与 2 小时滚动清理。

    路线 B 约定：
    - 彻底不再拉取换热站实时（/zx_hrz/、/get_yw_data/1）及二次网分区；
    - 并发拉取上游点位（/gk_get_data/）、商业用户（/get_sh_data/）及整点居民室温（/jumin/）；
    - 当前未结束小时仅更新瞬时代表断面（累计耗量留空）；跨小时后自动对已结束小时做梯形积分定格，
      并执行“算完即清”（仅保留当前小时 + 上一小时采样明细）。
    """
    ensure_smart_heating_fact_tables()
    with _SNAPSHOT_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        snap_interval = int(cfg.get("snapshot_interval_minutes", 5))
        max_workers = max(1, min(16, int(cfg.get("max_workers", 4))))
        timeout = float(cfg.get("request_timeout_seconds", 15.0))
        cookie = normalize_cookie_input(str(cfg.get("cookie") or ""))

        sample_bucket = floor_to_bucket(now_e8, snap_interval)
        biz_hour = floor_to_hour(now_e8)

        should_fetch_jumin = (sample_bucket.minute == 0) if include_jumin is None else bool(include_jumin)
        run_type = "MANUAL" if trigger == "MANUAL" else "SNAPSHOT_5M"
        run_id = _insert_run_log(biz_hour, run_type, cfg.get("source_mode", "public"))

        headers = {
            "User-Agent": "Phoenix-SmartHeating-Collector/2.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Connection": "close",
        }

        caches = _load_dict_caches()
        prev_valid = _load_prev_valid_snapshots(biz_hour)

        upstream_rows: List[Dict[str, Any]] = []
        temp_rows: List[Dict[str, Any]] = []
        merchant_rows: List[Dict[str, Any]] = []
        fault_rows: List[Dict[str, Any]] = []
        cookie_valid: Optional[bool] = None

        def _fetch_upstream() -> Dict[str, Any]:
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                r_gk = _post_with_retry(client, f"{base_url}/gk_get_data/", headers=headers)
                r_gk.raise_for_status()
                return r_gk.json() or {}

        def _fetch_jumin() -> Tuple[Optional[bool], List[Dict[str, Any]]]:
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                r_jm = _post_with_retry(
                    client,
                    f"{base_url}/jumin/",
                    data={"department_name": "0", "filter_level": "0", "isDownload": "1"},
                    headers={**headers, "Cookie": cookie},
                )
                if r_jm.status_code != 200:
                    return False, []
                jm_json = r_jm.json()
                items = jm_json.get("data", []) if isinstance(jm_json, dict) else []
                return True, items

        try:
            partial_errors: List[str] = []
            gk_data: Dict[str, Any] = {}
            raw_merchants: List[Dict[str, Any]] = []
            jm_items: List[Dict[str, Any]] = []

            with ThreadPoolExecutor(max_workers=min(max_workers, 3)) as pool:
                fut_up = pool.submit(_fetch_upstream)
                fut_mc = pool.submit(
                    _fetch_merchant_realtime_items,
                    base_url,
                    headers,
                    caches["main_network_ids"],
                    timeout,
                    max_workers,
                )
                fut_jm = pool.submit(_fetch_jumin) if (should_fetch_jumin and cookie) else None

                gk_data = fut_up.result()
                try:
                    raw_merchants = fut_mc.result()
                except Exception as mc_exc:
                    partial_errors.append(f"get_sh_data: {mc_exc}")
                    logger.warning("采集商业用户实时断面异常已跳过继续: %s", mc_exc)
                if fut_jm is not None:
                    try:
                        cookie_valid, jm_items = fut_jm.result()
                    except Exception as jm_exc:
                        cookie_valid = False
                        partial_errors.append(f"jumin: {jm_exc}")

            for data_zone, zone_dict in (gk_data or {}).items():
                if not isinstance(zone_dict, dict):
                    continue
                for src_name, raw_item in zone_dict.items():
                    if not isinstance(raw_item, dict):
                        continue
                    meta = caches["upstream_by_key"].get(
                        (data_zone, src_name),
                        {
                            "point_id": None,
                            "data_zone": data_zone,
                            "source_name": src_name,
                            "name": raw_item.get("item_name") or src_name,
                            "category": data_zone,
                            "sub_category": None,
                        },
                    )
                    cleaned_u, u_faults = clean_upstream_point(
                        raw_item,
                        meta,
                        now_e8,
                        prev_valid=prev_valid["upstream"].get((data_zone, src_name)),
                    )
                    cleaned_u["sample_bucket"] = sample_bucket
                    cleaned_u["biz_hour"] = biz_hour
                    upstream_rows.append(cleaned_u)
                    fault_rows.extend(u_faults)

            for raw_u in jm_items:
                if not isinstance(raw_u, dict) or not raw_u.get("id"):
                    continue
                cleaned_t, t_faults = clean_temp_device(
                    raw_u,
                    device_dict=caches["device_by_id"],
                    alias_station_map=caches["alias_station_map"],
                    collected_at=now_e8,
                )
                cleaned_t["biz_hour"] = biz_hour
                temp_rows.append(cleaned_t)
                fault_rows.extend(t_faults)

            for raw_m in raw_merchants:
                sname_key = str(raw_m.get("name") or "").strip()
                cleaned_m, m_faults = clean_merchant_point(
                    raw_m,
                    merchant_lookup=caches["merchant_by_name"],
                    collected_at=now_e8,
                    prev_valid=prev_valid["merchant"].get(sname_key),
                )
                cleaned_m["sample_bucket"] = sample_bucket
                cleaned_m["biz_hour"] = biz_hour
                merchant_rows.append(cleaned_m)
                fault_rows.extend(m_faults)

            # 统一入库、完结历史小时积分、算完即清
            with engine.begin() as conn:
                _upsert_batch(
                    conn,
                    "fact_upstream_15min",
                    [
                        "sample_bucket", "biz_hour", "point_id", "data_zone", "source_name", "display_name",
                        "category", "sub_category", "source_time", "temp_raw", "temp_clean", "pressure_raw",
                        "pressure_clean", "flow_raw", "flow_clean", "heat_raw", "heat_clean", "load_val",
                        "freq_val", "value_source", "fault_tag",
                    ],
                    ["sample_bucket", "data_zone", "source_name"],
                    [
                        "point_id", "display_name", "source_time", "temp_raw", "temp_clean", "pressure_raw",
                        "pressure_clean", "flow_raw", "flow_clean", "heat_raw", "heat_clean", "load_val",
                        "freq_val", "value_source", "fault_tag",
                    ],
                    upstream_rows,
                )

                if temp_rows:
                    _upsert_batch(
                        conn,
                        "fact_temp_hourly",
                        [
                            "biz_hour", "temp_device_id", "station_id", "is_registered", "village_name",
                            "station_name_raw", "zdxh", "temp_raw", "temp_clean", "upload_time",
                            "is_online_valid", "remark_snapshot", "fault_tag",
                        ],
                        ["biz_hour", "temp_device_id"],
                        [
                            "station_id", "is_registered", "village_name", "station_name_raw", "zdxh",
                            "temp_raw", "temp_clean", "upload_time", "is_online_valid", "remark_snapshot", "fault_tag",
                        ],
                        temp_rows,
                        extra_set_clauses=["updated_at = NOW()"],
                    )

                if merchant_rows:
                    _upsert_batch(
                        conn,
                        "fact_merchant_15min",
                        [
                            "sample_bucket", "biz_hour", "merchant_id", "source_name", "is_registered", "online",
                            "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
                            "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
                            "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
                            "value_source", "fault_tag",
                        ],
                        ["sample_bucket", "source_name"],
                        [
                            "merchant_id", "is_registered", "online",
                            "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
                            "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
                            "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
                            "value_source", "fault_tag",
                        ],
                        merchant_rows,
                    )

                dedup_faults: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
                for flt in fault_rows:
                    flt["biz_hour"] = biz_hour
                    key = (flt["entity_type"], flt["entity_id"], flt["fault_code"])
                    dedup_faults[key] = flt
                _upsert_batch(
                    conn,
                    "fact_fault_ticket",
                    [
                        "biz_hour", "entity_type", "entity_id", "entity_name", "fault_code",
                        "owner_party", "raw_value_text", "clean_strategy", "rule_desc",
                    ],
                    ["biz_hour", "entity_type", "entity_id", "fault_code"],
                    ["entity_name", "owner_party", "raw_value_text", "clean_strategy", "rule_desc"],
                    list(dedup_faults.values()),
                    extra_set_clauses=["updated_at = NOW()"],
                )

                # 先对已结束但尚未清理的完整小时执行积分定格
                pending_up_hours = [
                    r[0]
                    for r in conn.execute(
                        text(
                            "SELECT DISTINCT biz_hour FROM smart_heating_platform.fact_upstream_15min "
                            "WHERE biz_hour < :bh ORDER BY biz_hour ASC"
                        ),
                        {"bh": biz_hour},
                    ).fetchall()
                ]
                pending_mc_hours = [
                    r[0]
                    for r in conn.execute(
                        text(
                            "SELECT DISTINCT biz_hour FROM smart_heating_platform.fact_merchant_15min "
                            "WHERE biz_hour < :bh ORDER BY biz_hour ASC"
                        ),
                        {"bh": biz_hour},
                    ).fetchall()
                ]
                for ph in pending_up_hours:
                    _aggregate_upstream_hourly(conn, ph, finalize=True)
                for ph in pending_mc_hours:
                    _aggregate_merchant_hourly(conn, ph, finalize=True)

                # 当前进行中的小时仅更新瞬时断面，不外推累计耗量
                up_hourly_cnt = _aggregate_upstream_hourly(conn, biz_hour, finalize=False)
                mc_hourly_cnt = _aggregate_merchant_hourly(conn, biz_hour, finalize=False)

                # 算完即清：保留当前小时 + 上一小时（2 小时），清理更早采样明细
                sampling_pruned = prune_old_sampling_rows(conn, reference_time=biz_hour, keep_hours=SAMPLING_KEEP_HOURS)
                temp_pruned_cnt = prune_old_temp_hourly(conn, reference_time=biz_hour)

            summary = {
                "sample_bucket": sample_bucket.strftime("%Y-%m-%d %H:%M:%S"),
                "biz_hour": biz_hour.strftime("%Y-%m-%d %H:00:00"),
                "sample_interval_minutes": snap_interval,
                "max_workers": max_workers,
                "upstream_samples": len(upstream_rows),
                "station_hourly": 0,
                "zone_hourly": 0,
                "temp_hourly": len(temp_rows),
                "temp_pruned": temp_pruned_cnt,
                "merchant_samples": len(merchant_rows),
                "sampling_pruned": sampling_pruned,
                "finalized_hours": sorted({
                    h.astimezone(EAST_8).strftime("%Y-%m-%d %H:00")
                    for h in (*pending_up_hours, *pending_mc_hours)
                }),
                "fault_tickets": len(dedup_faults),
                "upstream_hourly": up_hourly_cnt,
                "merchant_hourly": mc_hourly_cnt,
                "cookie_valid": cookie_valid,
                "partial_errors": partial_errors,
            }
            _finish_run_log(
                run_id,
                started_perf,
                "PARTIAL" if partial_errors else "SUCCESS",
                cookie_valid,
                summary,
                error_message="; ".join(partial_errors) if partial_errors else None,
            )
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("智慧供热快照采集失败: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", cookie_valid, {}, error_message=str(exc))
            raise


def _parse_station_history_records(raw_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """解析 `/hrz_ls_zb/` 原始数组并按时间戳去重排序。"""
    dedup_map: Dict[datetime, Dict[str, Any]] = {}
    for rec in raw_records:
        if not isinstance(rec, dict):
            continue
        ts = parse_dt_east8(rec.get("create_time"))
        if ts is None:
            continue
        dedup_map[ts] = {
            "ts": ts,
            "f1": to_float(rec.get("f1")),
            "f2": to_float(rec.get("f2")),
            "f3": to_float(rec.get("f3")),
            "f4": to_float(rec.get("f4")),
            "f5": to_float(rec.get("f5")),
            "f209": to_float(rec.get("f209")),  # 瞬时补水流量 (t/h)
            "f220": to_float(rec.get("f220")),  # totF
            "f221": to_float(rec.get("f221")),  # totJ
            "f222": to_float(rec.get("f222")),  # flowJ
            "f253": to_float(rec.get("f253")),  # 电能累计
            "f254": to_float(rec.get("f254")),  # 补水累计
        }
    return [dedup_map[k] for k in sorted(dedup_map.keys())]


def _calibrate_station_parsed_hours(
    st: Dict[str, Any],
    parsed: List[Dict[str, Any]],
    hours_to_calib: List[datetime],
    prev_station_db: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """基于已解析的 `/hrz_ls_zb/` 序列执行单日整点表底差值、坏表隔离与瞬时积分兜底清洗。"""
    st_id = st["station_id"]
    st_name = st["name"]
    covered_area = float(st["covered_area"]) if st.get("covered_area") else 100000.0
    max_hourly_heat = station_max_hourly_heat_gj(covered_area)

    if not parsed:
        empty_rows = [
            {
                "biz_hour": hr,
                "station_id": st_id,
                "sample_count": 0,
                "online": False,
                "e1_raw": None, "e1_clean": None,
                "e3_raw": None, "e3_clean": None,
                "e4_raw": None, "e4_clean": None,
                "e7_raw": None, "e7_clean": None,
                "e8_raw": None, "e8_clean": None,
                "e11_raw": None, "e11_clean": None,
                "e14_raw": None, "e14_clean": None,
                "tot_j": None, "tot_f": None,
                "tot_water_f254": None, "tot_elec_f253": None,
                "hour_heat_raw_gj": None,
                "hour_heat_gj": None, "hour_heat_source": SRC_SOURCE_EMPTY,
                "hour_flow_t": None, "hour_flow_source": SRC_SOURCE_EMPTY,
                "hour_water_t": None, "hour_water_source": SRC_SOURCE_EMPTY,
                "hour_elec_kwh": None, "hour_elec_source": SRC_SOURCE_EMPTY,
                "value_source": SRC_SOURCE_EMPTY,
                "fault_tag": None,
            }
            for hr in hours_to_calib
        ]
        return empty_rows, []

    seq_j = [(p["ts"], p["f221"]) for p in parsed]
    seq_f = [(p["ts"], p["f220"]) for p in parsed]
    seq_w = [(p["ts"], p["f254"]) for p in parsed]
    seq_e = [(p["ts"], p["f253"]) for p in parsed]

    max_hourly_elec = station_max_hourly_elec_kwh(covered_area)
    max_hourly_water = station_max_hourly_water_t(covered_area)
    osc_w, osc_w_msg = is_meter_sequence_oscillating(seq_w, min_reversal=0.5)
    osc_e, osc_e_msg = is_meter_sequence_oscillating(seq_e, min_reversal=1.0)
    osc_w_fault_logged = False
    osc_e_fault_logged = False

    upsert_rows: List[Dict[str, Any]] = []
    faults: List[Dict[str, Any]] = []
    rolling_prev = prev_station_db

    for hr in hours_to_calib:
        hr_next = hr + timedelta(hours=1)
        j0 = interpolate_meter_at_hour(seq_j, hr)
        j1 = interpolate_meter_at_hour(seq_j, hr_next)
        f0 = interpolate_meter_at_hour(seq_f, hr)
        f1_v = interpolate_meter_at_hour(seq_f, hr_next)
        w0 = interpolate_meter_at_hour(seq_w, hr)
        w1 = interpolate_meter_at_hour(seq_w, hr_next)
        e0 = interpolate_meter_at_hour(seq_e, hr)
        e1_v = interpolate_meter_at_hour(seq_e, hr_next)

        win_pts = sorted((p for p in parsed if hr <= p["ts"] <= hr_next), key=lambda x: x["ts"])
        f222_limit = max_hourly_heat * 1.5
        fb_heat_raw = trapezoidal_hour_integral([(p["ts"], p["f222"]) for p in win_pts])
        bad_f222 = [
            round(float(p["f222"]), 2)
            for p in win_pts
            if p["f222"] is not None and (p["f222"] < 0.0 or p["f222"] > f222_limit)
        ]
        clean_f222_pts = [
            (
                p["ts"],
                None if (p["f222"] is not None and (p["f222"] < 0.0 or p["f222"] > f222_limit)) else p["f222"],
            )
            for p in win_pts
        ]
        fb_heat = trapezoidal_hour_integral(clean_f222_pts)
        extra_hour_tags: List[str] = []
        if bad_f222:
            extra_hour_tags.append(FAULT_SENSOR_RANGE)
            if (
                fb_heat is None
                and rolling_prev
                and rolling_prev.get("e11_clean") is not None
                and 0.0 <= float(rolling_prev["e11_clean"]) <= f222_limit
            ):
                fb_heat = round(float(rolling_prev["e11_clean"]), 4)
            faults.append({
                "biz_hour": hr,
                "entity_type": "STATION",
                "entity_id": st_id,
                "entity_name": st_name,
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"瞬时热量f222越限={bad_f222[:4]}, 原始积分={fb_heat_raw} GJ (上限={f222_limit:.1f} GJ/h)",
                "clean_strategy": f"留存原值 hour_heat_raw_gj={fb_heat_raw}，剔除越限瞬时样本后修正为 {fb_heat} GJ",
                "rule_desc": "单站一次网瞬时热量 f222 <0 或超过按面积核定极限热负荷 1.5 倍",
            })

        fb_flow = trapezoidal_hour_integral([(p["ts"], p["f2"]) for p in win_pts])
        clean_f209_pts = [
            (
                p["ts"],
                None if (p["f209"] is not None and (p["f209"] < 0.0 or p["f209"] > 100.0)) else p["f209"],
            )
            for p in win_pts
        ]
        fb_water = trapezoidal_hour_integral(clean_f209_pts)

        raw_delta_j = round(j1 - j0, 4) if (j0 is not None and j1 is not None) else None
        eff_delta_j = raw_delta_j
        scale_rule = STATION_METER_SCALE_FACTORS.get(st_name)
        if scale_rule and raw_delta_j is not None and raw_delta_j > 0.0:
            factor, scale_note = scale_rule
            scaled_val = round(raw_delta_j * factor, 4)
            should_scale = (
                (abs(scaled_val - fb_heat) < abs(raw_delta_j - fb_heat))
                if (fb_heat is not None and fb_heat > 0.1)
                else ((factor < 1.0 and raw_delta_j > max_hourly_heat * 0.5) or (factor > 1.0 and scaled_val <= f222_limit))
            )
            if should_scale:
                eff_delta_j = scaled_val
                extra_hour_tags.append(FAULT_SOFTWARE_DEFECT)
                faults.append({
                    "biz_hour": hr,
                    "entity_type": "STATION",
                    "entity_id": st_id,
                    "entity_name": st_name,
                    "fault_code": FAULT_SOFTWARE_DEFECT,
                    "owner_party": OWNER_UNIVERSITY,
                    "raw_value_text": f"表底差原值={raw_delta_j} GJ, 瞬时热量参考≈{fb_heat} GJ/h",
                    "clean_strategy": f"{scale_note} -> 修正为 {eff_delta_j} GJ（原值保留于 hour_heat_raw_gj）",
                    "rule_desc": "站点累计热量表底刻度与标准 GJ 不一致",
                })

        if eff_delta_j is not None:
            delta_j, jump_j, msg_j = validate_meter_delta(0.0, eff_delta_j, max_hourly_limit=max_hourly_heat)
            if jump_j and raw_delta_j is not None:
                msg_j = f"{msg_j} (原表底差={raw_delta_j:.2f}, j0={j0:.2f}, j1={j1:.2f})"
        else:
            delta_j, jump_j, msg_j = None, False, None

        if (
            not jump_j
            and delta_j is not None
            and fb_heat is not None
            and fb_heat > 1.0
            and delta_j > max(max_hourly_heat * 0.8, fb_heat * 4.0)
        ):
            jump_j = True
            msg_j = f"表底差与瞬时负荷严重背离: meter={delta_j:.2f} GJ, 瞬时积分={fb_heat:.2f} GJ"
            delta_j = None

        delta_f, _, _ = validate_meter_delta(f0, f1_v, max_hourly_limit=max_hourly_heat * 12)
        if osc_w:
            delta_w, jump_w, msg_w = None, True, osc_w_msg
        else:
            delta_w, jump_w, msg_w = validate_meter_delta(w0, w1, max_hourly_limit=max_hourly_water)
        if osc_e:
            delta_e, jump_e, msg_e = None, True, osc_e_msg
        else:
            delta_e, jump_e, msg_e = validate_meter_delta(e0, e1_v, max_hourly_limit=max_hourly_elec)

        if jump_w and (not osc_w or not osc_w_fault_logged):
            extra_hour_tags.append(FAULT_METER_JUMP)
            faults.append({
                "biz_hour": hr,
                "entity_type": "STATION",
                "entity_id": st_id,
                "entity_name": st_name,
                "fault_code": FAULT_METER_JUMP,
                "owner_party": OWNER_SHARED,
                "raw_value_text": f"补水表底 f254 异常: {msg_w}",
                "clean_strategy": (
                    f"表底跳过/倒走，自动降级采用清洗后瞬时补水 f209 积分 ({fb_water} t)"
                    if (not osc_w and fb_water is not None)
                    else "已置空异常小时补水读数 hour_water_t，避免虚假高补水污染榜单与日报"
                ),
                "rule_desc": "站点累计补水表底出现锯齿倒走或超过按面积核定上限 1.5 倍",
            })
            if osc_w:
                osc_w_fault_logged = True
        elif osc_w:
            extra_hour_tags.append(FAULT_METER_JUMP)

        if jump_e and (not osc_e or not osc_e_fault_logged):
            extra_hour_tags.append(FAULT_METER_JUMP)
            faults.append({
                "biz_hour": hr,
                "entity_type": "STATION",
                "entity_id": st_id,
                "entity_name": st_name,
                "fault_code": FAULT_METER_JUMP,
                "owner_party": OWNER_SHARED,
                "raw_value_text": f"电表表底 f253 异常: {msg_e}",
                "clean_strategy": "已置空异常小时电耗读数 hour_elec_kwh，避免虚假高电耗污染榜单与日报",
                "rule_desc": "站点累计电表表底出现锯齿倒走或超过按面积核定上限 1.5 倍",
            })
            if osc_e:
                osc_e_fault_logged = True
        elif osc_e:
            extra_hour_tags.append(FAULT_METER_JUMP)

        if jump_j:
            extra_hour_tags.append(FAULT_METER_JUMP)
            faults.append({
                "biz_hour": hr,
                "entity_type": "STATION",
                "entity_id": st_id,
                "entity_name": st_name,
                "fault_code": FAULT_METER_JUMP,
                "owner_party": OWNER_SHARED,
                "raw_value_text": msg_j,
                "clean_strategy": f"留存原值于 hour_heat_raw_gj，自动降级采用清洗后瞬时热量积分值 ({fb_heat} GJ)",
                "rule_desc": "相邻整点累计表底 totJ 出现倒走/清零或超过按面积核定极限负荷 1.5 倍",
            })

        if delta_j is not None:
            hr_heat, hr_heat_src = delta_j, SRC_METER_DIFF
        else:
            hr_heat, hr_heat_src = fb_heat, (SRC_FALLBACK_INTEGRAL if jump_j else SRC_INTEGRAL_15M)

        hour_heat_raw_gj = raw_delta_j if raw_delta_j is not None else fb_heat_raw

        hr_flow, hr_flow_src = (
            (delta_f, SRC_METER_DIFF) if delta_f is not None else (fb_flow, SRC_INTEGRAL_15M)
        )
        if delta_w is not None:
            hr_water, hr_water_src = delta_w, SRC_METER_DIFF
        elif not osc_w and fb_water is not None:
            hr_water, hr_water_src = fb_water, (SRC_FALLBACK_INTEGRAL if jump_w else SRC_INTEGRAL_15M)
        else:
            hr_water, hr_water_src = None, "NONE"

        rep = win_pts[-1] if win_pts else None
        cleaned_rep, rep_faults = clean_station_history_point(st, rep, prev_station_valid=rolling_prev)
        for rf in rep_faults:
            rf["biz_hour"] = hr
            faults.append(rf)
        if cleaned_rep["online"]:
            rolling_prev = cleaned_rep

        rep_tags = [t for t in str(cleaned_rep.get("fault_tag") or "").split(",") if t]
        merged_fault_tags = ",".join(dict.fromkeys([*rep_tags, *extra_hour_tags])) or None
        eff_value_source = (
            SRC_MASKED_PREV
            if (cleaned_rep["value_source"] == SRC_REAL and (bad_f222 or jump_j or (eff_delta_j != raw_delta_j)))
            else cleaned_rep["value_source"]
        )

        upsert_rows.append({
            "biz_hour": hr,
            "station_id": st_id,
            "sample_count": len(win_pts),
            "online": cleaned_rep["online"],
            "e1_raw": cleaned_rep["e1_raw"],
            "e1_clean": cleaned_rep["e1_clean"],
            "e3_raw": cleaned_rep["e3_raw"],
            "e3_clean": cleaned_rep["e3_clean"],
            "e4_raw": cleaned_rep["e4_raw"],
            "e4_clean": cleaned_rep["e4_clean"],
            "e7_raw": cleaned_rep["e7_raw"],
            "e7_clean": cleaned_rep["e7_clean"],
            "e8_raw": cleaned_rep["e8_raw"],
            "e8_clean": cleaned_rep["e8_clean"],
            "e11_raw": cleaned_rep["e11_raw"],
            "e11_clean": cleaned_rep["e11_clean"],
            "e14_raw": cleaned_rep["e14_raw"],
            "e14_clean": cleaned_rep["e14_clean"],
            "tot_j": j0,
            "tot_f": f0,
            "tot_water_f254": w0,
            "tot_elec_f253": e0,
            "hour_heat_raw_gj": hour_heat_raw_gj,
            "hour_heat_gj": hr_heat,
            "hour_heat_source": hr_heat_src,
            "hour_flow_t": hr_flow,
            "hour_flow_source": hr_flow_src,
            "hour_water_t": hr_water,
            "hour_water_source": hr_water_src,
            "hour_elec_kwh": delta_e,
            "hour_elec_source": SRC_METER_DIFF if delta_e is not None else "NONE",
            "value_source": eff_value_source,
            "fault_tag": merged_fault_tags,
        })

    return upsert_rows, faults


def _process_station_calibration(
    st: Dict[str, Any],
    base_url: str,
    query_start: str,
    query_end: str,
    hours_to_calib: List[datetime],
    timeout: float,
    prev_station_db: Optional[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """拉取单座换热站 `/hrz_ls_zb/` 并计算整点表底差值与代表断面（供多线程并发调用）。"""
    st_name = st["name"]
    st_query_name = st.get("name_raw") or st_name
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            resp = _post_with_retry(
                client,
                f"{base_url}/hrz_ls_zb/",
                data={
                    "name": st_query_name,
                    "start_date": query_start,
                    "end_date": query_end,
                    "isdownload": "1",
                },
                headers={"User-Agent": "Phoenix-SmartHeating-Collector/2.0", "Connection": "close"},
                retries=2,
            )
            if resp.status_code != 200:
                return st_name, [], [], False
            raw_records = resp.json()
            if not isinstance(raw_records, list):
                return st_name, [], [], False
    except Exception:
        return st_name, [], [], False

    parsed = _parse_station_history_records(raw_records)
    upsert_rows, faults = _calibrate_station_parsed_hours(
        st, parsed, hours_to_calib, prev_station_db=prev_station_db
    )
    return st_name, upsert_rows, faults, True


def _upsert_station_calibration_results(
    all_upsert_rows: List[Dict[str, Any]],
    all_faults: List[Dict[str, Any]],
) -> None:
    """将换热站整点校准结果与故障事件幂等写入 PostgreSQL。"""
    if all_upsert_rows:
        real_station_rows = [r for r in all_upsert_rows if r.get("value_source") != SRC_SOURCE_EMPTY]
        empty_station_rows = [r for r in all_upsert_rows if r.get("value_source") == SRC_SOURCE_EMPTY]
        sql = """
        INSERT INTO smart_heating_platform.fact_station_hourly (
            biz_hour, station_id, sample_count, online,
            e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean,
            e7_raw, e7_clean, e8_raw, e8_clean, e11_raw, e11_clean, e14_raw, e14_clean,
            tot_j, tot_f, tot_water_f254, tot_elec_f253,
            hour_heat_raw_gj, hour_heat_gj, hour_heat_source, hour_flow_t, hour_flow_source,
            hour_water_t, hour_water_source, hour_elec_kwh, hour_elec_source,
            value_source, fault_tag
        ) VALUES (
            :biz_hour, :station_id, :sample_count, :online,
            :e1_raw, :e1_clean, :e3_raw, :e3_clean, :e4_raw, :e4_clean,
            :e7_raw, :e7_clean, :e8_raw, :e8_clean, :e11_raw, :e11_clean, :e14_raw, :e14_clean,
            :tot_j, :tot_f, :tot_water_f254, :tot_elec_f253,
            :hour_heat_raw_gj, :hour_heat_gj, :hour_heat_source, :hour_flow_t, :hour_flow_source,
            :hour_water_t, :hour_water_source, :hour_elec_kwh, :hour_elec_source,
            :value_source, :fault_tag
        )
        ON CONFLICT (biz_hour, station_id) DO UPDATE SET
            sample_count = EXCLUDED.sample_count,
            online = EXCLUDED.online,
            e1_raw = COALESCE(EXCLUDED.e1_raw, smart_heating_platform.fact_station_hourly.e1_raw),
            e1_clean = EXCLUDED.e1_clean,
            e3_raw = COALESCE(EXCLUDED.e3_raw, smart_heating_platform.fact_station_hourly.e3_raw),
            e3_clean = EXCLUDED.e3_clean,
            e4_raw = COALESCE(EXCLUDED.e4_raw, smart_heating_platform.fact_station_hourly.e4_raw),
            e4_clean = EXCLUDED.e4_clean,
            e7_raw = COALESCE(EXCLUDED.e7_raw, smart_heating_platform.fact_station_hourly.e7_raw),
            e7_clean = EXCLUDED.e7_clean,
            e8_raw = COALESCE(EXCLUDED.e8_raw, smart_heating_platform.fact_station_hourly.e8_raw),
            e8_clean = EXCLUDED.e8_clean,
            e11_raw = COALESCE(EXCLUDED.e11_raw, smart_heating_platform.fact_station_hourly.e11_raw),
            e11_clean = EXCLUDED.e11_clean,
            e14_raw = COALESCE(EXCLUDED.e14_raw, smart_heating_platform.fact_station_hourly.e14_raw),
            e14_clean = EXCLUDED.e14_clean,
            tot_j = COALESCE(EXCLUDED.tot_j, smart_heating_platform.fact_station_hourly.tot_j),
            tot_f = COALESCE(EXCLUDED.tot_f, smart_heating_platform.fact_station_hourly.tot_f),
            tot_water_f254 = COALESCE(EXCLUDED.tot_water_f254, smart_heating_platform.fact_station_hourly.tot_water_f254),
            tot_elec_f253 = COALESCE(EXCLUDED.tot_elec_f253, smart_heating_platform.fact_station_hourly.tot_elec_f253),
            hour_heat_raw_gj = COALESCE(EXCLUDED.hour_heat_raw_gj, smart_heating_platform.fact_station_hourly.hour_heat_raw_gj),
            hour_heat_gj = EXCLUDED.hour_heat_gj,
            hour_heat_source = EXCLUDED.hour_heat_source,
            hour_flow_t = COALESCE(EXCLUDED.hour_flow_t, smart_heating_platform.fact_station_hourly.hour_flow_t),
            hour_flow_source = EXCLUDED.hour_flow_source,
            hour_water_t = EXCLUDED.hour_water_t,
            hour_water_source = EXCLUDED.hour_water_source,
            hour_elec_kwh = EXCLUDED.hour_elec_kwh,
            hour_elec_source = EXCLUDED.hour_elec_source,
            value_source = EXCLUDED.value_source,
            fault_tag = EXCLUDED.fault_tag,
            updated_at = NOW()
        """
        station_cols = [
            "biz_hour", "station_id", "sample_count", "online",
            "e1_raw", "e1_clean", "e3_raw", "e3_clean", "e4_raw", "e4_clean",
            "e7_raw", "e7_clean", "e8_raw", "e8_clean", "e11_raw", "e11_clean", "e14_raw", "e14_clean",
            "tot_j", "tot_f", "tot_water_f254", "tot_elec_f253",
            "hour_heat_raw_gj", "hour_heat_gj", "hour_heat_source", "hour_flow_t", "hour_flow_source",
            "hour_water_t", "hour_water_source", "hour_elec_kwh", "hour_elec_source",
            "value_source", "fault_tag",
        ]
        with engine.begin() as conn:
            for offset in range(0, len(real_station_rows), 500):
                conn.execute(text(sql), real_station_rows[offset:offset + 500])
            for offset in range(0, len(empty_station_rows), 500):
                _upsert_batch(
                    conn,
                    "fact_station_hourly",
                    station_cols,
                    ["biz_hour", "station_id"],
                    [],
                    empty_station_rows[offset:offset + 500],
                    do_nothing_on_conflict=True,
                )

    if all_faults:
        dedup_faults: Dict[Tuple[datetime, str, str, str], Dict[str, Any]] = {}
        for flt in all_faults:
            key = (flt["biz_hour"], flt["entity_type"], flt["entity_id"], flt["fault_code"])
            dedup_faults[key] = flt
        with engine.begin() as conn:
            _upsert_batch(
                conn,
                "fact_fault_ticket",
                [
                    "biz_hour", "entity_type", "entity_id", "entity_name", "fault_code",
                    "owner_party", "raw_value_text", "clean_strategy", "rule_desc",
                ],
                ["biz_hour", "entity_type", "entity_id", "fault_code"],
                ["entity_name", "owner_party", "raw_value_text", "clean_strategy", "rule_desc"],
                list(dedup_faults.values()),
                extra_set_clauses=["updated_at = NOW()"],
            )


def run_table_bottom_calibration(
    target_date_str: Optional[str] = None,
    station_names: Optional[List[str]] = None,
    target_hours: Optional[Sequence[datetime]] = None,
    trigger: str = "AUTO",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    受控并行拉取 `/hrz_ls_zb/`（isdownload=1），按整点线性插值计算精确表底差值与代表断面，
    写入 `fact_station_hourly`（路线 B 专责换热站每小时整点后产出，不阻塞 5 分钟快照采集）。
    支持传入 `target_hours` 仅写入真空期缺失小时，同时保留全日上下文以维持前序有效快照递推。
    """
    ensure_smart_heating_fact_tables()
    with _CALIB_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        default_d = (now_e8.date() - timedelta(days=1)) if now_e8.hour == 0 else now_e8.date()
        target_d = date.fromisoformat(target_date_str) if target_date_str else default_d
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)

        # 仅校准已结束的整点小时；今日截止到上一已完成整点，历史日覆盖全天 24 小时
        max_hour = (
            floor_to_hour(now_e8) - timedelta(hours=1)
            if target_d >= now_e8.date()
            else (next_day_start - timedelta(hours=1))
        )
        hours_to_calib: List[datetime] = []
        cursor = day_start
        while cursor <= max_hour:
            hours_to_calib.append(cursor)
            cursor += timedelta(hours=1)

        target_hour_set = {floor_to_hour(h) for h in target_hours} if target_hours is not None else None
        has_target_overlap = (
            any(h in target_hour_set for h in hours_to_calib)
            if target_hour_set is not None
            else bool(hours_to_calib)
        )

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        max_workers = max(1, min(16, int(cfg.get("max_workers", 4))))
        timeout = max(45.0, float(cfg.get("request_timeout_seconds", 15.0)))
        run_id = _insert_run_log(day_start, "TABLE_BOTTOM_CALIB" if trigger != "MANUAL" else "MANUAL_CALIB", cfg.get("source_mode", "public"))

        if not hours_to_calib or not has_target_overlap:
            summary = {
                "target_date": target_d.isoformat(),
                "stations_total": 0,
                "updated_station_hours": 0,
                "failed_stations": [],
                "jump_faults": 0,
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS", None, summary)
            return {"ok": True, "run_id": run_id, **summary}

        caches = _load_dict_caches()
        prev_station_map = _load_prev_valid_snapshots(day_start)["station"]
        target_stations = caches["stations"]
        if station_names:
            name_set = {s.strip() for s in station_names if s.strip()}
            target_stations = [s for s in target_stations if s["name"] in name_set]

        query_start = (day_start - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        query_end = (next_day_start + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        all_upsert_rows: List[Dict[str, Any]] = []
        failed_stations: List[str] = []
        all_faults: List[Dict[str, Any]] = []

        try:
            workers = max(1, min(max_workers, len(target_stations) or 1))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(
                        _process_station_calibration,
                        st,
                        base_url,
                        query_start,
                        query_end,
                        hours_to_calib,
                        timeout,
                        prev_station_map.get(st["station_id"]),
                    )
                    for st in target_stations
                ]
                total_futs = len(futures)
                for idx_done, fut in enumerate(as_completed(futures), 1):
                    st_name, st_rows, st_faults, ok_flag = fut.result()
                    if progress_cb is not None:
                        progress_cb(idx_done, total_futs, st_name)
                    if not ok_flag:
                        failed_stations.append(st_name)
                    if st_rows:
                        if target_hour_set is not None:
                            all_upsert_rows.extend(r for r in st_rows if floor_to_hour(r["biz_hour"]) in target_hour_set)
                        else:
                            all_upsert_rows.extend(st_rows)
                    if st_faults:
                        if target_hour_set is not None:
                            all_faults.extend(f for f in st_faults if floor_to_hour(f["biz_hour"]) in target_hour_set)
                        else:
                            all_faults.extend(st_faults)

            _upsert_station_calibration_results(all_upsert_rows, all_faults)

            jump_count = sum(1 for f in all_faults if f["fault_code"] == FAULT_METER_JUMP)
            summary = {
                "target_date": target_d.isoformat(),
                "stations_total": len(target_stations),
                "updated_station_hours": len(all_upsert_rows),
                "failed_stations": sorted(failed_stations)[:20],
                "jump_faults": jump_count,
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS" if not failed_stations else "PARTIAL", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("表底校准任务异常: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise


def run_merchant_daily_cycle(target_date_str: Optional[str] = None, trigger: str = "AUTO") -> Dict[str, Any]:
    """拉取 `/getall_bb_shrb/` 写入商业用户当月日耗量至 `fact_merchant_daily`。"""
    ensure_smart_heating_fact_tables()
    with _MERCHANT_DAILY_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        target_d = date.fromisoformat(target_date_str) if target_date_str else (now_e8.date() - timedelta(days=1))
        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        cookie = normalize_cookie_input(str(cfg.get("cookie") or ""))
        if not cookie:
            return {"ok": False, "message": "未配置 Cookie，跳过商业用户日耗量采集"}

        run_id = _insert_run_log(
            datetime(target_d.year, target_d.month, target_d.day, 0, 0, tzinfo=EAST_8),
            "MERCHANT_DAILY" if trigger != "MANUAL" else "MANUAL_MERCHANT",
            cfg.get("source_mode", "public"),
        )
        caches = _load_dict_caches()
        last_day = calendar.monthrange(target_d.year, target_d.month)[1]
        ym = f"{target_d.year}{target_d.month}"
        headers = {"User-Agent": "Phoenix-SmartHeating-Collector/2.0", "Cookie": cookie}
        interval = max(0.5, float(cfg.get("request_interval_seconds", 0.8)))

        try:
            with httpx.Client(timeout=20.0, follow_redirects=False, trust_env=False) as client:
                r_unit = client.post(
                    f"{base_url}/getall_bb_shrb/",
                    data={"selectof1": "0", "selectof2": "0", "selectof3": "1", "options4": ym, "lastDay": str(last_day)},
                    headers=headers,
                )
                if r_unit.status_code != 200:
                    _finish_run_log(run_id, started_perf, "FAILED", False, {}, f"HTTP {r_unit.status_code}")
                    return {"ok": False, "message": f"Cookie 可能已失效（HTTP {r_unit.status_code}）"}
                unit_list = r_unit.json() or []
                time.sleep(interval)
                r_tot = client.post(
                    f"{base_url}/getall_bb_shrb/",
                    data={"selectof1": "0", "selectof2": "0", "selectof3": "0", "options4": ym, "lastDay": str(last_day)},
                    headers=headers,
                )
                tot_list = r_tot.json() or [] if r_tot.status_code == 200 else []

            tot_by_id = {str(x.get("id") or ""): x for x in tot_list if isinstance(x, dict)}
            day_col = f"Data{target_d.day}"
            prev_col = f"Data{target_d.day - 1}" if target_d.day > 1 else "Data0"

            rows: List[Dict[str, Any]] = []
            for item in unit_list:
                if not isinstance(item, dict):
                    continue
                m_id = str(item.get("id") or "").strip()
                if m_id not in caches["merchant_by_id"]:
                    continue
                unit_val = to_float(item.get(day_col))
                tot_item = tot_by_id.get(m_id) or {}
                v_curr = to_float(tot_item.get(day_col))
                v_prev = to_float(tot_item.get(prev_col))
                daily_cons = None
                if v_curr is not None and v_prev is not None and v_curr >= v_prev:
                    daily_cons = round(v_curr - v_prev, 4)

                rows.append({
                    "biz_date": target_d,
                    "merchant_id": m_id,
                    "daily_consumption": daily_cons,
                    "daily_unit_heat": unit_val,
                    "raw_payload": json.dumps({"unit": item.get(day_col), "tot_curr": v_curr, "tot_prev": v_prev}, ensure_ascii=False),
                })

            with engine.begin() as conn:
                if rows:
                    sql = """
                    INSERT INTO smart_heating_platform.fact_merchant_daily (
                        biz_date, merchant_id, daily_consumption, daily_unit_heat, raw_payload
                    ) VALUES (
                        :biz_date, :merchant_id, :daily_consumption, :daily_unit_heat, CAST(:raw_payload AS JSONB)
                    )
                    ON CONFLICT (biz_date, merchant_id) DO UPDATE SET
                        daily_consumption = EXCLUDED.daily_consumption,
                        daily_unit_heat = EXCLUDED.daily_unit_heat,
                        raw_payload = EXCLUDED.raw_payload,
                        updated_at = NOW()
                    """
                    conn.execute(text(sql), rows)

            summary = {"biz_date": target_d.isoformat(), "merchants_saved": len(rows)}
            _finish_run_log(run_id, started_perf, "SUCCESS", True, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("商业用户日耗量采集失败: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise


def _build_completed_day_hours(
    day_start: datetime,
    max_hour: datetime,
    target_hour_set: Optional[set[datetime]],
) -> List[datetime]:
    """构造指定日期内（截止 max_hour）且命中 target_hour_set 的已完成整点列表。"""
    hours: List[datetime] = []
    cursor = day_start
    while cursor <= max_hour:
        if target_hour_set is None or cursor in target_hour_set:
            hours.append(cursor)
        cursor += timedelta(hours=1)
    return hours


def run_merchant_hourly_backfill(
    target_date_str: Optional[str] = None,
    merchant_names: Optional[List[str]] = None,
    target_hours: Optional[Sequence[datetime]] = None,
    trigger: str = "MANUAL",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    受控并行调用免 Cookie 历史接口 `/sh_ls_zb/`（5分钟颗粒度）补采商业用户指定日期逐小时指标，
    基于 `fFlowJ`/`fFlowF` 执行时间加权梯形面积积分写入 `fact_merchant_hourly`；
    对 HTTP 200 正常返回但源站本身无历史数据的已完成整点，写入 `SOURCE_EMPTY` 空值占位行以区分漏采。
    """
    ensure_smart_heating_fact_tables()
    with _MERCHANT_BACKFILL_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)
        latest_completed_hour = floor_to_hour(now_e8) - timedelta(hours=1)
        max_completed_hour = min(next_day_start - timedelta(hours=1), latest_completed_hour)
        target_hour_set = {floor_to_hour(h) for h in target_hours} if target_hours is not None else None
        expected_completed_hours = _build_completed_day_hours(day_start, max_completed_hour, target_hour_set)

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        max_workers = max(1, min(16, int(cfg.get("max_workers", 4))))
        timeout = max(20.0, float(cfg.get("request_timeout_seconds", 15.0)))
        run_id = _insert_run_log(
            day_start,
            "MERCHANT_HOURLY_BACKFILL" if trigger == "MANUAL" else "MERCHANT_BACKFILL",
            cfg.get("source_mode", "public"),
        )

        caches = _load_dict_caches()
        target_merchants = caches["merchants"]
        if merchant_names:
            name_set = {m.strip() for m in merchant_names if m.strip()}
            target_merchants = [m for m in target_merchants if m["name"] in name_set]

        query_start = day_start.strftime("%Y-%m-%d %H:%M:%S")
        query_end = next_day_start.strftime("%Y-%m-%d %H:%M:%S")
        failed_merchants: List[str] = []
        all_real_rows: List[Dict[str, Any]] = []
        all_empty_rows: List[Dict[str, Any]] = []

        def _fetch_one_merchant(mc: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], bool]:
            m_name = mc["name"]
            try:
                with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                    resp = _post_with_retry(
                        client,
                        f"{base_url}/sh_ls_zb/",
                        data={
                            "name": m_name,
                            "start_date": query_start,
                            "end_date": query_end,
                            "isdownload": "1",
                        },
                        headers={"User-Agent": "Phoenix-SmartHeating-Collector/2.0", "Connection": "close"},
                        retries=2,
                    )
                    if resp.status_code != 200:
                        return m_name, [], [], False
                    raw_records = resp.json()
                    if not isinstance(raw_records, list):
                        return m_name, [], [], False
            except Exception:
                return m_name, [], [], False

            by_hour: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = {}
            for rec in raw_records:
                if not isinstance(rec, dict):
                    continue
                ts = parse_dt_east8(rec.get("tmDate"))
                if ts is None:
                    continue
                cleaned, _ = clean_merchant_point(
                    {**rec, "name": m_name},
                    merchant_lookup=caches["merchant_by_name"],
                    collected_at=now_e8,
                )
                by_hour.setdefault(floor_to_hour(ts), []).append((ts, cleaned))

            real_rows: List[Dict[str, Any]] = []
            for bh, pts in sorted(by_hour.items()):
                if not (day_start <= bh < next_day_start):
                    continue
                if target_hour_set is not None and bh not in target_hour_set:
                    continue
                pts.sort(key=lambda x: x[0])
                latest = pts[-1][1]
                heat_samples = [(ts, p["heat_clean"]) for ts, p in pts]
                flow_samples = [(ts, p["flow_clean"]) for ts, p in pts]
                real_rows.append({
                    "biz_hour": bh,
                    "merchant_id": mc["merchant_id"],
                    "source_name": m_name,
                    "is_registered": True,
                    "sample_count": len(pts),
                    "online": True,
                    "flow_raw": latest["flow_raw"],
                    "flow_clean": latest["flow_clean"],
                    "return_flow_raw": latest["return_flow_raw"],
                    "temp_sup_raw": latest["temp_sup_raw"],
                    "temp_sup_clean": latest["temp_sup_clean"],
                    "temp_ret_raw": latest["temp_ret_raw"],
                    "temp_ret_clean": latest["temp_ret_clean"],
                    "pres_sup_raw": latest["pres_sup_raw"],
                    "pres_sup_clean": latest["pres_sup_clean"],
                    "pres_ret_raw": latest["pres_ret_raw"],
                    "pres_ret_clean": latest["pres_ret_clean"],
                    "heat_raw": latest["heat_raw"],
                    "heat_clean": latest["heat_clean"],
                    "valve_open": latest["valve_open"],
                    "valve_set": latest["valve_set"],
                    "hour_heat_gj": trapezoidal_hour_integral(heat_samples),
                    "hour_heat_source": "INTEGRAL_5M",
                    "hour_flow_t": trapezoidal_hour_integral(flow_samples),
                    "hour_flow_source": "INTEGRAL_5M",
                    "value_source": latest["value_source"],
                    "fault_tag": latest["fault_tag"],
                })

            empty_rows: List[Dict[str, Any]] = []
            for bh in expected_completed_hours:
                if bh in by_hour:
                    continue
                empty_rows.append({
                    "biz_hour": bh,
                    "merchant_id": mc["merchant_id"],
                    "source_name": m_name,
                    "is_registered": True,
                    "sample_count": 0,
                    "online": False,
                    "flow_raw": None,
                    "flow_clean": None,
                    "return_flow_raw": None,
                    "temp_sup_raw": None,
                    "temp_sup_clean": None,
                    "temp_ret_raw": None,
                    "temp_ret_clean": None,
                    "pres_sup_raw": None,
                    "pres_sup_clean": None,
                    "pres_ret_raw": None,
                    "pres_ret_clean": None,
                    "heat_raw": None,
                    "heat_clean": None,
                    "valve_open": None,
                    "valve_set": None,
                    "hour_heat_gj": None,
                    "hour_heat_source": SRC_SOURCE_EMPTY,
                    "hour_flow_t": None,
                    "hour_flow_source": SRC_SOURCE_EMPTY,
                    "value_source": SRC_SOURCE_EMPTY,
                    "fault_tag": None,
                })
            return m_name, real_rows, empty_rows, True

        try:
            workers = max(1, min(max_workers, len(target_merchants) or 1))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_fetch_one_merchant, mc) for mc in target_merchants]
                total_futs = len(futures)
                for idx_done, fut in enumerate(as_completed(futures), 1):
                    m_name, real_out, empty_out, ok_flag = fut.result()
                    if progress_cb is not None:
                        progress_cb(idx_done, total_futs, m_name)
                    if not ok_flag:
                        failed_merchants.append(m_name)
                    if real_out:
                        all_real_rows.extend(real_out)
                    if empty_out:
                        all_empty_rows.extend(empty_out)

            merchant_cols = [
                "biz_hour", "merchant_id", "source_name", "is_registered", "sample_count", "online",
                "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
                "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
                "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
                "hour_heat_gj", "hour_heat_source", "hour_flow_t", "hour_flow_source",
                "value_source", "fault_tag",
            ]
            merchant_update_cols = [
                "merchant_id", "is_registered", "sample_count", "online",
                "flow_raw", "flow_clean", "return_flow_raw", "temp_sup_raw", "temp_sup_clean",
                "temp_ret_raw", "temp_ret_clean", "pres_sup_raw", "pres_sup_clean",
                "pres_ret_raw", "pres_ret_clean", "heat_raw", "heat_clean", "valve_open", "valve_set",
                "hour_heat_gj", "hour_heat_source", "hour_flow_t", "hour_flow_source",
                "value_source", "fault_tag",
            ]
            if all_real_rows or all_empty_rows:
                with engine.begin() as conn:
                    for offset in range(0, len(all_real_rows), 500):
                        _upsert_batch(
                            conn,
                            "fact_merchant_hourly",
                            merchant_cols,
                            ["biz_hour", "source_name"],
                            merchant_update_cols,
                            all_real_rows[offset:offset + 500],
                            extra_set_clauses=["updated_at = NOW()"],
                        )
                    for offset in range(0, len(all_empty_rows), 500):
                        _upsert_batch(
                            conn,
                            "fact_merchant_hourly",
                            merchant_cols,
                            ["biz_hour", "source_name"],
                            [],
                            all_empty_rows[offset:offset + 500],
                            do_nothing_on_conflict=True,
                        )

            summary = {
                "target_date": target_d.isoformat(),
                "merchants_total": len(target_merchants),
                "updated_merchant_hours": len(all_real_rows),
                "empty_merchant_hours": len(all_empty_rows),
                "failed_merchants": sorted(failed_merchants)[:20],
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS" if not failed_merchants else "PARTIAL", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("商业用户小时历史补采异常: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise


def _to_east8_hour(value: Any) -> Optional[datetime]:
    """将数据库或外部传入的时间对象统一转换为东八区整点 datetime。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=EAST_8)
        return floor_to_hour(dt.astimezone(EAST_8))
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, 0, 0, tzinfo=EAST_8)
    parsed = parse_dt_east8(str(value))
    return floor_to_hour(parsed) if parsed else None


def _group_hours_by_date(hours: Sequence[datetime]) -> Dict[str, List[datetime]]:
    """按东八区日期字符串 YYYY-MM-DD 分组整点列表（按时间升序）。"""
    grouped: Dict[str, List[datetime]] = {}
    for h in sorted({floor_to_hour(x.astimezone(EAST_8) if x.tzinfo else x.replace(tzinfo=EAST_8)) for x in hours}):
        grouped.setdefault(h.date().isoformat(), []).append(h)
    return grouped


def run_upstream_hourly_backfill(
    target_date_str: Optional[str] = None,
    target_hours: Optional[Sequence[datetime]] = None,
    trigger: str = "MANUAL",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    受控并行调用免 Cookie 历史接口 `/ry_dcls_xx/get_history` 与 `/ry_szls_xx/get_history`
    补采上游电厂与首站逐小时运行工况，执行时间加权梯形积分并写入 `fact_upstream_hourly`。
    """
    ensure_smart_heating_fact_tables()
    with _UPSTREAM_BACKFILL_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        default_d = (now_e8.date() - timedelta(days=1)) if now_e8.hour == 0 else now_e8.date()
        target_d = date.fromisoformat(target_date_str) if target_date_str else default_d
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)
        latest_completed_hour = floor_to_hour(now_e8) - timedelta(hours=1)
        max_hour = min(next_day_start - timedelta(hours=1), latest_completed_hour)

        target_hour_set = {floor_to_hour(h) for h in target_hours} if target_hours is not None else None
        expected_completed_hours = _build_completed_day_hours(day_start, max_hour, target_hour_set)
        has_target_overlap = bool(expected_completed_hours)

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        max_workers = max(1, min(16, int(cfg.get("max_workers", 4))))
        timeout = max(20.0, float(cfg.get("request_timeout_seconds", 15.0)))
        run_id = _insert_run_log(
            day_start,
            "UPSTREAM_BACKFILL" if trigger != "MANUAL" else "MANUAL_UPSTREAM_BACKFILL",
            cfg.get("source_mode", "public"),
        )

        if max_hour < day_start or not has_target_overlap:
            summary = {
                "target_date": target_d.isoformat(),
                "points_total": 0,
                "updated_upstream_hours": 0,
                "empty_upstream_hours": 0,
                "failed_points": [],
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS", None, summary)
            return {"ok": True, "run_id": run_id, **summary}

        caches = _load_dict_caches()
        headers = {"User-Agent": "Phoenix-SmartHeating-Collector/2.0", "Connection": "close"}
        date_mmddyyyy = target_d.strftime("%m/%d/%Y")

        tasks: List[Tuple[str, str, str, str]] = []
        seen_task_keys: set[Tuple[str, str]] = set()
        try:
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                r_dc = _post_with_retry(client, f"{base_url}/get_dc_data/1", headers=headers, retries=2)
                r_sz = _post_with_retry(client, f"{base_url}/get_sz_data/1", headers=headers, retries=2)
                try:
                    dc_items = r_dc.json() if r_dc.status_code == 200 else []
                except Exception:
                    dc_items = []
                try:
                    sz_items = r_sz.json() if r_sz.status_code == 200 else []
                except Exception:
                    sz_items = []
                if isinstance(dc_items, list):
                    for item in dc_items:
                        if isinstance(item, dict) and item.get("name"):
                            key = ("dc_dict", str(item["name"]))
                            if key not in seen_task_keys:
                                seen_task_keys.add(key)
                                tasks.append(("dc_dict", key[1], str(item.get("id") or "1"), "/ry_dcls_xx/get_history"))
                if isinstance(sz_items, list):
                    for item in sz_items:
                        if isinstance(item, dict) and item.get("name"):
                            key = ("sz_dict", str(item["name"]))
                            if key not in seen_task_keys:
                                seen_task_keys.add(key)
                                tasks.append(("sz_dict", key[1], str(item.get("id") or "1"), "/ry_szls_xx/get_history"))

            # 若源站目录接口（如 /get_sz_data/1）临时异常，回落补齐库内已知电厂/首站测点清单
            with engine.connect() as conn:
                known_rows = conn.execute(
                    text(
                        "SELECT data_zone, source_name FROM smart_heating_platform.dict_upstream_point "
                        "WHERE data_zone IN ('dc_dict', 'sz_dict') "
                        "UNION "
                        "SELECT DISTINCT data_zone, source_name FROM smart_heating_platform.fact_upstream_hourly "
                        "WHERE data_zone IN ('dc_dict', 'sz_dict')"
                    )
                ).fetchall()
            for r in known_rows:
                key = (str(r.data_zone), str(r.source_name))
                if key not in seen_task_keys:
                    seen_task_keys.add(key)
                    ep = "/ry_dcls_xx/get_history" if key[0] == "dc_dict" else "/ry_szls_xx/get_history"
                    tasks.append((key[0], key[1], "1", ep))

            def _fetch_one_upstream(task_item: Tuple[str, str, str, str]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], bool]:
                dz, sname, grp_id, ep = task_item
                id_key = "dc_station_id" if dz == "dc_dict" else "sz_station_id"
                meta = caches["upstream_by_key"].get(
                    (dz, sname),
                    {
                        "point_id": None,
                        "data_zone": dz,
                        "source_name": sname,
                        "name": sname,
                        "category": "电厂" if dz == "dc_dict" else "首站",
                        "sub_category": None,
                    },
                )
                try:
                    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                        resp = _post_with_retry(
                            client,
                            f"{base_url}{ep}",
                            data={
                                "start_date": date_mmddyyyy,
                                "end_date": date_mmddyyyy,
                                "station_name": sname,
                                id_key: grp_id,
                            },
                            headers=headers,
                            retries=2,
                        )
                        if resp.status_code != 200:
                            return f"{dz}:{sname}", [], [], False
                        raw_records = resp.json()
                        if not isinstance(raw_records, list):
                            return f"{dz}:{sname}", [], [], False
                except Exception:
                    return f"{dz}:{sname}", [], [], False

                parsed_pts: List[Tuple[datetime, Dict[str, Any]]] = []
                for rec in raw_records:
                    if not isinstance(rec, dict):
                        continue
                    ts = parse_dt_east8(rec.get("tmDate"))
                    if ts is None:
                        continue
                    parsed_pts.append((ts, rec))
                parsed_pts.sort(key=lambda x: x[0])

                by_hour: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = {}
                hour_faults: List[Dict[str, Any]] = []
                prev_valid: Optional[Dict[str, Any]] = None
                for ts, rec in parsed_pts:
                    cleaned, pt_faults = clean_upstream_point({**rec, "SHIJIAN": rec.get("tmDate")}, meta, ts, prev_valid=prev_valid)
                    if cleaned["value_source"] == SRC_REAL and cleaned["temp_clean"] is not None:
                        prev_valid = cleaned
                    bh = floor_to_hour(ts)
                    by_hour.setdefault(bh, []).append((ts, cleaned))
                    if day_start <= bh <= max_hour and (target_hour_set is None or bh in target_hour_set):
                        for flt in pt_faults:
                            hour_faults.append({**flt, "biz_hour": bh})

                real_rows: List[Dict[str, Any]] = []
                for bh, pts in sorted(by_hour.items()):
                    if not (day_start <= bh <= max_hour):
                        continue
                    if target_hour_set is not None and bh not in target_hour_set:
                        continue
                    latest = pts[-1][1]
                    heat_raw_samples = [(ts, c["heat_raw"]) for ts, c in pts]
                    heat_samples = [(ts, c["heat_clean"]) for ts, c in pts]
                    flow_samples = [(ts, c["flow_clean"]) for ts, c in pts]
                    real_rows.append({
                        "biz_hour": bh,
                        "point_id": latest["point_id"],
                        "data_zone": dz,
                        "source_name": sname,
                        "display_name": latest["display_name"],
                        "category": latest["category"],
                        "sub_category": latest["sub_category"],
                        "is_core_gk": latest["point_id"] is not None,
                        "sample_count": len(pts),
                        "source_time": latest["source_time"],
                        "temp_raw": latest["temp_raw"],
                        "temp_clean": latest["temp_clean"],
                        "pressure_raw": latest["pressure_raw"],
                        "pressure_clean": latest["pressure_clean"],
                        "flow_raw": latest["flow_raw"],
                        "flow_clean": latest["flow_clean"],
                        "heat_raw": latest["heat_raw"],
                        "heat_clean": latest["heat_clean"],
                        "hour_heat_raw_gj": trapezoidal_hour_integral(heat_raw_samples),
                        "hour_heat_gj": trapezoidal_hour_integral(heat_samples),
                        "hour_flow_t": trapezoidal_hour_integral(flow_samples),
                        "value_source": latest["value_source"],
                        "fault_tag": latest["fault_tag"],
                    })

                empty_rows: List[Dict[str, Any]] = []
                for bh in expected_completed_hours:
                    if bh in by_hour:
                        continue
                    empty_rows.append({
                        "biz_hour": bh,
                        "point_id": meta["point_id"],
                        "data_zone": dz,
                        "source_name": sname,
                        "display_name": meta["name"],
                        "category": meta["category"],
                        "sub_category": meta["sub_category"],
                        "is_core_gk": meta["point_id"] is not None,
                        "sample_count": 0,
                        "source_time": None,
                        "temp_raw": None,
                        "temp_clean": None,
                        "pressure_raw": None,
                        "pressure_clean": None,
                        "flow_raw": None,
                        "flow_clean": None,
                        "heat_raw": None,
                        "heat_clean": None,
                        "hour_heat_raw_gj": None,
                        "hour_heat_gj": None,
                        "hour_flow_t": None,
                        "value_source": SRC_SOURCE_EMPTY,
                        "fault_tag": None,
                    })
                return f"{dz}:{sname}", real_rows, empty_rows, hour_faults, True

            failed_points: List[str] = []
            all_real_rows: List[Dict[str, Any]] = []
            all_empty_rows: List[Dict[str, Any]] = []
            all_upstream_faults: List[Dict[str, Any]] = []
            workers = max(1, min(max_workers, len(tasks) or 1))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_fetch_one_upstream, t) for t in tasks]
                total_futs = len(futures)
                for idx_done, fut in enumerate(as_completed(futures), 1):
                    pt_key, real_out, empty_out, faults_out, ok_flag = fut.result()
                    if progress_cb is not None:
                        progress_cb(idx_done, total_futs, pt_key)
                    if not ok_flag:
                        failed_points.append(pt_key)
                    if real_out:
                        all_real_rows.extend(real_out)
                    if empty_out:
                        all_empty_rows.extend(empty_out)
                    if faults_out:
                        all_upstream_faults.extend(faults_out)

            upstream_cols = [
                "biz_hour", "point_id", "data_zone", "source_name", "display_name", "category", "sub_category",
                "is_core_gk", "sample_count", "source_time", "temp_raw", "temp_clean", "pressure_raw",
                "pressure_clean", "flow_raw", "flow_clean", "heat_raw", "heat_clean", "hour_heat_raw_gj", "hour_heat_gj",
                "hour_flow_t", "value_source", "fault_tag",
            ]
            upstream_update_cols = [
                "point_id", "display_name", "category", "sub_category", "is_core_gk", "sample_count",
                "source_time", "temp_raw", "temp_clean", "pressure_raw", "pressure_clean", "flow_raw",
                "flow_clean", "heat_raw", "heat_clean", "hour_heat_raw_gj", "hour_heat_gj", "hour_flow_t", "value_source", "fault_tag",
            ]
            if all_real_rows or all_empty_rows:
                with engine.begin() as conn:
                    for offset in range(0, len(all_real_rows), 500):
                        _upsert_batch(
                            conn,
                            "fact_upstream_hourly",
                            upstream_cols,
                            ["biz_hour", "data_zone", "source_name"],
                            upstream_update_cols,
                            all_real_rows[offset:offset + 500],
                            extra_set_clauses=["updated_at = NOW()"],
                        )
                    for offset in range(0, len(all_empty_rows), 500):
                        _upsert_batch(
                            conn,
                            "fact_upstream_hourly",
                            upstream_cols,
                            ["biz_hour", "data_zone", "source_name"],
                            [],
                            all_empty_rows[offset:offset + 500],
                            do_nothing_on_conflict=True,
                        )
                    if all_upstream_faults:
                        dedup_up_faults: Dict[Tuple[datetime, str, str, str], Dict[str, Any]] = {}
                        for flt in all_upstream_faults:
                            dedup_up_faults[(flt["biz_hour"], flt["entity_type"], flt["entity_id"], flt["fault_code"])] = flt
                        _upsert_batch(
                            conn,
                            "fact_fault_ticket",
                            [
                                "biz_hour", "entity_type", "entity_id", "entity_name", "fault_code",
                                "owner_party", "raw_value_text", "clean_strategy", "rule_desc",
                            ],
                            ["biz_hour", "entity_type", "entity_id", "fault_code"],
                            ["entity_name", "owner_party", "raw_value_text", "clean_strategy", "rule_desc"],
                            list(dedup_up_faults.values()),
                            extra_set_clauses=["updated_at = NOW()"],
                        )

            summary = {
                "target_date": target_d.isoformat(),
                "points_total": len(tasks),
                "updated_upstream_hours": len(all_real_rows),
                "empty_upstream_hours": len(all_empty_rows),
                "failed_points": sorted(failed_points)[:20],
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS" if not failed_points else "PARTIAL", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("上游电厂/首站小时历史补采异常: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise


def _extract_covered_hours(
    rows: Sequence[Any],
    min_ratio: float,
    floor_if_populated: int,
    fallback_min_if_sparse: int = 1,
) -> set[datetime]:
    """根据每小时已入库主体数识别真正完整覆盖的整点（同时剔除仅部分写入的半残缺整点）。"""
    counts: Dict[datetime, int] = {}
    for r in rows:
        bh = _to_east8_hour(getattr(r, "biz_hour", None))
        if bh is None:
            continue
        cnt = int(getattr(r, "cnt", 1) or 0)
        if cnt > 0:
            counts[bh] = max(counts.get(bh, 0), cnt)
    if not counts:
        return set()
    peak = max(counts.values())
    threshold = max(fallback_min_if_sparse, int(peak * min_ratio)) if peak >= floor_if_populated else 1
    return {bh for bh, cnt in counts.items() if cnt >= threshold}


def _is_slot_cooled_down(track: str, slot_key: str, ref_time: datetime) -> bool:
    """判断因源站历史空白而暂时不可补齐的时段是否仍处于冷却期内。"""
    with _GAP_STATE_LOCK:
        until = _GAP_COOLDOWN_UNTIL.get((track, slot_key))
        if until is None:
            return False
        if until <= ref_time:
            _GAP_COOLDOWN_UNTIL.pop((track, slot_key), None)
            return False
        return True


def detect_data_gaps(
    start_date_str: Optional[str] = None,
    reference_time: Optional[datetime] = None,
    include_empty_baseline: bool = False,
    respect_cooldown: bool = False,
) -> Dict[str, Any]:
    """
    只读巡检停机真空期与历史遗留缺口：
    从全库最早建表小时（或在最大回溯天数 1~365 内，默认 180 天覆盖全供暖季）起，
    逐一对比直至最新已完成整点，精准识别 0 条缺失与半残缺（未定格/覆盖率不足）整点，
    以及 `fact_merchant_daily` 缺失日期。
    """
    ensure_smart_heating_fact_tables()
    cfg = _read_raw_config()
    raw_start = str(start_date_str or cfg.get("gap_recovery_start_date") or DEFAULT_GAP_RECOVERY_START_DATE).strip()
    start_d = date.fromisoformat(raw_start)
    now_e8 = (reference_time or datetime.now(EAST_8)).astimezone(EAST_8)
    latest_completed_hour = floor_to_hour(now_e8) - timedelta(hours=1)
    scan_start = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=EAST_8)

    with engine.connect() as conn:
        bounds = []
        for tbl_sql in (
            "SELECT MIN(biz_hour) AS min_h, MAX(biz_hour) AS max_h FROM smart_heating_platform.fact_station_hourly",
            "SELECT MIN(biz_hour) AS min_h, MAX(biz_hour) AS max_h FROM smart_heating_platform.fact_upstream_hourly WHERE hour_heat_gj IS NOT NULL OR value_source = 'SOURCE_EMPTY'",
            "SELECT MIN(biz_hour) AS min_h, MAX(biz_hour) AS max_h FROM smart_heating_platform.fact_merchant_hourly WHERE hour_heat_gj IS NOT NULL OR value_source = 'SOURCE_EMPTY'",
        ):
            row = conn.execute(text(tbl_sql)).fetchone()
            min_h = _to_east8_hour(row.min_h) if row and row.min_h is not None else None
            max_h = _to_east8_hour(row.max_h) if row and row.max_h is not None else None
            if min_h is not None:
                bounds.append((min_h, max_h))

        platform_earliest = min((b[0] for b in bounds), default=None)
        platform_latest = max((b[1] for b in bounds if b[1] is not None), default=None)

        if platform_earliest is None and not include_empty_baseline:
            return {
                "has_gaps": False,
                "empty_baseline": True,
                "start_date": start_d.isoformat(),
                "scan_start": None,
                "latest_completed_hour": latest_completed_hour.strftime("%Y-%m-%d %H:00"),
                "platform_latest_hour": None,
                "missing_dates": [],
                "total_missing_track_hours": 0,
                "tracks": {
                    "stations": {"missing_count": 0, "missing_hours": []},
                    "upstream": {"missing_count": 0, "missing_hours": []},
                    "merchant_hourly": {"missing_count": 0, "missing_hours": []},
                    "merchant_daily": {"missing_count": 0, "missing_dates": []},
                },
                "_raw": {"stations": [], "upstream": [], "merchant_hourly": [], "merchant_daily": []},
            }

        if scan_start > latest_completed_hour:
            expected_hours: List[datetime] = []
        else:
            expected_hours = []
            cur = scan_start
            while cur <= latest_completed_hour:
                expected_hours.append(cur)
                cur += timedelta(hours=1)

        if expected_hours:
            st_rows = conn.execute(
                text(
                    "SELECT biz_hour, COUNT(*) AS cnt FROM smart_heating_platform.fact_station_hourly "
                    "WHERE biz_hour >= :s AND biz_hour <= :e GROUP BY biz_hour"
                ),
                {"s": scan_start, "e": latest_completed_hour},
            ).fetchall()
            up_rows = conn.execute(
                text(
                    "SELECT biz_hour, COUNT(*) AS cnt FROM smart_heating_platform.fact_upstream_hourly "
                    "WHERE biz_hour >= :s AND biz_hour <= :e "
                    "AND (hour_heat_gj IS NOT NULL OR value_source = 'SOURCE_EMPTY') "
                    "GROUP BY biz_hour HAVING COUNT(*) > 0"
                ),
                {"s": scan_start, "e": latest_completed_hour},
            ).fetchall()
            mh_rows = conn.execute(
                text(
                    "SELECT biz_hour, COUNT(*) AS cnt FROM smart_heating_platform.fact_merchant_hourly "
                    "WHERE biz_hour >= :s AND biz_hour <= :e "
                    "AND (hour_heat_gj IS NOT NULL OR value_source = 'SOURCE_EMPTY') "
                    "GROUP BY biz_hour HAVING COUNT(*) > 0"
                ),
                {"s": scan_start, "e": latest_completed_hour},
            ).fetchall()

            st_covered = _extract_covered_hours(st_rows, min_ratio=0.5, floor_if_populated=20, fallback_min_if_sparse=50)
            up_covered = _extract_covered_hours(up_rows, min_ratio=0.05, floor_if_populated=20, fallback_min_if_sparse=5)
            mh_covered = _extract_covered_hours(mh_rows, min_ratio=0.6, floor_if_populated=50, fallback_min_if_sparse=100)

            st_missing = [
                h for h in expected_hours
                if h not in st_covered and not (respect_cooldown and _is_slot_cooled_down("stations", h.strftime("%Y-%m-%d %H:00"), now_e8))
            ]
            up_missing = [
                h for h in expected_hours
                if h not in up_covered and not (respect_cooldown and _is_slot_cooled_down("upstream", h.strftime("%Y-%m-%d %H:00"), now_e8))
            ]
            mh_missing = [
                h for h in expected_hours
                if h not in mh_covered and not (respect_cooldown and _is_slot_cooled_down("merchant_hourly", h.strftime("%Y-%m-%d %H:00"), now_e8))
            ]
        else:
            st_missing, up_missing, mh_missing = [], [], []

        expected_end_date = now_e8.date() - timedelta(days=1 if now_e8.hour >= 9 else 2)
        expected_start_date = scan_start.date()
        md_missing: List[date] = []
        if expected_start_date <= expected_end_date:
            md_rows = conn.execute(
                text(
                    "SELECT DISTINCT biz_date FROM smart_heating_platform.fact_merchant_daily "
                    "WHERE biz_date >= :ds AND biz_date <= :de"
                ),
                {"ds": expected_start_date, "de": expected_end_date},
            ).fetchall()
            md_covered = {
                r.biz_date if isinstance(r.biz_date, date) and not isinstance(r.biz_date, datetime) else r.biz_date.date()
                for r in md_rows
                if r.biz_date is not None
            }
            cur_d = expected_start_date
            while cur_d <= expected_end_date:
                if cur_d not in md_covered and not (
                    respect_cooldown and _is_slot_cooled_down("merchant_daily", cur_d.isoformat(), now_e8)
                ):
                    md_missing.append(cur_d)
                cur_d += timedelta(days=1)

    all_missing_dates = sorted(
        {h.date().isoformat() for h in (*st_missing, *up_missing, *mh_missing)}
        | {d.isoformat() for d in md_missing}
    )
    has_gaps = bool(st_missing or up_missing or mh_missing or md_missing)

    return {
        "has_gaps": has_gaps,
        "empty_baseline": platform_earliest is None,
        "start_date": start_d.isoformat(),
        "scan_start": scan_start.strftime("%Y-%m-%d %H:00") if expected_hours else None,
        "latest_completed_hour": latest_completed_hour.strftime("%Y-%m-%d %H:00"),
        "platform_latest_hour": platform_latest.strftime("%Y-%m-%d %H:00") if platform_latest else None,
        "missing_dates": all_missing_dates,
        "total_missing_track_hours": len(st_missing) + len(up_missing) + len(mh_missing),
        "tracks": {
            "stations": {
                "missing_count": len(st_missing),
                "missing_hours": [h.strftime("%Y-%m-%d %H:00") for h in st_missing],
            },
            "upstream": {
                "missing_count": len(up_missing),
                "missing_hours": [h.strftime("%Y-%m-%d %H:00") for h in up_missing],
            },
            "merchant_hourly": {
                "missing_count": len(mh_missing),
                "missing_hours": [h.strftime("%Y-%m-%d %H:00") for h in mh_missing],
            },
            "merchant_daily": {
                "missing_count": len(md_missing),
                "missing_dates": [d.isoformat() for d in md_missing],
            },
        },
        "_raw": {
            "stations": st_missing,
            "upstream": up_missing,
            "merchant_hourly": mh_missing,
            "merchant_daily": md_missing,
        },
    }


def get_gap_recovery_status(start_date_str: Optional[str] = None) -> Dict[str, Any]:
    """查询当前真空期状态、后台补采实时步进心跳及最近 `GAP_RECOVERY` 执行历史。"""
    gaps = detect_data_gaps(start_date_str=start_date_str)
    public_gaps = {k: v for k, v in gaps.items() if k != "_raw"}
    with _GAP_STATE_LOCK:
        runtime = {
            **{k: v for k, v in _GAP_RUNTIME_STATE.items() if k not in ("recovered_counts", "recent_logs", "errors")},
            "recovered_counts": dict(_GAP_RUNTIME_STATE.get("recovered_counts") or {}),
            "recent_logs": list(_GAP_RUNTIME_STATE.get("recent_logs") or []),
            "errors": list(_GAP_RUNTIME_STATE.get("errors") or []),
        }

    now_e8 = datetime.now(EAST_8)
    elapsed_seconds: Optional[int] = None
    heartbeat_age_seconds: Optional[int] = None
    if runtime.get("started_at"):
        st_dt = parse_dt_east8(runtime["started_at"])
        if st_dt is not None:
            end_ref = (
                parse_dt_east8(runtime["finished_at"])
                if (not runtime.get("running") and runtime.get("finished_at"))
                else now_e8
            ) or now_e8
            elapsed_seconds = max(0, int((end_ref - st_dt).total_seconds()))
    if runtime.get("last_heartbeat_at"):
        hb_dt = parse_dt_east8(runtime["last_heartbeat_at"])
        if hb_dt is not None:
            heartbeat_age_seconds = max(0, int((now_e8 - hb_dt).total_seconds()))

    recent_runs: List[Dict[str, Any]] = []
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT run_id, started_at, finished_at, duration_ms, status, summary_json, error_message "
                "FROM smart_heating_platform.fact_collector_run "
                "WHERE run_type = 'GAP_RECOVERY' "
                "ORDER BY run_id DESC LIMIT 5"
            )
        ).fetchall()
        for row in rows:
            recent_runs.append({
                "run_id": row.run_id,
                "started_at": row.started_at.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S") if row.started_at else None,
                "finished_at": row.finished_at.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S") if row.finished_at else None,
                "duration_ms": row.duration_ms,
                "status": row.status,
                "summary": row.summary_json,
                "error_message": row.error_message,
            })

    return {
        **public_gaps,
        "running": runtime["running"],
        "running_started_at": runtime["started_at"],
        "running_finished_at": runtime["finished_at"],
        "running_trigger": runtime["trigger"],
        "last_heartbeat_at": runtime["last_heartbeat_at"],
        "elapsed_seconds": elapsed_seconds,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "current_step_index": runtime["current_step_index"],
        "total_steps": runtime["total_steps"],
        "current_date": runtime["current_date"],
        "current_track": runtime["current_track"],
        "current_step_label": runtime["current_step_label"],
        "sub_done": runtime["sub_done"],
        "sub_total": runtime["sub_total"],
        "sub_item": runtime["sub_item"],
        "recovered_counts": runtime["recovered_counts"],
        "recent_logs": runtime["recent_logs"],
        "runtime_errors": runtime["errors"],
        "last_recovery_run": recent_runs[0] if recent_runs else None,
        "recent_recovery_runs": recent_runs,
    }


def run_gap_recovery(
    start_date_str: Optional[str] = None,
    trigger: str = "AUTO",
    include_empty_baseline: bool = False,
) -> Dict[str, Any]:
    """
    自动/手动补足停机真空期历史数据：
    从起始日期（默认 `2026-11-01`）起按缺失日期与缺失小时精准调起换热站表底校准、
    上游电厂/首站历史积分、商业用户 5 分钟历史积分，以及（Cookie 有效时）商业日耗补采。
    全程实时上报当前步进、主体进度与最近心跳时间，便于前端观测是否正常运行。
    """
    ensure_smart_heating_fact_tables()
    if not _GAP_RECOVERY_LOCK.acquire(blocking=False):
        return {"ok": True, "already_running": True, "has_gaps": True, "message": "真空期自动补采已在运行中"}

    run_id: Optional[int] = None
    started_perf = time.perf_counter()
    try:
        is_manual = trigger == "MANUAL"
        if is_manual:
            with _GAP_STATE_LOCK:
                _GAP_COOLDOWN_UNTIL.clear()

        gap_info = detect_data_gaps(
            start_date_str=start_date_str,
            include_empty_baseline=include_empty_baseline,
            respect_cooldown=not is_manual,
        )
        if not gap_info["has_gaps"]:
            return {
                "ok": True,
                "has_gaps": False,
                "empty_baseline": gap_info["empty_baseline"],
                "recovered_station_hours": 0,
                "recovered_upstream_hours": 0,
                "recovered_merchant_hours": 0,
                "recovered_merchant_daily_days": 0,
                "remaining_missing_hours": 0,
            }

        cfg = _read_raw_config()
        now_e8 = datetime.now(EAST_8)
        raw = gap_info["_raw"]
        st_by_date = _group_hours_by_date(raw["stations"])
        up_by_date = _group_hours_by_date(raw["upstream"])
        mh_by_date = _group_hours_by_date(raw["merchant_hourly"])
        md_dates = sorted({d.isoformat() for d in raw["merchant_daily"]})
        has_cookie = bool(normalize_cookie_input(str(cfg.get("cookie") or "")))

        step_plan: List[Tuple[str, str, str]] = []
        for d_str in gap_info["missing_dates"]:
            if d_str in st_by_date:
                step_plan.append(("stations", d_str, f"换热站表底校准 {d_str}（缺失 {len(st_by_date[d_str])} 时）"))
            if d_str in up_by_date:
                step_plan.append(("upstream", d_str, f"上游电厂/首站积分 {d_str}（缺失 {len(up_by_date[d_str])} 时）"))
            if d_str in mh_by_date:
                step_plan.append(("merchant_hourly", d_str, f"商业用户小时积分 {d_str}（缺失 {len(mh_by_date[d_str])} 时）"))
        if has_cookie:
            for d_str in md_dates:
                step_plan.append(("merchant_daily", d_str, f"商业用户每日耗量 {d_str}"))

        with _GAP_STATE_LOCK:
            _GAP_RUNTIME_STATE.update({
                "running": True,
                "started_at": now_e8.strftime("%Y-%m-%d %H:%M:%S"),
                "finished_at": None,
                "last_heartbeat_at": now_e8.strftime("%Y-%m-%d %H:%M:%S"),
                "trigger": trigger,
                "current_step_index": 0,
                "total_steps": len(step_plan),
                "current_date": None,
                "current_track": None,
                "current_step_label": "正在初始化补采计划…",
                "sub_done": 0,
                "sub_total": 0,
                "sub_item": "",
                "recovered_counts": {
                    "station_hours": 0,
                    "upstream_hours": 0,
                    "merchant_hours": 0,
                    "merchant_daily_days": 0,
                },
                "recent_logs": [],
                "errors": [],
            })

        _append_gap_log(
            "info",
            f"启动真空期补采 ({trigger})：共 {len(step_plan)} 个步骤（涉及 {len(gap_info['missing_dates'])} 天，"
            f"站缺 {len(raw['stations'])} 时 · 上游缺 {len(raw['upstream'])} 时 · 商业缺 {len(raw['merchant_hourly'])} 时）",
        )

        run_id = _insert_run_log(floor_to_hour(now_e8), "GAP_RECOVERY", cfg.get("source_mode", "public"))
        recovered_st = 0
        recovered_up = 0
        recovered_mh = 0
        recovered_md = 0
        track_errors: List[str] = []

        logger.info(
            "开始执行停机真空期补采 (%s)：缺失日期=%s, 站缺=%d时, 上游缺=%d时, 商户缺=%d时, 商日缺=%d天",
            trigger,
            gap_info["missing_dates"],
            len(raw["stations"]),
            len(raw["upstream"]),
            len(raw["merchant_hourly"]),
            len(md_dates),
        )

        def _make_sub_progress_cb(step_label: str) -> Callable[[int, int, str], None]:
            def _cb(done_n: int, total_n: int, item_name: str) -> None:
                _update_gap_progress(
                    sub_done=done_n,
                    sub_total=total_n,
                    sub_item=item_name,
                    current_step_label=f"{step_label} · 已完成 {done_n}/{total_n}（{item_name}）",
                )
            return _cb

        for step_idx, (track, d_str, step_label) in enumerate(step_plan, 1):
            _update_gap_progress(
                current_step_index=step_idx,
                current_date=d_str,
                current_track=track,
                current_step_label=step_label,
                sub_done=0,
                sub_total=0,
                sub_item="",
            )
            _append_gap_log("info", f"[{step_idx}/{len(step_plan)}] 开始：{step_label}")
            try:
                if track == "stations":
                    res = run_table_bottom_calibration(
                        target_date_str=d_str,
                        target_hours=st_by_date[d_str],
                        trigger=trigger,
                        progress_cb=_make_sub_progress_cb(step_label),
                    )
                    delta_cnt = int(res.get("updated_station_hours") or 0)
                    recovered_st += delta_cnt
                    _append_gap_log("success", f"[{step_idx}/{len(step_plan)}] 完成：换热站 {d_str} 入库 {delta_cnt} 站·小时")
                elif track == "upstream":
                    res = run_upstream_hourly_backfill(
                        target_date_str=d_str,
                        target_hours=up_by_date[d_str],
                        trigger=trigger,
                        progress_cb=_make_sub_progress_cb(step_label),
                    )
                    delta_cnt = int(res.get("updated_upstream_hours") or 0)
                    recovered_up += delta_cnt
                    _append_gap_log("success", f"[{step_idx}/{len(step_plan)}] 完成：上游 {d_str} 入库 {delta_cnt} 点·小时")
                elif track == "merchant_hourly":
                    res = run_merchant_hourly_backfill(
                        target_date_str=d_str,
                        target_hours=mh_by_date[d_str],
                        trigger=trigger,
                        progress_cb=_make_sub_progress_cb(step_label),
                    )
                    delta_cnt = int(res.get("updated_merchant_hours") or 0)
                    recovered_mh += delta_cnt
                    _append_gap_log("success", f"[{step_idx}/{len(step_plan)}] 完成：商业小时 {d_str} 入库 {delta_cnt} 户·小时")
                elif track == "merchant_daily":
                    res = run_merchant_daily_cycle(target_date_str=d_str, trigger=trigger)
                    if res.get("ok") and not res.get("skipped"):
                        recovered_md += 1
                    _append_gap_log("success", f"[{step_idx}/{len(step_plan)}] 完成：商业日报 {d_str}")

                _update_gap_progress(
                    recovered_counts={
                        "station_hours": recovered_st,
                        "upstream_hours": recovered_up,
                        "merchant_hours": recovered_mh,
                        "merchant_daily_days": recovered_md,
                    }
                )
            except Exception as exc:
                err_msg = f"{track}@{d_str}: {exc}"
                track_errors.append(err_msg)
                _append_gap_log("error", f"[{step_idx}/{len(step_plan)}] 异常：{err_msg}")
                _update_gap_progress(errors=list(track_errors[:20]))

        after_gaps = detect_data_gaps(start_date_str=gap_info["start_date"], include_empty_baseline=include_empty_baseline)
        # 对本次无网络异常但源站仍无数据可补的历史时段记入 24 小时冷却，避免自动巡检死循环
        err_tags = {e.split(":")[0] for e in track_errors}
        cooldown_deadline = datetime.now(EAST_8) + timedelta(hours=24)
        with _GAP_STATE_LOCK:
            for trk, field in (("stations", "missing_hours"), ("upstream", "missing_hours"), ("merchant_hourly", "missing_hours")):
                attempted = {h.strftime("%Y-%m-%d %H:00") for h in raw[trk]}
                still_missing = set(after_gaps["tracks"][trk][field])
                for sk in attempted & still_missing:
                    d_part = sk[:10]
                    if f"{trk}@{d_part}" not in err_tags:
                        _GAP_COOLDOWN_UNTIL[(trk, sk)] = cooldown_deadline
            if has_cookie:
                attempted_md = {d.isoformat() for d in raw["merchant_daily"]}
                still_md = set(after_gaps["tracks"]["merchant_daily"]["missing_dates"])
                for dk in attempted_md & still_md:
                    if f"merchant_daily@{dk}" not in err_tags:
                        _GAP_COOLDOWN_UNTIL[("merchant_daily", dk)] = cooldown_deadline

        summary = {
            "trigger": trigger,
            "start_date": gap_info["start_date"],
            "target_dates": gap_info["missing_dates"],
            "recovered_station_hours": recovered_st,
            "recovered_upstream_hours": recovered_up,
            "recovered_merchant_hours": recovered_mh,
            "recovered_merchant_daily_days": recovered_md,
            "remaining_missing_hours": after_gaps["total_missing_track_hours"],
            "remaining_missing_dates": after_gaps["missing_dates"],
            "cookie_configured": has_cookie,
            "errors": track_errors[:20],
        }
        status = "SUCCESS" if not track_errors else "PARTIAL"
        _append_gap_log(
            "success" if status == "SUCCESS" else "warn",
            f"真空期补采结束（{status}）：站 +{recovered_st}、上游 +{recovered_up}、商业 +{recovered_mh}、日耗 +{recovered_md} 天，剩余未补 {after_gaps['total_missing_track_hours']} 时",
        )
        _finish_run_log(run_id, started_perf, status, has_cookie if md_dates else None, summary)
        return {"ok": True, "run_id": run_id, "has_gaps": after_gaps["has_gaps"], **summary}
    except Exception as exc:
        logger.exception("停机真空期补采执行异常: %s", exc)
        _append_gap_log("error", f"真空期补采中断：{exc}")
        if run_id is not None:
            _finish_run_log(run_id, started_perf, "FAILED", None, {"trigger": trigger}, error_message=str(exc))
        raise
    finally:
        with _GAP_STATE_LOCK:
            _GAP_RUNTIME_STATE.update({
                "running": False,
                "finished_at": datetime.now(EAST_8).strftime("%Y-%m-%d %H:%M:%S"),
                "current_step_label": "补采流程已结束",
                "sub_item": "",
            })
        _GAP_RECOVERY_LOCK.release()


_HEAT_AUDIT_LOCK = threading.RLock()


def run_daily_heat_audit_and_fix(
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    lookback_days: Optional[int] = None,
    trigger: str = "AUTO_DAILY_AUDIT",
) -> Dict[str, Any]:
    """
    每日定时（默认 00:00）或手动触发历史热量异常回看检测与修正：
    1. 忠实保留 `hour_heat_raw_gj` 原始值；
    2. 对超过按供暖面积核定极限、表底倍率异常（南山苑/经典A/联通公司/恒元公寓）或瞬时负荷严重背离的站-日，
       自动回溯重算并将 `hour_heat_gj` 更新为修正值；若源站已过保留期则就地兜底清洗；
    3. 同步拦截并留痕上游 `fact_upstream_hourly` 中累计量误当小时值或超限热源点；
    4. 所有修正记录同步写入 `fact_fault_ticket`（供“异常数据监测”页核查与督办）。
    """
    ensure_smart_heating_fact_tables()
    with _HEAT_AUDIT_LOCK:
        started_perf = time.perf_counter()
        cfg = _read_raw_config()
        now_e8 = datetime.now(EAST_8)
        end_d = date.fromisoformat(end_date_str) if end_date_str else now_e8.date()
        if start_date_str:
            start_d = date.fromisoformat(start_date_str)
        else:
            lb = max(1, int(lookback_days or cfg.get("heat_audit_lookback_days", 3)))
            start_d = end_d - timedelta(days=lb - 1)
        if start_d > end_d:
            start_d, end_d = end_d, start_d

        win_start = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=EAST_8)
        win_end = datetime(end_d.year, end_d.month, end_d.day, 0, 0, 0, tzinfo=EAST_8) + timedelta(days=1)
        run_id = _insert_run_log(
            datetime(end_d.year, end_d.month, end_d.day, 0, 0, 0, tzinfo=EAST_8),
            "HEAT_AUDIT_FIX",
            cfg.get("source_mode", "public"),
        )

        fixed_station_hours = 0
        fixed_upstream_hours = 0
        fault_tickets: List[Dict[str, Any]] = []
        recalib_days: Dict[str, set[str]] = {}

        try:
            with engine.begin() as conn:
                # 1. 先确保窗口内已有小时记录的 hour_heat_raw_gj 忠实保留原值
                conn.execute(
                    text(
                        "UPDATE smart_heating_platform.fact_station_hourly "
                        "SET hour_heat_raw_gj = hour_heat_gj "
                        "WHERE biz_hour >= :ws AND biz_hour < :we "
                        "AND hour_heat_raw_gj IS NULL AND hour_heat_gj IS NOT NULL"
                    ),
                    {"ws": win_start, "we": win_end},
                )
                conn.execute(
                    text(
                        "UPDATE smart_heating_platform.fact_upstream_hourly "
                        "SET hour_heat_raw_gj = hour_heat_gj "
                        "WHERE biz_hour >= :ws AND biz_hour < :we "
                        "AND hour_heat_raw_gj IS NULL AND hour_heat_gj IS NOT NULL"
                    ),
                    {"ws": win_start, "we": win_end},
                )

                # 2. 扫描换热站异常小时记录，按 (日期, 站点) 归集重算任务
                st_rows = conn.execute(
                    text(
                        "SELECT f.id, f.biz_hour, f.station_id, d.name, d.covered_area, "
                        "f.e11_raw, f.e11_clean, f.hour_heat_raw_gj, f.hour_heat_gj, f.hour_heat_source "
                        "FROM smart_heating_platform.fact_station_hourly f "
                        "JOIN smart_heating_platform.dict_heating_station d ON f.station_id = d.station_id "
                        "WHERE f.biz_hour >= :ws AND f.biz_hour < :we"
                    ),
                    {"ws": win_start, "we": win_end},
                ).fetchall()

                for r in st_rows:
                    bh_e8 = _to_east8_hour(r.biz_hour)
                    if bh_e8 is None:
                        continue
                    d_str = bh_e8.date().isoformat()
                    max_lim = station_max_hourly_heat_gj(float(r.covered_area) if r.covered_area is not None else None)
                    hr_val = float(r.hour_heat_gj) if r.hour_heat_gj is not None else None
                    raw_val = float(r.hour_heat_raw_gj) if r.hour_heat_raw_gj is not None else hr_val
                    e11_val = float(r.e11_clean) if r.e11_clean is not None else None

                    need_fix = False
                    if hr_val is not None and (hr_val < 0.0 or hr_val > max_lim * 1.5):
                        need_fix = True
                    elif e11_val is not None and (e11_val < 0.0 or e11_val > max_lim * 1.5):
                        need_fix = True
                    elif (
                        hr_val is not None
                        and e11_val is not None
                        and e11_val > 1.0
                        and r.hour_heat_source == SRC_METER_DIFF
                        and hr_val > max(max_lim * 0.8, e11_val * 4.0)
                    ):
                        need_fix = True
                    elif r.name in STATION_METER_SCALE_FACTORS and hr_val is not None and hr_val > 0.0:
                        factor, _ = STATION_METER_SCALE_FACTORS[r.name]
                        if factor < 1.0 and raw_val is not None and abs(hr_val - raw_val) < 0.01 and (
                            (e11_val is not None and e11_val > 0.5 and hr_val > e11_val * 3.0)
                            or hr_val > max_lim * 0.5
                        ):
                            need_fix = True
                        elif factor > 1.0 and raw_val is not None and abs(hr_val - raw_val) < 0.01 and e11_val is not None and e11_val > 0.5 and hr_val < e11_val * 0.5:
                            need_fix = True

                    if need_fix:
                        recalib_days.setdefault(d_str, set()).add(str(r.name))

            # 3. 对异常 (日期, 站点) 优先回溯源站 /hrz_ls_zb/ 重跑校准清洗
            for d_str in sorted(recalib_days):
                st_list = sorted(recalib_days[d_str])
                res_cal = run_table_bottom_calibration(
                    target_date_str=d_str,
                    station_names=st_list,
                    trigger=trigger,
                )
                fixed_station_hours += int(res_cal.get("updated_station_hours") or 0)

            # 4. 二次复核：若因源站过期等原因库内仍有越限或未折算记录，则就地修正并记入督办台账
            with engine.begin() as conn:
                still_rows = conn.execute(
                    text(
                        "SELECT f.id, f.biz_hour, f.station_id, d.name, d.covered_area, "
                        "f.e11_raw, f.e11_clean, f.hour_heat_raw_gj, f.hour_heat_gj, f.hour_heat_source, f.fault_tag "
                        "FROM smart_heating_platform.fact_station_hourly f "
                        "JOIN smart_heating_platform.dict_heating_station d ON f.station_id = d.station_id "
                        "WHERE f.biz_hour >= :ws AND f.biz_hour < :we"
                    ),
                    {"ws": win_start, "we": win_end},
                ).fetchall()

                for r in still_rows:
                    max_lim = station_max_hourly_heat_gj(float(r.covered_area) if r.covered_area is not None else None)
                    hr_val = float(r.hour_heat_gj) if r.hour_heat_gj is not None else None
                    raw_val = float(r.hour_heat_raw_gj) if r.hour_heat_raw_gj is not None else hr_val
                    e11_val = float(r.e11_clean) if r.e11_clean is not None else None
                    if hr_val is None and e11_val is None:
                        continue

                    changed = False
                    new_hr = hr_val
                    new_e11 = e11_val
                    tags = [t for t in str(r.fault_tag or "").split(",") if t]

                    if new_e11 is not None and (new_e11 < 0.0 or new_e11 > max_lim * 1.5):
                        fault_tickets.append({
                            "biz_hour": r.biz_hour,
                            "entity_type": "STATION",
                            "entity_id": r.station_id,
                            "entity_name": r.name,
                            "fault_code": FAULT_SENSOR_RANGE,
                            "owner_party": OWNER_RESEARCH,
                            "raw_value_text": f"一网瞬时热量={new_e11} GJ/h (物理上限={max_lim * 1.5:.1f} GJ/h)",
                            "clean_strategy": "回看复核置空越限瞬时热量并保留 e11_raw",
                            "rule_desc": "单站一次网瞬时热量 <0 或超过按面积核定极限热负荷 1.5 倍",
                        })
                        new_e11 = None
                        tags.append(FAULT_SENSOR_RANGE)
                        changed = True

                    if r.name in STATION_METER_SCALE_FACTORS and new_hr is not None and new_hr > 0.0:
                        factor, scale_note = STATION_METER_SCALE_FACTORS[r.name]
                        if raw_val is not None and abs(new_hr - raw_val) < 0.01 and (
                            (factor < 1.0 and ((new_e11 is not None and new_e11 > 0.5 and new_hr > new_e11 * 3.0) or new_hr > max_lim * 0.5))
                            or (factor > 1.0 and new_e11 is not None and new_e11 > 0.5 and new_hr < new_e11 * 0.5)
                        ):
                            new_hr = round(raw_val * factor, 4)
                            fault_tickets.append({
                                "biz_hour": r.biz_hour,
                                "entity_type": "STATION",
                                "entity_id": r.station_id,
                                "entity_name": r.name,
                                "fault_code": FAULT_SOFTWARE_DEFECT,
                                "owner_party": OWNER_UNIVERSITY,
                                "raw_value_text": f"表底差原值={raw_val} GJ (瞬时≈{new_e11} GJ/h)",
                                "clean_strategy": f"{scale_note} -> 回看修正为 {new_hr} GJ",
                                "rule_desc": "站点累计热量表底刻度与标准 GJ 不一致",
                            })
                            tags.append(FAULT_SOFTWARE_DEFECT)
                            changed = True

                    if new_hr is not None and (new_hr < 0.0 or new_hr > max_lim * 1.5):
                        fallback_val = new_e11 if (new_e11 is not None and 0.0 <= new_e11 <= max_lim * 1.5) else None
                        fault_tickets.append({
                            "biz_hour": r.biz_hour,
                            "entity_type": "STATION",
                            "entity_id": r.station_id,
                            "entity_name": r.name,
                            "fault_code": FAULT_METER_JUMP if r.hour_heat_source == SRC_METER_DIFF else FAULT_SENSOR_RANGE,
                            "owner_party": OWNER_SHARED,
                            "raw_value_text": f"小时热量原值={raw_val} GJ (物理上限={max_lim * 1.5:.1f} GJ/h)",
                            "clean_strategy": f"回看修正为 {fallback_val} GJ（原值保留于 hour_heat_raw_gj）",
                            "rule_desc": "单站小时供热量 <0 或超过按面积核定极限热负荷 1.5 倍",
                        })
                        new_hr = fallback_val
                        tags.append(FAULT_METER_JUMP if r.hour_heat_source == SRC_METER_DIFF else FAULT_SENSOR_RANGE)
                        changed = True

                    if changed:
                        conn.execute(
                            text(
                                "UPDATE smart_heating_platform.fact_station_hourly "
                                "SET hour_heat_raw_gj = COALESCE(hour_heat_raw_gj, :raw_v), "
                                "hour_heat_gj = :hr_v, e11_clean = :e11_v, "
                                "value_source = CASE WHEN value_source = 'REAL' THEN 'MASKED_PREV_HOLD' ELSE value_source END, "
                                "fault_tag = :ft, updated_at = NOW() "
                                "WHERE id = :rid"
                            ),
                            {
                                "raw_v": raw_val,
                                "hr_v": new_hr,
                                "e11_v": new_e11,
                                "ft": ",".join(dict.fromkeys(tags)) or None,
                                "rid": r.id,
                            },
                        )
                        fixed_station_hours += 1

                # 5. 回看检测上游表 fact_upstream_hourly 中的累计量/超限热源值并留痕
                up_bad_rows = conn.execute(
                    text(
                        "SELECT id, biz_hour, data_zone, source_name, display_name, heat_raw, hour_heat_raw_gj, hour_heat_gj, fault_tag "
                        "FROM smart_heating_platform.fact_upstream_hourly "
                        "WHERE biz_hour >= :ws AND biz_hour < :we "
                        "AND hour_heat_gj IS NOT NULL "
                        "AND (display_name LIKE '%累计%' OR source_name LIKE '%累计%' "
                        "     OR hour_heat_gj < 0 OR hour_heat_gj > :up_max)"
                    ),
                    {"ws": win_start, "we": win_end, "up_max": UPSTREAM_MAX_HEAT_GJH},
                ).fetchall()

                for ur in up_bad_rows:
                    is_cum = "累计" in str(ur.display_name or "") or "累计" in str(ur.source_name or "")
                    fc = FAULT_SOFTWARE_DEFECT if is_cum else FAULT_SENSOR_RANGE
                    tags = [t for t in str(ur.fault_tag or "").split(",") if t]
                    tags.append(fc)
                    raw_hr = float(ur.hour_heat_raw_gj) if ur.hour_heat_raw_gj is not None else float(ur.hour_heat_gj)
                    conn.execute(
                        text(
                            "UPDATE smart_heating_platform.fact_upstream_hourly "
                            "SET hour_heat_raw_gj = COALESCE(hour_heat_raw_gj, hour_heat_gj), "
                            "hour_heat_gj = NULL, heat_clean = NULL, "
                            "value_source = CASE WHEN value_source = 'REAL' THEN 'MASKED_PREV_HOLD' ELSE value_source END, "
                            "fault_tag = :ft, updated_at = NOW() "
                            "WHERE id = :uid"
                        ),
                        {"ft": ",".join(dict.fromkeys(tags)), "uid": ur.id},
                    )
                    fault_tickets.append({
                        "biz_hour": ur.biz_hour,
                        "entity_type": "UPSTREAM",
                        "entity_id": f"{ur.data_zone}:{ur.source_name}",
                        "entity_name": ur.display_name or ur.source_name,
                        "fault_code": fc,
                        "owner_party": OWNER_UNIVERSITY if is_cum else OWNER_RESEARCH,
                        "raw_value_text": f"上游小时热量原值={raw_hr:.2f} GJ (heat_raw={ur.heat_raw})",
                        "clean_strategy": "忠实保留 hour_heat_raw_gj，回看置空累计量/超限热量并记入异常监测",
                        "rule_desc": "上游测点为累计寄存器或小时热量超过 5000 GJ 上限",
                    })
                    fixed_upstream_hours += 1

                if fault_tickets:
                    dedup_t: Dict[Tuple[datetime, str, str, str], Dict[str, Any]] = {}
                    for flt in fault_tickets:
                        dedup_t[(flt["biz_hour"], flt["entity_type"], flt["entity_id"], flt["fault_code"])] = flt
                    _upsert_batch(
                        conn,
                        "fact_fault_ticket",
                        [
                            "biz_hour", "entity_type", "entity_id", "entity_name", "fault_code",
                            "owner_party", "raw_value_text", "clean_strategy", "rule_desc",
                        ],
                        ["biz_hour", "entity_type", "entity_id", "fault_code"],
                        ["entity_name", "owner_party", "raw_value_text", "clean_strategy", "rule_desc"],
                        list(dedup_t.values()),
                        extra_set_clauses=["updated_at = NOW()"],
                    )

                ticket_count_in_win = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM smart_heating_platform.fact_fault_ticket "
                        "WHERE biz_hour >= :ws AND biz_hour < :we "
                        "AND fault_code IN ('SENSOR_OUT_OF_RANGE', 'METER_JUMP', 'SOFTWARE_DEFECT')"
                    ),
                    {"ws": win_start, "we": win_end},
                ).scalar_one()

            summary = {
                "trigger": trigger,
                "start_date": start_d.isoformat(),
                "end_date": end_d.isoformat(),
                "anomalous_station_days": {d: sorted(s) for d, s in sorted(recalib_days.items())},
                "fixed_station_hours": fixed_station_hours,
                "fixed_upstream_hours": fixed_upstream_hours,
                "fault_tickets_written": int(ticket_count_in_win or 0),
            }
            _finish_run_log(run_id, started_perf, "SUCCESS", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("历史热量异常回看修正失败: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {"trigger": trigger}, error_message=str(exc))
            raise


