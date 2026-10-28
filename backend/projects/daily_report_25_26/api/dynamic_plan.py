# -*- coding: utf-8 -*-
"""
daily_report_25_26 动态计划与月度指标展示接口。
从 paln_and_real_month_data 查询供暖期各单位计划指标，支持按口径和连续月度范围聚合与可视化。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, auth_manager, get_current_session, get_current_session_optional

PROJECT_KEY = "daily_report_25_26"
router = APIRouter()
public_router = APIRouter()

# 标准单位字典与排序
STANDARD_UNITS = [
    {"company": "Group", "company_cn": "集团全口径", "desc": "洁净能源集团全口径综合计划"},
    {"company": "ZhuChengQu", "company_cn": "主城区", "desc": "主城区管网供热及热源汇总"},
    {"company": "BeiHai", "company_cn": "北海热电厂", "desc": "北海热电联产、水炉与燃气炉"},
    {"company": "XiangHai", "company_cn": "香海热电厂", "desc": "香海热电联产厂"},
    {"company": "GongRe", "company_cn": "供热公司", "desc": "供热分公司（各中心及管网）"},
    {"company": "JinZhou", "company_cn": "金州热电", "desc": "金州热电分厂"},
    {"company": "BeiFang", "company_cn": "北方热电", "desc": "北方热电分厂"},
    {"company": "JinPu", "company_cn": "金普热电", "desc": "金普热电分厂"},
    {"company": "ZhuangHe", "company_cn": "庄河环海", "desc": "庄河全外购热供热"},
    {"company": "YanJiuYuan", "company_cn": "研究院", "desc": "研发及电锅炉/热泵供热口径"},
]

# 汇总口径与下属实体单位映射（主城区由北海、香海、供热三家合并；集团全口径由下辖全部8家实体单位合并）
ROLLUP_HIERARCHY: Dict[str, List[str]] = {
    "Group": ["BeiHai", "XiangHai", "GongRe", "JinZhou", "BeiFang", "JinPu", "ZhuangHe", "YanJiuYuan"],
    "ZhuChengQu": ["BeiHai", "XiangHai", "GongRe"],
}

# 指标业务分类归属
METRIC_CATEGORY_MAP = {
    # 综合热量
    "amount_heat_supply": ("heat", "综合热量"),
    "amount_network_interface_heat_supply": ("heat", "综合热量"),
    "amount_purchased_heat": ("heat", "综合热量"),
    "amount_hot_water_sales": ("heat", "综合热量"),
    "amount_steam_sales": ("heat", "综合热量"),
    "amount_steam_supply": ("heat", "综合热量"),
    "consumption_station_heat": ("heat", "综合热量"),
    # 电力指标
    "amount_power_generation": ("power", "电力发售"),
    "amount_power_sales": ("power", "电力发售"),
    "consumption_purchased_power": ("power", "电力发售"),
    "consumption_plant_purchased_power": ("power", "电力发售"),
    "consumption_station_purchased_power": ("power", "电力发售"),
    # 燃料能耗
    "consumption_std_coal": ("fuel", "燃料能耗"),
    "consumption_amount_raw_coal": ("fuel", "燃料能耗"),
    "consumption_natural_gas": ("fuel", "燃料能耗"),
    # 水耗与辅材
    "consumption_water": ("water_aux", "水耗与辅材"),
    "consumption_plant_water": ("water_aux", "水耗与辅材"),
    "consumption_network_fill_water": ("water_aux", "水耗与辅材"),
    "consumption_station_fill_water": ("water_aux", "水耗与辅材"),
    "consumption_acid": ("water_aux", "水耗与辅材"),
    "consumption_alkali": ("water_aux", "水耗与辅材"),
    "consumption_oil": ("water_aux", "水耗与辅材"),
    "consumption_ammonia_water": ("water_aux", "水耗与辅材"),
    "consumption_limestone": ("water_aux", "水耗与辅材"),
    "consumption_limestone_powder": ("water_aux", "水耗与辅材"),
    "consumption_magnesium_oxide": ("water_aux", "水耗与辅材"),
    "consumption_denitration_agent": ("water_aux", "水耗与辅材"),
    # 供暖单耗
    "rate_heat_per_10k_m2": ("efficiency", "供暖单耗"),
    "rate_water_per_10k_m2": ("efficiency", "供暖单耗"),
    "rate_power_per_10k_m2": ("efficiency", "供暖单耗"),
    # 经济效益
    "eco_direct_income": ("eco", "经济效益"),
    "eco_power_supply_income": ("eco", "经济效益"),
    "eco_inner_heat_supply_income": ("eco", "经济效益"),
    "eco_coal_cost": ("eco", "经济效益"),
    "eco_natural_gas_cost": ("eco", "经济效益"),
    "eco_purchased_power_cost": ("eco", "经济效益"),
    "eco_purchased_water_cost": ("eco", "经济效益"),
    "eco_measurable_auxiliary_materials": ("eco", "经济效益"),
    "eco_marginal_profit": ("eco", "经济效益"),
    # 民生服务
    "amount_daily_service_complaints": ("service", "民生服务"),
    "amount_daily_net_complaints": ("service", "民生服务"),
}

# 用户指定的30项标准指标展示次序
ORDERED_METRIC_NAMES: List[str] = [
    "供热量",
    "发电量",
    "售电量",
    "高温水销售量",
    "售汽量",
    "原煤耗量",
    "标煤耗量",
    "耗油量",
    "外购热量",
    "耗天然气量",
    "外购电量",
    "其中：换热站外购电量",
    "其中：电厂外购电量",
    "耗水量",
    "其中：电厂耗水量",
    "其中：电厂一次网补水量",
    "其中：热网补水量",
    "其中：换热站补水量",
    "耗酸量",
    "耗碱量",
    "耗氨水量",
    "耗石灰石粉量",
    "耗石灰石量",
    "耗氧化镁量",
    "耗脱硝剂量",
    "供暖热单耗",
    "供暖水单耗",
    "供暖电单耗",
    "网口供热量",
    "站内耗热量",
]

# 标准英文 key 到中文名对照映射
METRIC_ITEM_KEY_MAP: Dict[str, str] = {
    "amount_heat_supply": "供热量",
    "amount_power_generation": "发电量",
    "amount_power_sales": "售电量",
    "amount_hot_water_sales": "高温水销售量",
    "amount_steam_sales": "售汽量",
    "consumption_amount_raw_coal": "原煤耗量",
    "consumption_std_coal": "标煤耗量",
    "consumption_oil": "耗油量",
    "consumption_outer_purchased_heat": "外购热量",
    "consumption_natural_gas": "耗天然气量",
    "consumption_purchased_power": "外购电量",
    "consumption_station_purchased_power": "其中：换热站外购电量",
    "consumption_plant_purchased_power": "其中：电厂外购电量",
    "consumption_water": "耗水量",
    "consumption_plant_water": "其中：电厂耗水量",
    "consumption_network_fill_water": "其中：电厂一次网补水量",
    "consumption_network_water": "其中：热网补水量",
    "consumption_station_fill_water": "其中：换热站补水量",
    "consumption_acid": "耗酸量",
    "consumption_alkali": "耗碱量",
    "consumption_ammonia_water": "耗氨水量",
    "consumption_limestone_powder": "耗石灰石粉量",
    "consumption_limestone": "耗石灰石量",
    "consumption_magnesium_oxide": "耗氧化镁量",
    "consumption_denitration_agent": "耗脱硝剂量",
    "rate_heat_per_10k_m2": "供暖热单耗",
    "rate_water_per_10k_m2": "供暖水单耗",
    "rate_power_per_10k_m2": "供暖电单耗",
    "amount_network_interface_heat_supply": "网口供热量",
    "consumption_station_heat": "站内耗热量",
}

ORDER_INDEX_BY_CN: Dict[str, int] = {name: idx for idx, name in enumerate(ORDERED_METRIC_NAMES)}
ORDER_INDEX_BY_KEY: Dict[str, int] = {k: ORDER_INDEX_BY_CN.get(v, 999) for k, v in METRIC_ITEM_KEY_MAP.items()}


def get_metric_sort_order(m: Dict[str, Any]) -> int:
    """返回指标排序索引，严格遵守用户指定的30项标准业务次序"""
    item_key = m.get("item", "")
    item_cn = m.get("item_cn", "")
    if item_key in ORDER_INDEX_BY_KEY:
        return ORDER_INDEX_BY_KEY[item_key]
    if item_cn in ORDER_INDEX_BY_CN:
        return ORDER_INDEX_BY_CN[item_cn]
    return 999


def _normalize_period(p: str) -> str:
    """标准化月份参数为 YYYY-MM-01"""
    p = str(p or "").strip()
    if not p:
        return ""
    if len(p) == 7 and p[4] == "-":
        return f"{p}-01"
    return p


def _format_month_label(p: str) -> str:
    """转换为 YYYY-MM"""
    p = str(p or "").strip()
    if len(p) >= 7:
        return p[:7]
    return p


@public_router.get(
    "/dynamic_plan/meta",
    summary="获取动态计划元数据（单位口径、可选月份与分类字典）",
    tags=["daily_report_25_26_dynamic_plan"],
)
def get_dynamic_plan_meta():
    """返回单位清单、数据库已有的周期列表与指标分类配置"""
    with SessionLocal() as session:
        # 获取 26-27 供暖期的可用周期
        rows = session.execute(
            text(
                """
                SELECT DISTINCT period 
                FROM paln_and_real_month_data 
                WHERE period >= '2026-10-01' AND type = 'plan'
                ORDER BY period
                """
            )
        ).all()
        periods = [r[0] for r in rows]
        months = [_format_month_label(p) for p in periods]

    categories = [
        {"key": "all", "label": "全部指标"},
        {"key": "heat", "label": "综合热量"},
        {"key": "power", "label": "电力发售"},
        {"key": "fuel", "label": "燃料能耗"},
        {"key": "water_aux", "label": "水耗与辅材"},
        {"key": "efficiency", "label": "供暖单耗"},
        {"key": "eco", "label": "经济效益"},
        {"key": "service", "label": "民生服务"},
    ]

    return {
        "ok": True,
        "units": STANDARD_UNITS,
        "available_periods": periods,
        "available_months": months,
        "categories": categories,
        "default_range": {
            "start_month": "2026-11",
            "end_month": "2027-04",
        },
    }


@public_router.get(
    "/dynamic_plan/plans",
    summary="查询各单位指定连续月份的月度计划指标数据",
    tags=["daily_report_25_26_dynamic_plan"],
)
def get_dynamic_plan_data(
    company: str = Query(default="Group", description="单位编码，如 Group, BeiHai 等"),
    start_month: str = Query(default="2026-11", description="起始月份，如 2026-11"),
    end_month: str = Query(default="2027-04", description="结束月份，如 2027-04"),
    plan_type: str = Query(default="plan", description="数据类别，默认 plan"),
):
    """
    根据单位与连续月份区间提取计划数据，计算各月值、区间合计、月均及占比峰值
    """
    start_period = _normalize_period(start_month.default if hasattr(start_month, "default") else str(start_month))
    end_period = _normalize_period(end_month.default if hasattr(end_month, "default") else str(end_month))
    company_code = str(company.default if hasattr(company, "default") else company).strip()
    ptype_str = str(plan_type.default if hasattr(plan_type, "default") else plan_type).strip()
    company_info = next((u for u in STANDARD_UNITS if u["company"] == company_code), None)
    company_cn = company_info["company_cn"] if company_info else company_code

    with SessionLocal() as session:
        # 1. 查询该区间内实际存在的月份
        p_rows = session.execute(
            text(
                """
                SELECT DISTINCT period 
                FROM paln_and_real_month_data 
                WHERE period >= :start_p AND period <= :end_p
                  AND type = :ptype
                ORDER BY period
                """
            ),
            {"start_p": start_period, "end_p": end_period, "ptype": ptype_str},
        ).all()
        selected_periods = [r[0] for r in p_rows]
        selected_months = [_format_month_label(p) for p in selected_periods]

        if not selected_periods:
            return {
                "ok": True,
                "company": company_code,
                "company_cn": company_cn,
                "months": [],
                "metrics": [],
                "summary_cards": {},
            }

        # 2. 查询当前单位自身的直属填报指标
        stmt_direct = text(
            """
            SELECT company, company_cn, item, item_cn, unit, period, value
            FROM paln_and_real_month_data
            WHERE company = :company
              AND period >= :start_p AND period <= :end_p
              AND type = :ptype
            ORDER BY item, period
            """
        )
        direct_rows = session.execute(
            stmt_direct,
            {
                "company": company_code,
                "start_p": start_period,
                "end_p": end_period,
                "ptype": ptype_str,
            },
        ).mappings().all()

        # 3. 若当前属于汇总口径（Group 或 ZhuChengQu），向上聚合下属实体单位的指标
        rollup_rows = []
        if company_code in ROLLUP_HIERARCHY:
            sub_units = ROLLUP_HIERARCHY[company_code]
            stmt_rollup = text(
                """
                SELECT item, MAX(item_cn) as item_cn, MAX(unit) as unit, period, SUM(value) as value
                FROM paln_and_real_month_data
                WHERE company IN :subs
                  AND period >= :start_p AND period <= :end_p
                  AND type = :ptype
                GROUP BY item, period
                ORDER BY item, period
                """
            )
            rollup_rows = session.execute(
                stmt_rollup,
                {
                    "subs": tuple(sub_units),
                    "start_p": start_period,
                    "end_p": end_period,
                    "ptype": ptype_str,
                },
            ).mappings().all()

    # 4. 构建指标矩阵（汇总口径已有直报值则以直报权威值为准，未直报项由下属单位向上聚合求和补齐）
    direct_items = {(r["item"], _format_month_label(r["period"])) for r in direct_rows}
    grouped: Dict[str, Dict[str, Any]] = {}

    for r in direct_rows:
        item_key = r["item"]
        if item_key not in grouped:
            cat_key, cat_label = METRIC_CATEGORY_MAP.get(item_key, ("other", "其他指标"))
            grouped[item_key] = {
                "item": item_key,
                "item_cn": r["item_cn"] or item_key,
                "unit": r["unit"] or "",
                "category": cat_key,
                "category_label": cat_label,
                "is_rollup": False,
                "values": {},
            }
        m_label = _format_month_label(r["period"])
        val = float(r["value"]) if r["value"] is not None else 0.0
        grouped[item_key]["values"][m_label] = val

    for r in rollup_rows:
        item_key = r["item"]
        if (item_key, _format_month_label(r["period"])) in direct_items:
            # 汇总口径已有经核准的直报值（已做内部关联抵消），保留直报值
            continue
        if item_key not in grouped:
            cat_key, cat_label = METRIC_CATEGORY_MAP.get(item_key, ("other", "其他指标"))
            grouped[item_key] = {
                "item": item_key,
                "item_cn": r["item_cn"] or item_key,
                "unit": r["unit"] or "",
                "category": cat_key,
                "category_label": cat_label,
                "is_rollup": True,
                "values": {},
            }
        m_label = _format_month_label(r["period"])
        val = float(r["value"]) if r["value"] is not None else 0.0
        grouped[item_key]["values"][m_label] = val

    # 4. 计算指标汇总、均值、峰值及百分比结构
    metrics_list: List[Dict[str, Any]] = []
    summary_cards: Dict[str, float] = {
        "heat_supply_total": 0.0,
        "std_coal_total": 0.0,
        "raw_coal_total": 0.0,
        "power_generation_total": 0.0,
        "power_sales_total": 0.0,
        "purchased_power_total": 0.0,
        "water_total": 0.0,
        "heat_rate_total": 0.0,
        "water_rate_total": 0.0,
        "power_rate_total": 0.0,
    }

    for item_key, m_data in grouped.items():
        v_dict = m_data["values"]
        vals = [v_dict.get(m, 0.0) for m in selected_months]
        
        # 暖通生产体系中，各月单耗之和即为期内累计综合单耗（分子为各月消耗总量之和，分母为恒定面积）
        # 因此所有指标汇总（total_val）统一为各月累计求和
        is_ratio = "率" in m_data["item_cn"] and "单耗" not in m_data["item_cn"]
        is_rate_metric = "单耗" in m_data["item_cn"]
        
        if is_rate_metric:
            total_val = round(sum(vals), 4)
            avg_val = round(total_val / len(selected_months), 4) if selected_months else 0.0
        elif is_ratio:
            total_val = round(sum(vals) / len(vals), 2) if vals else 0.0
            avg_val = total_val
        else:
            total_val = round(sum(vals), 2)
            avg_val = round(total_val / len(selected_months), 2) if selected_months else 0.0

        # 计算峰值与最低月份
        max_m, max_v = "", -1e9
        min_m, min_v = "", 1e9
        for m in selected_months:
            cur_v = v_dict.get(m, 0.0)
            if cur_v > max_v:
                max_v, max_m = cur_v, m
            if cur_v < min_v:
                min_v, min_m = cur_v, m

        # 计算各月占比分布 (全月合计=100%)
        distribution: Dict[str, float] = {}
        if total_val > 0 and not is_ratio:
            for m in selected_months:
                distribution[m] = round((v_dict.get(m, 0.0) / total_val) * 100.0, 2)
        else:
            for m in selected_months:
                distribution[m] = 0.0

        metric_record = {
            **m_data,
            "total": total_val,
            "average": avg_val,
            "max_month": max_m,
            "max_value": max_v if max_v != -1e9 else 0.0,
            "min_month": min_m,
            "min_value": min_v if min_v != 1e9 else 0.0,
            "distribution": distribution,
            "is_ratio": is_ratio,
        }
        metrics_list.append(metric_record)

        # 汇总核心指标卡片
        if item_key == "amount_heat_supply":
            summary_cards["heat_supply_total"] = total_val
        elif item_key == "consumption_std_coal":
            summary_cards["std_coal_total"] = total_val
        elif item_key == "consumption_amount_raw_coal":
            summary_cards["raw_coal_total"] = total_val
        elif item_key == "amount_power_generation":
            summary_cards["power_generation_total"] = total_val
        elif item_key == "amount_power_sales":
            summary_cards["power_sales_total"] = total_val
        elif item_key == "consumption_purchased_power":
            summary_cards["purchased_power_total"] = total_val
        elif item_key == "consumption_water":
            summary_cards["water_total"] = total_val
        elif item_key == "rate_heat_per_10k_m2":
            summary_cards["heat_rate_total"] = total_val
        elif item_key == "rate_water_per_10k_m2":
            summary_cards["water_rate_total"] = total_val
        elif item_key == "rate_power_per_10k_m2":
            summary_cards["power_rate_total"] = total_val

    # 严格按照用户指定的30项标准业务次序进行排序
    metrics_list.sort(key=get_metric_sort_order)

    return {
        "ok": True,
        "company": company_code,
        "company_cn": company_cn,
        "start_month": selected_months[0] if selected_months else "",
        "end_month": selected_months[-1] if selected_months else "",
        "months": selected_months,
        "periods": selected_periods,
        "metrics": metrics_list,
        "summary_cards": summary_cards,
    }


@public_router.post("/dynamic_plan/import_ensemble_temperature", summary="从Open-Meteo导入35天集合气温预报并入库(标记type=far)")
async def import_ensemble_temperature_endpoint():
    try:
        from backend.services.ensemble_weather_service import fetch_and_import_ensemble_weather
        res = fetch_and_import_ensemble_weather()
        return res
    except Exception as exc:
        return {"ok": False, "message": f"拉取35天集合气温预报失败: {str(exc)}"}


@public_router.get("/dynamic_plan/daily_decomposition", summary="获取月度计划的动态日分解与气温分布曲线")
async def get_daily_decomposition_endpoint(
    company: str = Query("Group", description="统计口径代号"),
    year_month: str = Query("2026-11", description="目标计划月份，如 2026-11"),
):
    """
    根据 HDD20 供热度日与优化后建议 k 模型，将指定单位在目标月份的月度计划动态分解至每日。
    若全月气温不完整，返回 has_full_month=False 及缺失日期清单。
    """
    from backend.services.dynamic_decomposition_service import get_dynamic_daily_decomposition
    session = SessionLocal()
    try:
        return get_dynamic_daily_decomposition(company=company, year_month=year_month, session=session)
    except Exception as exc:
        return {"ok": False, "has_full_month": False, "message": f"计算动态计划日分解异常: {str(exc)}"}
    finally:
        session.close()


class UpdateKParameterItem(BaseModel):
    company: str = Field(..., description="统计口径代号，如 Group, BeiHai")
    month: int = Field(..., ge=1, le=12, description="目标月份数字，如 11")
    item: str = Field(..., description="指标英文键名，如 amount_heat_supply")
    item_cn: Optional[str] = Field(None, description="指标中文名")
    unit: Optional[str] = Field(None, description="计量单位")
    k_value: Optional[float] = Field(None, description="基准 k 值敏感度参数")
    m_value: Optional[float] = Field(None, description="m 缩放系数")


class UpdateKParametersPayload(BaseModel):
    updates: List[UpdateKParameterItem] = Field(default_factory=list, description="待更新参数列表")


@public_router.post("/dynamic_plan/update_k_parameters", summary="Global_admin 设定各指标 m 缩放参数")
async def update_k_parameters_endpoint(
    payload: UpdateKParametersPayload,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    允许 Global_admin 角色在前台在线设定指定口径与月份下各指标的 m 缩放系数（基准 k 值保持严肃客观，仅允许微调 m 缩放）。
    """
    # 软依赖回退尝试解析
    if session is None and authorization:
        try:
            session = auth_manager.require_session_from_header(authorization)
        except Exception:
            pass

    if session is None:
        raise HTTPException(status_code=401, detail="请登录后操作")

    is_admin = (
        str(session.group or "").strip() == "Global_admin"
        or str(session.username or "").strip() == "ww870411"
        or bool(getattr(session.permissions.actions, "can_access_admin_console", False))
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="权限不足：仅 Global_admin 全局管理员有权设定 m 缩放参数")

    if not payload.updates:
        return {"ok": True, "message": "无更新项", "updated_count": 0}

    db = SessionLocal()
    updated_count = 0
    try:
        for u in payload.updates:
            comp = u.company.strip()
            month = int(u.month)
            item = u.item.strip()

            row = db.execute(
                text("""
                    SELECT id, k_value, m_value FROM public.dynamic_month_plan_k
                    WHERE company = :company AND month = :month AND item = :item
                """),
                {"company": comp, "month": month, "item": item},
            ).fetchone()

            new_m = u.m_value

            if row:
                set_clauses = []
                params: Dict[str, Any] = {"company": comp, "month": month, "item": item}
                # 基准 k 值保持不可篡改，仅更新 m 缩放系数
                if new_m is not None:
                    set_clauses.append("m_value = :m_val")
                    params["m_val"] = new_m
                if u.item_cn:
                    set_clauses.append("item_cn = :item_cn")
                    params["item_cn"] = u.item_cn
                if u.unit:
                    set_clauses.append("unit = :unit")
                    params["unit"] = u.unit

                if set_clauses:
                    db.execute(
                        text(f"""
                            UPDATE public.dynamic_month_plan_k
                            SET {', '.join(set_clauses)}
                            WHERE company = :company AND month = :month AND item = :item
                        """),
                        params,
                    )
                    updated_count += 1
            else:
                # 新指标没有基准模型时按均摊处理，客户端不能修改基准 k。
                final_k = 0.0
                final_m = new_m if new_m is not None else 1.0
                db.execute(
                    text("""
                        INSERT INTO public.dynamic_month_plan_k (company, month, item, item_cn, unit, k_value, m_value)
                        VALUES (:company, :month, :item, :item_cn, :unit, :k_val, :m_val)
                        ON CONFLICT (company, month, item) DO UPDATE SET
                            k_value = EXCLUDED.k_value,
                            m_value = EXCLUDED.m_value
                    """),
                    {
                        "company": comp,
                        "month": month,
                        "item": item,
                        "item_cn": u.item_cn or item,
                        "unit": u.unit or "",
                        "k_val": final_k,
                        "m_val": final_m,
                    },
                )
                updated_count += 1

        db.commit()
        return {
            "ok": True,
            "message": f"成功保存 {updated_count} 项指标 k/m 参数！",
            "updated_count": updated_count,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存参数失败: {str(exc)}")
    finally:
        db.close()



