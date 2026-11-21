# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 历史数据全量回溯补采脚本（2026-11-01 至今）。

设计原则：
1. 严格单线程串行 + >=0.8s 间隔保护源站 Werkzeug 容器；
2. 全部按天/多日窗口分片请求 + 自动重试（应对公网 NAT 断流），支持进度断点续传；
3. 复用 `cleaning_engine` 与表底插值/梯形积分口径，保持历史补采与实时采集完全同口径。

用法示例：
  python backend/scripts/backfill_smart_heating_history.py --start 2026-11-01 --end 2026-11-19 --steps all
  python backend/scripts/backfill_smart_heating_history.py --steps merchant_daily,stations
"""

from __future__ import annotations

import argparse
import calendar
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy import text

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import DATA_DIRECTORY  # noqa: E402
from backend.db.database_daily_report_25_26 import engine  # noqa: E402
from backend.projects.smart_heating_platform.services.cleaning_engine import (  # noqa: E402
    EAST_8,
    FAULT_COMM_OFFLINE,
    FAULT_METER_JUMP,
    FAULT_SENSOR_RANGE,
    FAULT_TEMP_INVERSION,
    OWNER_RESEARCH,
    OWNER_SHARED,
    SRC_FALLBACK_INTEGRAL,
    SRC_INTEGRAL_15M,
    SRC_MASKED_PREV,
    SRC_METER_DIFF,
    SRC_REAL,
    clean_merchant_point,
    clean_station_history_point,
    clean_upstream_point,
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
from backend.projects.smart_heating_platform.services.collector_config_service import (  # noqa: E402
    _read_raw_config,
    normalize_cookie_input,
    resolve_effective_base_url,
)
from backend.projects.smart_heating_platform.services.collector_engine import (  # noqa: E402
    _calibrate_station_parsed_hours,
    _load_dict_caches,
    _parse_station_history_records,
    _post_with_retry,
    _upsert_batch,
    _upsert_station_calibration_results,
)
from backend.projects.smart_heating_platform.services.db_schema import ensure_smart_heating_fact_tables  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill_smart_heating")

CHECKPOINT_FILE = (
    Path(DATA_DIRECTORY) / "projects" / "smart_heating_platform" / "config" / "backfill_progress.json"
)


def _load_checkpoint() -> Dict[str, Any]:
    if not CHECKPOINT_FILE.exists():
        return {"done": {}}
    try:
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("done"), dict):
            return data
    except Exception:
        pass
    return {"done": {}}


def _save_checkpoint(cp: Dict[str, Any]) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CHECKPOINT_FILE)


def _is_done(cp: Dict[str, Any], step: str, key: str) -> bool:
    return bool(cp.get("done", {}).get(step, {}).get(key))


def _mark_done(cp: Dict[str, Any], step: str, key: str, flush: bool = False) -> None:
    cp.setdefault("done", {}).setdefault(step, {})[key] = True
    if flush:
        _save_checkpoint(cp)


def _date_chunks(start_d: date, end_d: date, span_days: int) -> List[Tuple[date, date]]:
    chunks: List[Tuple[date, date]] = []
    cur = start_d
    while cur <= end_d:
        nxt = min(end_d, cur + timedelta(days=span_days - 1))
        chunks.append((cur, nxt))
        cur = nxt + timedelta(days=1)
    return chunks


# ---------------------------------------------------------------------------
# 1. 商业用户日耗量补采 (/getall_bb_shrb/) —— 仅需 2 次请求覆盖整月
# ---------------------------------------------------------------------------
def backfill_merchant_daily(
    client: httpx.Client,
    base_url: str,
    cookie: str,
    start_d: date,
    end_d: date,
    caches: Dict[str, Any],
    interval: float,
) -> Dict[str, Any]:
    if not cookie:
        logger.warning("未配置 Cookie，跳过商业用户日耗量补采。")
        return {"skipped": True, "reason": "no_cookie"}

    headers = {"User-Agent": "Phoenix-Backfill/1.0", "Cookie": cookie, "Connection": "close"}
    months: List[Tuple[int, int]] = []
    cur = date(start_d.year, start_d.month, 1)
    while cur <= end_d:
        months.append((cur.year, cur.month))
        cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)

    total_rows = 0
    for yr, mo in months:
        last_day = calendar.monthrange(yr, mo)[1]
        ym = f"{yr}{mo}"
        r_unit = _post_with_retry(
            client,
            f"{base_url}/getall_bb_shrb/",
            data={"selectof1": "0", "selectof2": "0", "selectof3": "1", "options4": ym, "lastDay": str(last_day)},
            headers=headers,
        )
        time.sleep(interval)
        r_tot = _post_with_retry(
            client,
            f"{base_url}/getall_bb_shrb/",
            data={"selectof1": "0", "selectof2": "0", "selectof3": "0", "options4": ym, "lastDay": str(last_day)},
            headers=headers,
        )
        if r_unit.status_code != 200 or r_tot.status_code != 200:
            logger.warning("商业日耗接口 HTTP %s/%s，跳过 %s", r_unit.status_code, r_tot.status_code, ym)
            continue

        unit_list = r_unit.json() or []
        tot_by_id = {str(x.get("id") or ""): x for x in (r_tot.json() or []) if isinstance(x, dict)}

        mo_start = max(start_d, date(yr, mo, 1))
        mo_end = min(end_d, date(yr, mo, last_day))
        rows: List[Dict[str, Any]] = []

        d_cur = mo_start
        while d_cur <= mo_end:
            day_col = f"Data{d_cur.day}"
            prev_col = f"Data{d_cur.day - 1}" if d_cur.day > 1 else "Data0"
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
                if unit_val is None and v_curr is None:
                    continue
                daily_cons = None
                if v_curr is not None and v_prev is not None and v_curr >= v_prev:
                    daily_cons = round(v_curr - v_prev, 4)
                rows.append({
                    "biz_date": d_cur,
                    "merchant_id": m_id,
                    "daily_consumption": daily_cons,
                    "daily_unit_heat": unit_val,
                    "raw_payload": json.dumps(
                        {"unit": item.get(day_col), "tot_curr": v_curr, "tot_prev": v_prev},
                        ensure_ascii=False,
                    ),
                })
            d_cur += timedelta(days=1)

        if rows:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO smart_heating_platform.fact_merchant_daily "
                        "(biz_date, merchant_id, daily_consumption, daily_unit_heat, raw_payload) "
                        "VALUES (:biz_date, :merchant_id, :daily_consumption, :daily_unit_heat, CAST(:raw_payload AS JSONB)) "
                        "ON CONFLICT (biz_date, merchant_id) DO UPDATE SET "
                        "daily_consumption = COALESCE(EXCLUDED.daily_consumption, smart_heating_platform.fact_merchant_daily.daily_consumption), "
                        "daily_unit_heat = COALESCE(EXCLUDED.daily_unit_heat, smart_heating_platform.fact_merchant_daily.daily_unit_heat), "
                        "raw_payload = EXCLUDED.raw_payload, updated_at = NOW()"
                    ),
                    rows,
                )
            total_rows += len(rows)
        logger.info("[merchant_daily] 月份 %s 完成，写入/更新 %d 条日记录。", ym, len(rows))
    return {"rows_saved": total_rows}


# ---------------------------------------------------------------------------
# 2. 242 座换热站逐小时 & 表底校准补采 (/hrz_ls_zb/)
# ---------------------------------------------------------------------------
def backfill_stations(
    client: httpx.Client,
    base_url: str,
    start_d: date,
    end_d: date,
    caches: Dict[str, Any],
    interval: float,
    cp: Dict[str, Any],
    limit: Optional[int] = None,
    workers: int = 2,
) -> Dict[str, Any]:
    now_e8 = datetime.now(EAST_8)
    max_hour_global = floor_to_hour(now_e8) - timedelta(hours=1)
    stations = caches["stations"][:limit] if limit else caches["stations"]
    chunks = _date_chunks(start_d, end_d, 5)
    headers = {"User-Agent": "Phoenix-Backfill/1.0", "Connection": "close"}

    saved_hours = 0
    failed: List[str] = []
    pending = [st for st in stations if not _is_done(cp, "stations", st["station_id"])]

    def _run_one_station(st: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        st_name = st["name"]
        st_query_name = st.get("name_raw") or st_name
        dedup_map: Dict[datetime, Dict[str, Any]] = {}
        st_failed = False

        with httpx.Client(timeout=90.0, follow_redirects=False, trust_env=False) as st_client:
            for c_start, c_end in chunks:
                time.sleep(interval)
                q_start = (datetime(c_start.year, c_start.month, c_start.day, 0, 0, tzinfo=EAST_8) - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
                q_end = (datetime(c_end.year, c_end.month, c_end.day, 0, 0, tzinfo=EAST_8) + timedelta(days=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
                try:
                    resp = _post_with_retry(
                        st_client,
                        f"{base_url}/hrz_ls_zb/",
                        data={"name": st_query_name, "start_date": q_start, "end_date": q_end, "isdownload": "1"},
                        headers=headers,
                        retries=2,
                    )
                    if resp.status_code != 200:
                        st_failed = True
                        continue
                    arr = resp.json()
                    if isinstance(arr, list):
                        for item in _parse_station_history_records(arr):
                            dedup_map[item["ts"]] = item
                    else:
                        st_failed = True
                except Exception as exc:
                    logger.warning("[stations] %s (%s~%s) 拉取失败: %s", st_name, c_start, c_end, exc)
                    st_failed = True

        parsed = [dedup_map[k] for k in sorted(dedup_map.keys())]
        if not parsed:
            return st, [], [], st_failed

        upsert_rows: List[Dict[str, Any]] = []
        fault_rows: List[Dict[str, Any]] = []
        prev_valid: Optional[Dict[str, Any]] = None
        d_cur = start_d
        while d_cur <= end_d:
            day_start = datetime(d_cur.year, d_cur.month, d_cur.day, 0, 0, tzinfo=EAST_8)
            next_day_start = day_start + timedelta(days=1)
            day_max_hour = min(max_hour_global, next_day_start - timedelta(hours=1))
            day_hours: List[datetime] = []
            hr_cur = day_start
            while hr_cur <= day_max_hour:
                day_hours.append(hr_cur)
                hr_cur += timedelta(hours=1)
            if day_hours:
                win_lo = day_start - timedelta(minutes=30)
                win_hi = next_day_start + timedelta(minutes=30)
                day_parsed = [p for p in parsed if win_lo <= p["ts"] <= win_hi]
                if day_parsed:
                    day_rows, day_faults = _calibrate_station_parsed_hours(
                        st, day_parsed, day_hours, prev_station_db=prev_valid
                    )
                    for r in reversed(day_rows):
                        if r.get("online"):
                            prev_valid = r
                            break
                    upsert_rows.extend(day_rows)
                    fault_rows.extend(day_faults)
            d_cur += timedelta(days=1)
        return st, upsert_rows, fault_rows, st_failed

    eff_workers = max(1, min(4, int(workers)))
    with ThreadPoolExecutor(max_workers=eff_workers) as pool:
        futures = [pool.submit(_run_one_station, st) for st in pending]
        for idx, fut in enumerate(as_completed(futures), 1):
            st, upsert_rows, fault_rows, st_failed = fut.result()
            st_id = st["station_id"]
            st_name = st["name"]
            if upsert_rows or fault_rows:
                _upsert_station_calibration_results(upsert_rows, fault_rows)
                saved_hours += len(upsert_rows)
            if not st_failed:
                _mark_done(cp, "stations", st_id, flush=(idx % 10 == 0 or idx == len(pending)))
            else:
                failed.append(st_name)
            if idx % 20 == 0 or idx == len(pending):
                logger.info("[stations] 进度 %d/%d，已回写站时数=%d，失败=%d", idx, len(pending), saved_hours, len(failed))

    _save_checkpoint(cp)
    return {"saved_hours": saved_hours, "failed_count": len(failed), "failed": failed[:20]}


# ---------------------------------------------------------------------------
# 3. 上游电厂与首站历史补采 (/ry_dcls_xx/get_history & /ry_szls_xx/get_history)
# ---------------------------------------------------------------------------
def backfill_upstream(
    client: httpx.Client,
    base_url: str,
    start_d: date,
    end_d: date,
    caches: Dict[str, Any],
    interval: float,
    cp: Dict[str, Any],
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    headers = {"User-Agent": "Phoenix-Backfill/1.0", "Connection": "close"}
    dc_items = _post_with_retry(client, f"{base_url}/get_dc_data/1", data={"dc_selected": "1"}, headers=headers).json() or []
    time.sleep(interval)
    sz_items = _post_with_retry(client, f"{base_url}/get_sz_data/1", data={"sz_selected": "1"}, headers=headers).json() or []
    time.sleep(interval)

    tasks: List[Tuple[str, str, str, str]] = []
    for x in dc_items:
        if isinstance(x, dict) and x.get("name"):
            tasks.append(("dc_dict", str(x["name"]), str(x.get("id") or "1"), "/ry_dcls_xx/get_history"))
    for x in sz_items:
        if isinstance(x, dict) and x.get("name"):
            tasks.append(("sz_dict", str(x["name"]), str(x.get("id") or "1"), "/ry_szls_xx/get_history"))

    if limit:
        tasks = tasks[:limit]

    chunks = _date_chunks(start_d, end_d, 7)
    saved_hours = 0
    failed: List[str] = []

    for idx, (dz, sname, grp_id, ep) in enumerate(tasks, 1):
        cp_key = f"{dz}:{sname}"
        if _is_done(cp, "upstream", cp_key):
            continue

        meta = caches["upstream_by_key"].get(
            (dz, sname),
            {"point_id": None, "data_zone": dz, "source_name": sname, "name": sname, "category": "电厂" if dz == "dc_dict" else "首站", "sub_category": None},
        )
        all_recs: List[Dict[str, Any]] = []
        pt_failed = False

        for c_start, c_end in chunks:
            time.sleep(interval)
            id_key = "dc_station_id" if dz == "dc_dict" else "sz_station_id"
            try:
                r = _post_with_retry(
                    client,
                    f"{base_url}{ep}",
                    data={
                        "start_date": c_start.strftime("%m/%d/%Y"),
                        "end_date": c_end.strftime("%m/%d/%Y"),
                        "station_name": sname,
                        id_key: grp_id,
                    },
                    headers=headers,
                    retries=2,
                )
                if r.status_code != 200:
                    pt_failed = True
                    continue
                arr = r.json()
                if isinstance(arr, list):
                    all_recs.extend(x for x in arr if isinstance(x, dict))
            except Exception as exc:
                logger.warning("[upstream] %s (%s~%s) 异常: %s", cp_key, c_start, c_end, exc)
                pt_failed = True

        if all_recs:
            parsed_pts: List[Tuple[datetime, Dict[str, Any]]] = []
            for rec in all_recs:
                ts = parse_dt_east8(rec.get("tmDate"))
                if ts is None:
                    continue
                parsed_pts.append((ts, rec))
            parsed_pts.sort(key=lambda x: x[0])

            by_hour: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = {}
            prev_valid: Optional[Dict[str, Any]] = None
            for ts, rec in parsed_pts:
                raw_conv = {**rec, "SHIJIAN": rec.get("tmDate")}
                cleaned, _ = clean_upstream_point(raw_conv, meta, ts, prev_valid=prev_valid)
                if cleaned["value_source"] == SRC_REAL and cleaned["temp_clean"] is not None:
                    prev_valid = cleaned
                by_hour.setdefault(floor_to_hour(ts), []).append((ts, cleaned))

            hourly_rows: List[Dict[str, Any]] = []
            for bh, items in sorted(by_hour.items()):
                latest = items[-1][1]
                heat_samples = [(ts, c["heat_clean"]) for ts, c in items]
                flow_samples = [(ts, c["flow_clean"]) for ts, c in items]
                hourly_rows.append({
                    "biz_hour": bh,
                    "point_id": latest["point_id"],
                    "data_zone": dz,
                    "source_name": sname,
                    "display_name": latest["display_name"],
                    "category": latest["category"],
                    "sub_category": latest["sub_category"],
                    "is_core_gk": latest["point_id"] is not None,
                    "sample_count": len(items),
                    "source_time": latest["source_time"],
                    "temp_raw": latest["temp_raw"], "temp_clean": latest["temp_clean"],
                    "pressure_raw": latest["pressure_raw"], "pressure_clean": latest["pressure_clean"],
                    "flow_raw": latest["flow_raw"], "flow_clean": latest["flow_clean"],
                    "heat_raw": latest["heat_raw"], "heat_clean": latest["heat_clean"],
                    "hour_heat_gj": trapezoidal_hour_integral(heat_samples),
                    "hour_flow_t": trapezoidal_hour_integral(flow_samples),
                    "value_source": latest["value_source"],
                    "fault_tag": latest["fault_tag"],
                })

            if hourly_rows:
                with engine.begin() as conn:
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
                saved_hours += len(hourly_rows)

        if not pt_failed:
            _mark_done(cp, "upstream", cp_key, flush=(idx % 10 == 0 or idx == len(tasks)))
        else:
            failed.append(cp_key)
        if idx % 20 == 0 or idx == len(tasks):
            logger.info("[upstream] 进度 %d/%d，已回写点时数=%d，失败=%d", idx, len(tasks), saved_hours, len(failed))

    _save_checkpoint(cp)
    return {"saved_hours": saved_hours, "failed_count": len(failed), "failed": failed[:20]}


# ---------------------------------------------------------------------------
# 4. 商业用户逐小时积分补采 (/sh_ls_zb/)
# ---------------------------------------------------------------------------
def backfill_merchant_hourly(
    client: httpx.Client,
    base_url: str,
    start_d: date,
    end_d: date,
    caches: Dict[str, Any],
    interval: float,
    cp: Dict[str, Any],
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    headers = {"User-Agent": "Phoenix-Backfill/1.0", "Connection": "close"}
    merchants = caches["merchants"][:limit] if limit else caches["merchants"]
    chunks = _date_chunks(start_d, end_d, 7)

    saved_hours = 0
    failed: List[str] = []

    for idx, mc in enumerate(merchants, 1):
        m_id = mc["merchant_id"]
        m_name = mc["name"]
        if _is_done(cp, "merchant_hourly", m_id):
            continue

        all_recs: List[Dict[str, Any]] = []
        m_failed = False
        for c_start, c_end in chunks:
            time.sleep(interval)
            q_start = datetime(c_start.year, c_start.month, c_start.day, 0, 0, tzinfo=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
            q_end = (datetime(c_end.year, c_end.month, c_end.day, 0, 0, tzinfo=EAST_8) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            try:
                r = _post_with_retry(
                    client,
                    f"{base_url}/sh_ls_zb/",
                    data={"name": m_name, "start_date": q_start, "end_date": q_end, "isdownload": "1"},
                    headers=headers,
                    retries=2,
                )
                if r.status_code != 200:
                    m_failed = True
                    continue
                arr = r.json()
                if isinstance(arr, list):
                    all_recs.extend(x for x in arr if isinstance(x, dict))
            except Exception as exc:
                logger.warning("[merchant_hourly] %s (%s~%s) 异常: %s", m_name, c_start, c_end, exc)
                m_failed = True

        if all_recs:
            parsed_pts: List[Tuple[datetime, Dict[str, Any]]] = []
            for rec in all_recs:
                ts = parse_dt_east8(rec.get("tmDate"))
                if ts is None:
                    continue
                parsed_pts.append((ts, rec))
            parsed_pts.sort(key=lambda x: x[0])

            by_hour: Dict[datetime, List[Tuple[datetime, Dict[str, Any]]]] = {}
            prev_valid: Optional[Dict[str, Any]] = None
            for ts, rec in parsed_pts:
                cleaned, _ = clean_merchant_point({**rec, "name": m_name}, caches["merchant_by_name"], ts, prev_valid=prev_valid)
                if cleaned["value_source"] == SRC_REAL:
                    prev_valid = cleaned
                by_hour.setdefault(floor_to_hour(ts), []).append((ts, cleaned))

            upsert_rows: List[Dict[str, Any]] = []
            for bh, pts in sorted(by_hour.items()):
                latest = pts[-1][1]
                heat_samples = [(ts, p["heat_clean"]) for ts, p in pts]
                flow_samples = [(ts, p["flow_clean"]) for ts, p in pts]
                upsert_rows.append({
                    "biz_hour": bh,
                    "merchant_id": m_id,
                    "source_name": m_name,
                    "is_registered": True,
                    "sample_count": len(pts),
                    "online": True,
                    "flow_raw": latest["flow_raw"], "flow_clean": latest["flow_clean"],
                    "return_flow_raw": latest["return_flow_raw"],
                    "temp_sup_raw": latest["temp_sup_raw"], "temp_sup_clean": latest["temp_sup_clean"],
                    "temp_ret_raw": latest["temp_ret_raw"], "temp_ret_clean": latest["temp_ret_clean"],
                    "pres_sup_raw": latest["pres_sup_raw"], "pres_sup_clean": latest["pres_sup_clean"],
                    "pres_ret_raw": latest["pres_ret_raw"], "pres_ret_clean": latest["pres_ret_clean"],
                    "heat_raw": latest["heat_raw"], "heat_clean": latest["heat_clean"],
                    "valve_open": latest["valve_open"], "valve_set": latest["valve_set"],
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
                saved_hours += len(upsert_rows)

        if not m_failed:
            _mark_done(cp, "merchant_hourly", m_id, flush=(idx % 15 == 0 or idx == len(merchants)))
        else:
            failed.append(m_name)
        if idx % 30 == 0 or idx == len(merchants):
            logger.info("[merchant_hourly] 进度 %d/%d，已回写户时数=%d，失败=%d", idx, len(merchants), saved_hours, len(failed))

    _save_checkpoint(cp)
    return {"saved_hours": saved_hours, "failed_count": len(failed), "failed": failed[:20]}


# ---------------------------------------------------------------------------
# 5. 2,097 户居民室温历史补采 (/sw_ls_export/)
# ---------------------------------------------------------------------------
def backfill_temps(
    client: httpx.Client,
    base_url: str,
    cookie: str,
    start_d: date,
    end_d: date,
    interval: float,
    cp: Dict[str, Any],
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    if not cookie:
        logger.warning("未配置 Cookie，跳过居民室温历史补采。")
        return {"skipped": True, "reason": "no_cookie"}

    with engine.connect() as conn:
        devices = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT temp_device_id, station_id, name, terminal_model, remark, station_name_raw "
                    "FROM smart_heating_platform.dict_temp_device ORDER BY temp_device_id"
                )
            ).fetchall()
        ]
    if limit:
        devices = devices[:limit]

    now_e8 = datetime.now(EAST_8)
    max_hour_global = floor_to_hour(now_e8)
    win_start_dt = datetime(start_d.year, start_d.month, start_d.day, 0, 0, tzinfo=EAST_8)
    win_end_dt = min(max_hour_global, datetime(end_d.year, end_d.month, end_d.day, 23, 0, tzinfo=EAST_8))

    target_hours: List[datetime] = []
    ch = win_start_dt
    while ch <= win_end_dt:
        target_hours.append(ch)
        ch += timedelta(hours=1)

    q_start = (win_start_dt - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    q_end = (win_end_dt + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    headers = {"User-Agent": "Phoenix-Backfill/1.0", "Cookie": cookie, "Connection": "close"}

    saved_hours = 0
    failed: List[str] = []
    batch_rows: List[Dict[str, Any]] = []

    def _flush_batch() -> None:
        nonlocal saved_hours
        if not batch_rows:
            return
        with engine.begin() as conn:
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
                batch_rows,
                extra_set_clauses=["updated_at = NOW()"],
            )
        saved_hours += len(batch_rows)
        batch_rows.clear()

    for idx, dev in enumerate(devices, 1):
        did = dev["temp_device_id"]
        if _is_done(cp, "temps", did):
            continue

        time.sleep(interval)
        try:
            r = _post_with_retry(
                client,
                f"{base_url}/sw_ls_export/",
                data={"user_id": did, "start_date": q_start, "end_date": q_end},
                headers=headers,
                retries=2,
            )
            if r.status_code != 200:
                failed.append(did)
                continue
            arr = r.json()
            if not isinstance(arr, list):
                _mark_done(cp, "temps", did, flush=(idx % 25 == 0))
                continue
        except Exception as exc:
            logger.warning("[temps] %s 拉取异常: %s", did, exc)
            failed.append(did)
            continue

        samples: List[Tuple[datetime, Optional[float]]] = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            ts = parse_dt_east8(item.get("year"))
            if ts is None:
                continue
            samples.append((ts, to_float(item.get("value"))))
        samples.sort(key=lambda x: x[0])

        # 双指针将采样映射至每个整点（与 /jumin/ 逻辑一致：展示截至该小时结束前最近一次有效上报）
        s_idx = 0
        latest_sample: Optional[Tuple[datetime, Optional[float]]] = None
        for bh in target_hours:
            bh_end = bh + timedelta(minutes=59, seconds=59)
            while s_idx < len(samples) and samples[s_idx][0] <= bh_end:
                latest_sample = samples[s_idx]
                s_idx += 1
            if latest_sample is None:
                continue
            up_ts, raw_t = latest_sample
            is_fresh = (bh_end - up_ts).total_seconds() <= 7 * 86400
            is_in_range = raw_t is not None and 5.0 < raw_t <= 40.0
            is_valid = is_fresh and is_in_range
            ftag = None
            if not is_fresh:
                ftag = FAULT_COMM_OFFLINE
            elif not is_in_range:
                ftag = FAULT_SENSOR_RANGE
            batch_rows.append({
                "biz_hour": bh,
                "temp_device_id": did,
                "station_id": dev["station_id"],
                "is_registered": True,
                "village_name": dev["name"][:128],
                "station_name_raw": dev["station_name_raw"][:128],
                "zdxh": dev["terminal_model"][:32],
                "temp_raw": raw_t,
                "temp_clean": raw_t if is_valid else None,
                "upload_time": up_ts,
                "is_online_valid": is_valid,
                "remark_snapshot": dev["remark"],
                "fault_tag": ftag,
            })

        _mark_done(cp, "temps", did, flush=False)
        if len(batch_rows) >= 4000 or idx == len(devices):
            _flush_batch()
            _save_checkpoint(cp)
        if idx % 100 == 0 or idx == len(devices):
            logger.info("[temps] 进度 %d/%d，已回写户时数=%d，失败=%d", idx, len(devices), saved_hours, len(failed))

    _flush_batch()
    _save_checkpoint(cp)
    return {"saved_hours": saved_hours, "failed_count": len(failed), "failed": failed[:20]}


def main() -> int:
    parser = argparse.ArgumentParser(description="智慧供热旁路平台历史数据全量补采脚本")
    parser.add_argument("--start", default="2026-11-01", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=datetime.now(EAST_8).date().isoformat(), help="结束日期 YYYY-MM-DD")
    parser.add_argument(
        "--steps",
        default="merchant_daily,stations,upstream,merchant_hourly,temps",
        help="执行步骤，逗号分隔或 all",
    )
    parser.add_argument("--interval", type=float, default=0.8, help="单线程请求间隔（秒）")
    parser.add_argument("--limit", type=int, default=0, help="调试用：每步最多处理主体数（0 表示全量）")
    parser.add_argument("--reset", action="store_true", help="忽略并重置历史断点进度")
    args = parser.parse_args()

    ensure_smart_heating_fact_tables()
    start_d = date.fromisoformat(args.start)
    end_d = date.fromisoformat(args.end)
    interval = max(0.5, float(args.interval))
    limit = args.limit if args.limit > 0 else None

    all_steps = ["merchant_daily", "stations", "upstream", "merchant_hourly", "temps"]
    steps = all_steps if args.steps.strip().lower() == "all" else [s.strip() for s in args.steps.split(",") if s.strip()]

    cp = {"done": {}} if args.reset else _load_checkpoint()
    cfg = _read_raw_config()
    base_url = resolve_effective_base_url(cfg)
    cookie = normalize_cookie_input(str(cfg.get("cookie") or ""))
    caches = _load_dict_caches()

    logger.info("开始全量历史补采：区间=%s~%s, 步骤=%s, 源站=%s, Cookie=%s", start_d, end_d, steps, base_url, "已配置" if cookie else "未配置")

    summary: Dict[str, Any] = {}
    with httpx.Client(timeout=30.0, follow_redirects=False, trust_env=False) as client:
        if "merchant_daily" in steps:
            summary["merchant_daily"] = backfill_merchant_daily(client, base_url, cookie, start_d, end_d, caches, interval)
        if "stations" in steps:
            summary["stations"] = backfill_stations(client, base_url, start_d, end_d, caches, interval, cp, limit=limit)
        if "upstream" in steps:
            summary["upstream"] = backfill_upstream(client, base_url, start_d, end_d, caches, interval, cp, limit=limit)
        if "merchant_hourly" in steps:
            summary["merchant_hourly"] = backfill_merchant_hourly(client, base_url, start_d, end_d, caches, interval, cp, limit=limit)
        if "temps" in steps:
            summary["temps"] = backfill_temps(client, base_url, cookie, start_d, end_d, interval, cp, limit=limit)

    logger.info("历史补采执行结束，总摘要：%s", json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
