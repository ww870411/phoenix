# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 核心旁路采集引擎与入库聚合服务。

支持三类安全采集作业（严格单线程串行 + 可配置间隔保护源站 Werkzeug 容器）：
1. `run_snapshot_cycle()`：每 15 分钟执行一次批量接口采样（/gk_get_data/ + /get_yw_data/1 +
   9次 /zx_hrz/），整点（或手动要求）附带 /jumin/；实时计算 15 分钟梯形积分写入 hourly 表；
2. `run_table_bottom_calibration()`：低峰错峰按站轮询 /hrz_ls_zb/（isdownload=1 提取
   f220/f221/f253/f254/f222），线性插值对齐整点并回刷校准热/水/电小时累计消耗量；
3. `run_merchant_daily_cycle()`：拉取 /getall_bb_shrb/（累计量 + 日单耗）写入商户日耗表。
"""

from __future__ import annotations

import calendar
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
    clean_station_and_zones,
    clean_temp_device,
    clean_upstream_point,
    floor_to_15min,
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

_COLLECT_LOCK = threading.RLock()
TEMP_RETENTION_HOURS = 48


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

        zn_rows = conn.execute(
            text(
                "SELECT DISTINCT ON (secondary_zone_id) secondary_zone_id, e5_clean, e6_clean "
                "FROM smart_heating_platform.fact_zone_hourly "
                "WHERE biz_hour >= :prev_start AND biz_hour < :biz_hour AND e5_clean IS NOT NULL "
                "ORDER BY secondary_zone_id, biz_hour DESC"
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
        "zone": {r.secondary_zone_id: dict(r._mapping) for r in zn_rows},
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


def _aggregate_upstream_hourly(conn: Any, biz_hour: datetime) -> int:
    """从 fact_upstream_15min 对指定小时做 15 分钟梯形积分与代表断面汇总。"""
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
            "hour_heat_gj": trapezoidal_hour_integral(heat_samples),
            "hour_flow_t": trapezoidal_hour_integral(flow_samples),
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


def _aggregate_station_hourly_from_15min(conn: Any, biz_hour: datetime) -> int:
    """从 fact_station_15min 计算换热站小时代表值与 15 分钟梯形积分（不覆盖已表底校准的 METER_DIFF）。"""
    rows = conn.execute(
        text(
            "SELECT sample_bucket, station_id, online, source_update_time, "
            "e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean, e7_raw, e7_clean, e8_raw, e8_clean, "
            "e11_raw, e11_clean, e13_raw, e14_raw, e14_clean, e16_raw, zone_heat_sum_e12, "
            "value_source, fault_tag "
            "FROM smart_heating_platform.fact_station_15min "
            "WHERE biz_hour = :biz_hour "
            "ORDER BY station_id, sample_bucket ASC"
        ),
        {"biz_hour": biz_hour},
    ).fetchall()

    grouped: Dict[str, List[Any]] = {}
    for r in rows:
        grouped.setdefault(r.station_id, []).append(r)

    hourly_rows: List[Dict[str, Any]] = []
    for st_id, items in grouped.items():
        latest = items[-1]
        heat_samples = [(it.sample_bucket, float(it.e11_clean) if it.e11_clean is not None else None) for it in items]
        flow_samples = [(it.sample_bucket, float(it.e1_clean) if it.e1_clean is not None else None) for it in items]
        water_samples = [(it.sample_bucket, float(it.e14_clean) if it.e14_clean is not None else None) for it in items]

        heat_diff_pct: Optional[float] = None
        if latest.zone_heat_sum_e12 is not None and latest.e11_raw is not None and float(latest.e11_raw) > 0.05:
            heat_diff_pct = round(
                (float(latest.zone_heat_sum_e12) - float(latest.e11_raw)) / float(latest.e11_raw) * 100.0,
                2,
            )

        hourly_rows.append({
            "biz_hour": biz_hour,
            "station_id": st_id,
            "sample_count": len(items),
            "online": latest.online,
            "source_update_time": latest.source_update_time,
            "e1_raw": latest.e1_raw,
            "e1_clean": latest.e1_clean,
            "e3_raw": latest.e3_raw,
            "e3_clean": latest.e3_clean,
            "e4_raw": latest.e4_raw,
            "e4_clean": latest.e4_clean,
            "e7_raw": latest.e7_raw,
            "e7_clean": latest.e7_clean,
            "e8_raw": latest.e8_raw,
            "e8_clean": latest.e8_clean,
            "e11_raw": latest.e11_raw,
            "e11_clean": latest.e11_clean,
            "e13_raw": latest.e13_raw,
            "e14_raw": latest.e14_raw,
            "e14_clean": latest.e14_clean,
            "e16_raw": latest.e16_raw,
            "zone_heat_sum_e12": latest.zone_heat_sum_e12,
            "heat_balance_diff_pct": heat_diff_pct,
            "hour_heat_gj": trapezoidal_hour_integral(heat_samples),
            "hour_heat_source": SRC_INTEGRAL_15M,
            "hour_flow_t": trapezoidal_hour_integral(flow_samples),
            "hour_flow_source": SRC_INTEGRAL_15M,
            "hour_water_t": trapezoidal_hour_integral(water_samples),
            "hour_water_source": SRC_INTEGRAL_15M,
            "value_source": latest.value_source,
            "fault_tag": latest.fault_tag,
        })

    if not hourly_rows:
        return 0

    sql = """
    INSERT INTO smart_heating_platform.fact_station_hourly (
        biz_hour, station_id, sample_count, online, source_update_time,
        e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean, e7_raw, e7_clean,
        e8_raw, e8_clean, e11_raw, e11_clean, e13_raw, e14_raw, e14_clean, e16_raw,
        zone_heat_sum_e12, heat_balance_diff_pct,
        hour_heat_gj, hour_heat_source, hour_flow_t, hour_flow_source,
        hour_water_t, hour_water_source, value_source, fault_tag
    ) VALUES (
        :biz_hour, :station_id, :sample_count, :online, :source_update_time,
        :e1_raw, :e1_clean, :e3_raw, :e3_clean, :e4_raw, :e4_clean, :e7_raw, :e7_clean,
        :e8_raw, :e8_clean, :e11_raw, :e11_clean, :e13_raw, :e14_raw, :e14_clean, :e16_raw,
        :zone_heat_sum_e12, :heat_balance_diff_pct,
        :hour_heat_gj, :hour_heat_source, :hour_flow_t, :hour_flow_source,
        :hour_water_t, :hour_water_source, :value_source, :fault_tag
    )
    ON CONFLICT (biz_hour, station_id) DO UPDATE SET
        sample_count = EXCLUDED.sample_count,
        online = EXCLUDED.online,
        source_update_time = EXCLUDED.source_update_time,
        e1_raw = EXCLUDED.e1_raw, e1_clean = EXCLUDED.e1_clean,
        e3_raw = EXCLUDED.e3_raw, e3_clean = EXCLUDED.e3_clean,
        e4_raw = EXCLUDED.e4_raw, e4_clean = EXCLUDED.e4_clean,
        e7_raw = EXCLUDED.e7_raw, e7_clean = EXCLUDED.e7_clean,
        e8_raw = EXCLUDED.e8_raw, e8_clean = EXCLUDED.e8_clean,
        e11_raw = EXCLUDED.e11_raw, e11_clean = EXCLUDED.e11_clean,
        e13_raw = EXCLUDED.e13_raw, e14_raw = EXCLUDED.e14_raw,
        e14_clean = EXCLUDED.e14_clean, e16_raw = EXCLUDED.e16_raw,
        zone_heat_sum_e12 = EXCLUDED.zone_heat_sum_e12,
        heat_balance_diff_pct = EXCLUDED.heat_balance_diff_pct,
        hour_heat_gj = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_heat_source = 'METER_DIFF'
            THEN smart_heating_platform.fact_station_hourly.hour_heat_gj
            ELSE EXCLUDED.hour_heat_gj END,
        hour_heat_source = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_heat_source = 'METER_DIFF'
            THEN 'METER_DIFF' ELSE EXCLUDED.hour_heat_source END,
        hour_flow_t = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_flow_source = 'METER_DIFF'
            THEN smart_heating_platform.fact_station_hourly.hour_flow_t
            ELSE EXCLUDED.hour_flow_t END,
        hour_flow_source = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_flow_source = 'METER_DIFF'
            THEN 'METER_DIFF' ELSE EXCLUDED.hour_flow_source END,
        hour_water_t = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_water_source = 'METER_DIFF'
            THEN smart_heating_platform.fact_station_hourly.hour_water_t
            ELSE EXCLUDED.hour_water_t END,
        hour_water_source = CASE
            WHEN smart_heating_platform.fact_station_hourly.hour_water_source = 'METER_DIFF'
            THEN 'METER_DIFF' ELSE EXCLUDED.hour_water_source END,
        value_source = EXCLUDED.value_source,
        fault_tag = EXCLUDED.fault_tag,
        updated_at = NOW()
    """
    conn.execute(text(sql), hourly_rows)
    return len(hourly_rows)


def _aggregate_zone_hourly(conn: Any, biz_hour: datetime) -> int:
    """从 fact_zone_15min 汇总二次网分区小时断面。"""
    rows = conn.execute(
        text(
            "SELECT DISTINCT ON (secondary_zone_id) secondary_zone_id, station_id, "
            "e2_raw, e2_clean, e5_raw, e5_clean, e6_raw, e6_clean, "
            "e9_raw, e9_clean, e10_raw, e10_clean, e12_raw, e15_raw, e15_clean, "
            "value_source, fault_tag, "
            "(SELECT COUNT(*) FROM smart_heating_platform.fact_zone_15min z2 "
            " WHERE z2.biz_hour = :biz_hour AND z2.secondary_zone_id = z1.secondary_zone_id) AS sample_count "
            "FROM smart_heating_platform.fact_zone_15min z1 "
            "WHERE biz_hour = :biz_hour "
            "ORDER BY secondary_zone_id, sample_bucket DESC"
        ),
        {"biz_hour": biz_hour},
    ).fetchall()

    hourly_rows = [
        {
            "biz_hour": biz_hour,
            "secondary_zone_id": r.secondary_zone_id,
            "station_id": r.station_id,
            "sample_count": int(r.sample_count or 1),
            "e2_raw": r.e2_raw,
            "e2_clean": r.e2_clean,
            "e5_raw": r.e5_raw,
            "e5_clean": r.e5_clean,
            "e6_raw": r.e6_raw,
            "e6_clean": r.e6_clean,
            "e9_raw": r.e9_raw,
            "e9_clean": r.e9_clean,
            "e10_raw": r.e10_raw,
            "e10_clean": r.e10_clean,
            "e12_raw": r.e12_raw,
            "e15_raw": r.e15_raw,
            "e15_clean": r.e15_clean,
            "value_source": r.value_source,
            "fault_tag": r.fault_tag,
        }
        for r in rows
    ]

    _upsert_batch(
        conn,
        "fact_zone_hourly",
        [
            "biz_hour", "secondary_zone_id", "station_id", "sample_count",
            "e2_raw", "e2_clean", "e5_raw", "e5_clean", "e6_raw", "e6_clean",
            "e9_raw", "e9_clean", "e10_raw", "e10_clean", "e12_raw", "e15_raw", "e15_clean",
            "value_source", "fault_tag",
        ],
        ["biz_hour", "secondary_zone_id"],
        [
            "station_id", "sample_count", "e2_raw", "e2_clean", "e5_raw", "e5_clean",
            "e6_raw", "e6_clean", "e9_raw", "e9_clean", "e10_raw", "e10_clean",
            "e12_raw", "e15_raw", "e15_clean", "value_source", "fault_tag",
        ],
        hourly_rows,
        extra_set_clauses=["updated_at = NOW()"],
    )
    return len(hourly_rows)


def _aggregate_merchant_hourly(conn: Any, biz_hour: datetime) -> int:
    """从 fact_merchant_15min 汇总商业用户小时代表断面与 15 分钟梯形积分（热量 GJ 与流量 t）。"""
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
        hour_heat = trapezoidal_hour_integral(heat_samples) if latest.is_registered else None
        hour_flow = trapezoidal_hour_integral(flow_samples) if latest.is_registered else None

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
            "hour_heat_source": SRC_INTEGRAL_15M,
            "hour_flow_t": hour_flow,
            "hour_flow_source": SRC_INTEGRAL_15M,
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
    client: httpx.Client,
    base_url: str,
    headers: Dict[str, str],
    main_network_ids: Sequence[int],
    interval: float,
) -> List[Dict[str, Any]]:
    """
    免 Cookie 获取商业用户全网实时运行参数（含瞬时热量与流量）。

    优先尝试单次调用 `/get_sh_data/0`（sh_selected=0）；若大包被源站 NAT 中断，
    则自动降级按主干网 ID（2..16）分片拉取 `/get_sh_data/{mn_id}` 合并去重。
    """
    req_headers = {**headers, "Connection": "close"}
    try:
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
        logger.info("全量 /get_sh_data/0 遇到截断抖动，切换主干网分片采集: %s", exc)

    seen: Dict[str, Dict[str, Any]] = {}
    for mid in main_network_ids:
        time.sleep(max(0.5, interval))
        rm = _post_with_retry(
            client,
            f"{base_url}/get_sh_data/{mid}",
            data={"sh_selected": str(mid)},
            headers=req_headers,
            retries=2,
        )
        if rm.status_code != 200:
            continue
        arr = rm.json() or []
        if isinstance(arr, list):
            for x in arr:
                if isinstance(x, dict) and x.get("name"):
                    seen[str(x["name"]).strip()] = x
    return list(seen.values())


def run_snapshot_cycle(
    include_jumin: Optional[bool] = None,
    trigger: str = "AUTO",
) -> Dict[str, Any]:
    """
    执行单轮 15 分钟批量断面采集、五重清洗与小时梯形积分聚合。

    当 `include_jumin` 为 None 时，仅在整点 00 分钟自动采集居民室温（降低 Cookie 接口压力）；
    手动触发时默认全量采集（若已配置 Cookie）。
    """
    ensure_smart_heating_fact_tables()
    with _COLLECT_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        sample_bucket = floor_to_15min(now_e8)
        biz_hour = floor_to_hour(now_e8)

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        interval = max(0.5, float(cfg.get("request_interval_seconds", 0.8)))
        timeout = float(cfg.get("request_timeout_seconds", 15.0))
        cookie = normalize_cookie_input(str(cfg.get("cookie") or ""))

        should_fetch_jumin = (sample_bucket.minute == 0) if include_jumin is None else bool(include_jumin)
        run_type = "MANUAL" if trigger == "MANUAL" else "SNAPSHOT_15M"
        run_id = _insert_run_log(biz_hour, run_type, cfg.get("source_mode", "public"))

        headers = {
            "User-Agent": "Phoenix-SmartHeating-Collector/2.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        caches = _load_dict_caches()
        prev_valid = _load_prev_valid_snapshots(biz_hour)

        upstream_rows: List[Dict[str, Any]] = []
        station_rows: List[Dict[str, Any]] = []
        zone_rows: List[Dict[str, Any]] = []
        temp_rows: List[Dict[str, Any]] = []
        merchant_rows: List[Dict[str, Any]] = []
        fault_rows: List[Dict[str, Any]] = []
        cookie_valid: Optional[bool] = None

        try:
            partial_errors: List[str] = []
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                # 1. 上游五大字典 (/gk_get_data/)
                r_gk = _post_with_retry(client, f"{base_url}/gk_get_data/", headers=headers)
                r_gk.raise_for_status()
                gk_data = r_gk.json()
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

                time.sleep(interval)

                # 2. 242 站精确时间戳与一网快照 (/get_yw_data/1)
                r_yw = _post_with_retry(client, f"{base_url}/get_yw_data/1", data={"yw_selected": "1"}, headers=headers)
                r_yw.raise_for_status()
                yw_by_name = {
                    str(item.get("name") or "").strip(): item
                    for item in (r_yw.json() or [])
                    if isinstance(item, dict)
                }

                # 3. 9 大服务中心 /zx_hrz/ (60..68)
                zx_by_id: Dict[str, Dict[str, Any]] = {}
                for center_id in range(60, 69):
                    time.sleep(interval)
                    try:
                        r_zx = _post_with_retry(client, f"{base_url}/zx_hrz/", data={"branch_id": str(center_id)}, headers=headers)
                        r_zx.raise_for_status()
                        for st_item in json.loads(r_zx.text):
                            if isinstance(st_item, dict) and st_item.get("id"):
                                zx_by_id[str(st_item["id"])] = st_item
                    except Exception as zx_exc:
                        partial_errors.append(f"zx_hrz({center_id}): {zx_exc}")
                        logger.warning("采集中心 %s 异常已跳过继续: %s", center_id, zx_exc)

                # 对全网 242 座台账换热站做统一清洗归口（含 5 座无分区站）
                for st_meta in caches["stations"]:
                    st_id = st_meta["station_id"]
                    st_name = st_meta["name"]
                    zx_item = zx_by_id.get(st_id)
                    yw_item = yw_by_name.get(st_name)
                    if zx_item is None and yw_item is None:
                        continue
                    cleaned_st, cleaned_zns, st_faults = clean_station_and_zones(
                        station_meta=st_meta,
                        zx_item=zx_item,
                        yw_item=yw_item,
                        zone_meta_map=caches["zones_by_station"].get(st_id, {}),
                        collected_at=now_e8,
                        prev_station_valid=prev_valid["station"].get(st_id),
                        prev_zones_valid=prev_valid["zone"],
                    )
                    cleaned_st["sample_bucket"] = sample_bucket
                    cleaned_st["biz_hour"] = biz_hour
                    station_rows.append(cleaned_st)
                    for z in cleaned_zns:
                        z["sample_bucket"] = sample_bucket
                        z["biz_hour"] = biz_hour
                        zone_rows.append(z)
                    fault_rows.extend(st_faults)

                # 4. 居民室温 (/jumin/)
                if should_fetch_jumin and cookie:
                    time.sleep(interval)
                    r_jm = _post_with_retry(
                        client,
                        f"{base_url}/jumin/",
                        data={"department_name": "0", "filter_level": "0", "isDownload": "1"},
                        headers={**headers, "Cookie": cookie},
                    )
                    if r_jm.status_code == 200:
                        jm_json = r_jm.json()
                        jm_items = jm_json.get("data", []) if isinstance(jm_json, dict) else []
                        cookie_valid = True
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
                    else:
                        cookie_valid = False

                # 5. 商业用户全网实时运行参数 (/get_sh_data/0，断流时自动降级分片拉取，免 Cookie)
                time.sleep(interval)
                try:
                    raw_merchants = _fetch_merchant_realtime_items(
                        client,
                        base_url,
                        headers,
                        caches["main_network_ids"],
                        interval,
                    )
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
                except Exception as mc_exc:
                    partial_errors.append(f"get_sh_data: {mc_exc}")
                    logger.warning("采集商业用户实时断面异常已跳过继续: %s", mc_exc)

            # 统一入库与小时聚合
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

                _upsert_batch(
                    conn,
                    "fact_station_15min",
                    [
                        "sample_bucket", "biz_hour", "station_id", "online", "source_update_time",
                        "e1_raw", "e1_clean", "e3_raw", "e3_clean", "e4_raw", "e4_clean",
                        "e7_raw", "e7_clean", "e8_raw", "e8_clean", "e11_raw", "e11_clean",
                        "e13_raw", "e14_raw", "e14_clean", "e16_raw", "zone_heat_sum_e12",
                        "value_source", "fault_tag",
                    ],
                    ["sample_bucket", "station_id"],
                    [
                        "online", "source_update_time", "e1_raw", "e1_clean", "e3_raw", "e3_clean",
                        "e4_raw", "e4_clean", "e7_raw", "e7_clean", "e8_raw", "e8_clean",
                        "e11_raw", "e11_clean", "e13_raw", "e14_raw", "e14_clean", "e16_raw",
                        "zone_heat_sum_e12", "value_source", "fault_tag",
                    ],
                    station_rows,
                )

                _upsert_batch(
                    conn,
                    "fact_zone_15min",
                    [
                        "sample_bucket", "biz_hour", "secondary_zone_id", "station_id",
                        "e2_raw", "e2_clean", "e5_raw", "e5_clean", "e6_raw", "e6_clean",
                        "e9_raw", "e9_clean", "e10_raw", "e10_clean", "e12_raw", "e15_raw", "e15_clean",
                        "value_source", "fault_tag",
                    ],
                    ["sample_bucket", "secondary_zone_id"],
                    [
                        "e2_raw", "e2_clean", "e5_raw", "e5_clean", "e6_raw", "e6_clean",
                        "e9_raw", "e9_clean", "e10_raw", "e10_clean", "e12_raw", "e15_raw", "e15_clean",
                        "value_source", "fault_tag",
                    ],
                    zone_rows,
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

                # 去重后写入阴面故障督办单
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

                up_hourly_cnt = _aggregate_upstream_hourly(conn, biz_hour)
                st_hourly_cnt = _aggregate_station_hourly_from_15min(conn, biz_hour)
                zn_hourly_cnt = _aggregate_zone_hourly(conn, biz_hour)
                mc_hourly_cnt = _aggregate_merchant_hourly(conn, biz_hour)
                temp_pruned_cnt = prune_old_temp_hourly(conn, reference_time=biz_hour)

            summary = {
                "sample_bucket": sample_bucket.strftime("%Y-%m-%d %H:%M:%S"),
                "biz_hour": biz_hour.strftime("%Y-%m-%d %H:00:00"),
                "upstream_15min": len(upstream_rows),
                "station_15min": len(station_rows),
                "zone_15min": len(zone_rows),
                "temp_hourly": len(temp_rows),
                "temp_pruned": temp_pruned_cnt,
                "merchant_15min": len(merchant_rows),
                "fault_tickets": len(dedup_faults),
                "upstream_hourly": up_hourly_cnt,
                "station_hourly": st_hourly_cnt,
                "zone_hourly": zn_hourly_cnt,
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


def run_table_bottom_calibration(
    target_date_str: Optional[str] = None,
    station_names: Optional[List[str]] = None,
    trigger: str = "AUTO",
) -> Dict[str, Any]:
    """
    错峰拉取 `/hrz_ls_zb/`（isdownload=1），按整点线性插值计算精确表底差值，
    回刷 `fact_station_hourly` 的小时累计热量/流量/补水/电量，并将坏表底写入阴面督办单。
    """
    ensure_smart_heating_fact_tables()
    with _COLLECT_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)

        # 如果是今天，校准截止到当前整点；若是历史日，校准全天 24 小时
        max_hour = floor_to_hour(now_e8) if target_d >= now_e8.date() else (next_day_start - timedelta(hours=1))
        hours_to_calib: List[datetime] = []
        cursor = day_start
        while cursor <= max_hour:
            hours_to_calib.append(cursor)
            cursor += timedelta(hours=1)

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        interval = max(1.0, float(cfg.get("request_interval_seconds", 0.8)))
        timeout = max(20.0, float(cfg.get("request_timeout_seconds", 15.0)))
        run_id = _insert_run_log(day_start, "TABLE_BOTTOM_CALIB" if trigger != "MANUAL" else "MANUAL_CALIB", cfg.get("source_mode", "public"))

        caches = _load_dict_caches()
        target_stations = caches["stations"]
        if station_names:
            name_set = {s.strip() for s in station_names if s.strip()}
            target_stations = [s for s in target_stations if s["name"] in name_set]

        query_start = (day_start - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        query_end = (next_day_start + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")

        updated_hours = 0
        failed_stations: List[str] = []
        jump_faults: List[Dict[str, Any]] = []

        try:
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                for idx, st in enumerate(target_stations):
                    if idx > 0:
                        time.sleep(interval)
                    st_id = st["station_id"]
                    st_name = st["name"]
                    covered_area = float(st["covered_area"]) if st.get("covered_area") else 100000.0
                    # 按 120 W/㎡ 估算单小时极限负荷 (GJ/h)，防止小站大跳变漏检
                    max_hourly_heat = max(250.0, covered_area * 0.00045)

                    try:
                        resp = client.post(
                            f"{base_url}/hrz_ls_zb/",
                            data={
                                "name": st_name,
                                "start_date": query_start,
                                "end_date": query_end,
                                "isdownload": "1",
                            },
                        )
                        if resp.status_code != 200:
                            failed_stations.append(st_name)
                            continue
                        raw_records = resp.json()
                        if not isinstance(raw_records, list) or not raw_records:
                            continue
                    except Exception:
                        failed_stations.append(st_name)
                        continue

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
                        continue

                    seq_j = [(p["ts"], p["f221"]) for p in parsed]
                    seq_f = [(p["ts"], p["f220"]) for p in parsed]
                    seq_w = [(p["ts"], p["f254"]) for p in parsed]
                    seq_e = [(p["ts"], p["f253"]) for p in parsed]

                    upsert_rows: List[Dict[str, Any]] = []
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

                        # 15分钟瞬时序列备用积分（用于补全历史小时或表底跳变降级）
                        win_pts = [p for p in parsed if hr <= p["ts"] <= hr_next]
                        fb_heat = trapezoidal_hour_integral([(p["ts"], p["f222"]) for p in win_pts])
                        fb_flow = trapezoidal_hour_integral([(p["ts"], p["f2"]) for p in win_pts])

                        delta_j, jump_j, msg_j = validate_meter_delta(j0, j1, max_hourly_limit=max_hourly_heat)
                        delta_f, jump_f, _ = validate_meter_delta(f0, f1_v, max_hourly_limit=max_hourly_heat * 12)
                        delta_w, jump_w, _ = validate_meter_delta(w0, w1, max_hourly_limit=200.0)
                        delta_e, jump_e, _ = validate_meter_delta(e0, e1_v, max_hourly_limit=5000.0)

                        if jump_j:
                            jump_faults.append({
                                "biz_hour": hr,
                                "entity_type": "STATION",
                                "entity_id": st_id,
                                "entity_name": st_name,
                                "fault_code": FAULT_METER_JUMP,
                                "owner_party": OWNER_SHARED,
                                "raw_value_text": msg_j,
                                "clean_strategy": "丢弃异常表底差，自动降级采用15分钟瞬时热量 f222 积分值",
                                "rule_desc": "相邻整点累计表底 totJ 出现倒走/清零或超过极限负荷1.5倍",
                            })

                        if delta_j is not None:
                            hr_heat, hr_heat_src = delta_j, SRC_METER_DIFF
                        else:
                            hr_heat, hr_heat_src = fb_heat, (SRC_FALLBACK_INTEGRAL if jump_j else SRC_INTEGRAL_15M)

                        hr_flow, hr_flow_src = (
                            (delta_f, SRC_METER_DIFF) if delta_f is not None else (fb_flow, SRC_INTEGRAL_15M)
                        )

                        # 供回温压代表值 (若表内尚无实时断面则一并补全)
                        rep = win_pts[-1] if win_pts else None
                        upsert_rows.append({
                            "biz_hour": hr,
                            "station_id": st_id,
                            "sample_count": len(win_pts),
                            "online": True,
                            "e1_raw": rep["f2"] if rep else None,
                            "e1_clean": rep["f2"] if rep else None,
                            "e3_raw": rep["f3"] if rep else None,
                            "e3_clean": rep["f3"] if rep else None,
                            "e4_raw": rep["f5"] if rep else None,
                            "e4_clean": rep["f5"] if rep else None,
                            "e7_raw": rep["f1"] if rep else None,
                            "e7_clean": rep["f1"] if rep else None,
                            "e8_raw": rep["f4"] if rep else None,
                            "e8_clean": rep["f4"] if rep else None,
                            "e11_raw": rep["f222"] if rep else None,
                            "e11_clean": rep["f222"] if rep else None,
                            "tot_j": j0,
                            "tot_f": f0,
                            "tot_water_f254": w0,
                            "tot_elec_f253": e0,
                            "hour_heat_gj": hr_heat,
                            "hour_heat_source": hr_heat_src,
                            "hour_flow_t": hr_flow,
                            "hour_flow_source": hr_flow_src,
                            "hour_water_t": delta_w,
                            "hour_water_source": SRC_METER_DIFF if delta_w is not None else SRC_INTEGRAL_15M,
                            "hour_elec_kwh": delta_e,
                            "hour_elec_source": SRC_METER_DIFF if delta_e is not None else "NONE",
                            "value_source": "REAL",
                        })

                    if upsert_rows:
                        with engine.begin() as conn:
                            sql = """
                            INSERT INTO smart_heating_platform.fact_station_hourly (
                                biz_hour, station_id, sample_count, online,
                                e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean,
                                e7_raw, e7_clean, e8_raw, e8_clean, e11_raw, e11_clean,
                                tot_j, tot_f, tot_water_f254, tot_elec_f253,
                                hour_heat_gj, hour_heat_source, hour_flow_t, hour_flow_source,
                                hour_water_t, hour_water_source, hour_elec_kwh, hour_elec_source, value_source
                            ) VALUES (
                                :biz_hour, :station_id, :sample_count, :online,
                                :e1_raw, :e1_clean, :e3_raw, :e3_clean, :e4_raw, :e4_clean,
                                :e7_raw, :e7_clean, :e8_raw, :e8_clean, :e11_raw, :e11_clean,
                                :tot_j, :tot_f, :tot_water_f254, :tot_elec_f253,
                                :hour_heat_gj, :hour_heat_source, :hour_flow_t, :hour_flow_source,
                                :hour_water_t, :hour_water_source, :hour_elec_kwh, :hour_elec_source, :value_source
                            )
                            ON CONFLICT (biz_hour, station_id) DO UPDATE SET
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
                                updated_at = NOW()
                            """
                            conn.execute(text(sql), upsert_rows)
                        updated_hours += len(upsert_rows)

            if jump_faults:
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
                        jump_faults,
                        extra_set_clauses=["updated_at = NOW()"],
                    )

            summary = {
                "target_date": target_d.isoformat(),
                "stations_total": len(target_stations),
                "updated_station_hours": updated_hours,
                "failed_stations": failed_stations[:20],
                "jump_faults": len(jump_faults),
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
    with _COLLECT_LOCK:
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
    利用免 Cookie 历史接口 `/sh_ls_zb/`（5分钟颗粒度）错峰补采商业用户指定日期逐小时指标，
    基于 `fFlowJ`/`fFlowF` 执行时间加权梯形面积积分写入 `fact_merchant_hourly`。
    """
    ensure_smart_heating_fact_tables()
    with _COLLECT_LOCK:
        started_perf = time.perf_counter()
        now_e8 = datetime.now(EAST_8)
        target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        next_day_start = day_start + timedelta(days=1)

        cfg = _read_raw_config()
        base_url = resolve_effective_base_url(cfg)
        interval = max(0.8, float(cfg.get("request_interval_seconds", 0.8)))
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
        updated_hours = 0
        failed_merchants: List[str] = []

        try:
            with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                for idx, mc in enumerate(target_merchants):
                    if idx > 0:
                        time.sleep(interval)
                    m_name = mc["name"]
                    try:
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
                            retries=1,
                        )
                        if resp.status_code != 200:
                            failed_merchants.append(m_name)
                            continue
                        raw_records = resp.json()
                        if not isinstance(raw_records, list) or not raw_records:
                            continue
                    except Exception:
                        failed_merchants.append(m_name)
                        continue

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

                    if upsert_rows:
                        with engine.begin() as conn:
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
                                upsert_rows,
                                extra_set_clauses=["updated_at = NOW()"],
                            )
                        updated_hours += len(upsert_rows)

            summary = {
                "target_date": target_d.isoformat(),
                "merchants_total": len(target_merchants),
                "updated_merchant_hours": updated_hours,
                "failed_merchants": failed_merchants[:20],
            }
            _finish_run_log(run_id, started_perf, "SUCCESS" if not failed_merchants else "PARTIAL", None, summary)
            return {"ok": True, "run_id": run_id, **summary}
        except Exception as exc:
            logger.exception("商业用户小时历史补采异常: %s", exc)
            _finish_run_log(run_id, started_perf, "FAILED", None, {}, error_message=str(exc))
            raise
