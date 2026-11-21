# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 阳面逐小时报告、每日精算日报及双轨对账查询服务。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import re
import openpyxl
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import (
    EAST_8,
    STATION_METER_SCALE_FACTORS,
)
from backend.projects.smart_heating_platform.services.collector_config_service import get_collector_settings_view
from backend.projects.smart_heating_platform.services.db_schema import ensure_smart_heating_fact_tables

# Phoenix 手工日报 (public.daily_basic_data) 公司编码 -> dict_service_center.center_id
CENTER_COMPANY_MAP: Dict[str, int] = {
    "HuaLe_Center": 60,
    "BeiGang_Center": 61,
    "ShuangXing_Center": 62,
    "XiangLuJiao_Center": 63,
    "XingGong_Center": 64,
    "ChunHai_Center": 65,
    "DaFang_Center": 66,
    "ZhongShan_Center": 67,
    "DongGang_Center": 68,
}


def _f(val: Any) -> Optional[float]:
    """Decimal/数值安全转为 float。"""
    if val is None:
        return None
    return float(val)


def _round(val: Optional[float], digits: int = 2) -> Optional[float]:
    return None if val is None else round(val, digits)


def _num_differs(raw_val: Any, clean_val: Any, tol: float = 0.05) -> bool:
    """判断原始值与修正值是否存在实质差异（或原始值有数但被置空）。"""
    r = _f(raw_val)
    c = _f(clean_val)
    if r is None:
        return False
    if c is None:
        return True
    return abs(r - c) > tol


def _fmt_num(val: Any, digits: int = 2) -> str:
    v = _f(val)
    return "空" if v is None else f"{v:.{digits}f}".rstrip("0").rstrip(".")


BURST_MAX_HOURS_PER_DAY = 6
BURST_HEAT_JUMP_THRESHOLD = 100.0


def _is_scale_only_heat_diff(row: Dict[str, Any], station_name: str) -> bool:
    """判断站点小时热量差异是否仅来自固定台账表底倍率换算（÷10 / ×3.6），而非突发跳变。"""
    scale_entry = STATION_METER_SCALE_FACTORS.get(station_name)
    if not scale_entry:
        return False
    fault_tag = str(row.get("fault_tag") or "")
    if "METER_JUMP" in fault_tag or "HEAT_SPIKE" in fault_tag:
        return False
    raw_gj = _f(row.get("hour_heat_raw_gj"))
    clean_gj = _f(row.get("hour_heat_gj"))
    if raw_gj is None or clean_gj is None:
        return False
    factor = float(scale_entry[0])
    expected = raw_gj * factor
    return abs(clean_gj - expected) <= max(1.0, abs(expected) * 0.15)


def _count_station_day_anomalies(
    rows: Sequence[Dict[str, Any]],
    name_resolver: Any,
) -> Dict[str, Dict[str, int]]:
    """按站统计当天各字段发生数值修正的小时数，用于区分“突发跳变”与“全天长期传感器故障”。"""
    counts: Dict[str, Dict[str, int]] = {}
    for row in rows:
        sid = row.get("station_id")
        if not sid:
            continue
        st_name = str(name_resolver(row) or sid)
        c = counts.setdefault(sid, {"heat": 0, "e11": 0, "temp": 0, "pres": 0, "water": 0})
        fault_tag = str(row.get("fault_tag") or "")

        if not _is_scale_only_heat_diff(row, st_name):
            raw_gj = _f(row.get("hour_heat_raw_gj"))
            clean_gj = _f(row.get("hour_heat_gj"))
            if _num_differs(raw_gj, clean_gj, tol=0.5) or (
                "METER_JUMP" in fault_tag and _num_differs(raw_gj, clean_gj, tol=0.05)
            ):
                c["heat"] += 1
        if _num_differs(row.get("e11_raw"), row.get("e11_clean"), tol=0.5):
            c["e11"] += 1
        if _num_differs(row.get("e3_raw"), row.get("e3_clean"), tol=0.5) or _num_differs(
            row.get("e4_raw"), row.get("e4_clean"), tol=0.5
        ):
            c["temp"] += 1
        if _num_differs(row.get("e7_raw"), row.get("e7_clean"), tol=0.05) or _num_differs(
            row.get("e8_raw"), row.get("e8_clean"), tol=0.05
        ):
            c["pres"] += 1
        if _num_differs(row.get("e14_raw"), row.get("e14_clean"), tol=0.5):
            c["water"] += 1
    return counts


def _is_burst_metric(
    raw_val: Any,
    clean_val: Any,
    day_count: Optional[int],
    huge_diff: float = BURST_HEAT_JUMP_THRESHOLD,
) -> bool:
    """判定是否为突发跳变：单日仅偶发修正（<=6小时），排除持续性长期传感器故障。"""
    if day_count is not None:
        return 0 < day_count <= BURST_MAX_HOURS_PER_DAY
    r = _f(raw_val)
    c = _f(clean_val)
    if r is not None and c is not None and abs(r - c) >= huge_diff:
        return True
    return True


def _fmt_anom_pair(station_name: str, label: str, raw_txt: str, clean_txt: str, mode: str) -> str:
    if str(mode).lower() == "raw":
        return f"{station_name}: 突发{label}异常原值 {raw_txt}（修正后为 {clean_txt}）"
    return f"{station_name}: 突发{label}已修正（原值 {raw_txt} → 修正 {clean_txt}）"


def _build_station_hour_anomalies(
    row: Dict[str, Any],
    station_name: str,
    day_counts: Optional[Dict[str, int]] = None,
    mode: str = "clean",
) -> Dict[str, str]:
    """抽取单座换热站单小时“突发跳变/突越限”异常备注（剔除固定单位折算与长期固定坏表）。"""
    notes: Dict[str, str] = {}
    fault_tag = str(row.get("fault_tag") or "")
    counts = day_counts or {}

    raw_gj = _f(row.get("hour_heat_raw_gj"))
    clean_gj = _f(row.get("hour_heat_gj"))
    if not _is_scale_only_heat_diff(row, station_name):
        heat_changed = _num_differs(raw_gj, clean_gj, tol=0.5) or (
            "METER_JUMP" in fault_tag and _num_differs(raw_gj, clean_gj, tol=0.05)
        )
        if heat_changed and _is_burst_metric(raw_gj, clean_gj, counts.get("heat")):
            notes["hour_heat_gj"] = _fmt_anom_pair(
                station_name,
                "热量跳变",
                f"{_fmt_num(raw_gj)} GJ",
                f"{_fmt_num(clean_gj)} GJ",
                mode,
            )

    if _num_differs(row.get("e11_raw"), row.get("e11_clean"), tol=0.5) and _is_burst_metric(
        row.get("e11_raw"), row.get("e11_clean"), counts.get("e11")
    ):
        e11_note = _fmt_anom_pair(
            station_name,
            "瞬时热量跳变",
            f"{_fmt_num(row.get('e11_raw'))} GJ/h",
            f"{_fmt_num(row.get('e11_clean'))} GJ/h",
            mode,
        )
        notes["e11"] = e11_note
        notes["heat_index_wm2"] = e11_note

    if (
        _num_differs(row.get("e3_raw"), row.get("e3_clean"), tol=0.5)
        or _num_differs(row.get("e4_raw"), row.get("e4_clean"), tol=0.5)
    ) and _is_burst_metric(row.get("e3_raw"), row.get("e3_clean"), counts.get("temp"), huge_diff=80.0):
        notes["e3_e4"] = _fmt_anom_pair(
            station_name,
            "供回温跳变",
            f"{_fmt_num(row.get('e3_raw'))}/{_fmt_num(row.get('e4_raw'))}℃",
            f"{_fmt_num(row.get('e3_clean'))}/{_fmt_num(row.get('e4_clean'))}℃",
            mode,
        )

    if (
        _num_differs(row.get("e7_raw"), row.get("e7_clean"), tol=0.05)
        or _num_differs(row.get("e8_raw"), row.get("e8_clean"), tol=0.05)
    ) and _is_burst_metric(row.get("e7_raw"), row.get("e7_clean"), counts.get("pres"), huge_diff=5.0):
        notes["e7_e8"] = _fmt_anom_pair(
            station_name,
            "压力跳变",
            f"{_fmt_num(row.get('e7_raw'), 3)}/{_fmt_num(row.get('e8_raw'), 3)} MPa",
            f"{_fmt_num(row.get('e7_clean'), 3)}/{_fmt_num(row.get('e8_clean'), 3)} MPa",
            mode,
        )

    if _num_differs(row.get("e14_raw"), row.get("e14_clean"), tol=0.5) and _is_burst_metric(
        row.get("e14_raw"), row.get("e14_clean"), counts.get("water"), huge_diff=50.0
    ):
        notes["e14"] = _fmt_anom_pair(
            station_name,
            "补水跳变",
            f"{_fmt_num(row.get('e14_raw'))} t/h",
            f"{_fmt_num(row.get('e14_clean'))} t/h",
            mode,
        )

    return notes


def _pack_agg_anomaly(note_list: Sequence[str]) -> Optional[Dict[str, Any]]:
    """将多个受影响站点的修正明细打包为统一聚合标注字典。"""
    unique = list(dict.fromkeys(n for n in note_list if n))
    if not unique:
        return None
    preview = "；".join(unique[:5]) + (" 等" if len(unique) > 5 else "")
    return {
        "count": len(unique),
        "note": f"受 {len(unique)} 项异常修正影响：{preview}",
    }


def _compute_weighted_temp_and_kpis(
    stations: List[Dict[str, Any]],
    temps_by_station: Dict[str, List[float]],
    mode: str,
) -> Dict[str, Any]:
    """按统一口径聚合一组换热站与居民室温的核心指标（用于全网及四大分组），并传递各指标受异常修正的影响标注。"""
    total_stations = len(stations)
    online_stations = sum(1 for s in stations if s.get("online"))
    area_m2 = sum((s.get("covered_area") or 0.0) for s in stations)
    missing_area_count = sum(1 for s in stations if s.get("covered_area") is None)

    hour_heat_gj = 0.0
    instant_load_gjh = 0.0
    hour_water_t = 0.0
    hour_elec_kwh = 0.0
    has_heat = False
    has_load = False
    has_water = False
    has_elec = False

    heat_anom_notes: List[str] = []
    load_anom_notes: List[str] = []
    water_anom_notes: List[str] = []
    temp_anom_notes: List[str] = []

    # 流量加权均温累计器
    sup_w_sum = 0.0
    sup_flow_sum = 0.0
    ret_w_sum = 0.0
    ret_flow_sum = 0.0
    pres_ret_vals: List[float] = []

    temp_vals: List[float] = []
    for s in stations:
        fn = s.get("field_notes") or {}
        if fn.get("hour_heat_gj"):
            heat_anom_notes.append(fn["hour_heat_gj"])
        if fn.get("e11"):
            load_anom_notes.append(fn["e11"])
        if fn.get("e14"):
            water_anom_notes.append(fn["e14"])
        if fn.get("e3_e4"):
            temp_anom_notes.append(fn["e3_e4"])

        e1 = s.get("e1")
        e3 = s.get("e3")
        e4 = s.get("e4")
        e8 = s.get("e8")
        e11 = s.get("e11")
        e14 = s.get("e14")
        hg = s.get("hour_heat_gj")
        hw = s.get("hour_water_t")
        he = s.get("hour_elec_kwh")

        if hg is not None:
            hour_heat_gj += hg
            has_heat = True
        if e11 is not None:
            instant_load_gjh += e11
            has_load = True
        if hw is not None:
            hour_water_t += hw
            has_water = True
        elif e14 is not None:
            hour_water_t += e14
            has_water = True
        if he is not None:
            hour_elec_kwh += he
            has_elec = True

        w = e1 if (e1 is not None and e1 > 0.0) else 0.0
        if w > 0 and e3 is not None:
            sup_w_sum += e3 * w
            sup_flow_sum += w
        if w > 0 and e4 is not None:
            ret_w_sum += e4 * w
            ret_flow_sum += w
        if e8 is not None:
            pres_ret_vals.append(e8)

        temp_vals.extend(temps_by_station.get(s["station_id"], []))

    area_wan = area_m2 / 10000.0 if area_m2 > 0 else 0.0
    avg_sup = (sup_w_sum / sup_flow_sum) if sup_flow_sum > 0 else None
    avg_ret = (ret_w_sum / ret_flow_sum) if ret_flow_sum > 0 else None
    avg_diff = (avg_sup - avg_ret) if (avg_sup is not None and avg_ret is not None) else None
    avg_pres_ret = (sum(pres_ret_vals) / len(pres_ret_vals)) if pres_ret_vals else None

    # 1 GJ/h = 277,777.78 W
    heat_index_wm2 = (instant_load_gjh * 277777.78 / area_m2) if (has_load and area_m2 > 0) else None
    heat_per_wan = (hour_heat_gj / area_wan) if (has_heat and area_wan > 0) else None
    water_per_wan = (hour_water_t / area_wan) if (has_water and area_wan > 0) else None
    elec_per_wan = (hour_elec_kwh / area_wan) if (has_elec and area_wan > 0) else None

    avg_room_temp = (sum(temp_vals) / len(temp_vals)) if temp_vals else None
    pass_rate = (sum(1 for t in temp_vals if t >= 18.0) / len(temp_vals) * 100.0) if temp_vals else None
    comfort_rate = (sum(1 for t in temp_vals if 20.0 <= t <= 25.0) / len(temp_vals) * 100.0) if temp_vals else None

    anomalies: Dict[str, Dict[str, Any]] = {}
    heat_pack = _pack_agg_anomaly(heat_anom_notes)
    load_pack = _pack_agg_anomaly(load_anom_notes)
    water_pack = _pack_agg_anomaly(water_anom_notes)
    temp_pack = _pack_agg_anomaly(temp_anom_notes)
    if heat_pack:
        anomalies["hour_heat_gj"] = heat_pack
        anomalies["heat_per_wan_gj"] = heat_pack
    if load_pack:
        anomalies["instant_load_gjh"] = load_pack
        anomalies["heat_index_wm2"] = load_pack
    if water_pack:
        anomalies["hour_water_t"] = water_pack
        anomalies["water_per_wan_t"] = water_pack
    if temp_pack:
        anomalies["avg_sup_temp"] = temp_pack
        anomalies["avg_ret_temp"] = temp_pack
        anomalies["avg_temp_diff"] = temp_pack

    return {
        "total_stations": total_stations,
        "online_stations": online_stations,
        "online_rate_pct": _round((online_stations / total_stations * 100.0) if total_stations else 0.0, 1),
        "covered_area_m2": _round(area_m2, 2),
        "covered_area_wan": _round(area_wan, 2),
        "missing_area_count": missing_area_count,
        "hour_heat_gj": _round(hour_heat_gj, 2) if has_heat else None,
        "instant_load_gjh": _round(instant_load_gjh, 2) if has_load else None,
        "heat_index_wm2": _round(heat_index_wm2, 2),
        "heat_per_wan_gj": _round(heat_per_wan, 2),
        "hour_water_t": _round(hour_water_t, 2) if has_water else None,
        "water_per_wan_t": _round(water_per_wan, 2),
        "hour_elec_kwh": _round(hour_elec_kwh, 2) if has_elec else None,
        "elec_per_wan_kwh": _round(elec_per_wan, 2),
        "avg_sup_temp": _round(avg_sup, 2),
        "avg_ret_temp": _round(avg_ret, 2),
        "avg_temp_diff": _round(avg_diff, 2),
        "avg_ret_pressure": _round(avg_pres_ret, 3),
        "valid_temp_count": len(temp_vals),
        "avg_room_temp": _round(avg_room_temp, 2),
        "temp_pass_rate_pct": _round(pass_rate, 1),
        "temp_comfort_rate_pct": _round(comfort_rate, 1),
        "anomalies": anomalies,
    }


def _load_outdoor_temps_24h(target_date: date) -> Dict[int, float]:
    """从 Phoenix public.temperature_data 查询指定日期各小时近端室外气温。"""
    day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    day_end = day_start + timedelta(days=1)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM date_time)::INT AS hr, AVG(value) AS val "
                "FROM public.temperature_data "
                "WHERE type = 'near' AND date_time >= :ds AND date_time < :de "
                "GROUP BY 1"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()
    return {int(r.hr): round(float(r.val), 1) for r in rows if r.val is not None}


def _build_trend_24h_from_rows(
    st_day_maps: Sequence[Dict[str, Any]],
    outdoor_24h: Dict[int, float],
    mode: str,
    temp_24h_map: Optional[Dict[int, Optional[float]]] = None,
) -> List[Dict[str, Any]]:
    """根据一批站-小时记录聚合 24 小时柱形/折线趋势，并保留突发跳变标注。"""
    use_raw = str(mode).lower() == "raw"
    st_day_counts = _count_station_day_anomalies(
        st_day_maps,
        lambda rm: rm.get("station_name") or rm.get("station_id"),
    )
    day_bucket: Dict[int, List[Dict[str, Any]]] = {h: [] for h in range(24)}
    for row_map in st_day_maps:
        sid = row_map["station_id"]
        day_bucket[int(row_map["hr"])].append({
            "station_id": sid,
            "online": row_map["online"],
            "covered_area": _f(row_map["covered_area"]),
            "e1": _f(row_map["e1_raw"] if use_raw else row_map["e1_clean"]),
            "e3": _f(row_map["e3_raw"] if use_raw else row_map["e3_clean"]),
            "e4": _f(row_map["e4_raw"] if use_raw else row_map["e4_clean"]),
            "e11": _f(row_map["e11_raw"] if use_raw else row_map["e11_clean"]),
            "e14": _f(row_map["e14_raw"] if use_raw else row_map["e14_clean"]),
            "hour_heat_gj": _f(
                row_map["hour_heat_raw_gj"]
                if (use_raw and row_map["hour_heat_raw_gj"] is not None)
                else row_map["hour_heat_gj"]
            ),
            "hour_water_t": _f(row_map["hour_water_t"]),
            "field_notes": _build_station_hour_anomalies(
                row_map,
                str(row_map.get("station_name") or sid),
                day_counts=st_day_counts.get(sid),
                mode=mode,
            ),
        })

    trend_24h: List[Dict[str, Any]] = []
    temp_map = temp_24h_map or {}
    for h in range(24):
        items = day_bucket[h]
        k = _compute_weighted_temp_and_kpis(items, {}, mode) if items else {}
        trend_24h.append({
            "hour": h,
            "label": f"{h:02d}:00",
            "has_data": len(items) > 0,
            "station_count": len(items),
            "hour_heat_gj": k.get("hour_heat_gj"),
            "heat_index_wm2": k.get("heat_index_wm2"),
            "avg_sup_temp": k.get("avg_sup_temp"),
            "avg_ret_temp": k.get("avg_ret_temp"),
            "avg_room_temp": temp_map.get(h),
            "outdoor_temp": outdoor_24h.get(h),
            "anomalies": k.get("anomalies", {}),
        })
    return trend_24h


def _resolve_latest_available_biz_hour(
    conn: Any,
    target_d: Optional[date] = None,
) -> Optional[datetime]:
    """查询指定日期（或全库）最新一个已有数据的小时断面（优先换热站表底校准小时，其次上游/商业户）。"""
    tables = (
        "fact_station_hourly",
        "fact_upstream_hourly",
        "fact_merchant_hourly",
    )
    if target_d is not None:
        ds = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        de = ds + timedelta(days=1)
        for tbl in tables:
            val = conn.execute(
                text(f"SELECT MAX(biz_hour) FROM smart_heating_platform.{tbl} WHERE biz_hour >= :ds AND biz_hour < :de"),
                {"ds": ds, "de": de},
            ).scalar()
            if val is not None:
                return val.astimezone(EAST_8) if val.tzinfo else val.replace(tzinfo=EAST_8)
        return None

    for tbl in tables:
        val = conn.execute(text(f"SELECT MAX(biz_hour) FROM smart_heating_platform.{tbl}")).scalar()
        if val is not None:
            return val.astimezone(EAST_8) if val.tzinfo else val.replace(tzinfo=EAST_8)
    return None


def get_hourly_report(target_date_str: Optional[str], hour: Optional[int], mode: str = "clean") -> Dict[str, Any]:
    """构建【界面一：阳面逐小时精细化运行报告】全量数据载荷。"""
    ensure_smart_heating_fact_tables()
    now_e8 = datetime.now(EAST_8)
    use_raw = str(mode).lower() == "raw"

    with engine.connect() as conn:
        if target_date_str is None and hour is None:
            latest_bh = _resolve_latest_available_biz_hour(conn, target_d=None)
            if latest_bh is not None:
                target_d = latest_bh.date()
                sel_hour = latest_bh.hour
            else:
                target_d = now_e8.date()
                sel_hour = now_e8.hour
        elif target_date_str is not None and hour is None:
            target_d = date.fromisoformat(target_date_str)
            latest_day_bh = _resolve_latest_available_biz_hour(conn, target_d=target_d)
            if latest_day_bh is not None:
                sel_hour = latest_day_bh.hour
            else:
                sel_hour = now_e8.hour if target_d == now_e8.date() else 23
        else:
            target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
            sel_hour = now_e8.hour if hour is None else max(0, min(23, int(hour)))

        biz_hour = datetime(target_d.year, target_d.month, target_d.day, sel_hour, 0, 0, tzinfo=EAST_8)
        day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        day_end = day_start + timedelta(days=1)

    outdoor_24h = _load_outdoor_temps_24h(target_d)

    with engine.connect() as conn:
        # 1. 静态主体与关联
        stations_meta = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT hs.station_id, hs.name, hs.center_id, sc.name AS center_name, "
                    "hs.branch_network_id, bn.name AS branch_name, bn.main_network_id, mn.name AS main_name, "
                    "hs.covered_area, hs.rdfz, hs.rdry, hs.rdss "
                    "FROM smart_heating_platform.dict_heating_station hs "
                    "JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id "
                    "JOIN smart_heating_platform.dict_branch_network bn ON hs.branch_network_id = bn.branch_network_id "
                    "JOIN smart_heating_platform.dict_main_network mn ON bn.main_network_id = mn.main_network_id "
                    "ORDER BY hs.center_id, hs.name"
                )
            ).fetchall()
        ]

        # 2. 当天 24 小时全网趋势聚合 (供趋势折线图与时间轴状态条)
        st_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (f.biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "f.station_id, hs.name AS station_name, f.online, f.e1_raw, f.e1_clean, f.e3_raw, f.e3_clean, "
                "f.e4_raw, f.e4_clean, f.e7_raw, f.e7_clean, f.e8_raw, f.e8_clean, "
                "f.e11_raw, f.e11_clean, f.e14_raw, f.e14_clean, "
                "f.hour_heat_raw_gj, f.hour_heat_gj, f.hour_heat_source, f.hour_water_t, "
                "f.value_source, f.fault_tag, hs.covered_area "
                "FROM smart_heating_platform.fact_station_hourly f "
                "JOIN smart_heating_platform.dict_heating_station hs ON f.station_id = hs.station_id "
                "WHERE f.biz_hour >= :ds AND f.biz_hour < :de"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()

        temp_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "AVG(temp_clean) AS avg_temp, COUNT(*) AS cnt "
                "FROM smart_heating_platform.fact_temp_hourly "
                "WHERE biz_hour >= :ds AND biz_hour < :de AND is_online_valid IS TRUE "
                "GROUP BY 1"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()
        temp_24h_map = {int(r.hr): _round(_f(r.avg_temp), 2) for r in temp_day_rows}

        # 3. 选中小时的站、上游、室温、运行日志（已停用二次网分区统计）
        st_hour_map = {
            r.station_id: dict(r._mapping)
            for r in conn.execute(
                text("SELECT * FROM smart_heating_platform.fact_station_hourly WHERE biz_hour = :bh"),
                {"bh": biz_hour},
            ).fetchall()
        }
        up_hour_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT * FROM smart_heating_platform.fact_upstream_hourly "
                    "WHERE biz_hour = :bh ORDER BY is_core_gk DESC, category, data_zone, display_name"
                ),
                {"bh": biz_hour},
            ).fetchall()
        ]
        temp_hour_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT temp_device_id, station_id, is_registered, temp_raw, temp_clean, is_online_valid "
                    "FROM smart_heating_platform.fact_temp_hourly WHERE biz_hour = :bh"
                ),
                {"bh": biz_hour},
            ).fetchall()
        ]
        merchants_meta = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT m.merchant_id, m.name, m.rdfz, m.rdry, m.rdss, m.rdjg, m.rdgz, "
                    "m.branch_network_id, bn.name AS branch_name, bn.main_network_id, mn.name AS main_name "
                    "FROM smart_heating_platform.dict_merchant m "
                    "JOIN smart_heating_platform.dict_branch_network bn ON m.branch_network_id = bn.branch_network_id "
                    "JOIN smart_heating_platform.dict_main_network mn ON bn.main_network_id = mn.main_network_id "
                    "ORDER BY mn.main_network_id, bn.branch_network_id, m.name"
                )
            ).fetchall()
        ]
        mc_hour_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT * FROM smart_heating_platform.fact_merchant_hourly WHERE biz_hour = :bh"
                ),
                {"bh": biz_hour},
            ).fetchall()
        ]
        # 统计当天上游与商业户各测点出现非单位折算越限的小时数，区分“突发跳变”与“全天长期坏表”
        up_day_counts: Dict[Tuple[str, str], Dict[str, int]] = {}
        for ur in conn.execute(
            text(
                "SELECT data_zone, source_name, display_name, temp_raw, temp_clean, pressure_raw, pressure_clean, "
                "heat_raw, heat_clean, hour_heat_raw_gj, hour_heat_gj "
                "FROM smart_heating_platform.fact_upstream_hourly "
                "WHERE biz_hour >= :ds AND biz_hour < :de"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall():
            uk = (str(ur.data_zone), str(ur.source_name))
            uc = up_day_counts.setdefault(uk, {"temp": 0, "pres": 0, "heat": 0})
            if _num_differs(ur.temp_raw, ur.temp_clean, tol=0.5):
                uc["temp"] += 1
            if _num_differs(ur.pressure_raw, ur.pressure_clean, tol=0.05):
                uc["pres"] += 1
            if "累计" not in str(ur.display_name or ur.source_name or "") and (
                _num_differs(ur.heat_raw, ur.heat_clean, tol=1.0)
                or _num_differs(ur.hour_heat_raw_gj, ur.hour_heat_gj, tol=1.0)
            ):
                uc["heat"] += 1

        mc_day_counts: Dict[str, Dict[str, int]] = {}
        for mr in conn.execute(
            text(
                "SELECT f.merchant_id, m.rdry, f.flow_raw, f.flow_clean, f.temp_sup_raw, f.temp_sup_clean, "
                "f.temp_ret_raw, f.temp_ret_clean, f.pres_sup_raw, f.pres_sup_clean, "
                "f.pres_ret_raw, f.pres_ret_clean, f.heat_raw, f.heat_clean "
                "FROM smart_heating_platform.fact_merchant_hourly f "
                "JOIN smart_heating_platform.dict_merchant m ON f.merchant_id = m.merchant_id "
                "WHERE f.biz_hour >= :ds AND f.biz_hour < :de AND f.is_registered IS TRUE"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall():
            if str(mr.rdry or "").strip() == "蒸汽":
                continue
            mc = mc_day_counts.setdefault(mr.merchant_id, {"flow": 0, "temp": 0, "pres": 0, "heat": 0})
            if _num_differs(mr.flow_raw, mr.flow_clean, tol=0.5):
                mc["flow"] += 1
            if _num_differs(mr.temp_sup_raw, mr.temp_sup_clean, tol=0.5) or _num_differs(
                mr.temp_ret_raw, mr.temp_ret_clean, tol=0.5
            ):
                mc["temp"] += 1
            if _num_differs(mr.pres_sup_raw, mr.pres_sup_clean, tol=0.05) or _num_differs(
                mr.pres_ret_raw, mr.pres_ret_clean, tol=0.05
            ):
                mc["pres"] += 1
            if _num_differs(mr.heat_raw, mr.heat_clean, tol=0.5):
                mc["heat"] += 1
        last_run = conn.execute(
            text(
                "SELECT run_id, run_type, status, finished_at, summary_json "
                "FROM smart_heating_platform.fact_collector_run "
                "ORDER BY run_id DESC LIMIT 1"
            )
        ).mappings().first()

    # 构建全网 24h 趋势（与单主体 24h 趋势共用同一套聚合及突发跳变标注引擎）
    st_day_maps = [dict(r._mapping) for r in st_day_rows]
    st_day_counts = _count_station_day_anomalies(
        st_day_maps,
        lambda rm: rm.get("station_name") or rm.get("station_id"),
    )
    trend_24h = _build_trend_24h_from_rows(
        st_day_maps,
        outdoor_24h,
        mode,
        temp_24h_map=temp_24h_map,
    )

    # 整理当前选中小时的居民室温统计与站级分桶
    temps_by_station: Dict[str, List[float]] = {}
    room_dist = {"under_18": 0, "ok_18_20": 0, "comfort_20_25": 0, "over_25": 0}
    total_raw_devices = len(temp_hour_rows)
    unregistered_excluded = 0
    offline_invalid_excluded = 0

    for t in temp_hour_rows:
        if not t["is_registered"]:
            unregistered_excluded += 1
            continue
        if not t["is_online_valid"] or t["temp_clean"] is None:
            offline_invalid_excluded += 1
            continue
        val = float(t["temp_clean"])
        st_id = t.get("station_id")
        if st_id:
            temps_by_station.setdefault(st_id, []).append(val)
        if val < 18.0:
            room_dist["under_18"] += 1
        elif val < 20.0:
            room_dist["ok_18_20"] += 1
        elif val <= 25.0:
            room_dist["comfort_20_25"] += 1
        else:
            room_dist["over_25"] += 1

    # 已停用二次网分区统计，保持接口结构兼容并返回空数组
    zones_by_station: Dict[str, List[Dict[str, Any]]] = {}

    # 整理 242 站小时全貌
    stations_full: List[Dict[str, Any]] = []
    for sm in stations_meta:
        st_id = sm["station_id"]
        sf = st_hour_map.get(st_id) or {}
        st_temps = temps_by_station.get(st_id, [])
        st_avg_temp = _round(sum(st_temps) / len(st_temps), 2) if st_temps else None
        st_pass_pct = _round(sum(1 for x in st_temps if x >= 18.0) / len(st_temps) * 100.0, 1) if st_temps else None

        e1 = _f(sf.get("e1_raw") if use_raw else sf.get("e1_clean"))
        e3 = _f(sf.get("e3_raw") if use_raw else sf.get("e3_clean"))
        e4 = _f(sf.get("e4_raw") if use_raw else sf.get("e4_clean"))
        e7 = _f(sf.get("e7_raw") if use_raw else sf.get("e7_clean"))
        e8 = _f(sf.get("e8_raw") if use_raw else sf.get("e8_clean"))
        e11 = _f(sf.get("e11_raw") if use_raw else sf.get("e11_clean"))
        e14 = _f(sf.get("e14_raw") if use_raw else sf.get("e14_clean"))
        area = _f(sm.get("covered_area"))
        heat_wm2 = _round(e11 * 277777.78 / area, 2) if (e11 is not None and area and area > 0) else None
        field_notes = (
            _build_station_hour_anomalies(
                sf,
                sm["name"],
                day_counts=st_day_counts.get(st_id),
                mode=mode,
            )
            if sf
            else {}
        )

        stations_full.append({
            "station_id": st_id,
            "name": sm["name"],
            "center_id": sm["center_id"],
            "center_name": sm["center_name"],
            "main_network_id": sm["main_network_id"],
            "main_name": sm["main_name"],
            "branch_network_id": sm["branch_network_id"],
            "branch_name": sm["branch_name"],
            "rdfz": sm["rdfz"],
            "rdry": sm["rdry"],
            "rdss": sm["rdss"],
            "covered_area": area,
            "online": bool(sf.get("online")) if sf else False,
            "has_record": bool(sf),
            "sample_count": sf.get("sample_count", 0),
            "source_update_time": sf["source_update_time"].strftime("%Y-%m-%d %H:%M:%S") if sf.get("source_update_time") else None,
            "e1": e1,
            "e3": e3,
            "e4": e4,
            "e7": e7,
            "e8": e8,
            "e11": e11,
            "e14": e14,
            "e16": _f(sf.get("e16_raw")),
            "heat_index_wm2": heat_wm2,
            "tot_j": _f(sf.get("tot_j")),
            "tot_f": _f(sf.get("tot_f")),
            "hour_heat_gj": _f(sf.get("hour_heat_raw_gj") if (use_raw and sf.get("hour_heat_raw_gj") is not None) else sf.get("hour_heat_gj")),
            "hour_heat_raw_gj": _f(sf.get("hour_heat_raw_gj")),
            "hour_heat_source": sf.get("hour_heat_source"),
            "hour_flow_t": _f(sf.get("hour_flow_t")),
            "hour_water_t": _f(sf.get("hour_water_t")),
            "hour_elec_kwh": _f(sf.get("hour_elec_kwh")),
            "zone_heat_sum_e12": _f(sf.get("zone_heat_sum_e12")),
            "heat_balance_diff_pct": _f(sf.get("heat_balance_diff_pct")),
            "value_source": sf.get("value_source") or "NO_DATA",
            "fault_tag": sf.get("fault_tag"),
            "field_notes": field_notes,
            "avg_room_temp": st_avg_temp,
            "temp_valid_count": len(st_temps),
            "temp_pass_rate_pct": st_pass_pct,
            "zones": zones_by_station.get(st_id, []),
        })

    # 全网 KPI
    overall_kpi = _compute_weighted_temp_and_kpis(stations_full, temps_by_station, mode)
    overall_kpi["outdoor_temp"] = outdoor_24h.get(sel_hour)

    # 4 种维度聚合汇总
    def _group_by(key_field: str, label_field: str) -> List[Dict[str, Any]]:
        buckets: Dict[Any, List[Dict[str, Any]]] = {}
        labels: Dict[Any, str] = {}
        for s in stations_full:
            k = s[key_field]
            buckets.setdefault(k, []).append(s)
            labels[k] = s[label_field]
        res = []
        for k, group_items in buckets.items():
            agg = _compute_weighted_temp_and_kpis(group_items, temps_by_station, mode)
            res.append({"group_key": k, "group_name": labels[k], **agg})
        return sorted(res, key=lambda x: str(x["group_key"]))

    group_summaries = {
        "by_center": _group_by("center_id", "center_name"),
        "by_rdfz": _group_by("rdfz", "rdfz"),
        "by_main": _group_by("main_network_id", "main_name"),
        "by_branch": _group_by("branch_network_id", "branch_name"),
    }

    upstream_points: List[Dict[str, Any]] = []
    for u in up_hour_rows:
        u_notes: Dict[str, str] = {}
        u_name = str(u.get("display_name") or u.get("source_name") or "")
        uc = up_day_counts.get((str(u["data_zone"]), str(u["source_name"])), {})
        if _num_differs(u.get("temp_raw"), u.get("temp_clean"), tol=0.5) and _is_burst_metric(
            u.get("temp_raw"), u.get("temp_clean"), uc.get("temp"), huge_diff=80.0
        ):
            u_notes["temp"] = _fmt_anom_pair(
                u_name, "温度跳变", f"{_fmt_num(u.get('temp_raw'))}℃", f"{_fmt_num(u.get('temp_clean'))}℃", mode
            )
        if _num_differs(u.get("pressure_raw"), u.get("pressure_clean"), tol=0.05) and _is_burst_metric(
            u.get("pressure_raw"), u.get("pressure_clean"), uc.get("pres"), huge_diff=5.0
        ):
            u_notes["pressure"] = _fmt_anom_pair(
                u_name,
                "压力跳变",
                f"{_fmt_num(u.get('pressure_raw'), 3)} MPa",
                f"{_fmt_num(u.get('pressure_clean'), 3)} MPa",
                mode,
            )
        if "累计" not in u_name and (
            _num_differs(u.get("heat_raw"), u.get("heat_clean"), tol=1.0)
            or _num_differs(u.get("hour_heat_raw_gj"), u.get("hour_heat_gj"), tol=1.0)
        ) and _is_burst_metric(
            u.get("hour_heat_raw_gj") if u.get("hour_heat_raw_gj") is not None else u.get("heat_raw"),
            u.get("hour_heat_gj") if u.get("hour_heat_gj") is not None else u.get("heat_clean"),
            uc.get("heat"),
        ):
            h_txt = _fmt_anom_pair(
                u_name,
                "热量跳变",
                f"{_fmt_num(u.get('hour_heat_raw_gj') or u.get('heat_raw'))} GJ",
                f"{_fmt_num(u.get('hour_heat_gj') if u.get('hour_heat_gj') is not None else u.get('heat_clean'))} GJ",
                mode,
            )
            u_notes["heat"] = h_txt
            u_notes["hour_heat_gj"] = h_txt
        upstream_points.append({
            "point_id": u.get("point_id"),
            "data_zone": u["data_zone"],
            "source_name": u["source_name"],
            "display_name": u["display_name"],
            "category": u["category"],
            "sub_category": u.get("sub_category"),
            "is_core_gk": u.get("is_core_gk"),
            "sample_count": u.get("sample_count", 0),
            "source_time": u["source_time"].strftime("%Y-%m-%d %H:%M:%S") if u.get("source_time") else None,
            "temp": _f(u.get("temp_raw") if use_raw else u.get("temp_clean")),
            "temp_raw": _f(u.get("temp_raw")),
            "pressure": _f(u.get("pressure_raw") if use_raw else u.get("pressure_clean")),
            "flow": _f(u.get("flow_raw") if use_raw else u.get("flow_clean")),
            "heat": _f(u.get("heat_raw") if use_raw else u.get("heat_clean")),
            "hour_heat_gj": _f(u.get("hour_heat_raw_gj") if (use_raw and u.get("hour_heat_raw_gj") is not None) else u.get("hour_heat_gj")),
            "hour_heat_raw_gj": _f(u.get("hour_heat_raw_gj")),
            "hour_flow_t": _f(u.get("hour_flow_t")),
            "value_source": u.get("value_source"),
            "fault_tag": u.get("fault_tag"),
            "field_notes": u_notes,
        })

    temp_station_rankings = [
        {
            "station_id": s["station_id"],
            "name": s["name"],
            "center_name": s["center_name"],
            "valid_count": s["temp_valid_count"],
            "avg_room_temp": s["avg_room_temp"],
            "pass_rate_pct": s["temp_pass_rate_pct"],
        }
        for s in stations_full
        if s["temp_valid_count"] > 0
    ]
    temp_station_rankings.sort(key=lambda x: (x["avg_room_temp"] or 999))

    # 整理 464 户商业用户小时明细与汇总
    mc_by_id: Dict[str, Dict[str, Any]] = {}
    unregistered_merchants_excluded = 0
    for mr in mc_hour_rows:
        if not mr.get("is_registered"):
            unregistered_merchants_excluded += 1
            continue
        if mr.get("merchant_id"):
            mc_by_id[mr["merchant_id"]] = mr

    merchants_full: List[Dict[str, Any]] = []
    mc_online_count = 0
    mc_active_heat_count = 0
    mc_total_hour_heat = 0.0
    mc_total_hour_flow = 0.0
    mc_total_instant_heat = 0.0
    mc_has_heat = False
    mc_has_flow = False
    mc_heat_anom_notes: List[str] = []

    for mm in merchants_meta:
        mf = mc_by_id.get(mm["merchant_id"]) or {}
        is_online = bool(mf.get("online")) if mf else False
        flow_val = _f(mf.get("flow_raw") if use_raw else mf.get("flow_clean"))
        temp_sup = _f(mf.get("temp_sup_raw") if use_raw else mf.get("temp_sup_clean"))
        temp_ret = _f(mf.get("temp_ret_raw") if use_raw else mf.get("temp_ret_clean"))
        pres_sup = _f(mf.get("pres_sup_raw") if use_raw else mf.get("pres_sup_clean"))
        pres_ret = _f(mf.get("pres_ret_raw") if use_raw else mf.get("pres_ret_clean"))
        heat_inst = _f(mf.get("heat_raw") if use_raw else mf.get("heat_clean"))
        hr_heat = _f(mf.get("hour_heat_gj"))
        hr_flow = _f(mf.get("hour_flow_t"))

        m_notes: Dict[str, str] = {}
        is_steam_mc = str(mm.get("rdry") or "").strip() == "蒸汽"
        if mf and not is_steam_mc:
            mn = mm["name"]
            mc = mc_day_counts.get(mm["merchant_id"], {})
            if _num_differs(mf.get("flow_raw"), mf.get("flow_clean"), tol=0.5) and _is_burst_metric(
                mf.get("flow_raw"), mf.get("flow_clean"), mc.get("flow"), huge_diff=50.0
            ):
                m_notes["flow"] = _fmt_anom_pair(
                    mn, "流量跳变", f"{_fmt_num(mf.get('flow_raw'))} t/h", f"{_fmt_num(mf.get('flow_clean'))} t/h", mode
                )
            if (
                _num_differs(mf.get("temp_sup_raw"), mf.get("temp_sup_clean"), tol=0.5)
                or _num_differs(mf.get("temp_ret_raw"), mf.get("temp_ret_clean"), tol=0.5)
            ) and _is_burst_metric(mf.get("temp_sup_raw"), mf.get("temp_sup_clean"), mc.get("temp"), huge_diff=80.0):
                m_notes["temp"] = _fmt_anom_pair(
                    mn,
                    "供回温跳变",
                    f"{_fmt_num(mf.get('temp_sup_raw'))}/{_fmt_num(mf.get('temp_ret_raw'))}℃",
                    f"{_fmt_num(mf.get('temp_sup_clean'))}/{_fmt_num(mf.get('temp_ret_clean'))}℃",
                    mode,
                )
            if (
                _num_differs(mf.get("pres_sup_raw"), mf.get("pres_sup_clean"), tol=0.05)
                or _num_differs(mf.get("pres_ret_raw"), mf.get("pres_ret_clean"), tol=0.05)
            ) and _is_burst_metric(mf.get("pres_sup_raw"), mf.get("pres_sup_clean"), mc.get("pres"), huge_diff=5.0):
                m_notes["pres"] = _fmt_anom_pair(
                    mn,
                    "压力跳变",
                    f"{_fmt_num(mf.get('pres_sup_raw'), 3)}/{_fmt_num(mf.get('pres_ret_raw'), 3)} MPa",
                    f"{_fmt_num(mf.get('pres_sup_clean'), 3)}/{_fmt_num(mf.get('pres_ret_clean'), 3)} MPa",
                    mode,
                )
            if _num_differs(mf.get("heat_raw"), mf.get("heat_clean"), tol=0.5) and _is_burst_metric(
                mf.get("heat_raw"), mf.get("heat_clean"), mc.get("heat")
            ):
                h_m_note = _fmt_anom_pair(
                    mn,
                    "热量跳变",
                    f"{_fmt_num(mf.get('heat_raw'))} GJ/h",
                    f"{_fmt_num(mf.get('heat_clean'))} GJ/h",
                    mode,
                )
                m_notes["heat"] = h_m_note
                m_notes["hour_heat_gj"] = h_m_note
                mc_heat_anom_notes.append(h_m_note)

        if is_online:
            mc_online_count += 1
        if heat_inst is not None and heat_inst > 0:
            mc_active_heat_count += 1
            mc_total_instant_heat += heat_inst
        if hr_heat is not None:
            mc_total_hour_heat += hr_heat
            mc_has_heat = True
        if hr_flow is not None:
            mc_total_hour_flow += hr_flow
            mc_has_flow = True

        merchants_full.append({
            "merchant_id": mm["merchant_id"],
            "name": mm["name"],
            "rdfz": mm["rdfz"],
            "rdry": mm["rdry"],
            "rdjg": mm["rdjg"],
            "main_network_id": mm["main_network_id"],
            "main_name": mm["main_name"],
            "branch_network_id": mm["branch_network_id"],
            "branch_name": mm["branch_name"],
            "has_record": bool(mf),
            "sample_count": mf.get("sample_count", 0),
            "online": is_online,
            "flow": flow_val,
            "temp_sup": temp_sup,
            "temp_ret": temp_ret,
            "pres_sup": pres_sup,
            "pres_ret": pres_ret,
            "heat": heat_inst,
            "valve_open": _f(mf.get("valve_open")),
            "valve_set": _f(mf.get("valve_set")),
            "hour_heat_gj": hr_heat,
            "hour_heat_source": mf.get("hour_heat_source"),
            "hour_flow_t": hr_flow,
            "value_source": mf.get("value_source") or "NO_DATA",
            "fault_tag": mf.get("fault_tag"),
            "field_notes": m_notes,
        })

    merchants_full.sort(key=lambda x: (x["hour_heat_gj"] if x["hour_heat_gj"] is not None else -1.0), reverse=True)

    return {
        "meta": {
            "date": target_d.isoformat(),
            "hour": sel_hour,
            "biz_hour_label": f"{target_d.isoformat()} {sel_hour:02d}:00",
            "mode": "raw" if use_raw else "clean",
            "station_records_count": len(st_hour_map),
            "merchant_records_count": len(mc_by_id),
            "last_run": {
                "run_id": last_run["run_id"],
                "run_type": last_run["run_type"],
                "status": last_run["status"],
                "finished_at": last_run["finished_at"].astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S")
                if last_run and last_run.get("finished_at") else None,
            } if last_run else None,
        },
        "kpis": overall_kpi,
        "trend_24h": trend_24h,
        "upstream_points": upstream_points,
        "group_summaries": group_summaries,
        "stations": stations_full,
        "merchants": merchants_full,
        "merchant_summary": {
            "total_merchants": len(merchants_meta),
            "online_merchants": mc_online_count,
            "active_heat_merchants": mc_active_heat_count,
            "unregistered_excluded": unregistered_merchants_excluded,
            "total_instant_heat_gjh": _round(mc_total_instant_heat, 2) if mc_by_id else None,
            "total_hour_heat_gj": _round(mc_total_hour_heat, 2) if mc_has_heat else None,
            "total_hour_flow_t": _round(mc_total_hour_flow, 2) if mc_has_flow else None,
            "heat_anomaly": _pack_agg_anomaly(mc_heat_anom_notes),
        },
        "temp_summary": {
            "total_fetched_devices": total_raw_devices,
            "valid_devices": sum(room_dist.values()),
            "unregistered_excluded": unregistered_excluded,
            "offline_invalid_excluded": offline_invalid_excluded,
            "distribution": room_dist,
            "station_rankings": temp_station_rankings,
        },
    }


def get_entity_trend_24h(
    target_date_str: str,
    scope: str,
    key: str,
    mode: str = "clean",
) -> Dict[str, Any]:
    """查询指定主体（服务中心 / 主干热网 / 支线热网 / 单个换热站）当日 24 小时柱形与曲线数据。"""
    ensure_smart_heating_fact_tables()
    target_d = date.fromisoformat(target_date_str)
    day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
    day_end = day_start + timedelta(days=1)
    norm_scope = str(scope or "").strip()
    scope_labels = {
        "by_center": "服务中心",
        "by_rdfz": "主干热网",
        "by_branch": "支线热网",
        "station": "换热站",
    }
    if norm_scope not in scope_labels:
        raise ValueError(f"不支持的主体维度 scope={scope}")

    outdoor_24h = _load_outdoor_temps_24h(target_d)
    filter_param: Any = key
    if norm_scope == "by_center":
        where_clause = "hs.center_id = :k"
        filter_param = int(key)
        name_sql = "SELECT name FROM smart_heating_platform.dict_service_center WHERE center_id = :k"
    elif norm_scope == "by_rdfz":
        where_clause = "hs.rdfz = :k"
        name_sql = None
    elif norm_scope == "by_branch":
        where_clause = "hs.branch_network_id = :k"
        filter_param = int(key)
        name_sql = "SELECT name FROM smart_heating_platform.dict_branch_network WHERE branch_network_id = :k"
    else:
        where_clause = "hs.station_id = :k"
        name_sql = "SELECT name FROM smart_heating_platform.dict_heating_station WHERE station_id = :k"

    with engine.connect() as conn:
        entity_name = str(key)
        if name_sql:
            row_name = conn.execute(text(name_sql), {"k": filter_param}).scalar()
            if row_name:
                entity_name = str(row_name)

        station_count = int(
            conn.execute(
                text(f"SELECT COUNT(*) FROM smart_heating_platform.dict_heating_station hs WHERE {where_clause}"),
                {"k": filter_param},
            ).scalar()
            or 0
        )

        st_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (f.biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "f.station_id, hs.name AS station_name, f.online, f.e1_raw, f.e1_clean, f.e3_raw, f.e3_clean, "
                "f.e4_raw, f.e4_clean, f.e7_raw, f.e7_clean, f.e8_raw, f.e8_clean, "
                "f.e11_raw, f.e11_clean, f.e14_raw, f.e14_clean, "
                "f.hour_heat_raw_gj, f.hour_heat_gj, f.hour_heat_source, f.hour_water_t, "
                "f.value_source, f.fault_tag, hs.covered_area "
                "FROM smart_heating_platform.fact_station_hourly f "
                "JOIN smart_heating_platform.dict_heating_station hs ON f.station_id = hs.station_id "
                f"WHERE f.biz_hour >= :ds AND f.biz_hour < :de AND {where_clause}"
            ),
            {"ds": day_start, "de": day_end, "k": filter_param},
        ).fetchall()

    st_day_maps = [dict(r._mapping) for r in st_day_rows]
    trend_24h = _build_trend_24h_from_rows(st_day_maps, outdoor_24h, mode)
    return {
        "date": target_d.isoformat(),
        "mode": "raw" if str(mode).lower() == "raw" else "clean",
        "scope": norm_scope,
        "scope_label": scope_labels[norm_scope],
        "key": str(key),
        "entity_name": entity_name,
        "station_count": station_count,
        "trend_24h": trend_24h,
    }


def get_upstream_point_24h(target_date_str: str, data_zone: str, source_name: str) -> List[Dict[str, Any]]:
    """查询单个上游测点当日 24 小时温/压/流/热趋势。"""
    target_d = date.fromisoformat(target_date_str)
    day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
    day_end = day_start + timedelta(days=1)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "temp_clean, pressure_clean, flow_clean, heat_clean, hour_heat_raw_gj, hour_heat_gj, value_source "
                "FROM smart_heating_platform.fact_upstream_hourly "
                "WHERE biz_hour >= :ds AND biz_hour < :de AND data_zone = :dz AND source_name = :sn "
                "ORDER BY biz_hour ASC"
            ),
            {"ds": day_start, "de": day_end, "dz": data_zone, "sn": source_name},
        ).fetchall()
    return [
        {
            "hour": int(r.hr),
            "label": f"{int(r.hr):02d}:00",
            "temp": _f(r.temp_clean),
            "pressure": _f(r.pressure_clean),
            "flow": _f(r.flow_clean),
            "heat": _f(r.heat_clean),
            "hour_heat_raw_gj": _f(r.hour_heat_raw_gj),
            "hour_heat_gj": _f(r.hour_heat_gj),
            "value_source": r.value_source,
        }
        for r in rows
    ]


def get_station_temp_devices(target_date_str: str, hour: int, station_id: str) -> List[Dict[str, Any]]:
    """下钻查看某座换热站下属居民室温终端单户明细及现场备注。"""
    target_d = date.fromisoformat(target_date_str)
    biz_hour = datetime(target_d.year, target_d.month, target_d.day, int(hour), 0, 0, tzinfo=EAST_8)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT temp_device_id, village_name, zdxh, temp_raw, temp_clean, upload_time, "
                "is_online_valid, is_registered, remark_snapshot, fault_tag "
                "FROM smart_heating_platform.fact_temp_hourly "
                "WHERE biz_hour = :bh AND station_id = :sid "
                "ORDER BY is_online_valid DESC, temp_clean ASC NULLS LAST, village_name"
            ),
            {"bh": biz_hour, "sid": station_id},
        ).fetchall()
    return [
        {
            "temp_device_id": r.temp_device_id,
            "village_name": r.village_name,
            "zdxh": r.zdxh,
            "temp_raw": _f(r.temp_raw),
            "temp_clean": _f(r.temp_clean),
            "upload_time": r.upload_time.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S") if r.upload_time else None,
            "is_online_valid": r.is_online_valid,
            "is_registered": r.is_registered,
            "remark": r.remark_snapshot,
            "fault_tag": r.fault_tag,
        }
        for r in rows
    ]


def get_daily_report(
    target_date_str: Optional[str],
    period_mode: str = "natural",
    data_mode: str = "clean",
    *,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """构建【界面二：每日生产精算日报与手工日报双轨核对】载荷（支持修正后 clean / 原始口径 raw 切换）。"""
    now_e8 = datetime.now(EAST_8)
    target_d = date.fromisoformat(target_date_str) if target_date_str else (now_e8.date() - timedelta(days=1))
    period = "shift" if str(period_mode).lower() == "shift" else "natural"
    effective_mode = str(mode if mode is not None else data_mode).lower()
    use_raw = effective_mode == "raw"

    if period == "shift":
        win_end = datetime(target_d.year, target_d.month, target_d.day, 8, 0, 0, tzinfo=EAST_8)
        win_start = win_end - timedelta(days=1)
    else:
        win_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
        win_end = win_start + timedelta(days=1)

    with engine.connect() as conn:
        centers = [
            dict(r._mapping)
            for r in conn.execute(
                text("SELECT center_id, name FROM smart_heating_platform.dict_service_center ORDER BY center_id")
            ).fetchall()
        ]
        stations_meta = {
            r.station_id: dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT hs.station_id, hs.name, hs.center_id, sc.name AS center_name, hs.covered_area, hs.rdfz "
                    "FROM smart_heating_platform.dict_heating_station hs "
                    "JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id"
                )
            ).fetchall()
        }
        hourly_rows = conn.execute(
            text(
                "SELECT biz_hour, station_id, e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean, "
                "e7_raw, e7_clean, e8_raw, e8_clean, e11_raw, e11_clean, e14_raw, e14_clean, "
                "tot_j, hour_heat_raw_gj, hour_heat_gj, hour_heat_source, hour_flow_t, hour_water_t, hour_elec_kwh, "
                "value_source, fault_tag "
                "FROM smart_heating_platform.fact_station_hourly "
                "WHERE biz_hour >= :ws AND biz_hour < :we ORDER BY station_id, biz_hour ASC"
            ),
            {"ws": win_start, "we": win_end},
        ).fetchall()

        # 止表底应取结算结束时刻 (win_end，如自然日次日 00:00 / 生产班次当日 08:00) 的整点表底
        end_meter_rows = conn.execute(
            text(
                "SELECT station_id, tot_j "
                "FROM smart_heating_platform.fact_station_hourly "
                "WHERE biz_hour = :we"
            ),
            {"we": win_end},
        ).fetchall()
        end_row_stations = {r.station_id for r in end_meter_rows}
        end_tot_j_map = {r.station_id: _f(r.tot_j) for r in end_meter_rows if r.tot_j is not None}

        temp_rows = conn.execute(
            text(
                "SELECT hs.center_id, AVG(t.temp_clean) AS avg_temp "
                "FROM smart_heating_platform.fact_temp_hourly t "
                "JOIN smart_heating_platform.dict_heating_station hs ON t.station_id = hs.station_id "
                "WHERE t.biz_hour >= :ws AND t.biz_hour < :we AND t.is_online_valid IS TRUE "
                "GROUP BY hs.center_id"
            ),
            {"ws": win_start, "we": win_end},
        ).fetchall()
        center_temp_map = {int(r.center_id): _round(_f(r.avg_temp), 2) for r in temp_rows}

        # 读取 Phoenix 手工生产日报 (public.daily_basic_data)
        manual_rows = conn.execute(
            text(
                "SELECT company, item, value "
                "FROM public.daily_basic_data "
                "WHERE date = :biz_date "
                "AND (sheet_name = 'GongRe_branches_detail_Sheet' OR company = 'GongRe') "
                "AND item IN ('consumption_station_heat', 'consumption_station_fill_water', 'consumption_station_purchased_power')"
            ),
            {"biz_date": target_d},
        ).fetchall()

        # 读取商户日耗量（含入库记录存在性与原始起止表底，用于拆分正常/缺记录/表底倒走三类）
        merchant_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT m.merchant_id, m.name, m.rdfz, m.rdry, m.rdss, m.rdjg, m.rdgz, "
                    "f.id AS fact_id, f.daily_consumption, f.daily_unit_heat, f.raw_payload "
                    "FROM smart_heating_platform.dict_merchant m "
                    "LEFT JOIN smart_heating_platform.fact_merchant_daily f "
                    "ON m.merchant_id = f.merchant_id AND f.biz_date = :biz_date "
                    "ORDER BY f.daily_consumption DESC NULLS LAST, m.name"
                ),
                {"biz_date": target_d},
            ).fetchall()
        ]

    # 按站汇总 24 小时（累计指标初始为 None，读到有效小时值时再累加，避免无读数误显 0）
    st_agg: Dict[str, Dict[str, Any]] = {}
    for st_id, sm in stations_meta.items():
        st_agg[st_id] = {
            "station_id": st_id,
            "name": sm["name"],
            "center_id": sm["center_id"],
            "center_name": sm["center_name"],
            "rdfz": sm["rdfz"],
            "covered_area": _f(sm["covered_area"]),
            "hours_count": 0,
            "meter_diff_hours": 0,
            "start_tot_j": None,
            "end_tot_j": end_tot_j_map.get(st_id),
            "last_meter_end_tot_j": None,
            "day_heat_gj": None,
            "day_flow_t": None,
            "day_water_t": None,
            "day_elec_kwh": None,
            "sup_w_sum": 0.0,
            "ret_w_sum": 0.0,
            "flow_w_sum": 0.0,
            "heat_anom_notes": [],
            "water_anom_notes": [],
            "temp_anom_notes": [],
        }

    hourly_row_maps = [dict(r._mapping) for r in hourly_rows]
    st_day_counts = _count_station_day_anomalies(
        hourly_row_maps,
        lambda rm: (stations_meta.get(rm.get("station_id")) or {}).get("name") or rm.get("station_id"),
    )

    for r, row_map in zip(hourly_rows, hourly_row_maps):
        st = st_agg.get(r.station_id)
        if not st:
            continue
        hr_label = r.biz_hour.astimezone(EAST_8).strftime("%H:00") if r.biz_hour.tzinfo else r.biz_hour.strftime("%H:00")
        row_anoms = _build_station_hour_anomalies(
            row_map,
            st["name"],
            day_counts=st_day_counts.get(r.station_id),
            mode=effective_mode,
        )
        if row_anoms.get("hour_heat_gj"):
            st["heat_anom_notes"].append(f"{hr_label} {row_anoms['hour_heat_gj'].split(': ', 1)[-1]}")
        if row_anoms.get("e14"):
            st["water_anom_notes"].append(f"{hr_label} {row_anoms['e14'].split(': ', 1)[-1]}")
        if row_anoms.get("e3_e4"):
            st["temp_anom_notes"].append(f"{hr_label} {row_anoms['e3_e4'].split(': ', 1)[-1]}")
        if st["start_tot_j"] is None and r.tot_j is not None:
            st["start_tot_j"] = _f(r.tot_j)
        if (
            r.station_id not in end_row_stations
            and r.tot_j is not None
            and r.hour_heat_source == "METER_DIFF"
            and r.hour_heat_raw_gj is not None
        ):
            st["last_meter_end_tot_j"] = float(r.tot_j) + float(r.hour_heat_raw_gj)
        else:
            st["last_meter_end_tot_j"] = None
        eff_heat = r.hour_heat_raw_gj if (use_raw and r.hour_heat_raw_gj is not None) else r.hour_heat_gj
        if eff_heat is not None:
            st["hours_count"] += 1
            st["day_heat_gj"] = (st["day_heat_gj"] or 0.0) + float(eff_heat)
            if r.hour_heat_source == "METER_DIFF":
                st["meter_diff_hours"] += 1
        if r.hour_flow_t is not None:
            st["day_flow_t"] = (st["day_flow_t"] or 0.0) + float(r.hour_flow_t)
        if r.hour_water_t is not None:
            st["day_water_t"] = (st["day_water_t"] or 0.0) + float(r.hour_water_t)
        if r.hour_elec_kwh is not None:
            st["day_elec_kwh"] = (st["day_elec_kwh"] or 0.0) + float(r.hour_elec_kwh)
        raw_or_clean_e1 = r.e1_raw if use_raw else r.e1_clean
        raw_or_clean_e3 = r.e3_raw if use_raw else r.e3_clean
        raw_or_clean_e4 = r.e4_raw if use_raw else r.e4_clean
        w = float(raw_or_clean_e1) if raw_or_clean_e1 is not None and float(raw_or_clean_e1) > 0 else 0.0
        if w > 0 and raw_or_clean_e3 is not None and raw_or_clean_e4 is not None:
            st["sup_w_sum"] += float(raw_or_clean_e3) * w
            st["ret_w_sum"] += float(raw_or_clean_e4) * w
            st["flow_w_sum"] += w

    station_daily: List[Dict[str, Any]] = []
    for st in st_agg.values():
        area = st["covered_area"]
        area_wan = area / 10000.0 if (area and area > 0) else 0.0
        end_tot_j_val = st["end_tot_j"] if st["end_tot_j"] is not None else st["last_meter_end_tot_j"]
        heat_per_wan = _round(st["day_heat_gj"] / area_wan, 2) if (area_wan > 0 and st["day_heat_gj"] is not None) else None
        st_anoms: Dict[str, Dict[str, Any]] = {}
        h_pack = _pack_agg_anomaly(st["heat_anom_notes"])
        w_pack = _pack_agg_anomaly(st["water_anom_notes"])
        t_pack = _pack_agg_anomaly(st["temp_anom_notes"])
        if h_pack:
            st_anoms["day_heat_gj"] = h_pack
            st_anoms["heat_per_wan_gj"] = h_pack
        if w_pack:
            st_anoms["day_water_t"] = w_pack
        if t_pack:
            st_anoms["avg_sup_temp"] = t_pack
            st_anoms["avg_ret_temp"] = t_pack
        station_daily.append({
            "station_id": st["station_id"],
            "name": st["name"],
            "center_id": st["center_id"],
            "center_name": st["center_name"],
            "rdfz": st["rdfz"],
            "covered_area": area,
            "hours_count": st["hours_count"],
            "meter_diff_hours": st["meter_diff_hours"],
            "start_tot_j": _round(st["start_tot_j"], 2),
            "end_tot_j": _round(end_tot_j_val, 2),
            "day_heat_gj": _round(st["day_heat_gj"], 2),
            "heat_per_wan_gj": heat_per_wan,
            "day_flow_t": _round(st["day_flow_t"], 2),
            "day_water_t": _round(st["day_water_t"], 2),
            "day_elec_kwh": _round(st["day_elec_kwh"], 2),
            "avg_sup_temp": _round(st["sup_w_sum"] / st["flow_w_sum"], 2) if st["flow_w_sum"] > 0 else None,
            "avg_ret_temp": _round(st["ret_w_sum"] / st["flow_w_sum"], 2) if st["flow_w_sum"] > 0 else None,
            "anomalies": st_anoms,
        })
    station_daily.sort(key=lambda x: (x["heat_per_wan_gj"] if x["heat_per_wan_gj"] is not None else -1.0), reverse=True)

    # 解析手工日报到 center_id
    manual_by_center: Dict[int, Dict[str, float]] = {}
    manual_gongre: Dict[str, float] = {}
    for mr in manual_rows:
        comp = str(mr.company)
        val = _f(mr.value)
        if val is None:
            continue
        if comp == "GongRe":
            manual_gongre[mr.item] = val
        elif comp in CENTER_COMPANY_MAP:
            cid = CENTER_COMPANY_MAP[comp]
            manual_by_center.setdefault(cid, {})[mr.item] = val

    # 9 大中心双轨对比
    center_comparison: List[Dict[str, Any]] = []
    tot_sys_heat = 0.0
    tot_sys_water = 0.0
    tot_man_heat = 0.0
    tot_man_water = 0.0
    tot_area = 0.0
    has_man_heat = False

    all_heat_anom_stations: List[str] = []
    all_water_anom_stations: List[str] = []

    for c in centers:
        cid = c["center_id"]
        c_sts = [s for s in station_daily if s["center_id"] == cid]
        c_area = sum((s["covered_area"] or 0.0) for s in c_sts)
        sys_heat = sum((s["day_heat_gj"] or 0.0) for s in c_sts)
        sys_water = sum((s["day_water_t"] or 0.0) for s in c_sts)
        sys_elec = sum((s["day_elec_kwh"] or 0.0) for s in c_sts)
        man = manual_by_center.get(cid, {})
        man_heat = man.get("consumption_station_heat")
        man_water = man.get("consumption_station_fill_water")

        diff_heat = (sys_heat - man_heat) if (man_heat is not None and hourly_rows) else None
        diff_pct = (diff_heat / man_heat * 100.0) if (diff_heat is not None and man_heat and man_heat != 0) else None
        diff_water = (sys_water - man_water) if (man_water is not None and hourly_rows) else None

        c_heat_notes = [
            f"{s['name']}({s['anomalies']['day_heat_gj']['note']})"
            for s in c_sts
            if (s.get("anomalies") or {}).get("day_heat_gj")
        ]
        c_water_notes = [
            f"{s['name']}({s['anomalies']['day_water_t']['note']})"
            for s in c_sts
            if (s.get("anomalies") or {}).get("day_water_t")
        ]
        all_heat_anom_stations.extend(c_heat_notes)
        all_water_anom_stations.extend(c_water_notes)
        c_anoms: Dict[str, Dict[str, Any]] = {}
        ch_pack = _pack_agg_anomaly(c_heat_notes)
        cw_pack = _pack_agg_anomaly(c_water_notes)
        if ch_pack:
            c_anoms["sys_heat_gj"] = ch_pack
            c_anoms["heat_per_wan_gj"] = ch_pack
            c_anoms["heat_diff_gj"] = ch_pack
            c_anoms["heat_diff_pct"] = ch_pack
        if cw_pack:
            c_anoms["sys_water_t"] = cw_pack
            c_anoms["water_diff_t"] = cw_pack

        tot_area += c_area
        tot_sys_heat += sys_heat
        tot_sys_water += sys_water
        if man_heat is not None:
            tot_man_heat += man_heat
            has_man_heat = True
        if man_water is not None:
            tot_man_water += man_water

        center_comparison.append({
            "center_id": cid,
            "center_name": c["name"],
            "covered_area_wan": _round(c_area / 10000.0, 2),
            "sys_heat_gj": _round(sys_heat, 2) if hourly_rows else None,
            "heat_per_wan_gj": _round(sys_heat / (c_area / 10000.0), 2) if (hourly_rows and c_area > 0) else None,
            "man_heat_gj": _round(man_heat, 2),
            "heat_diff_gj": _round(diff_heat, 2),
            "heat_diff_pct": _round(diff_pct, 2),
            "is_heat_alert": abs(diff_pct) > 10.0 if diff_pct is not None else False,
            "sys_water_t": _round(sys_water, 2) if hourly_rows else None,
            "man_water_t": _round(man_water, 2),
            "water_diff_t": _round(diff_water, 2),
            "sys_elec_kwh": _round(sys_elec, 2) if hourly_rows else None,
            "avg_room_temp": center_temp_map.get(cid),
            "anomalies": c_anoms,
        })

    # 若分中心未填而供热公司总表有值则回退供热公司总表
    ref_man_heat = tot_man_heat if has_man_heat else manual_gongre.get("consumption_station_heat")
    overall_diff_pct = (
        _round((tot_sys_heat - ref_man_heat) / ref_man_heat * 100.0, 2)
        if (hourly_rows and ref_man_heat and ref_man_heat != 0)
        else None
    )

    daily_kpi_anomalies: Dict[str, Dict[str, Any]] = {}
    all_h_pack = _pack_agg_anomaly(all_heat_anom_stations)
    all_w_pack = _pack_agg_anomaly(all_water_anom_stations)
    if all_h_pack:
        daily_kpi_anomalies["day_heat_gj"] = all_h_pack
        daily_kpi_anomalies["day_heat_per_wan"] = all_h_pack
        daily_kpi_anomalies["overall_diff_pct"] = all_h_pack
    if all_w_pack:
        daily_kpi_anomalies["day_water_t"] = all_w_pack

    try:
        snap_interval = int(get_collector_settings_view().get("snapshot_interval_minutes", 5))
    except Exception:
        snap_interval = 5

    merchant_items: List[Dict[str, Any]] = []
    mc_valid_count = 0
    mc_missing_count = 0
    mc_rollback_count = 0
    for m in merchant_rows:
        cons = _f(m.get("daily_consumption"))
        unit_heat = _f(m.get("daily_unit_heat"))
        payload = m.get("raw_payload") if isinstance(m.get("raw_payload"), dict) else {}
        tot_curr = _f(payload.get("tot_curr"))
        tot_prev = _f(payload.get("tot_prev"))
        if cons is not None:
            calc_status = "VALID"
            status_label = "正常"
            status_note = ""
            mc_valid_count += 1
        elif m.get("fact_id") is None:
            calc_status = "MISSING_RECORD"
            status_label = "缺日耗记录"
            status_note = "源站商业日报接口(/getall_bb_shrb/)未返回该户记录"
            mc_missing_count += 1
        elif tot_curr is not None and tot_prev is not None and tot_curr < tot_prev:
            calc_status = "METER_ROLLBACK"
            status_label = "表读数倒走"
            status_note = f"止表底({_fmt_num(tot_curr)}) < 起表底({_fmt_num(tot_prev)})，无法计算日耗"
            unit_heat = None
            mc_rollback_count += 1
        else:
            calc_status = "MISSING_RECORD"
            status_label = "缺日耗记录"
            status_note = "源站日报起止表底缺失，无法计算"
            unit_heat = None
            mc_missing_count += 1

        merchant_items.append({
            "merchant_id": m["merchant_id"],
            "name": m["name"],
            "rdfz": m["rdfz"],
            "rdry": m["rdry"],
            "rdss": m["rdss"],
            "rdjg": m["rdjg"],
            "rdgz": m["rdgz"],
            "daily_consumption": cons,
            "daily_unit_heat": unit_heat,
            "calc_status": calc_status,
            "status_label": status_label,
            "status_note": status_note,
        })

    return {
        "meta": {
            "date": target_d.isoformat(),
            "period_mode": period,
            "mode": "raw" if use_raw else "clean",
            "snapshot_interval_minutes": snap_interval,
            "window_start": win_start.strftime("%Y-%m-%d %H:%M"),
            "window_end": win_end.strftime("%Y-%m-%d %H:%M"),
            "has_hourly_data": len(hourly_rows) > 0,
        },
        "kpis": {
            "day_heat_gj": _round(tot_sys_heat, 2) if hourly_rows else None,
            "day_heat_per_wan": _round(tot_sys_heat / (tot_area / 10000.0), 2) if (hourly_rows and tot_area > 0) else None,
            "day_water_t": _round(tot_sys_water, 2) if hourly_rows else None,
            "manual_total_heat_gj": _round(ref_man_heat, 2),
            "overall_diff_pct": overall_diff_pct,
            "anomalies": daily_kpi_anomalies,
        },
        "center_comparison": center_comparison,
        "station_daily": station_daily,
        "merchant_summary": {
            "total_count": len(merchant_items),
            "valid_count": mc_valid_count,
            "missing_record_count": mc_missing_count,
            "rollback_count": mc_rollback_count,
        },
        "merchant_daily": merchant_items,
    }


def _safe_sheet_title(raw_title: str, existing: Sequence[str]) -> str:
    """生成符合 Excel 规范（<=31 字符且无非法符号）的唯一工作表标题。"""
    cleaned = re.sub(r'[\[\]:*?/\\]', "_", str(raw_title or "Sheet")).strip() or "Sheet"
    base = cleaned[:28]
    cand = cleaned[:31]
    idx = 2
    existing_set = set(existing)
    while cand in existing_set:
        suffix = f"_{idx}"
        cand = f"{base[:31 - len(suffix)]}{suffix}"
        idx += 1
    return cand


def _style_excel_sheet(
    ws: Any,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    highlight_cells: Optional[Dict[Tuple[int, int], str]] = None,
    warn_cells: Optional[Dict[Tuple[int, int], str]] = None,
    bold_last_row: bool = False,
) -> None:
    """统一为导出 Excel Sheet 设置表头样式、自适应列宽及异常单元格标红/告警标橙与批注。"""
    fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    font = Font(color="FFFFFF", bold=True)
    anom_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    anom_font = Font(color="B91C1C", bold=True)
    warn_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    warn_font = Font(color="92400E", bold=True)
    total_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    total_font = Font(color="0F172A", bold=True)

    ws.append(list(headers))
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for r in rows:
        ws.append(list(r))

    if warn_cells:
        for (r_idx_0, c_idx_0), warn_txt in warn_cells.items():
            excel_r = r_idx_0 + 2
            excel_c = c_idx_0 + 1
            if 2 <= excel_r <= ws.max_row and 1 <= excel_c <= len(headers):
                cell = ws.cell(row=excel_r, column=excel_c)
                cell.fill = warn_fill
                cell.font = warn_font
                if warn_txt:
                    cell.comment = Comment(str(warn_txt)[:300], "双轨对账告警")

    if highlight_cells:
        for (r_idx_0, c_idx_0), note_txt in highlight_cells.items():
            excel_r = r_idx_0 + 2
            excel_c = c_idx_0 + 1
            if 2 <= excel_r <= ws.max_row and 1 <= excel_c <= len(headers):
                cell = ws.cell(row=excel_r, column=excel_c)
                cell.fill = anom_fill
                cell.font = anom_font
                if note_txt:
                    cell.comment = Comment(str(note_txt)[:300], "智慧供热质检")

    if bold_last_row and rows:
        last_row_num = len(rows) + 1
        for col_i in range(1, len(headers) + 1):
            cell = ws.cell(row=last_row_num, column=col_i)
            in_hl = bool(highlight_cells and (len(rows) - 1, col_i - 1) in highlight_cells)
            in_warn = bool(warn_cells and (len(rows) - 1, col_i - 1) in warn_cells)
            if not in_hl and not in_warn:
                cell.fill = total_fill
                cell.font = total_font

    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 4, 10), 42)


def _join_anom_notes(anomalies: Optional[Dict[str, Any]], keys: Optional[Sequence[str]] = None) -> str:
    """将指标 anomalies 字典拼接为可读备注文本。"""
    if not anomalies:
        return ""
    target_keys = keys if keys else list(anomalies.keys())
    notes: List[str] = []
    for k in target_keys:
        val = anomalies.get(k)
        txt = val.get("note") if isinstance(val, dict) else (str(val) if val else "")
        if txt and txt not in notes:
            notes.append(txt)
    return "；".join(notes)


def build_hourly_export_payload(
    target_date_str: Optional[str],
    hour: Optional[int],
    mode: str = "clean",
    scope: Optional[str] = None,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """为《逐小时统计》Excel 准备当天 24 小时全量横表矩阵、全天突发跳变记录与选中小时明细。"""
    report = get_hourly_report(target_date_str=target_date_str, hour=hour, mode=mode)
    target_d = date.fromisoformat(report["meta"]["date"])
    use_raw = str(mode).lower() == "raw"
    day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
    day_end = day_start + timedelta(days=1)

    with engine.connect() as conn:
        st_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (f.biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "f.station_id, hs.name AS station_name, hs.center_id, sc.name AS center_name, "
                "hs.rdfz, hs.branch_network_id, bn.name AS branch_name, hs.covered_area, "
                "f.e1_raw, f.e1_clean, f.e3_raw, f.e3_clean, f.e4_raw, f.e4_clean, "
                "f.e7_raw, f.e7_clean, f.e8_raw, f.e8_clean, f.e11_raw, f.e11_clean, "
                "f.e14_raw, f.e14_clean, f.hour_heat_raw_gj, f.hour_heat_gj, f.value_source, f.fault_tag "
                "FROM smart_heating_platform.fact_station_hourly f "
                "JOIN smart_heating_platform.dict_heating_station hs ON f.station_id = hs.station_id "
                "JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id "
                "JOIN smart_heating_platform.dict_branch_network bn ON hs.branch_network_id = bn.branch_network_id "
                "WHERE f.biz_hour >= :ds AND f.biz_hour < :de"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()

        up_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "data_zone, source_name, display_name, temp_raw, temp_clean, pressure_raw, pressure_clean, "
                "heat_raw, heat_clean, hour_heat_raw_gj, hour_heat_gj "
                "FROM smart_heating_platform.fact_upstream_hourly "
                "WHERE biz_hour >= :ds AND biz_hour < :de"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()

        mc_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (f.biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "f.merchant_id, m.name AS merchant_name, m.rdry, "
                "f.flow_raw, f.flow_clean, f.temp_sup_raw, f.temp_sup_clean, f.temp_ret_raw, f.temp_ret_clean, "
                "f.pres_sup_raw, f.pres_sup_clean, f.pres_ret_raw, f.pres_ret_clean, f.heat_raw, f.heat_clean "
                "FROM smart_heating_platform.fact_merchant_hourly f "
                "JOIN smart_heating_platform.dict_merchant m ON f.merchant_id = m.merchant_id "
                "WHERE f.biz_hour >= :ds AND f.biz_hour < :de AND f.is_registered IS TRUE"
            ),
            {"ds": day_start, "de": day_end},
        ).fetchall()

    st_day_maps = [dict(r._mapping) for r in st_day_rows]
    st_day_counts = _count_station_day_anomalies(
        st_day_maps,
        lambda rm: rm.get("station_name") or rm.get("station_id"),
    )

    station_hour_heats: Dict[str, List[Optional[float]]] = {}
    station_hour_notes: Dict[str, Dict[int, str]] = {}
    center_hour_heats: Dict[int, List[Optional[float]]] = {}
    center_hour_notes: Dict[int, Dict[int, List[str]]] = {}
    rdfz_hour_heats: Dict[str, List[Optional[float]]] = {}
    rdfz_hour_notes: Dict[str, Dict[int, List[str]]] = {}
    burst_events: List[Dict[str, Any]] = []

    field_labels = {
        "hour_heat_gj": "小时供热量(GJ)",
        "e11": "一网瞬时热量(GJ/h)",
        "e3_e4": "一网供回温(℃)",
        "e7_e8": "一网供回压(MPa)",
        "e14": "瞬时补水量(t/h)",
    }

    for rm in st_day_maps:
        sid = rm["station_id"]
        sname = str(rm.get("station_name") or sid)
        cid = int(rm["center_id"])
        rdfz = str(rm.get("rdfz") or "未分配")
        hr = int(rm["hr"])
        heat_v = _f(
            rm["hour_heat_raw_gj"]
            if (use_raw and rm.get("hour_heat_raw_gj") is not None)
            else rm.get("hour_heat_gj")
        )
        fn = _build_station_hour_anomalies(
            rm,
            sname,
            day_counts=st_day_counts.get(sid),
            mode=mode,
        )

        st_arr = station_hour_heats.setdefault(sid, [None] * 24)
        if heat_v is not None:
            st_arr[hr] = _round(heat_v, 2)
        if fn.get("hour_heat_gj"):
            station_hour_notes.setdefault(sid, {})[hr] = fn["hour_heat_gj"]
            center_hour_notes.setdefault(cid, {}).setdefault(hr, []).append(fn["hour_heat_gj"])
            rdfz_hour_notes.setdefault(rdfz, {}).setdefault(hr, []).append(fn["hour_heat_gj"])

        if heat_v is not None:
            c_arr = center_hour_heats.setdefault(cid, [None] * 24)
            c_arr[hr] = round((c_arr[hr] or 0.0) + heat_v, 2)
            r_arr = rdfz_hour_heats.setdefault(rdfz, [None] * 24)
            r_arr[hr] = round((r_arr[hr] or 0.0) + heat_v, 2)

        for fkey, note in fn.items():
            if fkey == "heat_index_wm2":
                continue
            burst_events.append({
                "hour": hr,
                "label": f"{hr:02d}:00",
                "entity_type": "换热站",
                "entity_name": sname,
                "metric": field_labels.get(fkey, fkey),
                "note": note,
            })

    # 扫描全天上游与商业户突发跳变入突发事件表
    up_counts: Dict[Tuple[str, str], Dict[str, int]] = {}
    for ur in up_day_rows:
        uk = (str(ur.data_zone), str(ur.source_name))
        uc = up_counts.setdefault(uk, {"temp": 0, "pres": 0, "heat": 0})
        if _num_differs(ur.temp_raw, ur.temp_clean, tol=0.5):
            uc["temp"] += 1
        if _num_differs(ur.pressure_raw, ur.pressure_clean, tol=0.05):
            uc["pres"] += 1
        if "累计" not in str(ur.display_name or ur.source_name or "") and (
            _num_differs(ur.heat_raw, ur.heat_clean, tol=1.0)
            or _num_differs(ur.hour_heat_raw_gj, ur.hour_heat_gj, tol=1.0)
        ):
            uc["heat"] += 1
    for ur in up_day_rows:
        uname = str(ur.display_name or ur.source_name or "")
        uc = up_counts.get((str(ur.data_zone), str(ur.source_name)), {})
        hr = int(ur.hr)
        if _num_differs(ur.temp_raw, ur.temp_clean, tol=0.5) and _is_burst_metric(ur.temp_raw, ur.temp_clean, uc.get("temp"), huge_diff=80.0):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "上游热源/首站", "entity_name": uname, "metric": "温度(℃)", "note": _fmt_anom_pair(uname, "温度跳变", f"{_fmt_num(ur.temp_raw)}℃", f"{_fmt_num(ur.temp_clean)}℃", mode)})
        if _num_differs(ur.pressure_raw, ur.pressure_clean, tol=0.05) and _is_burst_metric(ur.pressure_raw, ur.pressure_clean, uc.get("pres"), huge_diff=5.0):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "上游热源/首站", "entity_name": uname, "metric": "压力(MPa)", "note": _fmt_anom_pair(uname, "压力跳变", f"{_fmt_num(ur.pressure_raw, 3)} MPa", f"{_fmt_num(ur.pressure_clean, 3)} MPa", mode)})
        if "累计" not in uname and (
            _num_differs(ur.heat_raw, ur.heat_clean, tol=1.0) or _num_differs(ur.hour_heat_raw_gj, ur.hour_heat_gj, tol=1.0)
        ) and _is_burst_metric(ur.hour_heat_raw_gj if ur.hour_heat_raw_gj is not None else ur.heat_raw, ur.hour_heat_gj if ur.hour_heat_gj is not None else ur.heat_clean, uc.get("heat")):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "上游热源/首站", "entity_name": uname, "metric": "热量(GJ)", "note": _fmt_anom_pair(uname, "热量跳变", f"{_fmt_num(ur.hour_heat_raw_gj or ur.heat_raw)} GJ", f"{_fmt_num(ur.hour_heat_gj if ur.hour_heat_gj is not None else ur.heat_clean)} GJ", mode)})

    mc_counts: Dict[str, Dict[str, int]] = {}
    for mr in mc_day_rows:
        if str(mr.rdry or "").strip() == "蒸汽":
            continue
        mc = mc_counts.setdefault(mr.merchant_id, {"flow": 0, "temp": 0, "pres": 0, "heat": 0})
        if _num_differs(mr.flow_raw, mr.flow_clean, tol=0.5):
            mc["flow"] += 1
        if _num_differs(mr.temp_sup_raw, mr.temp_sup_clean, tol=0.5) or _num_differs(mr.temp_ret_raw, mr.temp_ret_clean, tol=0.5):
            mc["temp"] += 1
        if _num_differs(mr.pres_sup_raw, mr.pres_sup_clean, tol=0.05) or _num_differs(mr.pres_ret_raw, mr.pres_ret_clean, tol=0.05):
            mc["pres"] += 1
        if _num_differs(mr.heat_raw, mr.heat_clean, tol=0.5):
            mc["heat"] += 1
    for mr in mc_day_rows:
        if str(mr.rdry or "").strip() == "蒸汽":
            continue
        mname = str(mr.merchant_name or mr.merchant_id)
        mc = mc_counts.get(mr.merchant_id, {})
        hr = int(mr.hr)
        if _num_differs(mr.flow_raw, mr.flow_clean, tol=0.5) and _is_burst_metric(mr.flow_raw, mr.flow_clean, mc.get("flow"), huge_diff=50.0):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "商业用户", "entity_name": mname, "metric": "流量(t/h)", "note": _fmt_anom_pair(mname, "流量跳变", f"{_fmt_num(mr.flow_raw)} t/h", f"{_fmt_num(mr.flow_clean)} t/h", mode)})
        if (_num_differs(mr.temp_sup_raw, mr.temp_sup_clean, tol=0.5) or _num_differs(mr.temp_ret_raw, mr.temp_ret_clean, tol=0.5)) and _is_burst_metric(mr.temp_sup_raw, mr.temp_sup_clean, mc.get("temp"), huge_diff=80.0):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "商业用户", "entity_name": mname, "metric": "供回温(℃)", "note": _fmt_anom_pair(mname, "供回温跳变", f"{_fmt_num(mr.temp_sup_raw)}/{_fmt_num(mr.temp_ret_raw)}℃", f"{_fmt_num(mr.temp_sup_clean)}/{_fmt_num(mr.temp_ret_clean)}℃", mode)})
        if _num_differs(mr.heat_raw, mr.heat_clean, tol=0.5) and _is_burst_metric(mr.heat_raw, mr.heat_clean, mc.get("heat")):
            burst_events.append({"hour": hr, "label": f"{hr:02d}:00", "entity_type": "商业用户", "entity_name": mname, "metric": "瞬时热量(GJ/h)", "note": _fmt_anom_pair(mname, "热量跳变", f"{_fmt_num(mr.heat_raw)} GJ/h", f"{_fmt_num(mr.heat_clean)} GJ/h", mode)})

    burst_events.sort(key=lambda x: (x["hour"], x["entity_type"], x["entity_name"]))

    # 组装 9大中心 24h 横表与 主干网 24h 横表
    center_matrix_24h: List[Dict[str, Any]] = []
    for g in report["group_summaries"]["by_center"]:
        cid = int(g["group_key"])
        hrs = center_hour_heats.get(cid, [None] * 24)
        valid_hrs = [v for v in hrs if v is not None]
        day_sum = round(sum(valid_hrs), 2) if valid_hrs else None
        area_wan = g.get("covered_area_wan") or 0.0
        center_matrix_24h.append({
            "name": g["group_name"],
            "covered_area_wan": area_wan,
            "hours": hrs,
            "hour_notes": {h: _pack_agg_anomaly(ns)["note"] for h, ns in center_hour_notes.get(cid, {}).items() if ns},
            "day_heat_gj": day_sum,
            "heat_per_wan_gj": _round(day_sum / area_wan, 2) if (day_sum is not None and area_wan > 0) else None,
        })

    rdfz_matrix_24h: List[Dict[str, Any]] = []
    for g in report["group_summaries"]["by_rdfz"]:
        rname = str(g["group_key"] or "未分配")
        hrs = rdfz_hour_heats.get(rname, [None] * 24)
        valid_hrs = [v for v in hrs if v is not None]
        day_sum = round(sum(valid_hrs), 2) if valid_hrs else None
        area_wan = g.get("covered_area_wan") or 0.0
        rdfz_matrix_24h.append({
            "name": g["group_name"],
            "covered_area_wan": area_wan,
            "hours": hrs,
            "hour_notes": {h: _pack_agg_anomaly(ns)["note"] for h, ns in rdfz_hour_notes.get(rname, {}).items() if ns},
            "day_heat_gj": day_sum,
            "heat_per_wan_gj": _round(day_sum / area_wan, 2) if (day_sum is not None and area_wan > 0) else None,
        })

    station_matrix_24h: List[Dict[str, Any]] = []
    for s in report["stations"]:
        sid = s["station_id"]
        hrs = station_hour_heats.get(sid, [None] * 24)
        valid_hrs = [v for v in hrs if v is not None]
        day_sum = round(sum(valid_hrs), 2) if valid_hrs else None
        area = s.get("covered_area")
        area_wan = area / 10000.0 if (area and area > 0) else 0.0
        h_notes = station_hour_notes.get(sid, {})
        station_matrix_24h.append({
            "name": s["name"],
            "center_name": s["center_name"],
            "rdfz": s["rdfz"],
            "branch_name": s["branch_name"],
            "covered_area": area,
            "hours": hrs,
            "hour_notes": h_notes,
            "day_heat_gj": day_sum,
            "heat_per_wan_gj": _round(day_sum / area_wan, 2) if (day_sum is not None and area_wan > 0) else None,
            "anomaly_note": "；".join(f"{h:02d}:00 {n.split(': ', 1)[-1]}" for h, n in sorted(h_notes.items())),
        })
    station_matrix_24h.sort(key=lambda x: (x["day_heat_gj"] if x["day_heat_gj"] is not None else -1.0), reverse=True)

    entity_trend = None
    if scope and key:
        try:
            entity_trend = get_entity_trend_24h(report["meta"]["date"], scope, key, mode=mode)
        except Exception:
            entity_trend = None

    return {
        "report": report,
        "center_matrix_24h": center_matrix_24h,
        "rdfz_matrix_24h": rdfz_matrix_24h,
        "station_matrix_24h": station_matrix_24h,
        "burst_events": burst_events,
        "entity_trend": entity_trend,
    }


def _append_24h_trend_sheet(
    wb: Any,
    title: str,
    trend_rows: Sequence[Dict[str, Any]],
    total_stations_default: Optional[int] = None,
) -> None:
    """将 24 小时逐时统计序列写入工作表（含汇总行与突发跳变标红）。"""
    is_pristine_active = (
        len(wb.sheetnames) == 1
        and wb.active.max_row == 1
        and wb.active.max_column == 1
        and wb.active.cell(1, 1).value is None
    )
    if is_pristine_active:
        ws = wb.active
        ws.title = _safe_sheet_title(title, [])
    else:
        ws = wb.create_sheet(_safe_sheet_title(title, wb.sheetnames))
    headers = [
        "小时", "在线/上报站", "小时供热量(GJ)", "折算热指标(W/㎡)", "一网加权供温(℃)",
        "一网加权回温(℃)", "供回温差(℃)", "近端室外气温(℃)", "突发跳变修正说明",
    ]
    rows: List[List[Any]] = []
    hl: Dict[Tuple[int, int], str] = {}
    tot_heat = 0.0
    has_heat = False
    idx_vals: List[float] = []
    sup_vals: List[float] = []
    ret_vals: List[float] = []
    out_vals: List[float] = []

    for r_i, item in enumerate(trend_rows):
        anoms = item.get("anomalies") or {}
        hg = item.get("hour_heat_gj")
        wm2 = item.get("heat_index_wm2")
        sup = item.get("avg_sup_temp")
        ret = item.get("avg_ret_temp")
        diff_t = _round(sup - ret, 2) if (sup is not None and ret is not None) else None
        out_t = item.get("outdoor_temp")
        st_cnt = item.get("station_count")
        st_txt = f"{st_cnt}/{total_stations_default}" if (total_stations_default and st_cnt is not None) else (st_cnt if st_cnt is not None else "-")
        note_txt = _join_anom_notes(anoms, ["hour_heat_gj", "heat_index_wm2", "avg_sup_temp", "avg_ret_temp"])

        if hg is not None:
            tot_heat += float(hg)
            has_heat = True
        if wm2 is not None:
            idx_vals.append(float(wm2))
        if sup is not None:
            sup_vals.append(float(sup))
        if ret is not None:
            ret_vals.append(float(ret))
        if out_t is not None:
            out_vals.append(float(out_t))

        if anoms.get("hour_heat_gj"):
            hl[(r_i, 2)] = anoms["hour_heat_gj"]["note"]
        if anoms.get("heat_index_wm2"):
            hl[(r_i, 3)] = anoms["heat_index_wm2"]["note"]
        if anoms.get("avg_sup_temp"):
            hl[(r_i, 4)] = anoms["avg_sup_temp"]["note"]
            hl[(r_i, 6)] = anoms["avg_sup_temp"]["note"]
        if anoms.get("avg_ret_temp"):
            hl[(r_i, 5)] = anoms["avg_ret_temp"]["note"]
            hl[(r_i, 6)] = anoms["avg_ret_temp"]["note"]

        rows.append([item["label"], st_txt, hg, wm2, sup, ret, diff_t, out_t, note_txt])

    avg_sup = _round(sum(sup_vals) / len(sup_vals), 2) if sup_vals else None
    avg_ret = _round(sum(ret_vals) / len(ret_vals), 2) if ret_vals else None
    rows.append([
        "全天合计/均值",
        "-",
        round(tot_heat, 2) if has_heat else None,
        _round(sum(idx_vals) / len(idx_vals), 2) if idx_vals else None,
        avg_sup,
        avg_ret,
        _round(avg_sup - avg_ret, 2) if (avg_sup is not None and avg_ret is not None) else None,
        _round(sum(out_vals) / len(out_vals), 1) if out_vals else None,
        f"共 {sum(1 for r in rows if r[-1])} 个时段含突发跳变",
    ])
    _style_excel_sheet(ws, headers, rows, highlight_cells=hl, bold_last_row=True)


def _append_matrix_24h_sheet(
    wb: Any,
    title: str,
    entity_label: str,
    matrix_rows: Sequence[Dict[str, Any]],
    *,
    include_station_dims: bool = False,
) -> None:
    """将主体或242站24小时横向热量矩阵写入工作表，并标红突发跳变单元格。"""
    ws = wb.create_sheet(_safe_sheet_title(title, wb.sheetnames))
    hour_cols = [f"{h:02d}:00" for h in range(24)]
    if include_station_dims:
        headers = [entity_label, "所属中心", "主干热网", "支线热网", "面积(㎡)", *hour_cols, "日累计(GJ)", "日万平耗热(GJ/万㎡·d)", "突发跳变说明"]
        offset = 5
    else:
        headers = [entity_label, "在网面积(万㎡)", *hour_cols, "日累计供热量(GJ)", "日万平耗热(GJ/万㎡·d)", "突发跳变小时备注"]
        offset = 2

    rows: List[List[Any]] = []
    hl: Dict[Tuple[int, int], str] = {}
    col_sums = [0.0] * 24
    col_has = [False] * 24
    tot_area = 0.0
    tot_day = 0.0
    has_tot_day = False

    for r_i, item in enumerate(matrix_rows):
        hrs = item.get("hours") or [None] * 24
        h_notes = item.get("hour_notes") or {}
        for h in range(24):
            val = hrs[h]
            if val is not None:
                col_sums[h] += float(val)
                col_has[h] = True
            if h in h_notes:
                hl[(r_i, offset + h)] = h_notes[h]
        day_val = item.get("day_heat_gj")
        if day_val is not None:
            tot_day += float(day_val)
            has_tot_day = True
            if h_notes:
                hl[(r_i, offset + 24)] = "；".join(h_notes.values())

        if include_station_dims:
            area_val = item.get("covered_area") or 0.0
            tot_area += float(area_val)
            rows.append([
                item["name"], item.get("center_name"), item.get("rdfz"), item.get("branch_name"),
                item.get("covered_area"), *hrs, day_val, item.get("heat_per_wan_gj"), item.get("anomaly_note") or "",
            ])
        else:
            area_wan = item.get("covered_area_wan") or 0.0
            tot_area += float(area_wan)
            note_summary = "；".join(f"{h:02d}:00" for h in sorted(h_notes.keys()))
            rows.append([
                item["name"], area_wan, *hrs, day_val, item.get("heat_per_wan_gj"),
                f"突发时段: {note_summary}" if note_summary else "",
            ])

    sum_hr_cells = [round(col_sums[h], 2) if col_has[h] else None for h in range(24)]
    if include_station_dims:
        area_wan_tot = tot_area / 10000.0
        rows.append([
            "合计", "-", "-", "-", round(tot_area, 2), *sum_hr_cells,
            round(tot_day, 2) if has_tot_day else None,
            _round(tot_day / area_wan_tot, 2) if (has_tot_day and area_wan_tot > 0) else None,
            "",
        ])
    else:
        rows.append([
            "全网合计", round(tot_area, 2), *sum_hr_cells,
            round(tot_day, 2) if has_tot_day else None,
            _round(tot_day / tot_area, 2) if (has_tot_day and tot_area > 0) else None,
            "",
        ])
    _style_excel_sheet(ws, headers, rows, highlight_cells=hl, bold_last_row=True)


def build_hourly_excel(report_data: Dict[str, Any], export_ctx: Optional[Dict[str, Any]] = None) -> bytes:
    """生成《当日 24 小时逐时统计 + 选中断面明细》多 Sheet Excel 字节流。"""
    wb = openpyxl.Workbook()
    meta = report_data.get("meta") or {}
    sel_hr_str = f"{int(meta.get('hour', 0)):02d}时"
    total_st = (report_data.get("kpis") or {}).get("total_stations") or 242

    # Sheet 1: 全网 24 小时逐时运行统计
    _append_24h_trend_sheet(
        wb,
        "全网24小时逐时统计",
        report_data.get("trend_24h") or [],
        total_stations_default=total_st,
    )

    # Sheet 2 (可选): 若页面上当前正查看某个特定主体，同步导出该主体的 24h 逐时统计
    entity_trend = (export_ctx or {}).get("entity_trend")
    if entity_trend and entity_trend.get("trend_24h"):
        _append_24h_trend_sheet(
            wb,
            f"{entity_trend['entity_name']}_24小时",
            entity_trend["trend_24h"],
            total_stations_default=entity_trend.get("station_count"),
        )

    # Sheet 3/4/5: 横向 24 小时矩阵（9大中心 / 主干热网 / 242换热站）
    if export_ctx:
        _append_matrix_24h_sheet(wb, "9大中心_24小时供热矩阵", "服务中心", export_ctx.get("center_matrix_24h") or [])
        _append_matrix_24h_sheet(wb, "主干热网_24小时供热矩阵", "主干热网", export_ctx.get("rdfz_matrix_24h") or [])
        _append_matrix_24h_sheet(
            wb,
            "242站_24小时供热矩阵",
            "站点名称",
            export_ctx.get("station_matrix_24h") or [],
            include_station_dims=True,
        )

        # Sheet 6: 当日突发跳变记录清单
        ws_burst = wb.create_sheet(_safe_sheet_title("当日突发跳变记录", wb.sheetnames))
        burst_rows = [
            [e["label"], e["entity_type"], e["entity_name"], e["metric"], e["note"]]
            for e in (export_ctx.get("burst_events") or [])
        ]
        burst_hl = {(i, 4): r[4] for i, r in enumerate(burst_rows)}
        _style_excel_sheet(
            ws_burst,
            ["发生小时", "对象类型", "主体/站点名称", "触发指标", "突发跳变及修正说明"],
            burst_rows or [["-", "-", "当日无突发跳变记录", "-", "-"]],
            highlight_cells=burst_hl,
        )

    # Sheet 7: 当前选中小时 多维汇总（9大中心 + 9主干热网 + 41支线网）
    ws_dim = wb.create_sheet(_safe_sheet_title(f"{sel_hr_str}_多维汇总", wb.sheetnames))
    dim_rows: List[List[Any]] = []
    dim_hl: Dict[Tuple[int, int], str] = {}
    dim_defs = (
        ("服务中心", "by_center"),
        ("主干热网", "by_rdfz"),
        ("支线热网", "by_branch"),
    )
    gs = report_data.get("group_summaries") or {}
    for dim_label, dim_key in dim_defs:
        for g in gs.get(dim_key) or []:
            r_i = len(dim_rows)
            anoms = g.get("anomalies") or {}
            if anoms.get("hour_heat_gj"):
                dim_hl[(r_i, 4)] = anoms["hour_heat_gj"]["note"]
            if anoms.get("instant_load_gjh"):
                dim_hl[(r_i, 5)] = anoms["instant_load_gjh"]["note"]
            if anoms.get("heat_index_wm2"):
                dim_hl[(r_i, 6)] = anoms["heat_index_wm2"]["note"]
            if anoms.get("hour_water_t"):
                dim_hl[(r_i, 7)] = anoms["hour_water_t"]["note"]
            if anoms.get("avg_sup_temp"):
                dim_hl[(r_i, 8)] = anoms["avg_sup_temp"]["note"]
            if anoms.get("avg_ret_temp"):
                dim_hl[(r_i, 9)] = anoms["avg_ret_temp"]["note"]
            dim_rows.append([
                dim_label, g["group_name"], f"{g['online_stations']}/{g['total_stations']}",
                g["covered_area_wan"], g["hour_heat_gj"], g["instant_load_gjh"], g["heat_index_wm2"],
                g["hour_water_t"], g["avg_sup_temp"], g["avg_ret_temp"], _join_anom_notes(anoms),
            ])
    _style_excel_sheet(
        ws_dim,
        ["分类维度", "主体名称", "在线/总站", "供热面积(万㎡)", "小时供热量(GJ)", "瞬时负荷(GJ/h)", "折算热指标(W/㎡)", "小时补水(t)", "加权供温(℃)", "加权回温(℃)", "突发跳变说明"],
        dim_rows,
        highlight_cells=dim_hl,
    )

    # Sheet 8: 当前小时 242 换热站全参数明细（含突发标红与批注）
    ws_st = wb.create_sheet(_safe_sheet_title(f"{sel_hr_str}_242换热站明细", wb.sheetnames))
    st_rows: List[List[Any]] = []
    st_hl: Dict[Tuple[int, int], str] = {}
    for r_i, s in enumerate(report_data.get("stations") or []):
        fn = s.get("field_notes") or {}
        if fn.get("e3_e4"):
            st_hl[(r_i, 6)] = fn["e3_e4"]
            st_hl[(r_i, 7)] = fn["e3_e4"]
        if fn.get("e7_e8"):
            st_hl[(r_i, 8)] = fn["e7_e8"]
            st_hl[(r_i, 9)] = fn["e7_e8"]
        if fn.get("e11"):
            st_hl[(r_i, 10)] = fn["e11"]
        if fn.get("hour_heat_gj"):
            st_hl[(r_i, 11)] = fn["hour_heat_gj"]
        if fn.get("heat_index_wm2"):
            st_hl[(r_i, 13)] = fn["heat_index_wm2"]
        if fn.get("e14"):
            st_hl[(r_i, 14)] = fn["e14"]
        st_rows.append([
            s["name"], s["center_name"], s["rdfz"], s.get("covered_area"), "在线" if s["online"] else "离线",
            s["e1"], s["e3"], s["e4"], s["e7"], s["e8"], s["e11"], s["hour_heat_gj"], s["hour_heat_source"],
            s["heat_index_wm2"], s["hour_water_t"], s["value_source"], _join_anom_notes(fn),
        ])
    _style_excel_sheet(
        ws_st,
        ["站点名称", "所属中心", "主干热网", "面积(㎡)", "在线", "一网供流(t/h)", "一网供温(℃)", "一网回温(℃)", "一网供压(MPa)", "一网回压(MPa)", "瞬时热量(GJ/h)", "小时供热量(GJ)", "热量口径", "热指标(W/㎡)", "小时补水(t)", "数据来源", "突发跳变说明"],
        st_rows,
        highlight_cells=st_hl,
    )

    # Sheet 9: 当前小时 上游热源与首站
    ws_up = wb.create_sheet(_safe_sheet_title(f"{sel_hr_str}_上游热源首站", wb.sheetnames))
    up_rows: List[List[Any]] = []
    up_hl: Dict[Tuple[int, int], str] = {}
    for r_i, u in enumerate(report_data.get("upstream_points") or []):
        fn = u.get("field_notes") or {}
        if fn.get("temp"):
            up_hl[(r_i, 4)] = fn["temp"]
        if fn.get("pressure"):
            up_hl[(r_i, 5)] = fn["pressure"]
        if fn.get("heat"):
            up_hl[(r_i, 7)] = fn["heat"]
        if fn.get("hour_heat_gj"):
            up_hl[(r_i, 8)] = fn["hour_heat_gj"]
        up_rows.append([
            u["category"], u["sub_category"], u["display_name"], u["data_zone"],
            u["temp"], u["pressure"], u["flow"], u["heat"], u["hour_heat_gj"], u["value_source"], _join_anom_notes(fn),
        ])
    _style_excel_sheet(
        ws_up,
        ["类别", "子类", "测点名称", "数据区", "温度(℃)", "压力(MPa)", "瞬时流量", "瞬时热量", "小时积分热量(GJ)", "状态", "突发跳变说明"],
        up_rows,
        highlight_cells=up_hl,
    )

    # Sheet 10: 当前小时 商业用户明细
    ws_mc = wb.create_sheet(_safe_sheet_title(f"{sel_hr_str}_464商业用户", wb.sheetnames))
    mc_rows: List[List[Any]] = []
    mc_hl: Dict[Tuple[int, int], str] = {}
    for r_i, m in enumerate(report_data.get("merchants") or []):
        fn = m.get("field_notes") or {}
        if fn.get("flow"):
            mc_hl[(r_i, 4)] = fn["flow"]
        if fn.get("temp"):
            mc_hl[(r_i, 5)] = fn["temp"]
            mc_hl[(r_i, 6)] = fn["temp"]
        if fn.get("heat"):
            mc_hl[(r_i, 7)] = fn["heat"]
        if fn.get("hour_heat_gj"):
            mc_hl[(r_i, 8)] = fn["hour_heat_gj"]
        mc_rows.append([
            m["name"], m["rdfz"], m["branch_name"], "在线" if m["online"] else "离线",
            m["flow"], m["temp_sup"], m["temp_ret"], m["heat"], m["hour_heat_gj"], m["hour_flow_t"],
            m["valve_open"], m["value_source"], _join_anom_notes(fn),
        ])
    _style_excel_sheet(
        ws_mc,
        ["商业户名称", "主干热网", "支线网", "状态", "供水流量(t/h)", "供温(℃)", "回温(℃)", "瞬时热量(GJ/h)", "小时供热量(GJ)", "小时流量(t)", "阀门开度(%)", "数据来源", "突发跳变说明"],
        mc_rows,
        highlight_cells=mc_hl,
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_daily_export_payload(
    target_date_str: Optional[str],
    period_mode: str = "natural",
    mode: str = "clean",
    max_days: int = 31,
) -> Dict[str, Any]:
    """为《每日运行报告》Excel 准备选定日起止（最长近 31 天 / 2026-11-01 起）的多日逐日趋势、对账矩阵与选定日明细。"""
    report = get_daily_report(target_date_str=target_date_str, period_mode=period_mode, mode=mode)
    target_d = date.fromisoformat(report["meta"]["date"])
    period = report["meta"]["period_mode"]
    effective_mode = report["meta"].get("mode", "clean")
    use_raw = effective_mode == "raw"

    season_start = date(2026, 11, 1)
    win_start_d = max(season_start, target_d - timedelta(days=max(0, int(max_days) - 1)))
    if win_start_d > target_d:
        win_start_d = target_d

    date_list: List[date] = []
    cur_d = win_start_d
    while cur_d <= target_d:
        date_list.append(cur_d)
        cur_d += timedelta(days=1)

    if period == "shift":
        win_start_ts = datetime(win_start_d.year, win_start_d.month, win_start_d.day, 8, 0, 0, tzinfo=EAST_8) - timedelta(days=1)
        win_end_ts = datetime(target_d.year, target_d.month, target_d.day, 8, 0, 0, tzinfo=EAST_8)
    else:
        win_start_ts = datetime(win_start_d.year, win_start_d.month, win_start_d.day, 0, 0, 0, tzinfo=EAST_8)
        win_end_ts = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8) + timedelta(days=1)

    with engine.connect() as conn:
        centers = [
            dict(r._mapping)
            for r in conn.execute(
                text("SELECT center_id, name FROM smart_heating_platform.dict_service_center ORDER BY center_id")
            ).fetchall()
        ]
        stations_meta = {
            r.station_id: dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT hs.station_id, hs.name, hs.center_id, sc.name AS center_name, hs.rdfz, hs.covered_area "
                    "FROM smart_heating_platform.dict_heating_station hs "
                    "JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id"
                )
            ).fetchall()
        }
        hourly_rows = conn.execute(
            text(
                "SELECT biz_hour, station_id, e1_raw, e1_clean, e3_raw, e3_clean, e4_raw, e4_clean, "
                "e7_raw, e7_clean, e8_raw, e8_clean, e11_raw, e11_clean, e14_raw, e14_clean, "
                "hour_heat_raw_gj, hour_heat_gj, hour_water_t, value_source, fault_tag "
                "FROM smart_heating_platform.fact_station_hourly "
                "WHERE biz_hour >= :ws AND biz_hour < :we"
            ),
            {"ws": win_start_ts, "de": win_end_ts, "we": win_end_ts},
        ).fetchall()
        manual_rows = conn.execute(
            text(
                "SELECT date, company, item, value "
                "FROM public.daily_basic_data "
                "WHERE date >= :sd AND date <= :ed "
                "AND (sheet_name = 'GongRe_branches_detail_Sheet' OR company = 'GongRe') "
                "AND item IN ('consumption_station_heat', 'consumption_station_fill_water')"
            ),
            {"sd": win_start_d, "ed": target_d},
        ).fetchall()
        mc_daily_rows = conn.execute(
            text(
                "SELECT biz_date, COALESCE(SUM(daily_consumption), 0) AS tot_mc_heat "
                "FROM smart_heating_platform.fact_merchant_daily "
                "WHERE biz_date >= :sd AND biz_date <= :ed "
                "GROUP BY biz_date"
            ),
            {"sd": win_start_d, "ed": target_d},
        ).fetchall()
        temp_rows = conn.execute(
            text(
                "SELECT date_time, value FROM public.temperature_data "
                "WHERE type = 'near' AND date_time >= :ws AND date_time < :we AND value IS NOT NULL"
            ),
            {"ws": win_start_ts.replace(tzinfo=None), "we": win_end_ts.replace(tzinfo=None)},
        ).fetchall()

    def _assign_biz_date(dt_val: datetime) -> date:
        dt_e8 = dt_val.astimezone(EAST_8) if dt_val.tzinfo else dt_val.replace(tzinfo=EAST_8)
        return (dt_e8 + timedelta(hours=16)).date() if period == "shift" else dt_e8.date()

    # 按日分桶计算全周期站点/中心每日汇总与突发跳变
    rows_by_day: Dict[date, List[Dict[str, Any]]] = {d: [] for d in date_list}
    for r in hourly_rows:
        bd = _assign_biz_date(r.biz_hour)
        if bd in rows_by_day:
            rows_by_day[bd].append(dict(r._mapping))

    outdoor_by_day: Dict[date, List[float]] = {}
    for tr in temp_rows:
        bd = _assign_biz_date(tr.date_time)
        if bd in rows_by_day and tr.value is not None:
            outdoor_by_day.setdefault(bd, []).append(float(tr.value))

    mc_heat_by_day: Dict[date, float] = {r.biz_date: float(r.tot_mc_heat) for r in mc_daily_rows if r.tot_mc_heat is not None}

    manual_by_day_center: Dict[Tuple[date, int], Dict[str, float]] = {}
    manual_gongre_by_day: Dict[date, Dict[str, float]] = {}
    for mr in manual_rows:
        val = _f(mr.value)
        if val is None:
            continue
        comp = str(mr.company)
        if comp == "GongRe":
            manual_gongre_by_day.setdefault(mr.date, {})[mr.item] = val
        elif comp in CENTER_COMPANY_MAP:
            manual_by_day_center.setdefault((mr.date, CENTER_COMPANY_MAP[comp]), {})[mr.item] = val

    tot_area_m2 = sum((_f(sm["covered_area"]) or 0.0) for sm in stations_meta.values())
    tot_area_wan = tot_area_m2 / 10000.0 if tot_area_m2 > 0 else 0.0
    center_areas_wan = {
        c["center_id"]: sum((_f(sm["covered_area"]) or 0.0) for sm in stations_meta.values() if sm["center_id"] == c["center_id"]) / 10000.0
        for c in centers
    }

    daily_overview: List[Dict[str, Any]] = []
    center_day_heat: Dict[int, Dict[date, Optional[float]]] = {c["center_id"]: {} for c in centers}
    center_day_diff_pct: Dict[int, Dict[date, Optional[float]]] = {c["center_id"]: {} for c in centers}
    center_day_notes: Dict[int, Dict[date, str]] = {c["center_id"]: {} for c in centers}
    station_day_heat: Dict[str, Dict[date, Optional[float]]] = {sid: {} for sid in stations_meta}
    station_day_notes: Dict[str, Dict[date, str]] = {sid: {} for sid in stations_meta}

    for bd in date_list:
        d_rows = rows_by_day.get(bd) or []
        day_counts = _count_station_day_anomalies(
            d_rows,
            lambda rm: (stations_meta.get(rm.get("station_id")) or {}).get("name") or rm.get("station_id"),
        )
        d_sys_heat = 0.0
        d_sys_water = 0.0
        has_d = len(d_rows) > 0
        c_heat_acc: Dict[int, float] = {}
        c_notes_acc: Dict[int, List[str]] = {}
        st_heat_acc: Dict[str, float] = {}
        st_notes_acc: Dict[str, List[str]] = {}
        day_anom_notes: List[str] = []

        for rm in d_rows:
            sid = rm["station_id"]
            sm = stations_meta.get(sid)
            if not sm:
                continue
            cid = sm["center_id"]
            eff_h = _f(rm["hour_heat_raw_gj"] if (use_raw and rm.get("hour_heat_raw_gj") is not None) else rm.get("hour_heat_gj"))
            eff_w = _f(rm.get("hour_water_t"))
            if eff_h is not None:
                d_sys_heat += eff_h
                c_heat_acc[cid] = c_heat_acc.get(cid, 0.0) + eff_h
                st_heat_acc[sid] = st_heat_acc.get(sid, 0.0) + eff_h
            if eff_w is not None:
                d_sys_water += eff_w

            fn = _build_station_hour_anomalies(rm, sm["name"], day_counts=day_counts.get(sid), mode=effective_mode)
            if fn.get("hour_heat_gj"):
                hr_txt = rm["biz_hour"].astimezone(EAST_8).strftime("%H:00") if rm["biz_hour"].tzinfo else rm["biz_hour"].strftime("%H:00")
                note_item = f"{hr_txt} {fn['hour_heat_gj']}"
                c_notes_acc.setdefault(cid, []).append(note_item)
                st_notes_acc.setdefault(sid, []).append(note_item)
                day_anom_notes.append(note_item)

        d_man_heat = 0.0
        d_man_water = 0.0
        has_man_h = False
        has_man_w = False
        for c in centers:
            cid = c["center_id"]
            ch = round(c_heat_acc[cid], 2) if cid in c_heat_acc else None
            center_day_heat[cid][bd] = ch
            man = manual_by_day_center.get((bd, cid), {})
            mh = man.get("consumption_station_heat")
            mw = man.get("consumption_station_fill_water")
            if mh is not None:
                d_man_heat += mh
                has_man_h = True
            if mw is not None:
                d_man_water += mw
                has_man_w = True
            if ch is not None and mh is not None and mh != 0:
                center_day_diff_pct[cid][bd] = round((ch - mh) / mh * 100.0, 2)
            else:
                center_day_diff_pct[cid][bd] = None
            if c_notes_acc.get(cid):
                center_day_notes[cid][bd] = _pack_agg_anomaly(c_notes_acc[cid])["note"]

        for sid in stations_meta:
            station_day_heat[sid][bd] = round(st_heat_acc[sid], 2) if sid in st_heat_acc else None
            if st_notes_acc.get(sid):
                station_day_notes[sid][bd] = _pack_agg_anomaly(st_notes_acc[sid])["note"]

        ref_man_h = d_man_heat if has_man_h else (manual_gongre_by_day.get(bd, {}).get("consumption_station_heat"))
        ref_man_w = d_man_water if has_man_w else (manual_gongre_by_day.get(bd, {}).get("consumption_station_fill_water"))
        diff_h = (d_sys_heat - ref_man_h) if (has_d and ref_man_h is not None) else None
        diff_pct = (diff_h / ref_man_h * 100.0) if (diff_h is not None and ref_man_h and ref_man_h != 0) else None
        out_list = outdoor_by_day.get(bd) or []

        daily_overview.append({
            "date": bd.isoformat(),
            "avg_outdoor_temp": round(sum(out_list) / len(out_list), 1) if out_list else None,
            "sys_heat_gj": round(d_sys_heat, 2) if has_d else None,
            "man_heat_gj": _round(ref_man_h, 2),
            "heat_diff_gj": _round(diff_h, 2),
            "heat_diff_pct": _round(diff_pct, 2),
            "heat_per_wan_gj": _round(d_sys_heat / tot_area_wan, 2) if (has_d and tot_area_wan > 0) else None,
            "sys_water_t": round(d_sys_water, 2) if has_d else None,
            "man_water_t": _round(ref_man_w, 2),
            "merchant_heat_gj": _round(mc_heat_by_day.get(bd), 2),
            "anomaly_note": _pack_agg_anomaly(day_anom_notes)["note"] if day_anom_notes else "",
        })

    # 组织中心/站点跨天横向矩阵
    center_matrix = []
    for c in centers:
        cid = c["center_id"]
        vals = [center_day_heat[cid][bd] for bd in date_list]
        valid_v = [v for v in vals if v is not None]
        sum_v = round(sum(valid_v), 2) if valid_v else None
        area_wan = center_areas_wan.get(cid, 0.0)
        center_matrix.append({
            "center_id": cid,
            "name": c["name"],
            "covered_area_wan": round(area_wan, 2),
            "values": vals,
            "diff_pcts": [center_day_diff_pct[cid][bd] for bd in date_list],
            "day_notes": {idx: center_day_notes[cid][bd] for idx, bd in enumerate(date_list) if bd in center_day_notes[cid]},
            "sum_heat_gj": sum_v,
            "avg_per_wan_gj": _round(sum_v / (area_wan * len(valid_v)), 2) if (sum_v is not None and area_wan > 0 and valid_v) else None,
        })

    station_matrix = []
    for s in report["station_daily"]:
        sid = s["station_id"]
        vals = [station_day_heat[sid][bd] for bd in date_list]
        valid_v = [v for v in vals if v is not None]
        sum_v = round(sum(valid_v), 2) if valid_v else None
        area = s.get("covered_area")
        area_wan = area / 10000.0 if (area and area > 0) else 0.0
        notes_map = {idx: station_day_notes[sid][bd] for idx, bd in enumerate(date_list) if bd in station_day_notes[sid]}
        station_matrix.append({
            "name": s["name"],
            "center_name": s["center_name"],
            "rdfz": s["rdfz"],
            "covered_area": area,
            "values": vals,
            "day_notes": notes_map,
            "sum_heat_gj": sum_v,
            "avg_per_wan_gj": _round(sum_v / (area_wan * len(valid_v)), 2) if (sum_v is not None and area_wan > 0 and valid_v) else None,
            "anomaly_summary": "；".join(f"{date_list[idx].strftime('%m-%d')} 突跳" for idx in sorted(notes_map.keys())),
        })

    return {
        "report": report,
        "dates": date_list,
        "date_labels": [d.strftime("%m-%d") for d in date_list],
        "daily_overview": daily_overview,
        "center_matrix": center_matrix,
        "station_matrix": station_matrix,
        "tot_area_wan": round(tot_area_wan, 2),
    }


def build_daily_excel(report_data: Dict[str, Any], export_ctx: Optional[Dict[str, Any]] = None) -> bytes:
    """生成《每日生产精算与双轨对账全量报告》Excel（含周期逐日总览/矩阵 + 结算日核对与明细）。"""
    wb = openpyxl.Workbook()
    meta = report_data.get("meta") or {}
    sel_date_short = str(meta.get("date") or "当日")[-5:]

    # 1. 若具备全周期上下文，先写入前 4 张跨天逐日表
    if export_ctx:
        date_labels = export_ctx.get("date_labels") or []
        overview = export_ctx.get("daily_overview") or []

        # Sheet 1: 全网逐日统计总览
        ws_ov = wb.active
        ws_ov.title = "全网逐日统计总览"
        ov_rows: List[List[Any]] = []
        ov_hl: Dict[Tuple[int, int], str] = {}
        ov_warn: Dict[Tuple[int, int], str] = {}
        sum_sys_h, sum_man_h, sum_sys_w, sum_man_w, sum_mc_h = 0.0, 0.0, 0.0, 0.0, 0.0
        has_sh, has_mh, has_sw, has_mw, has_mc = False, False, False, False, False
        out_temps: List[float] = []
        wan_vals: List[float] = []

        for r_i, item in enumerate(overview):
            pct = item.get("heat_diff_pct")
            if pct is not None and abs(pct) > 10.0:
                ov_warn[(r_i, 5)] = f"双轨热量偏差 {pct:+.2f}%（超过 ±10% 阈值）"
            if item.get("anomaly_note"):
                ov_hl[(r_i, 2)] = item["anomaly_note"]
                ov_hl[(r_i, 6)] = item["anomaly_note"]

            if item.get("avg_outdoor_temp") is not None:
                out_temps.append(float(item["avg_outdoor_temp"]))
            if item.get("sys_heat_gj") is not None:
                sum_sys_h += float(item["sys_heat_gj"])
                has_sh = True
            if item.get("man_heat_gj") is not None:
                sum_man_h += float(item["man_heat_gj"])
                has_mh = True
            if item.get("heat_per_wan_gj") is not None:
                wan_vals.append(float(item["heat_per_wan_gj"]))
            if item.get("sys_water_t") is not None:
                sum_sys_w += float(item["sys_water_t"])
                has_sw = True
            if item.get("man_water_t") is not None:
                sum_man_w += float(item["man_water_t"])
                has_mw = True
            if item.get("merchant_heat_gj") is not None:
                sum_mc_h += float(item["merchant_heat_gj"])
                has_mc = True

            ov_rows.append([
                item["date"], item["avg_outdoor_temp"], item["sys_heat_gj"], item["man_heat_gj"],
                item["heat_diff_gj"], item["heat_diff_pct"], item["heat_per_wan_gj"],
                item["sys_water_t"], item["man_water_t"], item["merchant_heat_gj"], item["anomaly_note"],
            ])

        tot_diff = (sum_sys_h - sum_man_h) if (has_sh and has_mh) else None
        tot_pct = _round(tot_diff / sum_man_h * 100.0, 2) if (tot_diff is not None and sum_man_h != 0) else None
        ov_rows.append([
            "期间合计/均值",
            _round(sum(out_temps) / len(out_temps), 1) if out_temps else None,
            round(sum_sys_h, 2) if has_sh else None,
            round(sum_man_h, 2) if has_mh else None,
            _round(tot_diff, 2),
            tot_pct,
            _round(sum(wan_vals) / len(wan_vals), 2) if wan_vals else None,
            round(sum_sys_w, 2) if has_sw else None,
            round(sum_man_w, 2) if has_mw else None,
            round(sum_mc_h, 2) if has_mc else None,
            f"结算口径: {'生产班次(08-08)' if meta.get('period_mode') == 'shift' else '自然日(00-24)'} / {'原始' if meta.get('mode') == 'raw' else '修正后'}",
        ])
        _style_excel_sheet(
            ws_ov,
            ["日期", "近端日均气温(℃)", "系统精算热量(GJ)", "手工日报热量(GJ)", "热量偏差(GJ)", "偏差率(%)", "万平耗热(GJ/万㎡·d)", "系统补水(t)", "手工补水(t)", "商业日耗(GJ)", "突发跳变说明"],
            ov_rows,
            highlight_cells=ov_hl,
            warn_cells=ov_warn,
            bold_last_row=True,
        )

        # Sheet 2: 9大中心_逐日供热矩阵
        ws_cm = wb.create_sheet("9大中心_逐日供热矩阵")
        cm_headers = ["服务中心", "在网面积(万㎡)", *date_labels, "期间累计(GJ)", "日均万平耗热(GJ/万㎡·d)"]
        cm_rows: List[List[Any]] = []
        cm_hl: Dict[Tuple[int, int], str] = {}
        day_sums = [0.0] * len(date_labels)
        day_has = [False] * len(date_labels)
        tot_cm_heat = 0.0
        has_cm_tot = False
        for r_i, c in enumerate(export_ctx.get("center_matrix") or []):
            vals = c["values"]
            for idx, v in enumerate(vals):
                if v is not None:
                    day_sums[idx] += float(v)
                    day_has[idx] = True
                if idx in c["day_notes"]:
                    cm_hl[(r_i, 2 + idx)] = c["day_notes"][idx]
            if c["sum_heat_gj"] is not None:
                tot_cm_heat += float(c["sum_heat_gj"])
                has_cm_tot = True
            cm_rows.append([c["name"], c["covered_area_wan"], *vals, c["sum_heat_gj"], c["avg_per_wan_gj"]])
        tot_area_wan = export_ctx.get("tot_area_wan") or 0.0
        valid_days_cnt = sum(1 for f in day_has if f)
        cm_rows.append([
            "全网合计",
            tot_area_wan,
            *[round(day_sums[i], 2) if day_has[i] else None for i in range(len(date_labels))],
            round(tot_cm_heat, 2) if has_cm_tot else None,
            _round(tot_cm_heat / (tot_area_wan * valid_days_cnt), 2) if (has_cm_tot and tot_area_wan > 0 and valid_days_cnt > 0) else None,
        ])
        _style_excel_sheet(ws_cm, cm_headers, cm_rows, highlight_cells=cm_hl, bold_last_row=True)

        # Sheet 3: 9大中心_逐日双轨偏差率
        ws_dm = wb.create_sheet("9大中心_逐日双轨偏差率")
        dm_headers = ["服务中心", "说明", *date_labels]
        dm_rows: List[List[Any]] = []
        dm_warn: Dict[Tuple[int, int], str] = {}
        for r_i, c in enumerate(export_ctx.get("center_matrix") or []):
            pcts = c["diff_pcts"]
            for idx, pv in enumerate(pcts):
                if pv is not None and abs(pv) > 10.0:
                    dm_warn[(r_i, 2 + idx)] = f"{c['name']} {date_labels[idx]} 偏差 {pv:+.2f}%（超 ±10%）"
            dm_rows.append([c["name"], "(系统-手工)/手工×100%", *pcts])
        _style_excel_sheet(ws_dm, dm_headers, dm_rows, warn_cells=dm_warn)

        # Sheet 4: 242站_逐日供热矩阵
        ws_sm = wb.create_sheet("242站_逐日供热矩阵")
        sm_headers = ["站点名称", "所属中心", "主干热网", "面积(㎡)", *date_labels, "期间累计(GJ)", "日均万平耗热", "突发跳变记录"]
        sm_rows: List[List[Any]] = []
        sm_hl: Dict[Tuple[int, int], str] = {}
        st_day_sums = [0.0] * len(date_labels)
        st_day_has = [False] * len(date_labels)
        tot_sm_area = 0.0
        tot_sm_heat = 0.0
        has_sm_tot = False
        for r_i, s in enumerate(export_ctx.get("station_matrix") or []):
            vals = s["values"]
            for idx, v in enumerate(vals):
                if v is not None:
                    st_day_sums[idx] += float(v)
                    st_day_has[idx] = True
                if idx in s["day_notes"]:
                    sm_hl[(r_i, 4 + idx)] = s["day_notes"][idx]
            if s.get("covered_area"):
                tot_sm_area += float(s["covered_area"])
            if s["sum_heat_gj"] is not None:
                tot_sm_heat += float(s["sum_heat_gj"])
                has_sm_tot = True
            sm_rows.append([
                s["name"], s["center_name"], s["rdfz"], s["covered_area"], *vals,
                s["sum_heat_gj"], s["avg_per_wan_gj"], s["anomaly_summary"],
            ])
        sm_area_wan = tot_sm_area / 10000.0
        sm_valid_days = sum(1 for f in st_day_has if f)
        sm_rows.append([
            "合计", "-", "-", round(tot_sm_area, 2),
            *[round(st_day_sums[i], 2) if st_day_has[i] else None for i in range(len(date_labels))],
            round(tot_sm_heat, 2) if has_sm_tot else None,
            _round(tot_sm_heat / (sm_area_wan * sm_valid_days), 2) if (has_sm_tot and sm_area_wan > 0 and sm_valid_days > 0) else None,
            "",
        ])
        _style_excel_sheet(ws_sm, sm_headers, sm_rows, highlight_cells=sm_hl, bold_last_row=True)

    # Sheet 5 (or 1): 选定结算日 9大中心双轨核对（带合计行与±10%告警）
    cmp_title = _safe_sheet_title(f"{sel_date_short}_9大中心核对" if export_ctx else "9大中心双轨核对", wb.sheetnames)
    ws_cmp = wb.create_sheet(cmp_title) if export_ctx else wb.active
    if not export_ctx:
        ws_cmp.title = cmp_title

    cmp_rows: List[List[Any]] = []
    cmp_hl: Dict[Tuple[int, int], str] = {}
    cmp_warn: Dict[Tuple[int, int], str] = {}
    sum_c_area, sum_c_sh, sum_c_mh, sum_c_sw, sum_c_mw = 0.0, 0.0, 0.0, 0.0, 0.0
    has_c_mh, has_c_mw = False, False
    for r_i, c in enumerate(report_data["center_comparison"]):
        anoms = c.get("anomalies") or {}
        if c.get("is_heat_alert"):
            cmp_warn[(r_i, 5)] = f"热量双轨偏差率 {c['heat_diff_pct']:+.2f}% 超过 ±10% 告警线"
        if anoms.get("sys_heat_gj"):
            cmp_hl[(r_i, 2)] = anoms["sys_heat_gj"]["note"]
        if anoms.get("heat_diff_gj"):
            cmp_hl[(r_i, 4)] = anoms["heat_diff_gj"]["note"]
        if anoms.get("heat_diff_pct"):
            cmp_hl[(r_i, 5)] = anoms["heat_diff_pct"]["note"]
        if anoms.get("heat_per_wan_gj"):
            cmp_hl[(r_i, 6)] = anoms["heat_per_wan_gj"]["note"]
        if anoms.get("sys_water_t"):
            cmp_hl[(r_i, 7)] = anoms["sys_water_t"]["note"]
        sum_c_area += float(c.get("covered_area_wan") or 0.0)
        if c.get("sys_heat_gj") is not None:
            sum_c_sh += float(c["sys_heat_gj"])
        if c.get("man_heat_gj") is not None:
            sum_c_mh += float(c["man_heat_gj"])
            has_c_mh = True
        if c.get("sys_water_t") is not None:
            sum_c_sw += float(c["sys_water_t"])
        if c.get("man_water_t") is not None:
            sum_c_mw += float(c["man_water_t"])
            has_c_mw = True

        cmp_rows.append([
            c["center_name"], c["covered_area_wan"], c["sys_heat_gj"], c["man_heat_gj"],
            c["heat_diff_gj"], c["heat_diff_pct"], c["heat_per_wan_gj"], c["sys_water_t"],
            c["man_water_t"], c["avg_room_temp"], _join_anom_notes(anoms),
        ])
    c_diff_tot = (sum_c_sh - sum_c_mh) if has_c_mh else None
    c_pct_tot = _round(c_diff_tot / sum_c_mh * 100.0, 2) if (c_diff_tot is not None and sum_c_mh != 0) else None
    cmp_rows.append([
        "全网合计", round(sum_c_area, 2), round(sum_c_sh, 2), round(sum_c_mh, 2) if has_c_mh else None,
        _round(c_diff_tot, 2), c_pct_tot, _round(sum_c_sh / sum_c_area, 2) if sum_c_area > 0 else None,
        round(sum_c_sw, 2), round(sum_c_mw, 2) if has_c_mw else None, None,
        f"结算窗口: {meta.get('window_start', '-')} ~ {meta.get('window_end', '-')}",
    ])
    _style_excel_sheet(
        ws_cmp,
        ["中心名称", "面积(万㎡)", "系统精算热量(GJ)", "手工日报热量(GJ)", "热量偏差(GJ)", "偏差率(%)", "万平耗热(GJ/万㎡)", "系统补水(t)", "手工补水(t)", "日均室温(℃)", "突发跳变说明"],
        cmp_rows,
        highlight_cells=cmp_hl,
        warn_cells=cmp_warn,
        bold_last_row=True,
    )

    # Sheet 6: 选定结算日 242站日度能耗（补齐起止表底差值、日水量、日均供回温、合计行）
    ws_st = wb.create_sheet(_safe_sheet_title(f"{sel_date_short}_242站日耗" if export_ctx else "242站日度能耗", wb.sheetnames))
    st_rows: List[List[Any]] = []
    st_hl: Dict[Tuple[int, int], str] = {}
    tot_st_area, tot_st_h, tot_st_flow, tot_st_w, tot_st_e = 0.0, 0.0, 0.0, 0.0, 0.0
    for r_i, s in enumerate(report_data["station_daily"]):
        anoms = s.get("anomalies") or {}
        if anoms.get("day_heat_gj"):
            st_hl[(r_i, 9)] = anoms["day_heat_gj"]["note"]
        if anoms.get("heat_per_wan_gj"):
            st_hl[(r_i, 10)] = anoms["heat_per_wan_gj"]["note"]
        if anoms.get("day_water_t"):
            st_hl[(r_i, 12)] = anoms["day_water_t"]["note"]
        if anoms.get("avg_sup_temp"):
            st_hl[(r_i, 14)] = anoms["avg_sup_temp"]["note"]
        if anoms.get("avg_ret_temp"):
            st_hl[(r_i, 15)] = anoms["avg_ret_temp"]["note"]

        tot_diff = (
            _round(s["end_tot_j"] - s["start_tot_j"], 2)
            if (s.get("end_tot_j") is not None and s.get("start_tot_j") is not None)
            else None
        )
        tot_st_area += float(s.get("covered_area") or 0.0)
        tot_st_h += float(s.get("day_heat_gj") or 0.0)
        tot_st_flow += float(s.get("day_flow_t") or 0.0)
        tot_st_w += float(s.get("day_water_t") or 0.0)
        tot_st_e += float(s.get("day_elec_kwh") or 0.0)

        note_parts = [_join_anom_notes(anoms)]
        if s.get("day_heat_gj") is None:
            note_parts.append("全天无热量读数（缺失）")
        st_note = "；".join(p for p in note_parts if p)

        st_rows.append([
            s["name"], s["center_name"], s["rdfz"], s["covered_area"], s["hours_count"], s["meter_diff_hours"],
            s["start_tot_j"], s["end_tot_j"], tot_diff, s["day_heat_gj"], s["heat_per_wan_gj"],
            s.get("day_flow_t"), s["day_water_t"], s["day_elec_kwh"],
            s.get("avg_sup_temp"), s.get("avg_ret_temp"), st_note,
        ])
    st_area_wan = tot_st_area / 10000.0
    st_rows.append([
        "合计", "-", "-", round(tot_st_area, 2), "-", "-", "-", "-", "-",
        round(tot_st_h, 2), _round(tot_st_h / st_area_wan, 2) if st_area_wan > 0 else None,
        round(tot_st_flow, 2), round(tot_st_w, 2), round(tot_st_e, 2), None, None, "",
    ])
    _style_excel_sheet(
        ws_st,
        ["站点名称", "服务中心", "主干热网", "面积(㎡)", "有效热量小时", "表底小时", "起表底(GJ)", "止表底(GJ)", "表底止起差(GJ)", "日供热量(GJ)", "万平耗热", "日累计水量(t)", "日补水(t)", "日电耗(kWh)", "日均供温(℃)", "日均回温(℃)", "突发跳变/缺失说明"],
        st_rows,
        highlight_cells=st_hl,
        bold_last_row=True,
    )

    # Sheet 7: 选定结算日 464商业用户日耗量（对齐前端准确台账表头、三类状态及合计行）
    ws_mc = wb.create_sheet(_safe_sheet_title(f"{sel_date_short}_464商业用户" if export_ctx else "464商业用户日耗量", wb.sheetnames))
    mc_list = report_data.get("merchant_daily") or []
    mc_sum = report_data.get("merchant_summary") or {}
    mc_rows: List[List[Any]] = []
    mc_hl: Dict[Tuple[int, int], str] = {}
    mc_warn: Dict[Tuple[int, int], str] = {}
    for r_i, m in enumerate(mc_list):
        c_status = m.get("calc_status") or ("VALID" if m.get("daily_consumption") is not None else "MISSING_RECORD")
        s_label = m.get("status_label") or ("正常" if c_status == "VALID" else "缺日耗记录")
        s_note = m.get("status_note") or ""
        if c_status == "METER_ROLLBACK":
            mc_hl[(r_i, 8)] = s_note or s_label
        elif c_status == "MISSING_RECORD":
            mc_warn[(r_i, 8)] = s_note or s_label
        mc_rows.append([
            m["name"], m.get("rdfz"), m.get("rdry"), m.get("rdss"), m.get("rdjg"), m.get("rdgz"),
            m.get("daily_consumption"), m.get("daily_unit_heat"), s_label, s_note,
        ])
    tot_mc_heat = sum(float(m.get("daily_consumption") or 0.0) for m in mc_list)
    v_cnt = mc_sum.get("valid_count", sum(1 for m in mc_list if m.get("daily_consumption") is not None))
    m_cnt = mc_sum.get("missing_record_count", sum(1 for m in mc_list if (m.get("calc_status") == "MISSING_RECORD" or (m.get("calc_status") is None and m.get("daily_consumption") is None))))
    r_cnt = mc_sum.get("rollback_count", sum(1 for m in mc_list if m.get("calc_status") == "METER_ROLLBACK"))
    mc_rows.append([
        "合计", "-", "-", "-", "-", "-", round(tot_mc_heat, 2), None,
        f"共{len(mc_list)}户", f"可算日耗 {v_cnt} 户 · 缺日耗记录 {m_cnt} 户 · 表读数倒走 {r_cnt} 户",
    ])
    _style_excel_sheet(
        ws_mc,
        ["商户名称", "主干热网 (rdfz)", "介质 (rdry)", "产权 (rdss)", "价格分类 (rdjg)", "改造批次 (rdgz)", "日累计消耗量(GJ)", "日单耗参考", "计算状态", "说明"],
        mc_rows,
        highlight_cells=mc_hl,
        warn_cells=mc_warn,
        bold_last_row=True,
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
