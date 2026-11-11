# -*- coding: utf-8 -*-
"""
供暖期竞赛指标自动取数与持久化服务。
从 monthly_data_show（月报）提取能耗与运营月度指标（计划值与实际值），
从 daily_basic_data（日报）与 constant_data 提取服务投诉累计量与万平米投诉率，
并支持将竞赛月度打分测算结果持久化到 PostgreSQL 的 competition_monthly_records 表中。
"""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal

PROJECT_KEY = "monthly_data_show"

# 7 家参评单位代码映射到月报 company 字段
UNIT_MONTHLY_COMPANY_MAP = {
    "BeiHai": "北海",
    "XiangHai": "香海",
    "GongRe": "供热公司",  # 主城区与供热公司共用
    "JinZhou": "金州",
    "BeiFang": "北方",
    "JinPu": "金普",
    "ZhuangHe": "庄河",
}

# 日报中 5 家参评供热单位代码映射
UNIT_DAILY_COMPANY_MAP = {
    "GongRe": "GongRe",
    "BeiFang": "BeiFang",
    "JinZhou": "JinZhou",
    "JinPu": "JinPu",
    "ZhuangHe": "ZhuangHe",
}


def ensure_competition_table() -> None:
    """确保竞赛结果归档表存在。"""
    ddl = """
    CREATE TABLE IF NOT EXISTS competition_monthly_records (
        id BIGSERIAL PRIMARY KEY,
        project_key TEXT NOT NULL DEFAULT 'monthly_data_show',
        report_month DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'saved',
        total_reward NUMERIC(14, 2) DEFAULT 0,
        disqualified_count INT DEFAULT 0,
        data_payload JSONB NOT NULL,
        summary_payload JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT uq_competition_project_month UNIQUE (project_key, report_month)
    );
    CREATE INDEX IF NOT EXISTS idx_competition_report_month ON competition_monthly_records (project_key, report_month);
    """
    with SessionLocal() as session:
        session.execute(text(ddl))
        session.commit()


def parse_month_date(month_str: str) -> Tuple[date, date]:
    """
    解析 YYYY-MM 格式为月初与月末日期。
    若为 YYYY-YYYY（总评），返回异常或按上年11月至当年3月处理。
    """
    parts = str(month_str or "").strip().split("-")
    if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 2:
        year = int(parts[0])
        month = int(parts[1])
        start_d = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_d = date(year, month, last_day)
        return start_d, end_d
    raise ValueError(f"无效的考核月份格式: {month_str}，应为 YYYY-MM")


def get_auto_fetch_competition_data(month_str: str) -> Dict[str, Any]:
    """
    一键从系统自动提取竞赛所需月度指标：
    1. 从 monthly_data_show 提取 7 家单位能耗与运营指标的计划值与完成值；
    2. 从 daily_basic_data 提取月末服务净投诉累计量，并结合 constant_data 供暖收费面积折算万平米投诉率；
    3. 对非停、断管率、安全文明等手动填报项预置标准缺省值。
    """
    start_d, end_d = parse_month_date(month_str)

    monthly_records: List[Dict[str, Any]] = []
    complaint_records: Dict[str, Dict[str, Any]] = {}
    area_records: Dict[str, float] = {}
    daily_sum_map: Dict[Tuple[str, str], float] = {}
    analysis_latest_map: Dict[Tuple[str, str], float] = {}
    latest_daily_date = ""

    # 1. 采用月报官方计算引擎获取全量指标（支持动态公式计算，如全厂热效率、供暖单耗等）
    monthly_engine_map: Dict[Tuple[str, str, str], float] = {}
    try:
        from backend.projects.monthly_data_show.api.workspace import query_month_data_show, QueryRequest
        req = QueryRequest(
            date_from=start_d.isoformat(),
            date_to=end_d.isoformat(),
            companies=["北海", "香海", "供热公司", "主城区", "金州", "北方", "金普", "庄河"],
            items=[
                "耗标煤总量", "电厂耗水量", "全厂热效率", "外购热量",
                "供暖热耗率", "供暖电耗率", "供暖水耗率",
            ],
            periods=["month"],
            types=["plan", "real"],
            limit=500,
        )
        res_engine = query_month_data_show(req)
        for r in res_engine.rows:
            comp = str(r.get("company") or "")
            item = str(r.get("item") or "")
            v_type = str(r.get("type") or "")
            val = r.get("value")
            if val is not None:
                monthly_engine_map[(comp, item, v_type)] = float(val)
    except Exception as exc:
        print(f"[competition_service] 调用月报官方计算引擎警告: {exc}")

    with SessionLocal() as session:
        # 2. 抽取 monthly_data_show 当月基础底表记录
        sql_monthly = text("""
            SELECT company, item, unit, type, value
            FROM monthly_data_show
            WHERE report_month = :start_d
              AND date = :start_d
              AND period = 'month'
              AND type IN ('plan', 'real')
        """)
        rows_monthly = session.execute(sql_monthly, {"start_d": start_d}).fetchall()
        for r in rows_monthly:
            monthly_records.append({
                "company": str(r[0]),
                "item": str(r[1]),
                "unit": str(r[2] or ""),
                "type": str(r[3]),
                "value": float(r[4]) if r[4] is not None else None,
            })

        # 3. 抽取 daily_basic_data 中当月月末（或最新一天）累计净投诉量与当月生产消耗累计
        sql_complaints = text("""
            SELECT company, company_cn, value, date
            FROM daily_basic_data
            WHERE item = 'sum_month_total_net_complaints'
              AND date >= :start_d
              AND date <= :end_d
            ORDER BY date DESC
        """)
        rows_complaints = session.execute(sql_complaints, {"start_d": start_d, "end_d": end_d}).fetchall()
        for r in rows_complaints:
            comp_code = str(r[0])
            if comp_code not in complaint_records and r[2] is not None:
                complaint_records[comp_code] = {
                    "company_cn": str(r[1]),
                    "complaints": float(r[2]),
                    "date": str(r[3]),
                }
                if not latest_daily_date:
                    latest_daily_date = str(r[3])

        # 抽取当月 daily_basic_data 生产消耗求和 (如标煤、电厂水耗、外购热等)
        sql_daily_sums = text("""
            SELECT company, item, SUM(value)
            FROM daily_basic_data
            WHERE date >= :start_d AND date <= :end_d
            GROUP BY company, item
        """)
        rows_daily = session.execute(sql_daily_sums, {"start_d": start_d, "end_d": end_d}).fetchall()
        for r in rows_daily:
            if r[2] is not None:
                daily_sum_map[(str(r[0]), str(r[1]))] = float(r[2])

        # 抽取当月换热站相关分项消耗求和
        sql_daily_station_sums = text("""
            SELECT company, item_cn, SUM(value)
            FROM daily_basic_data
            WHERE date >= :start_d AND date <= :end_d
            GROUP BY company, item_cn
        """)
        rows_station_daily = session.execute(sql_daily_station_sums, {"start_d": start_d, "end_d": end_d}).fetchall()
        for r in rows_station_daily:
            if r[2] is not None:
                daily_sum_map[(str(r[0]), str(r[1]))] = float(r[2])

        # 4. 抽取 analysis_company_sum 当月最新一日的指标数据
        sql_analysis = text("""
            SELECT company, item_cn, value_biz_date, biz_date
            FROM analysis_company_sum
            WHERE biz_date >= :start_d AND biz_date <= :end_d
            ORDER BY biz_date DESC
        """)
        rows_analysis = session.execute(sql_analysis, {"start_d": start_d, "end_d": end_d}).fetchall()
        for r in rows_analysis:
            c_key = (str(r[0]), str(r[1]))
            if c_key not in analysis_latest_map and r[2] is not None:
                analysis_latest_map[c_key] = float(r[2])
                if not latest_daily_date:
                    latest_daily_date = str(r[3])

        # 5. 抽取 constant_data 中的供暖收费面积
        sql_area = text("""
            SELECT company, value, period, operation_time
            FROM constant_data
            WHERE item = 'amount_heating_fee_area'
              AND company IN ('GongRe', 'BeiFang', 'JinZhou', 'JinPu', 'ZhuangHe')
            ORDER BY operation_time DESC NULLS LAST
        """)
        rows_area = session.execute(sql_area).fetchall()
        for r in rows_area:
            comp_code = str(r[0])
            if comp_code not in area_records and r[1] is not None:
                area_records[comp_code] = float(r[1])

    # 建立底表索引：(company, item, type) -> value
    monthly_map: Dict[Tuple[str, str, str], float] = {}
    for mr in monthly_records:
        if mr["value"] is not None:
            monthly_map[(mr["company"], mr["item"], mr["type"])] = mr["value"]

    def get_monthly_val(comp: str, item_name: str, val_type: str) -> Optional[float]:
        # 优先从月报官方计算引擎取（包含全厂热效率等公式），若无再查底表
        val = monthly_engine_map.get((comp, item_name, val_type))
        if val is None:
            val = monthly_map.get((comp, item_name, val_type))
        if val is None and comp == "供热公司":
            val = monthly_engine_map.get(("主城区", item_name, val_type))
            if val is None:
                val = monthly_map.get(("主城区", item_name, val_type))
        return val

    # 5. 组装 7 家单位指标抽取数据
    units_extracted: Dict[str, Dict[str, Any]] = {}

    for unit_code, comp_name in UNIT_MONTHLY_COMPANY_MAP.items():
        extracted_indicators: Dict[str, Dict[str, Any]] = {}
        daily_code = UNIT_DAILY_COMPANY_MAP.get(unit_code, unit_code)
        area = area_records.get(daily_code, 0.0)

        if unit_code in ("BeiHai", "XiangHai"):
            # 耗标煤总量 (吨)
            c_plan = get_monthly_val(comp_name, "耗标煤总量", "plan")
            c_real = get_monthly_val(comp_name, "耗标煤总量", "real")
            c_source = "月报表 (monthly_data_show)"
            if c_real is None:
                # 智能降级：从日报当月累计汇总
                d_val = daily_sum_map.get((daily_code, "consumption_std_coal"))
                if d_val is not None:
                    c_real = d_val
                    c_source = f"日报当月累计 (截至{latest_daily_date})"

            extracted_indicators["coal_consumption"] = {
                "name": "耗标煤总量",
                "unit": "吨",
                "targetValue": round(c_plan, 2) if c_plan is not None else None,
                "actualValue": round(c_real, 2) if c_real is not None else None,
                "source": c_source,
            }

            # 厂内水耗量 (吨) -> 电厂耗水量
            w_plan = get_monthly_val(comp_name, "电厂耗水量", "plan")
            w_real = get_monthly_val(comp_name, "电厂耗水量", "real")
            w_source = "月报表 (monthly_data_show)"
            if w_real is None:
                d_val = daily_sum_map.get((daily_code, "consumption_plant_water"))
                if d_val is not None:
                    w_real = d_val
                    w_source = f"日报当月累计 (截至{latest_daily_date})"

            extracted_indicators["water_consumption"] = {
                "name": "厂内水耗量",
                "unit": "吨",
                "targetValue": round(w_plan, 2) if w_plan is not None else None,
                "actualValue": round(w_real, 2) if w_real is not None else None,
                "source": w_source,
            }

            # 全厂热效率 (%) -> 原始为 0.8176，需 × 100 得到 81.76%
            e_plan = get_monthly_val(comp_name, "全厂热效率", "plan")
            e_real = get_monthly_val(comp_name, "全厂热效率", "real")
            e_source = "月报表 (monthly_data_show)"
            if e_real is None:
                # 从 analysis_company_sum 取最新日热效率
                d_eff = analysis_latest_map.get((daily_code, "全厂热效率"))
                if d_eff is not None:
                    e_real = d_eff  # 库内已是 0.8444 或百分比
                    e_source = f"运行分析最新 (截至{latest_daily_date})"

            # 处理百分比换算：若数值 <= 1.5 说明是小数形式，需乘以 100
            eff_plan_val = round(e_plan * 100, 2) if (e_plan is not None and e_plan <= 1.5) else (round(e_plan, 2) if e_plan is not None else None)
            eff_real_val = round(e_real * 100, 2) if (e_real is not None and e_real <= 1.5) else (round(e_real, 2) if e_real is not None else None)

            extracted_indicators["heat_efficiency"] = {
                "name": "全厂热效率",
                "unit": "%",
                "targetValue": eff_plan_val,
                "actualValue": eff_real_val,
                "source": e_source,
            }

        elif unit_code in ("GongRe", "JinZhou", "BeiFang", "JinPu"):
            # 耗标煤总量 (吨)
            c_plan = get_monthly_val(comp_name, "耗标煤总量", "plan")
            c_real = get_monthly_val(comp_name, "耗标煤总量", "real")
            c_source = "月报表 (monthly_data_show)"
            if c_real is None:
                if unit_code == "GongRe":
                    # 供热公司主城区耗标煤总量 = 北海标煤累计 + 香海标煤累计
                    bh_c = daily_sum_map.get(("BeiHai", "consumption_std_coal"), 0.0)
                    xh_c = daily_sum_map.get(("XiangHai", "consumption_std_coal"), 0.0)
                    if bh_c > 0 or xh_c > 0:
                        c_real = bh_c + xh_c
                        c_source = f"主城区两厂日报当月累计 (截至{latest_daily_date})"
                else:
                    d_val = daily_sum_map.get((daily_code, "consumption_std_coal"))
                    if d_val is not None:
                        c_real = d_val
                        c_source = f"日报当月累计 (截至{latest_daily_date})"

            extracted_indicators["coal_consumption"] = {
                "name": "耗标煤总量",
                "unit": "吨",
                "targetValue": round(c_plan, 2) if c_plan is not None else None,
                "actualValue": round(c_real, 2) if c_real is not None else None,
                "source": c_source,
            }

            # 供暖热单耗 (GJ/万㎡) -> 库内为 供暖热耗率 (吉焦/平方米) × 10000
            hu_plan = get_monthly_val(comp_name, "供暖热耗率", "plan")
            hu_real = get_monthly_val(comp_name, "供暖热耗率", "real")
            hu_source = "月报表 (monthly_data_show)"
            if hu_real is None:
                # 从换热站累计耗热量或供热量除以面积折算
                station_heat = (
                    daily_sum_map.get((daily_code, "amount_network_interface_heat_supply"))
                    or daily_sum_map.get((daily_code, "consumption_station_heat"))
                    or daily_sum_map.get((daily_code, "站内耗热量"))
                    or daily_sum_map.get((daily_code, "amount_heat_supply"))
                    or daily_sum_map.get((daily_code, "供热量"), 0.0)
                )
                if area > 0 and station_heat > 0:
                    hu_real = (station_heat / area) / 10000.0  # 对应吉焦/平方米
                    hu_source = f"日报当月供暖耗热累计折算 (截至{latest_daily_date})"

            extracted_indicators["heat_unit_consumption"] = {
                "name": "供暖热单耗",
                "unit": "GJ/万㎡",
                "targetValue": round(hu_plan * 10000, 2) if hu_plan is not None else None,
                "actualValue": round(hu_real * 10000, 2) if hu_real is not None else None,
                "source": hu_source,
            }

            # 供暖电单耗 (kWh/万㎡) -> 库内为 供暖电耗率 (千瓦时/平方米) × 10000
            eu_plan = get_monthly_val(comp_name, "供暖电耗率", "plan")
            eu_real = get_monthly_val(comp_name, "供暖电耗率", "real")
            eu_source = "月报表 (monthly_data_show)"
            if eu_real is None:
                # 换热站外购电量 (万kWh) * 10000 / 面积
                st_power = (
                    daily_sum_map.get((daily_code, "consumption_station_purchased_power"))
                    or daily_sum_map.get((daily_code, "其中：换热站外购电量"))
                    or daily_sum_map.get((daily_code, "consumption_purchased_power"))
                    or daily_sum_map.get((daily_code, "外购电量"), 0.0)
                )
                if area > 0 and st_power and st_power > 0:
                    eu_real = ((st_power * 10000.0) / area) / 10000.0
                    eu_source = f"换热站当月外购电累计折算 (截至{latest_daily_date})"

            extracted_indicators["elec_unit_consumption"] = {
                "name": "供暖电单耗",
                "unit": "kWh/万㎡",
                "targetValue": round(eu_plan * 10000, 2) if eu_plan is not None else None,
                "actualValue": round(eu_real * 10000, 2) if eu_real is not None else None,
                "source": eu_source,
            }

            # 供暖水单耗 (t/万㎡) -> 库内为 供暖水耗率 (千克/平方米) × 10 (1千克/㎡ = 10吨/万㎡)
            wu_plan = get_monthly_val(comp_name, "供暖水耗率", "plan")
            wu_real = get_monthly_val(comp_name, "供暖水耗率", "real")
            wu_source = "月报表 (monthly_data_show)"
            if wu_real is None:
                st_water = (
                    daily_sum_map.get((daily_code, "consumption_station_fill_water"))
                    or daily_sum_map.get((daily_code, "其中：换热站补水量"))
                    or daily_sum_map.get((daily_code, "consumption_network_water"))
                    or daily_sum_map.get((daily_code, "consumption_water"))
                    or daily_sum_map.get((daily_code, "耗水量"), 0.0)
                )
                if area > 0 and st_water and st_water > 0:
                    wu_real = (st_water / area) / 10.0
                    wu_source = f"换热站当月补水累计折算 (截至{latest_daily_date})"

            extracted_indicators["water_unit_consumption"] = {
                "name": "供暖水单耗",
                "unit": "t/万㎡",
                "targetValue": round(wu_plan * 10, 2) if wu_plan is not None else None,
                "actualValue": round(wu_real * 10, 2) if wu_real is not None else None,
                "source": wu_source,
            }

        elif unit_code == "ZhuangHe":
            # 庄河：外购热量 (吉焦)
            ph_plan = get_monthly_val(comp_name, "外购热量", "plan")
            ph_real = get_monthly_val(comp_name, "外购热量", "real")
            ph_source = "月报表 (monthly_data_show)"
            if ph_real is None:
                d_heat = (
                    daily_sum_map.get(("ZhuangHe", "consumption_outer_purchased_heat"))
                    or daily_sum_map.get(("ZhuangHe", "amount_heat_supply"))
                )
                if d_heat is not None:
                    ph_real = d_heat
                    ph_source = f"日报当月外购热累计 (截至{latest_daily_date})"

            extracted_indicators["purchased_heat"] = {
                "name": "外购热量",
                "unit": "GJ",
                "targetValue": round(ph_plan, 2) if ph_plan is not None else None,
                "actualValue": round(ph_real, 2) if ph_real is not None else None,
                "source": ph_source,
            }

            # 庄河供暖热单耗 (GJ/万㎡)
            hu_plan = get_monthly_val(comp_name, "供暖热耗率", "plan")
            hu_real = get_monthly_val(comp_name, "供暖热耗率", "real")
            hu_source = "月报表 (monthly_data_show)"
            if hu_real is None:
                station_heat = (
                    daily_sum_map.get(("ZhuangHe", "amount_heat_supply"))
                    or daily_sum_map.get(("ZhuangHe", "consumption_outer_purchased_heat"))
                    or daily_sum_map.get(("ZhuangHe", "供热量"), 0.0)
                )
                if area > 0 and station_heat > 0:
                    hu_real = (station_heat / area) / 10000.0  # 对应吉焦/平方米
                    hu_source = f"日报当月供暖耗热累计折算 (截至{latest_daily_date})"

            extracted_indicators["heat_unit_consumption"] = {
                "name": "供暖热单耗",
                "unit": "GJ/万㎡",
                "targetValue": round(hu_plan * 10000, 2) if hu_plan is not None else None,
                "actualValue": round(hu_real * 10000, 2) if hu_real is not None else None,
                "source": hu_source,
            }

            # 庄河供暖电单耗 (kWh/万㎡)
            eu_plan = get_monthly_val(comp_name, "供暖电耗率", "plan")
            eu_real = get_monthly_val(comp_name, "供暖电耗率", "real")
            eu_source = "月报表 (monthly_data_show)"
            if eu_real is None:
                st_power = (
                    daily_sum_map.get(("ZhuangHe", "consumption_station_purchased_power"))
                    or daily_sum_map.get(("ZhuangHe", "其中：换热站外购电量"))
                    or daily_sum_map.get(("ZhuangHe", "consumption_purchased_power"))
                    or daily_sum_map.get(("ZhuangHe", "外购电量"), 0.0)
                )
                if area > 0 and st_power and st_power > 0:
                    eu_real = ((st_power * 10000.0) / area) / 10000.0
                    eu_source = f"换热站当月外购电累计折算 (截至{latest_daily_date})"

            extracted_indicators["elec_unit_consumption"] = {
                "name": "供暖电单耗",
                "unit": "kWh/万㎡",
                "targetValue": round(eu_plan * 10000, 2) if eu_plan is not None else None,
                "actualValue": round(eu_real * 10000, 2) if eu_real is not None else None,
                "source": eu_source,
            }

            # 庄河供暖水单耗 (t/万㎡)
            wu_plan = get_monthly_val(comp_name, "供暖水耗率", "plan")
            wu_real = get_monthly_val(comp_name, "供暖水耗率", "real")
            wu_source = "月报表 (monthly_data_show)"
            if wu_real is None:
                st_water = (
                    daily_sum_map.get(("ZhuangHe", "consumption_network_water"))
                    or daily_sum_map.get(("ZhuangHe", "其中：换热站补水量"))
                    or daily_sum_map.get(("ZhuangHe", "consumption_water"))
                    or daily_sum_map.get(("ZhuangHe", "耗水量"), 0.0)
                )
                if area > 0 and st_water and st_water > 0:
                    wu_real = (st_water / area) / 10.0
                    wu_source = f"换热站当月补水累计折算 (截至{latest_daily_date})"

            extracted_indicators["water_unit_consumption"] = {
                "name": "供暖水单耗",
                "unit": "t/万㎡",
                "targetValue": round(wu_plan * 10, 2) if wu_plan is not None else None,
                "actualValue": round(wu_real * 10, 2) if wu_real is not None else None,
                "source": wu_source,
            }

        # 5. 服务投诉率计算（针对供热 5 家单位）
        if unit_code in UNIT_DAILY_COMPANY_MAP:
            d_comp = UNIT_DAILY_COMPANY_MAP[unit_code]
            c_info = complaint_records.get(d_comp)
            area = area_records.get(d_comp)

            complaint_count = c_info["complaints"] if c_info else 0.0
            complaint_date = c_info["date"] if c_info else ""
            complaint_rate = round(complaint_count / area, 4) if (area and area > 0) else 0.0

            extracted_indicators["service_complaint_rate"] = {
                "name": "服务投诉率",
                "unit": "件/万㎡",
                "targetValue": None,  # 横向排名考核，无事前固定基准
                "actualValue": complaint_rate,
                "complaintCount": complaint_count,
                "heatingArea": round(area, 2) if area else None,
                "source": f"日报表 (截至 {complaint_date} 净投诉 {complaint_count}件 / 面积 {round(area, 2) if area else 0}万㎡)",
            }

        # 6. 手动填报项的缺省值（非停、断管率、安全文明）
        extracted_indicators["unplanned_outage"] = {
            "name": "非计划停炉停机",
            "unit": "次",
            "targetValue": 0,
            "actualValue": 0,
            "source": "手动填报 (默认0次)",
        }
        extracted_indicators["pipe_break_rate"] = {
            "name": "停供断管率",
            "unit": "%",
            "targetValue": 100,
            "actualValue": 100,
            "source": "手动填报 (默认100%)",
        }
        extracted_indicators["safety_production"] = {
            "name": "安全文明生产",
            "unit": "分",
            "targetValue": 10,
            "actualValue": 10,
            "source": "手动填报 (基准满分10分)",
        }

        units_extracted[unit_code] = extracted_indicators

    has_monthly_real = any(mr.get("type") == "real" for mr in monthly_records)

    return {
        "ok": True,
        "month": month_str,
        "is_historical": has_monthly_real,
        "latest_daily_date": latest_daily_date,
        "monthly_rows_matched": len(monthly_records),
        "complaint_units_matched": len(complaint_records),
        "units": units_extracted,
        "fetched_at": datetime.now().isoformat(),
    }


def save_competition_record(month_str: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存月度竞赛打分测算记录到 PostgreSQL。
    """
    ensure_competition_table()
    start_d, _ = parse_month_date(month_str)

    total_reward = float(payload.get("total_reward", 0.0))
    disqualified_count = int(payload.get("disqualified_count", 0))
    data_payload = payload.get("data_payload") or []
    summary_payload = payload.get("summary_payload") or {}

    upsert_sql = text("""
        INSERT INTO competition_monthly_records (
            project_key, report_month, status, total_reward, disqualified_count,
            data_payload, summary_payload, updated_at
        ) VALUES (
            :project_key, :report_month, 'saved', :total_reward, :disqualified_count,
            :data_payload, :summary_payload, NOW()
        )
        ON CONFLICT (project_key, report_month) DO UPDATE SET
            status = 'saved',
            total_reward = EXCLUDED.total_reward,
            disqualified_count = EXCLUDED.disqualified_count,
            data_payload = EXCLUDED.data_payload,
            summary_payload = EXCLUDED.summary_payload,
            updated_at = NOW()
        RETURNING id, updated_at;
    """)

    with SessionLocal() as session:
        result = session.execute(
            upsert_sql,
            {
                "project_key": PROJECT_KEY,
                "report_month": start_d,
                "total_reward": total_reward,
                "disqualified_count": disqualified_count,
                "data_payload": json.dumps(data_payload, ensure_ascii=False),
                "summary_payload": json.dumps(summary_payload, ensure_ascii=False),
            },
        ).fetchone()
        session.commit()

        return {
            "ok": True,
            "id": result[0] if result else None,
            "month": month_str,
            "updated_at": str(result[1]) if result else None,
            "message": f"成功保存 {month_str} 指标竞赛打分测算数据至系统数据库",
        }


def get_competition_record(month_str: str) -> Dict[str, Any]:
    """
    从 PostgreSQL 查询指定月份已保存的竞赛测算记录。
    """
    ensure_competition_table()
    start_d, _ = parse_month_date(month_str)

    select_sql = text("""
        SELECT id, report_month, status, total_reward, disqualified_count,
               data_payload, summary_payload, created_at, updated_at
        FROM competition_monthly_records
        WHERE project_key = :project_key
          AND report_month = :report_month
    """)

    with SessionLocal() as session:
        row = session.execute(select_sql, {
            "project_key": PROJECT_KEY,
            "report_month": start_d,
        }).fetchone()

        if not row:
            return {
                "ok": False,
                "found": False,
                "month": month_str,
                "message": f"{month_str} 尚未保存过测算记录",
            }

        return {
            "ok": True,
            "found": True,
            "id": row[0],
            "month": month_str,
            "status": row[2],
            "total_reward": float(row[3]) if row[3] is not None else 0.0,
            "disqualified_count": int(row[4] or 0),
            "data_payload": row[5],
            "summary_payload": row[6],
            "created_at": str(row[7]) if row[7] else None,
            "updated_at": str(row[8]) if row[8] else None,
        }
