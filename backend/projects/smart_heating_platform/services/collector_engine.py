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
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import (
    EAST_8,
    FAULT_METER_JUMP,
    OWNER_SHARED,
    SRC_FALLBACK_INTEGRAL,
    SRC_INTEGRAL_15M,
    SRC_METER_DIFF,
    clean_merchant_point,
    clean_station_history_point,
    clean_temp_device,
    clean_upstream_point,
    floor_to_bucket,
    floor_to_hour,
    interpolate_meter_at_hour,
    parse_dt_east8,
    to_float,
    trapezoidal_hour_integral,
    validate_meter_delta,
)
from backend.projects.smart_heating_platform.services.collector_config_service import (
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
) -> None:
    """在当前数据库事务内执行批量幂等 UPSERT。"""
    if not rows:
        return
    col_str = ", ".join(columns)
    val_str = ", ".join(f":{c}" for c in columns)
    conf_str = ", ".join(conflict_cols)
    sets = [f"{c} = EXCLUDED.{c}" for c in update_cols]
    if extra_set_clauses:
        sets.extend(extra_set_clauses)
    sql = (
        f"INSERT INTO smart_heating_platform.{table_name} ({col_str}) "
        f"VALUES ({val_str}) "
        f"ON CONFLICT ({conf_str}) DO UPDATE SET {', '.join(sets)}"
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
            "pressure_clean", "flow_raw", "flow_clean", "heat_raw", "heat_clean", "hour_heat_gj",
            "hour_flow_t", "value_source", "fault_tag",
        ],
        ["biz_hour", "data_zone", "source_name"],
        [
            "point_id", "display_name", "category", "sub_category", "is_core_gk", "sample_count",
            "source_time", "temp_raw", "temp_clean", "pressure_raw", "pressure_clean", "flow_raw",
            "flow_clean", "heat_raw", "heat_clean", "hour_heat_gj", "hour_flow_t", "value_source", "fault_tag",
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
    st_id = st["station_id"]
    st_name = st["name"]
    covered_area = float(st["covered_area"]) if st.get("covered_area") else 100000.0
    max_hourly_heat = max(250.0, covered_area * 0.00045)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            resp = _post_with_retry(
                client,
                f"{base_url}/hrz_ls_zb/",
                data={
                    "name": st_name,
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
            if not isinstance(raw_records, list) or not raw_records:
                return st_name, [], [], True
    except Exception:
        return st_name, [], [], False

    parsed: List[Dict[str, Any]] = []
    for rec in raw_records:
        ts = parse_dt_east8(rec.get("create_time"))
        if ts is None:
            continue
        parsed.append({
            "ts": ts,
            "f1": to_float(rec.get("f1")),
            "f2": to_float(rec.get("f2")),
            "f3": to_float(rec.get("f3")),
            "f4": to_float(rec.get("f4")),
            "f5": to_float(rec.get("f5")),
            "f220": to_float(rec.get("f220")),  # totF
            "f221": to_float(rec.get("f221")),  # totJ
            "f222": to_float(rec.get("f222")),  # flowJ
            "f253": to_float(rec.get("f253")),  # 电能累计
            "f254": to_float(rec.get("f254")),  # 补水累计
        })

    if not parsed:
        return st_name, [], [], True

    seq_j = [(p["ts"], p["f221"]) for p in parsed]
    seq_f = [(p["ts"], p["f220"]) for p in parsed]
    seq_w = [(p["ts"], p["f254"]) for p in parsed]
    seq_e = [(p["ts"], p["f253"]) for p in parsed]

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
        fb_heat = trapezoidal_hour_integral([(p["ts"], p["f222"]) for p in win_pts])
        fb_flow = trapezoidal_hour_integral([(p["ts"], p["f2"]) for p in win_pts])

        delta_j, jump_j, msg_j = validate_meter_delta(j0, j1, max_hourly_limit=max_hourly_heat)
        delta_f, _, _ = validate_meter_delta(f0, f1_v, max_hourly_limit=max_hourly_heat * 12)
        delta_w, _, _ = validate_meter_delta(w0, w1, max_hourly_limit=200.0)
        delta_e, _, _ = validate_meter_delta(e0, e1_v, max_hourly_limit=5000.0)

        if jump_j:
            faults.append({
                "biz_hour": hr,
                "entity_type": "STATION",
                "entity_id": st_id,
                "entity_name": st_name,
                "fault_code": FAULT_METER_JUMP,
                "owner_party": OWNER_SHARED,
                "raw_value_text": msg_j,
                "clean_strategy": "丢弃异常表底差，自动降级采用历史瞬时热量 f222 积分值",
                "rule_desc": "相邻整点累计表底 totJ 出现倒走/清零或超过极限负荷1.5倍",
            })

        if delta_j is not None:
            hr_heat, hr_heat_src = delta_j, SRC_METER_DIFF
        else:
            hr_heat, hr_heat_src = fb_heat, (SRC_FALLBACK_INTEGRAL if jump_j else SRC_INTEGRAL_15M)

        hr_flow, hr_flow_src = (
            (delta_f, SRC_METER_DIFF) if delta_f is not None else (fb_flow, SRC_INTEGRAL_15M)
        )

        rep = win_pts[-1] if win_pts else None
        cleaned_rep, rep_faults = clean_station_history_point(st, rep, prev_station_valid=rolling_prev)
        for rf in rep_faults:
            rf["biz_hour"] = hr
            faults.append(rf)
        if cleaned_rep["online"]:
            rolling_prev = cleaned_rep

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
            "tot_j": j0,
            "tot_f": f0,
            "tot_water_f254": w0,
            "tot_elec_f253": e0,
            "hour_heat_gj": hr_heat,
            "hour_heat_source": hr_heat_src,
            "hour_flow_t": hr_flow,
            "hour_flow_source": hr_flow_src,
            "hour_water_t": delta_w,
            "hour_water_source": SRC_METER_DIFF if delta_w is not None else "NONE",
            "hour_elec_kwh": delta_e,
            "hour_elec_source": SRC_METER_DIFF if delta_e is not None else "NONE",
            "value_source": cleaned_rep["value_source"],
            "fault_tag": cleaned_rep["fault_tag"],
        })

    return st_name, upsert_rows, faults, True


def run_table_bottom_calibration(
    target_date_str: Optional[str] = None,
    station_names: Optional[List[str]] = None,
    trigger: str = "AUTO",
) -> Dict[str, Any]:
    """
    受控并行拉取 `/hrz_ls_zb/`（isdownload=1），按整点线性插值计算精确表底差值与代表断面，
    写入 `fact_station_hourly`（路线 B 专责换热站每小时整点后产出，不阻塞 5 分钟快照采集）。
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

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        max_workers = max(1, min(16, int(cfg.get("max_workers", 4))))
        timeout = max(20.0, float(cfg.get("request_timeout_seconds", 15.0)))
        run_id = _insert_run_log(day_start, "TABLE_BOTTOM_CALIB" if trigger != "MANUAL" else "MANUAL_CALIB", cfg.get("source_mode", "public"))

        if not hours_to_calib:
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
                for fut in as_completed(futures):
                    st_name, st_rows, st_faults, ok_flag = fut.result()
                    if not ok_flag:
                        failed_stations.append(st_name)
                    if st_rows:
                        all_upsert_rows.extend(st_rows)
                    if st_faults:
                        all_faults.extend(st_faults)

            if all_upsert_rows:
                sql = """
                INSERT INTO smart_heating_platform.fact_station_hourly (
                    biz_hour, station_id, sample_count, online,
                    e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean,
                    e7_raw, e7_clean, e8_raw, e8_clean, e11_raw, e11_clean,
                    tot_j, tot_f, tot_water_f254, tot_elec_f253,
                    hour_heat_gj, hour_heat_source, hour_flow_t, hour_flow_source,
                    hour_water_t, hour_water_source, hour_elec_kwh, hour_elec_source,
                    value_source, fault_tag
                ) VALUES (
                    :biz_hour, :station_id, :sample_count, :online,
                    :e1_raw, :e1_clean, :e3_raw, :e3_clean, :e4_raw, :e4_clean,
                    :e7_raw, :e7_clean, :e8_raw, :e8_clean, :e11_raw, :e11_clean,
                    :tot_j, :tot_f, :tot_water_f254, :tot_elec_f253,
                    :hour_heat_gj, :hour_heat_source, :hour_flow_t, :hour_flow_source,
                    :hour_water_t, :hour_water_source, :hour_elec_kwh, :hour_elec_source,
                    :value_source, :fault_tag
                )
                ON CONFLICT (biz_hour, station_id) DO UPDATE SET
                    sample_count = EXCLUDED.sample_count,
                    online = EXCLUDED.online,
                    e1_raw = COALESCE(EXCLUDED.e1_raw, smart_heating_platform.fact_station_hourly.e1_raw),
                    e1_clean = COALESCE(EXCLUDED.e1_clean, smart_heating_platform.fact_station_hourly.e1_clean),
                    e3_raw = COALESCE(EXCLUDED.e3_raw, smart_heating_platform.fact_station_hourly.e3_raw),
                    e3_clean = COALESCE(EXCLUDED.e3_clean, smart_heating_platform.fact_station_hourly.e3_clean),
                    e4_raw = COALESCE(EXCLUDED.e4_raw, smart_heating_platform.fact_station_hourly.e4_raw),
                    e4_clean = COALESCE(EXCLUDED.e4_clean, smart_heating_platform.fact_station_hourly.e4_clean),
                    e7_raw = COALESCE(EXCLUDED.e7_raw, smart_heating_platform.fact_station_hourly.e7_raw),
                    e7_clean = COALESCE(EXCLUDED.e7_clean, smart_heating_platform.fact_station_hourly.e7_clean),
                    e8_raw = COALESCE(EXCLUDED.e8_raw, smart_heating_platform.fact_station_hourly.e8_raw),
                    e8_clean = COALESCE(EXCLUDED.e8_clean, smart_heating_platform.fact_station_hourly.e8_clean),
                    e11_raw = COALESCE(EXCLUDED.e11_raw, smart_heating_platform.fact_station_hourly.e11_raw),
                    e11_clean = COALESCE(EXCLUDED.e11_clean, smart_heating_platform.fact_station_hourly.e11_clean),
                    tot_j = COALESCE(EXCLUDED.tot_j, smart_heating_platform.fact_station_hourly.tot_j),
                    tot_f = COALESCE(EXCLUDED.tot_f, smart_heating_platform.fact_station_hourly.tot_f),
                    tot_water_f254 = COALESCE(EXCLUDED.tot_water_f254, smart_heating_platform.fact_station_hourly.tot_water_f254),
                    tot_elec_f253 = COALESCE(EXCLUDED.tot_elec_f253, smart_heating_platform.fact_station_hourly.tot_elec_f253),
                    hour_heat_gj = COALESCE(EXCLUDED.hour_heat_gj, smart_heating_platform.fact_station_hourly.hour_heat_gj),
                    hour_heat_source = EXCLUDED.hour_heat_source,
                    hour_flow_t = COALESCE(EXCLUDED.hour_flow_t, smart_heating_platform.fact_station_hourly.hour_flow_t),
                    hour_flow_source = EXCLUDED.hour_flow_source,
                    hour_water_t = COALESCE(EXCLUDED.hour_water_t, smart_heating_platform.fact_station_hourly.hour_water_t),
                    hour_water_source = CASE
                        WHEN EXCLUDED.hour_water_t IS NOT NULL THEN EXCLUDED.hour_water_source
                        ELSE smart_heating_platform.fact_station_hourly.hour_water_source END,
                    hour_elec_kwh = COALESCE(EXCLUDED.hour_elec_kwh, smart_heating_platform.fact_station_hourly.hour_elec_kwh),
                    hour_elec_source = CASE
                        WHEN EXCLUDED.hour_elec_kwh IS NOT NULL THEN EXCLUDED.hour_elec_source
                        ELSE smart_heating_platform.fact_station_hourly.hour_elec_source END,
                    value_source = EXCLUDED.value_source,
                    fault_tag = EXCLUDED.fault_tag,
                    updated_at = NOW()
                """
                with engine.begin() as conn:
                    for offset in range(0, len(all_upsert_rows), 500):
                        conn.execute(text(sql), all_upsert_rows[offset:offset + 500])

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


def run_merchant_hourly_backfill(
    target_date_str: Optional[str] = None,
    merchant_names: Optional[List[str]] = None,
    trigger: str = "MANUAL",
) -> Dict[str, Any]:
    """
    受控并行调用免 Cookie 历史接口 `/sh_ls_zb/`（5分钟颗粒度）补采商业用户指定日期逐小时指标，
    基于 `fFlowJ`/`fFlowF` 执行时间加权梯形面积积分写入 `fact_merchant_hourly`。
    """
    ensure_smart_heating_fact_tables()
    with _MERCHANT_BACKFILL_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)

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
        all_upsert_rows: List[Dict[str, Any]] = []

        def _fetch_one_merchant(mc: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], bool]:
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
                        return m_name, [], False
                    raw_records = resp.json()
                    if not isinstance(raw_records, list) or not raw_records:
                        return m_name, [], True
            except Exception:
                return m_name, [], False

            by_hour: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = {}
            for rec in raw_records:
                ts = parse_dt_east8(rec.get("tmDate"))
                if ts is None:
                    continue
                cleaned, _ = clean_merchant_point(
                    {**rec, "name": m_name},
                    merchant_lookup=caches["merchant_by_name"],
                    collected_at=now_e8,
                )
                by_hour.setdefault(floor_to_hour(ts), []).append((ts, cleaned))

            upsert_rows: List[Dict[str, Any]] = []
            for bh, pts in sorted(by_hour.items()):
                pts.sort(key=lambda x: x[0])
                latest = pts[-1][1]
                heat_samples = [(ts, p["heat_clean"]) for ts, p in pts]
                flow_samples = [(ts, p["flow_clean"]) for ts, p in pts]
                upsert_rows.append({
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
            return m_name, upsert_rows, True

        try:
            workers = max(1, min(max_workers, len(target_merchants) or 1))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_fetch_one_merchant, mc) for mc in target_merchants]
                for fut in as_completed(futures):
                    m_name, rows_out, ok_flag = fut.result()
                    if not ok_flag:
                        failed_merchants.append(m_name)
                    if rows_out:
                        all_upsert_rows.extend(rows_out)

            if all_upsert_rows:
                with engine.begin() as conn:
                    for offset in range(0, len(all_upsert_rows), 500):
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
                            all_upsert_rows[offset:offset + 500],
                            extra_set_clauses=["updated_at = NOW()"],
                        )

            summary = {
                "target_date": target_d.isoformat(),
                "merchants_total": len(target_merchants),
                "updated_merchant_hours": len(all_upsert_rows),
                "failed_merchants": sorted(failed_merchants)[:20],
                "max_workers": max_workers,
            }
            _finish_run_log(run_id, started_perf, "SUCCESS" if not failed_merchants else "PARTIAL", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("商业用户小时历史补采异常: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise
