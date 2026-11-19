# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 阳面逐小时报告、每日精算日报及双轨对账查询服务。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import EAST_8
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


def _compute_weighted_temp_and_kpis(
    stations: List[Dict[str, Any]],
    temps_by_station: Dict[str, List[float]],
    mode: str,
) -> Dict[str, Any]:
    """按统一口径聚合一组换热站与居民室温的核心指标（用于全网及四大分组）。"""
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

    # 流量加权均温累计器
    sup_w_sum = 0.0
    sup_flow_sum = 0.0
    ret_w_sum = 0.0
    ret_flow_sum = 0.0
    pres_ret_vals: List[float] = []

    temp_vals: List[float] = []
    for s in stations:
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


def get_hourly_report(target_date_str: Optional[str], hour: Optional[int], mode: str = "clean") -> Dict[str, Any]:
    """构建【界面一：阳面逐小时精细化运行报告】全量数据载荷。"""
    ensure_smart_heating_fact_tables()
    now_e8 = datetime.now(EAST_8)
    target_d = date.fromisoformat(target_date_str) if target_date_str else now_e8.date()
    sel_hour = now_e8.hour if hour is None else max(0, min(23, int(hour)))
    biz_hour = datetime(target_d.year, target_d.month, target_d.day, sel_hour, 0, 0, tzinfo=EAST_8)
    day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
    day_end = day_start + timedelta(days=1)
    use_raw = str(mode).lower() == "raw"

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
        zones_meta = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT secondary_zone_id, station_id, zone_name, is_online "
                    "FROM smart_heating_platform.dict_secondary_zone ORDER BY secondary_zone_id"
                )
            ).fetchall()
        ]

        # 2. 当天 24 小时全网趋势聚合 (供趋势折线图与时间轴状态条)
        st_day_rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (f.biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "f.station_id, f.online, f.e1_raw, f.e1_clean, f.e3_raw, f.e3_clean, "
                "f.e4_raw, f.e4_clean, f.e11_raw, f.e11_clean, f.e14_raw, f.e14_clean, "
                "f.hour_heat_gj, f.hour_water_t, hs.covered_area "
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

        # 3. 选中小时的站、区、上游、室温、运行日志
        st_hour_map = {
            r.station_id: dict(r._mapping)
            for r in conn.execute(
                text("SELECT * FROM smart_heating_platform.fact_station_hourly WHERE biz_hour = :bh"),
                {"bh": biz_hour},
            ).fetchall()
        }
        zn_hour_map = {
            r.secondary_zone_id: dict(r._mapping)
            for r in conn.execute(
                text("SELECT * FROM smart_heating_platform.fact_zone_hourly WHERE biz_hour = :bh"),
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
        last_run = conn.execute(
            text(
                "SELECT run_id, run_type, status, finished_at, summary_json "
                "FROM smart_heating_platform.fact_collector_run "
                "ORDER BY run_id DESC LIMIT 1"
            )
        ).mappings().first()

    # 构建 24h 趋势
    day_bucket: Dict[int, List[Dict[str, Any]]] = {h: [] for h in range(24)}
    for r in st_day_rows:
        day_bucket[int(r.hr)].append({
            "station_id": r.station_id,
            "online": r.online,
            "covered_area": _f(r.covered_area),
            "e1": _f(r.e1_raw if use_raw else r.e1_clean),
            "e3": _f(r.e3_raw if use_raw else r.e3_clean),
            "e4": _f(r.e4_raw if use_raw else r.e4_clean),
            "e11": _f(r.e11_raw if use_raw else r.e11_clean),
            "e14": _f(r.e14_raw if use_raw else r.e14_clean),
            "hour_heat_gj": _f(r.hour_heat_gj),
            "hour_water_t": _f(r.hour_water_t),
        })

    trend_24h: List[Dict[str, Any]] = []
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
            "avg_room_temp": temp_24h_map.get(h),
            "outdoor_temp": outdoor_24h.get(h),
        })

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

    # 整理二次网分区按站分组
    zones_by_station: Dict[str, List[Dict[str, Any]]] = {}
    for zm in zones_meta:
        zf = zn_hour_map.get(zm["secondary_zone_id"]) or {}
        zones_by_station.setdefault(zm["station_id"], []).append({
            "secondary_zone_id": zm["secondary_zone_id"],
            "zone_name": zm["zone_name"],
            "baseline_online": zm["is_online"],
            "e2": _f(zf.get("e2_raw") if use_raw else zf.get("e2_clean")),
            "e5": _f(zf.get("e5_raw") if use_raw else zf.get("e5_clean")),
            "e6": _f(zf.get("e6_raw") if use_raw else zf.get("e6_clean")),
            "e9": _f(zf.get("e9_raw") if use_raw else zf.get("e9_clean")),
            "e10": _f(zf.get("e10_raw") if use_raw else zf.get("e10_clean")),
            "e15": _f(zf.get("e15_raw") if use_raw else zf.get("e15_clean")),
            "e12_audit": _f(zf.get("e12_raw")),
            "value_source": zf.get("value_source") or ("REAL" if zm["is_online"] else "OFFLINE_PERMANENT"),
            "fault_tag": zf.get("fault_tag"),
        })

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
            "hour_heat_gj": _f(sf.get("hour_heat_gj")),
            "hour_heat_source": sf.get("hour_heat_source"),
            "hour_flow_t": _f(sf.get("hour_flow_t")),
            "hour_water_t": _f(sf.get("hour_water_t")),
            "hour_elec_kwh": _f(sf.get("hour_elec_kwh")),
            "zone_heat_sum_e12": _f(sf.get("zone_heat_sum_e12")),
            "heat_balance_diff_pct": _f(sf.get("heat_balance_diff_pct")),
            "value_source": sf.get("value_source") or "NO_DATA",
            "fault_tag": sf.get("fault_tag"),
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

    upstream_points = [
        {
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
            "hour_heat_gj": _f(u.get("hour_heat_gj")),
            "hour_flow_t": _f(u.get("hour_flow_t")),
            "value_source": u.get("value_source"),
            "fault_tag": u.get("fault_tag"),
        }
        for u in up_hour_rows
    ]

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


def get_upstream_point_24h(target_date_str: str, data_zone: str, source_name: str) -> List[Dict[str, Any]]:
    """查询单个上游测点当日 24 小时温/压/流/热趋势。"""
    target_d = date.fromisoformat(target_date_str)
    day_start = datetime(target_d.year, target_d.month, target_d.day, 0, 0, 0, tzinfo=EAST_8)
    day_end = day_start + timedelta(days=1)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT EXTRACT(HOUR FROM (biz_hour AT TIME ZONE 'Asia/Shanghai'))::INT AS hr, "
                "temp_clean, pressure_clean, flow_clean, heat_clean, hour_heat_gj, value_source "
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


def get_daily_report(target_date_str: Optional[str], period_mode: str = "natural") -> Dict[str, Any]:
    """构建【界面二：每日生产精算日报与手工日报双轨核对】载荷。"""
    now_e8 = datetime.now(EAST_8)
    target_d = date.fromisoformat(target_date_str) if target_date_str else (now_e8.date() - timedelta(days=1))
    mode = "shift" if str(period_mode).lower() == "shift" else "natural"

    if mode == "shift":
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
                "SELECT biz_hour, station_id, e1_clean, e3_clean, e4_clean, "
                "tot_j, hour_heat_gj, hour_heat_source, hour_flow_t, hour_water_t, hour_elec_kwh "
                "FROM smart_heating_platform.fact_station_hourly "
                "WHERE biz_hour >= :ws AND biz_hour < :we ORDER BY station_id, biz_hour ASC"
            ),
            {"ws": win_start, "we": win_end},
        ).fetchall()

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

        # 读取商户日耗量
        merchant_rows = [
            dict(r._mapping)
            for r in conn.execute(
                text(
                    "SELECT m.merchant_id, m.name, m.rdfz, m.rdry, m.rdss, m.rdjg, m.rdgz, "
                    "f.daily_consumption, f.daily_unit_heat "
                    "FROM smart_heating_platform.dict_merchant m "
                    "LEFT JOIN smart_heating_platform.fact_merchant_daily f "
                    "ON m.merchant_id = f.merchant_id AND f.biz_date = :biz_date "
                    "ORDER BY f.daily_consumption DESC NULLS LAST, m.name"
                ),
                {"biz_date": target_d},
            ).fetchall()
        ]

    # 按站汇总 24 小时
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
            "end_tot_j": None,
            "day_heat_gj": 0.0,
            "day_flow_t": 0.0,
            "day_water_t": 0.0,
            "day_elec_kwh": 0.0,
            "sup_w_sum": 0.0,
            "ret_w_sum": 0.0,
            "flow_w_sum": 0.0,
        }

    for r in hourly_rows:
        st = st_agg.get(r.station_id)
        if not st:
            continue
        st["hours_count"] += 1
        if r.hour_heat_source == "METER_DIFF":
            st["meter_diff_hours"] += 1
        if st["start_tot_j"] is None and r.tot_j is not None:
            st["start_tot_j"] = _f(r.tot_j)
        if r.tot_j is not None:
            st["end_tot_j"] = _f(r.tot_j)
        if r.hour_heat_gj is not None:
            st["day_heat_gj"] += float(r.hour_heat_gj)
        if r.hour_flow_t is not None:
            st["day_flow_t"] += float(r.hour_flow_t)
        if r.hour_water_t is not None:
            st["day_water_t"] += float(r.hour_water_t)
        if r.hour_elec_kwh is not None:
            st["day_elec_kwh"] += float(r.hour_elec_kwh)
        w = float(r.e1_clean) if r.e1_clean is not None and float(r.e1_clean) > 0 else 0.0
        if w > 0 and r.e3_clean is not None and r.e4_clean is not None:
            st["sup_w_sum"] += float(r.e3_clean) * w
            st["ret_w_sum"] += float(r.e4_clean) * w
            st["flow_w_sum"] += w

    station_daily: List[Dict[str, Any]] = []
    for st in st_agg.values():
        area = st["covered_area"]
        area_wan = area / 10000.0 if (area and area > 0) else 0.0
        heat_per_wan = _round(st["day_heat_gj"] / area_wan, 2) if (area_wan > 0 and st["hours_count"] > 0) else None
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
            "end_tot_j": _round(st["end_tot_j"], 2),
            "day_heat_gj": _round(st["day_heat_gj"], 2) if st["hours_count"] > 0 else None,
            "heat_per_wan_gj": heat_per_wan,
            "day_flow_t": _round(st["day_flow_t"], 2) if st["hours_count"] > 0 else None,
            "day_water_t": _round(st["day_water_t"], 2) if st["hours_count"] > 0 else None,
            "day_elec_kwh": _round(st["day_elec_kwh"], 2) if st["hours_count"] > 0 else None,
            "avg_sup_temp": _round(st["sup_w_sum"] / st["flow_w_sum"], 2) if st["flow_w_sum"] > 0 else None,
            "avg_ret_temp": _round(st["ret_w_sum"] / st["flow_w_sum"], 2) if st["flow_w_sum"] > 0 else None,
        })
    station_daily.sort(key=lambda x: (x["heat_per_wan_gj"] or -1.0), reverse=True)

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
        })

    # 若分中心未填而供热公司总表有值则回退供热公司总表
    ref_man_heat = tot_man_heat if has_man_heat else manual_gongre.get("consumption_station_heat")
    overall_diff_pct = (
        _round((tot_sys_heat - ref_man_heat) / ref_man_heat * 100.0, 2)
        if (hourly_rows and ref_man_heat and ref_man_heat != 0)
        else None
    )

    return {
        "meta": {
            "date": target_d.isoformat(),
            "period_mode": mode,
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
        },
        "center_comparison": center_comparison,
        "station_daily": station_daily,
        "merchant_daily": [
            {
                "merchant_id": m["merchant_id"],
                "name": m["name"],
                "rdfz": m["rdfz"],
                "rdry": m["rdry"],
                "rdss": m["rdss"],
                "rdjg": m["rdjg"],
                "rdgz": m["rdgz"],
                "daily_consumption": _f(m.get("daily_consumption")),
                "daily_unit_heat": _f(m.get("daily_unit_heat")),
            }
            for m in merchant_rows
        ],
    }


def _style_excel_sheet(ws: Any, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    """统一为导出 Excel Sheet 设置表头样式与自适应列宽。"""
    fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    font = Font(color="FFFFFF", bold=True)
    ws.append(list(headers))
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for r in rows:
        ws.append(list(r))
    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 4, 12), 40)


def build_hourly_excel(report_data: Dict[str, Any]) -> bytes:
    """生成《逐小时精细化运行报告》多 Sheet Excel 字节流。"""
    wb = openpyxl.Workbook()
    ws_center = wb.active
    ws_center.title = "9大中心小时汇总"
    _style_excel_sheet(
        ws_center,
        ["中心名称", "总站数", "在线站数", "供热面积(万㎡)", "小时供热量(GJ)", "瞬时负荷(GJ/h)", "折算热指标(W/㎡)", "小时补水(t)", "加权供温(℃)", "加权回温(℃)", "平均室温(℃)", "室温达标率(%)"],
        [
            [
                g["group_name"], g["total_stations"], g["online_stations"], g["covered_area_wan"],
                g["hour_heat_gj"], g["instant_load_gjh"], g["heat_index_wm2"], g["hour_water_t"],
                g["avg_sup_temp"], g["avg_ret_temp"], g["avg_room_temp"], g["temp_pass_rate_pct"],
            ]
            for g in report_data["group_summaries"]["by_center"]
        ],
    )

    ws_st = wb.create_sheet("242换热站小时明细")
    _style_excel_sheet(
        ws_st,
        ["站点名称", "所属中心", "热源大网", "面积(㎡)", "在线", "一网供流(t/h)", "一网供温(℃)", "一网回温(℃)", "一网供压(MPa)", "一网回压(MPa)", "一网瞬时热量(GJ/h)", "小时供热量(GJ)", "热量口径", "小时补水(t)", "平均室温(℃)", "数据来源"],
        [
            [
                s["name"], s["center_name"], s["rdfz"], s["covered_area"], "在线" if s["online"] else "离线",
                s["e1"], s["e3"], s["e4"], s["e7"], s["e8"], s["e11"], s["hour_heat_gj"], s["hour_heat_source"],
                s["hour_water_t"], s["avg_room_temp"], s["value_source"],
            ]
            for s in report_data["stations"]
        ],
    )

    ws_up = wb.create_sheet("上游热源与首站")
    _style_excel_sheet(
        ws_up,
        ["类别", "子类", "测点名称", "数据区", "温度(℃)", "压力(MPa)", "瞬时流量", "瞬时热量", "小时积分热量(GJ)", "状态"],
        [
            [
                u["category"], u["sub_category"], u["display_name"], u["data_zone"],
                u["temp"], u["pressure"], u["flow"], u["heat"], u["hour_heat_gj"], u["value_source"],
            ]
            for u in report_data["upstream_points"]
        ],
    )

    ws_mc = wb.create_sheet("464商业用户小时明细")
    _style_excel_sheet(
        ws_mc,
        ["商业户名称", "热源大网", "主干网", "支线网", "状态", "供水流量(t/h)", "供温(℃)", "回温(℃)", "瞬时热量(GJ/h)", "小时供热量(GJ)", "小时流量(t)", "阀门开度(%)", "数据来源"],
        [
            [
                m["name"], m["rdfz"], m["main_name"], m["branch_name"], "在线" if m["online"] else "离线",
                m["flow"], m["temp_sup"], m["temp_ret"], m["heat"], m["hour_heat_gj"], m["hour_flow_t"],
                m["valve_open"], m["value_source"],
            ]
            for m in report_data.get("merchants", [])
        ],
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_daily_excel(report_data: Dict[str, Any]) -> bytes:
    """生成《每日生产精算日报与双轨核对表》Excel 字节流。"""
    wb = openpyxl.Workbook()
    ws_cmp = wb.active
    ws_cmp.title = "9大中心双轨核对"
    _style_excel_sheet(
        ws_cmp,
        ["中心名称", "面积(万㎡)", "系统精算热量(GJ)", "手工日报热量(GJ)", "热量偏差(GJ)", "偏差率(%)", "万平耗热(GJ/万㎡)", "系统补水(t)", "手工补水(t)", "平均室温(℃)"],
        [
            [
                c["center_name"], c["covered_area_wan"], c["sys_heat_gj"], c["man_heat_gj"],
                c["heat_diff_gj"], c["heat_diff_pct"], c["heat_per_wan_gj"], c["sys_water_t"],
                c["man_water_t"], c["avg_room_temp"],
            ]
            for c in report_data["center_comparison"]
        ],
    )

    ws_st = wb.create_sheet("242站日度能耗")
    _style_excel_sheet(
        ws_st,
        ["站点名称", "中心", "热源大网", "面积(㎡)", "采集小时数", "表底小时数", "起表底(GJ)", "止表底(GJ)", "日供热量(GJ)", "万平耗热", "日补水(t)", "日电耗(kWh)"],
        [
            [
                s["name"], s["center_name"], s["rdfz"], s["covered_area"], s["hours_count"], s["meter_diff_hours"],
                s["start_tot_j"], s["end_tot_j"], s["day_heat_gj"], s["heat_per_wan_gj"], s["day_water_t"], s["day_elec_kwh"],
            ]
            for s in report_data["station_daily"]
        ],
    )

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
