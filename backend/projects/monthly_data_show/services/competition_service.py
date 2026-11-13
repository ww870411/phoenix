# -*- coding: utf-8 -*-
"""
供暖期竞赛指标自动取数与持久化服务。
从 monthly_data_show（月报）提取能耗与运营月度指标（计划值与实际值；月报未出数前实际值留空），
从 spot_electricity_15min_data（电力现货市场）提取北海/香海电厂动态现货电价及辽宁统一结算点均价上浮5%基准，
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


DEFAULT_SEASON_MONTHS = ["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"]

STANDARD_UNIT_DEFS = [
    ("BeiHai", "北海热电厂"),
    ("XiangHai", "香海热电厂"),
    ("GongRe", "供热公司"),
    ("JinZhou", "金州热电"),
    ("BeiFang", "北方热电"),
    ("JinPu", "金普公司"),
    ("ZhuangHe", "庄河环海"),
]


def ensure_competition_table() -> None:
    """确保竞赛结果归档表及其扩展字段存在。"""
    ddl = """
    CREATE TABLE IF NOT EXISTS competition_monthly_records (
        id BIGSERIAL PRIMARY KEY,
        project_key TEXT NOT NULL DEFAULT 'monthly_data_show',
        report_month DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'saved',
        base_reward NUMERIC(14, 2) DEFAULT 0,
        extra_reward NUMERIC(14, 2) DEFAULT 0,
        total_reward NUMERIC(14, 2) DEFAULT 0,
        disqualified_count INT DEFAULT 0,
        data_payload JSONB NOT NULL,
        summary_payload JSONB DEFAULT '{}'::jsonb,
        published_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT uq_competition_project_month UNIQUE (project_key, report_month)
    );
    ALTER TABLE competition_monthly_records ADD COLUMN IF NOT EXISTS base_reward NUMERIC(14, 2) DEFAULT 0;
    ALTER TABLE competition_monthly_records ADD COLUMN IF NOT EXISTS extra_reward NUMERIC(14, 2) DEFAULT 0;
    ALTER TABLE competition_monthly_records ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;
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


def _monthly_source_label(plan_val: Optional[float], real_val: Optional[float]) -> str:
    """根据月报计划值与实际值存在状态生成来源说明。"""
    if real_val is not None:
        return "月报表 (monthly_data_show)"
    if plan_val is not None:
        return "月报表 (计划已取 · 实际值待月报出数)"
    return "月报表 (暂无当月数据)"


def _fetch_spot_price_metrics(session: Any, start_d: date, end_d: date) -> Dict[str, Any]:
    """
    沿用电力现货市场页面 (/pages/spot_electricity) 完全一致的计算口径，
    提取当月累计至今的辽宁省统一结算点实时电价算术平均值×1.05（标准值），
    以及北海/香海电厂完整账单日（96点完整且量价非空）的电量加权现货电价（完成值）。
    """
    rt_row = session.execute(
        text("""
            SELECT
                AVG(real_time_price) AS avg_rt,
                MAX(trade_date) AS max_rt_date
            FROM public.spot_electricity_15min_data
            WHERE trade_date BETWEEN :start_d AND :end_d
              AND real_time_price IS NOT NULL
        """),
        {"start_d": start_d, "end_d": end_d},
    ).fetchone()

    avg_rt = float(rt_row[0]) if (rt_row and rt_row[0] is not None) else None
    max_rt_date = str(rt_row[1]) if (rt_row and rt_row[1] is not None) else ""
    target_price = round(avg_rt * 1.05, 2) if avg_rt is not None else None

    plant_results: Dict[str, Dict[str, Any]] = {}
    plant_specs = {
        "BeiHai": "(beihai_unit1_sales + beihai_unit2_sales + beihai_unit3_sales)",
        "XiangHai": "(xianghai_unit1_sales + xianghai_unit2_sales + xianghai_unit3_sales + xianghai_unit4_sales)",
    }

    for unit_code, sales_expr in plant_specs.items():
        daily_sql = text(f"""
            WITH daily_bill AS (
                SELECT
                    trade_date,
                    SUM(({sales_expr}) * bill_real_time_price) AS daily_spot_fee,
                    SUM({sales_expr}) AS daily_sales
                FROM public.spot_electricity_15min_data
                WHERE trade_date BETWEEN :start_d AND :end_d
                GROUP BY trade_date
                HAVING COUNT(*) = 96
                   AND COUNT(({sales_expr}) * bill_real_time_price) = 96
            )
            SELECT
                SUM(daily_spot_fee) AS total_spot_fee,
                SUM(daily_sales) AS total_sales,
                MAX(trade_date) AS max_bill_date
            FROM daily_bill
        """)
        p_row = session.execute(daily_sql, {"start_d": start_d, "end_d": end_d}).fetchone()
        total_fee = float(p_row[0]) if (p_row and p_row[0] is not None) else None
        total_sales = float(p_row[1]) if (p_row and p_row[1] is not None) else None
        max_bill_date = str(p_row[2]) if (p_row and p_row[2] is not None) else ""

        actual_price = (
            round(total_fee / total_sales, 2)
            if (total_fee is not None and total_sales is not None and total_sales != 0)
            else None
        )
        plant_results[unit_code] = {
            "actual": actual_price,
            "max_bill_date": max_bill_date,
        }

    return {
        "target": target_price,
        "avg_rt": round(avg_rt, 2) if avg_rt is not None else None,
        "max_rt_date": max_rt_date,
        "plants": plant_results,
    }


def get_auto_fetch_competition_data(month_str: str) -> Dict[str, Any]:
    """
    一键从系统自动提取竞赛所需月度指标：
    1. 从 monthly_data_show 提取 7 家单位能耗与运营指标的计划值与完成值（月报未出数前实际值保持为空）；
    2. 从 spot_electricity_15min_data 动态计算北海/香海电厂加权现货电价与辽宁统一结算点均价×1.05基准；
    3. 从 daily_basic_data 提取月末服务净投诉累计量，并结合 constant_data 供暖收费面积折算万平米投诉率；
    4. 对非停、断管率、安全文明等手动填报项预置标准缺省值（不与系统其他表联动）。
    """
    start_d, end_d = parse_month_date(month_str)

    monthly_records: List[Dict[str, Any]] = []
    complaint_records: Dict[str, Dict[str, Any]] = {}
    area_records: Dict[str, float] = {}
    spot_metrics: Dict[str, Any] = {}
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

        # 3. 抽取 daily_basic_data 中当月最新一天累计净投诉量
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

        # 4. 抽取 constant_data 中的供暖收费面积
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

        # 5. 抽取电力现货市场电价指标（北海、香海）
        spot_metrics = _fetch_spot_price_metrics(session, start_d, end_d)

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

    def build_monthly_item(
        comp: str,
        item_name: str,
        display_name: str,
        unit: str,
        scale: float = 1.0,
        percent_decimal_auto: bool = False,
    ) -> Dict[str, Any]:
        """从月报提取单个指标；月报无实际值时不回退日报，保持 actualValue 为 None。"""
        raw_plan = get_monthly_val(comp, item_name, "plan")
        raw_real = get_monthly_val(comp, item_name, "real")

        def _convert(val: Optional[float]) -> Optional[float]:
            if val is None:
                return None
            if percent_decimal_auto:
                return round(val * 100, 2) if val <= 1.5 else round(val, 2)
            return round(val * scale, 2)

        return {
            "name": display_name,
            "unit": unit,
            "targetValue": _convert(raw_plan),
            "actualValue": _convert(raw_real),
            "source": _monthly_source_label(raw_plan, raw_real),
        }

    # 5. 组装 7 家单位指标抽取数据
    units_extracted: Dict[str, Dict[str, Any]] = {}
    spot_target = spot_metrics.get("target")
    spot_rt_date = spot_metrics.get("max_rt_date") or ""
    spot_plants = spot_metrics.get("plants") or {}

    for unit_code, comp_name in UNIT_MONTHLY_COMPANY_MAP.items():
        extracted_indicators: Dict[str, Dict[str, Any]] = {}
        daily_code = UNIT_DAILY_COMPANY_MAP.get(unit_code, unit_code)

        if unit_code in ("BeiHai", "XiangHai"):
            extracted_indicators["coal_consumption"] = build_monthly_item(
                comp_name, "耗标煤总量", "耗标煤总量", "吨"
            )
            extracted_indicators["water_consumption"] = build_monthly_item(
                comp_name, "电厂耗水量", "厂内水耗量", "吨"
            )
            extracted_indicators["heat_efficiency"] = build_monthly_item(
                comp_name, "全厂热效率", "全厂热效率", "%", percent_decimal_auto=True
            )

            # 现货电价：标准值=辽宁实时均价×1.05，完成值=电厂账单电量加权现货电价
            p_spot = spot_plants.get(unit_code) or {}
            p_actual = p_spot.get("actual")
            p_bill_date = p_spot.get("max_bill_date") or ""
            if spot_target is not None and p_actual is not None:
                spot_source = f"电力现货 (基准至{spot_rt_date} · 账单加权至{p_bill_date})"
            elif spot_target is not None:
                spot_source = f"电力现货 (基准至{spot_rt_date} · 账单加权待导入)"
            else:
                spot_source = "电力现货 (暂无当月数据)"

            extracted_indicators["spot_price"] = {
                "name": "现货电价",
                "unit": "元/MWh",
                "targetValue": spot_target,
                "actualValue": p_actual,
                "source": spot_source,
            }

        elif unit_code in ("GongRe", "JinZhou", "BeiFang", "JinPu"):
            extracted_indicators["coal_consumption"] = build_monthly_item(
                comp_name, "耗标煤总量", "耗标煤总量", "吨"
            )
            extracted_indicators["heat_unit_consumption"] = build_monthly_item(
                comp_name, "供暖热耗率", "供暖热单耗", "GJ/万㎡", scale=10000.0
            )
            extracted_indicators["elec_unit_consumption"] = build_monthly_item(
                comp_name, "供暖电耗率", "供暖电单耗", "kWh/万㎡", scale=10000.0
            )
            extracted_indicators["water_unit_consumption"] = build_monthly_item(
                comp_name, "供暖水耗率", "供暖水单耗", "t/万㎡", scale=10.0
            )

        elif unit_code == "ZhuangHe":
            extracted_indicators["purchased_heat"] = build_monthly_item(
                comp_name, "外购热量", "外购热量", "GJ"
            )
            extracted_indicators["heat_unit_consumption"] = build_monthly_item(
                comp_name, "供暖热耗率", "供暖热单耗", "GJ/万㎡", scale=10000.0
            )
            extracted_indicators["elec_unit_consumption"] = build_monthly_item(
                comp_name, "供暖电耗率", "供暖电单耗", "kWh/万㎡", scale=10000.0
            )
            extracted_indicators["water_unit_consumption"] = build_monthly_item(
                comp_name, "供暖水耗率", "供暖水单耗", "t/万㎡", scale=10.0
            )

        # 6. 服务投诉率计算（针对供热 5 家单位）
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

        # 7. 手动填报项的缺省值（非停、断管率、安全文明；不与系统表联动）
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
    spot_bill_dates = [
        v.get("max_bill_date")
        for v in spot_plants.values()
        if isinstance(v, dict) and v.get("max_bill_date")
    ]
    spot_bill_latest_date = max(spot_bill_dates) if spot_bill_dates else ""

    return {
        "ok": True,
        "month": month_str,
        "is_historical": has_monthly_real,
        "latest_daily_date": latest_daily_date,
        "spot_latest_date": spot_rt_date,
        "spot_bill_latest_date": spot_bill_latest_date,
        "monthly_rows_matched": len(monthly_records),
        "complaint_units_matched": len(complaint_records),
        "units": units_extracted,
        "fetched_at": datetime.now().isoformat(),
    }


def _safe_float(val: Any, default: float = 0.0) -> float:
    """安全转换为浮点数，异常或 NaN 返回默认值。"""
    if val is None or val == "":
        return default
    try:
        num = float(val)
        return default if num != num else num
    except (TypeError, ValueError):
        return default


def _extract_unit_extra_total(unit: Dict[str, Any]) -> float:
    """汇总单位额外嘉奖列表或小计金额。"""
    extra_items = unit.get("extraRewards")
    if isinstance(extra_items, list) and len(extra_items) > 0:
        total = 0.0
        has_valid = False
        for item in extra_items:
            if isinstance(item, dict) and item.get("amount") not in (None, ""):
                total += _safe_float(item.get("amount"), 0.0)
                has_valid = True
        if has_valid:
            return total
    return _safe_float(unit.get("extraRewardTotal"), 0.0)


def _extract_units_snapshot(
    data_payload: Any,
    summary_payload: Any,
) -> List[Dict[str, Any]]:
    """从归档 JSON 中提取标准 7 家单位的奖金与得分摘要。"""
    unit_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(data_payload, list):
        for u in data_payload:
            if not isinstance(u, dict) or not u.get("code"):
                continue
            code = str(u["code"])
            eligible = bool(u.get("eligible", True))
            score = _safe_float(u.get("score"), 0.0)
            extra_amt = _extract_unit_extra_total(u)
            if u.get("baseReward") is not None:
                base_amt = _safe_float(u.get("baseReward"), 0.0)
            elif u.get("calculatedReward") is not None and extra_amt == 0:
                base_amt = _safe_float(u.get("calculatedReward"), 0.0) if eligible else 0.0
            else:
                raw_base = _safe_float(u.get("baseAmount"), 0.0) * (score / 100.0)
                base_amt = round(raw_base / 5.0) * 5.0 if eligible else 0.0
            total_amt = (
                _safe_float(u.get("calculatedReward"), base_amt + extra_amt)
                if u.get("calculatedReward") is not None
                else (base_amt + extra_amt)
            )
            unit_map[code] = {
                "code": code,
                "name": str(u.get("name") or code),
                "score": round(score, 2),
                "baseReward": round(base_amt, 2),
                "extraReward": round(extra_amt, 2),
                "reward": round(total_amt, 2),
                "eligible": eligible,
                "disqualifyReason": str(u.get("disqualifyReason") or ""),
            }

    if not unit_map and isinstance(summary_payload, dict):
        for lb in summary_payload.get("leaderboard") or []:
            if not isinstance(lb, dict) or not lb.get("code"):
                continue
            code = str(lb["code"])
            reward = _safe_float(lb.get("reward"), 0.0)
            extra_amt = _safe_float(lb.get("extraReward"), 0.0)
            base_amt = (
                _safe_float(lb.get("baseReward"), reward - extra_amt)
                if lb.get("baseReward") is not None
                else (reward - extra_amt)
            )
            unit_map[code] = {
                "code": code,
                "name": str(lb.get("name") or code),
                "score": round(_safe_float(lb.get("score"), 0.0), 2),
                "baseReward": round(base_amt, 2),
                "extraReward": round(extra_amt, 2),
                "reward": round(reward, 2),
                "eligible": bool(lb.get("eligible", True)),
                "disqualifyReason": str(lb.get("disqualifyReason") or ""),
            }

    ordered: List[Dict[str, Any]] = []
    for code, std_name in STANDARD_UNIT_DEFS:
        if code in unit_map:
            ordered.append(unit_map[code])
        else:
            ordered.append({
                "code": code,
                "name": std_name,
                "score": 0.0,
                "baseReward": 0.0,
                "extraReward": 0.0,
                "reward": 0.0,
                "eligible": True,
                "disqualifyReason": "",
            })
    return ordered


def _resolve_reward_breakdown(payload: Dict[str, Any]) -> Tuple[float, float, float]:
    """解析或从 data_payload 汇总 base_reward、extra_reward 与 total_reward。"""
    data_payload = payload.get("data_payload") or []
    summary_payload = payload.get("summary_payload") or {}
    units = _extract_units_snapshot(data_payload, summary_payload)
    computed_base = round(sum(u["baseReward"] for u in units), 2)
    computed_extra = round(sum(u["extraReward"] for u in units), 2)

    base_reward = (
        _safe_float(payload["base_reward"], computed_base)
        if payload.get("base_reward") is not None
        else computed_base
    )
    extra_reward = (
        _safe_float(payload["extra_reward"], computed_extra)
        if payload.get("extra_reward") is not None
        else computed_extra
    )
    total_reward = (
        _safe_float(payload["total_reward"], base_reward + extra_reward)
        if payload.get("total_reward") is not None
        else round(base_reward + extra_reward, 2)
    )
    return round(base_reward, 2), round(extra_reward, 2), round(total_reward, 2)


def save_competition_record(month_str: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存月度竞赛打分测算记录到 PostgreSQL。
    支持两种状态：'saved'（暂存保存）与 'final'（正式发布定稿）。
    """
    ensure_competition_table()
    start_d, _ = parse_month_date(month_str)

    status = str(payload.get("status") or "saved").strip().lower()
    if status not in ("saved", "final"):
        raise ValueError(f"无效的竞赛归档状态: {status}，仅支持 'saved' 或 'final'")

    base_reward, extra_reward, total_reward = _resolve_reward_breakdown(payload)
    disqualified_count = int(payload.get("disqualified_count", 0))
    data_payload = payload.get("data_payload") or []
    summary_payload = payload.get("summary_payload") or {}

    upsert_sql = text("""
        INSERT INTO competition_monthly_records (
            project_key, report_month, status, base_reward, extra_reward, total_reward,
            disqualified_count, data_payload, summary_payload, published_at, updated_at
        ) VALUES (
            :project_key, :report_month, :status, :base_reward, :extra_reward, :total_reward,
            :disqualified_count, :data_payload, :summary_payload,
            CASE WHEN :status = 'final' THEN NOW() ELSE NULL END,
            NOW()
        )
        ON CONFLICT (project_key, report_month) DO UPDATE SET
            status = EXCLUDED.status,
            base_reward = EXCLUDED.base_reward,
            extra_reward = EXCLUDED.extra_reward,
            total_reward = EXCLUDED.total_reward,
            disqualified_count = EXCLUDED.disqualified_count,
            data_payload = EXCLUDED.data_payload,
            summary_payload = EXCLUDED.summary_payload,
            published_at = CASE WHEN EXCLUDED.status = 'final' THEN NOW() ELSE NULL END,
            updated_at = NOW()
        RETURNING id, status, published_at, updated_at;
    """)

    with SessionLocal() as session:
        result = session.execute(
            upsert_sql,
            {
                "project_key": PROJECT_KEY,
                "report_month": start_d,
                "status": status,
                "base_reward": base_reward,
                "extra_reward": extra_reward,
                "total_reward": total_reward,
                "disqualified_count": disqualified_count,
                "data_payload": json.dumps(data_payload, ensure_ascii=False),
                "summary_payload": json.dumps(summary_payload, ensure_ascii=False),
            },
        ).fetchone()
        session.commit()

        action_label = "发布定稿 (final)" if status == "final" else "保存 (saved)"
        return {
            "ok": True,
            "id": result[0] if result else None,
            "month": month_str,
            "status": result[1] if result else status,
            "base_reward": base_reward,
            "extra_reward": extra_reward,
            "total_reward": total_reward,
            "published_at": str(result[2]) if (result and result[2]) else None,
            "updated_at": str(result[3]) if (result and result[3]) else None,
            "message": f"成功{action_label} {month_str} 指标竞赛打分测算数据至系统数据库",
        }


def get_competition_record(month_str: str) -> Dict[str, Any]:
    """
    从 PostgreSQL 查询指定月份已保存的竞赛测算记录。
    """
    ensure_competition_table()
    start_d, _ = parse_month_date(month_str)

    select_sql = text("""
        SELECT id, report_month, status, base_reward, extra_reward, total_reward, disqualified_count,
               data_payload, summary_payload, published_at, created_at, updated_at
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

        data_payload = row[7]
        summary_payload = row[8]
        total_reward = float(row[5]) if row[5] is not None else 0.0
        base_reward = float(row[3]) if row[3] is not None else None
        extra_reward = float(row[4]) if row[4] is not None else None
        if base_reward is None or extra_reward is None:
            units = _extract_units_snapshot(data_payload, summary_payload)
            if base_reward is None:
                base_reward = round(sum(u["baseReward"] for u in units), 2)
            if extra_reward is None:
                extra_reward = round(sum(u["extraReward"] for u in units), 2)

        return {
            "ok": True,
            "found": True,
            "id": row[0],
            "month": month_str,
            "status": str(row[2] or "saved").lower(),
            "base_reward": base_reward,
            "extra_reward": extra_reward,
            "total_reward": total_reward,
            "disqualified_count": int(row[6] or 0),
            "data_payload": data_payload,
            "summary_payload": summary_payload,
            "published_at": str(row[9]) if row[9] else None,
            "created_at": str(row[10]) if row[10] else None,
            "updated_at": str(row[11]) if row[11] else None,
        }


def get_competition_records_summary(months: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    汇总供暖期指定月份（默认 2026-11 至 2027-03）的月度定稿状态、奖金拆解与各单位明细。
    """
    ensure_competition_table()
    target_months = [m.strip() for m in (months or DEFAULT_SEASON_MONTHS) if str(m or "").strip()]
    if not target_months:
        target_months = list(DEFAULT_SEASON_MONTHS)

    parsed_pairs = [(m, parse_month_date(m)[0]) for m in target_months]
    min_d = min(d for _, d in parsed_pairs)
    max_d = max(d for _, d in parsed_pairs)

    select_sql = text("""
        SELECT report_month, status, base_reward, extra_reward, total_reward,
               disqualified_count, data_payload, summary_payload, published_at, updated_at
        FROM competition_monthly_records
        WHERE project_key = :project_key
          AND report_month BETWEEN :min_d AND :max_d
        ORDER BY report_month ASC
    """)

    rows_by_month: Dict[str, Any] = {}
    with SessionLocal() as session:
        rows = session.execute(select_sql, {
            "project_key": PROJECT_KEY,
            "min_d": min_d,
            "max_d": max_d,
        }).fetchall()
        for r in rows:
            m_key = r[0].strftime("%Y-%m") if hasattr(r[0], "strftime") else str(r[0])[:7]
            rows_by_month[m_key] = r

    records: List[Dict[str, Any]] = []
    final_summary = {"count": 0, "base_reward": 0.0, "extra_reward": 0.0, "total_reward": 0.0}
    all_saved_summary = {"count": 0, "base_reward": 0.0, "extra_reward": 0.0, "total_reward": 0.0}

    for month_str, _ in parsed_pairs:
        row = rows_by_month.get(month_str)
        if not row:
            records.append({
                "month": month_str,
                "exists": False,
                "status": "unrecorded",
                "base_reward": 0.0,
                "extra_reward": 0.0,
                "total_reward": 0.0,
                "disqualified_count": 0,
                "published_at": None,
                "updated_at": None,
                "units": [],
            })
            continue

        status = str(row[1] or "saved").lower()
        data_payload = row[6]
        summary_payload = row[7]
        units = _extract_units_snapshot(data_payload, summary_payload)
        computed_base = round(sum(u["baseReward"] for u in units), 2)
        computed_extra = round(sum(u["extraReward"] for u in units), 2)

        # 兼容历史记录：若未写入 base_reward/extra_reward 字段（均为 0 且 total_reward > 0），由快照回算
        db_base = float(row[2]) if row[2] is not None else 0.0
        db_extra = float(row[3]) if row[3] is not None else 0.0
        db_total = float(row[4]) if row[4] is not None else 0.0
        if db_base == 0.0 and db_extra == 0.0 and db_total > 0.0 and (computed_base > 0.0 or computed_extra != 0.0):
            base_val, extra_val = computed_base, computed_extra
        else:
            base_val = db_base if row[2] is not None else computed_base
            extra_val = db_extra if row[3] is not None else computed_extra

        total_val = db_total if row[4] is not None else round(base_val + extra_val, 2)

        rec = {
            "month": month_str,
            "exists": True,
            "status": status,
            "base_reward": round(base_val, 2),
            "extra_reward": round(extra_val, 2),
            "total_reward": round(total_val, 2),
            "disqualified_count": int(row[5] or 0),
            "published_at": str(row[8]) if row[8] else None,
            "updated_at": str(row[9]) if row[9] else None,
            "units": units,
        }
        records.append(rec)

        all_saved_summary["count"] += 1
        all_saved_summary["base_reward"] = round(all_saved_summary["base_reward"] + rec["base_reward"], 2)
        all_saved_summary["extra_reward"] = round(all_saved_summary["extra_reward"] + rec["extra_reward"], 2)
        all_saved_summary["total_reward"] = round(all_saved_summary["total_reward"] + rec["total_reward"], 2)

        if status == "final":
            final_summary["count"] += 1
            final_summary["base_reward"] = round(final_summary["base_reward"] + rec["base_reward"], 2)
            final_summary["extra_reward"] = round(final_summary["extra_reward"] + rec["extra_reward"], 2)
            final_summary["total_reward"] = round(final_summary["total_reward"] + rec["total_reward"], 2)

    return {
        "ok": True,
        "months": target_months,
        "records": records,
        "final_summary": final_summary,
        "all_saved_summary": all_saved_summary,
    }
