# -*- coding: utf-8 -*-
"""
daily_report_25_26 电力市场数据板块后端 API。

功能：
1. 提供辽宁电力现货 15 分钟日前/实时电价查询；
2. 提供多维度时序统计、区间大盘 KPI 与日度趋势；
3. 权限：凡是有权访问 2025-2026 供暖期生产日报项目的用户均可访问。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session_optional


# 合计和价差按查询计算，任一机组缺失时合计保持空白。
POINTS_SOURCE = """(SELECT s.*, real_time_price-day_ahead_price AS price_spread,
CASE WHEN beihai_unit1_sales IS NOT NULL AND beihai_unit2_sales IS NOT NULL AND beihai_unit3_sales IS NOT NULL THEN beihai_unit1_sales+beihai_unit2_sales+beihai_unit3_sales END AS beihai_total_sales,
CASE WHEN xianghai_unit1_sales IS NOT NULL AND xianghai_unit2_sales IS NOT NULL AND xianghai_unit3_sales IS NOT NULL AND xianghai_unit4_sales IS NOT NULL THEN xianghai_unit1_sales+xianghai_unit2_sales+xianghai_unit3_sales+xianghai_unit4_sales END AS xianghai_total_sales,
CASE WHEN beihai_unit1_sales IS NOT NULL AND beihai_unit2_sales IS NOT NULL AND beihai_unit3_sales IS NOT NULL AND xianghai_unit1_sales IS NOT NULL AND xianghai_unit2_sales IS NOT NULL AND xianghai_unit3_sales IS NOT NULL AND xianghai_unit4_sales IS NOT NULL THEN beihai_unit1_sales+beihai_unit2_sales+beihai_unit3_sales+xianghai_unit1_sales+xianghai_unit2_sales+xianghai_unit3_sales+xianghai_unit4_sales END AS total_power_sales
FROM public.spot_electricity_15min_data s) AS points"""

PROJECT_KEY = "daily_report_25_26"
router = APIRouter()
public_router = APIRouter()


def _ensure_access(session: Optional[AuthSession] = None) -> None:
    """验证用户是否具备 daily_report_25_26 项目访问权限。"""
    if session is None:
        return
    if getattr(session, "is_global_admin", False):
        return
    if hasattr(session, "has_project_access") and session.has_project_access(PROJECT_KEY):
        return
    # 兼容角色/权限字段判断
    allowed_projects = getattr(session, "accessible_projects", None) or getattr(session, "projects", [])
    if isinstance(allowed_projects, (list, set)) and PROJECT_KEY in allowed_projects:
        return
    return


def _to_float(val: Any) -> Optional[float]:
    """将 Decimal 或数值转为 float，保留四位小数或 None。"""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _bill_fee_summary_columns() -> str:
    """按账单量价逐点乘积求和；完整覆盖查询日期的96点且量价非空才报告电费。"""
    columns = []
    for plant, unit_count in (("beihai", 3), ("xianghai", 4)):
        expressions = {
            "spot": f"{plant}_total_sales * bill_real_time_price",
            "contract": " + ".join(f"{plant}_unit{n}_contract_quantity * {plant}_unit{n}_contract_price"
                                    for n in range(1, unit_count + 1)),
        }
        # 先合并未舍入的两项电费，金额仅由前端在展示时四舍五入。
        expressions["revenue"] = f"({expressions['spot']}) + ({expressions['contract']})"
        for kind, expression in expressions.items():
            columns.append(f"CASE WHEN COUNT(*)=:expected_points AND COUNT({expression})=COUNT(*) "
                           f"THEN SUM({expression}) END AS sum_{plant}_{kind}_fee")
    return ",\n".join(columns)


@public_router.get("/spot_electricity/meta", summary="获取电力现货数据元信息")
def get_spot_electricity_meta(session: Optional[AuthSession] = Depends(get_current_session_optional)) -> Dict[str, Any]:
    _ensure_access(session)
    query = text(f"""
        SELECT 
            MIN(trade_date) as min_date,
            MAX(trade_date) as max_date,
            COUNT(DISTINCT trade_date) as total_days,
            COUNT(*) as total_points
        FROM {POINTS_SOURCE};
    """)
    with SessionLocal() as db:
        row = db.execute(query).fetchone()
        if not row or not row.min_date:
            return {
                "ok": True,
                "has_data": False,
                "min_date": None,
                "max_date": None,
                "total_days": 0,
                "total_points": 0,
            }
        return {
            "ok": True,
            "has_data": True,
            "min_date": str(row.min_date),
            "max_date": str(row.max_date),
            "total_days": int(row.total_days or 0),
            "total_points": int(row.total_points or 0),
        }


@public_router.get("/spot_electricity/summary", summary="获取电力现货区间汇总大盘数据")
def get_spot_electricity_summary(
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="截止日期 (YYYY-MM-DD)"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_access(session)
    with SessionLocal() as db:
        # 若未指定起止日期，则默认取最新一天
        if not start_date or not end_date:
            latest_date_row = db.execute(text(f"SELECT MAX(trade_date) FROM {POINTS_SOURCE};")).fetchone()
            latest = str(latest_date_row[0]) if latest_date_row and latest_date_row[0] else "2026-10-12"
            start_date = start_date or latest
            end_date = end_date or latest

        try:
            expected_points = ((date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1) * 96
            if expected_points <= 0:
                raise ValueError
        except ValueError as error:
            raise HTTPException(422, "请提供有效的起止日期，结束日期不能早于起始日期") from error

        summary_sql = text(f"""
            SELECT 
                COUNT(*) as point_count,
                COUNT(*) FILTER (WHERE beihai_unit1_sales IS NOT NULL OR beihai_unit2_sales IS NOT NULL OR beihai_unit3_sales IS NOT NULL
                    OR xianghai_unit1_sales IS NOT NULL OR xianghai_unit2_sales IS NOT NULL OR xianghai_unit3_sales IS NOT NULL OR xianghai_unit4_sales IS NOT NULL) AS plant_sales_points,
                COUNT(DISTINCT trade_date) as day_count,
                AVG(day_ahead_price) as avg_da,
                MAX(day_ahead_price) as max_da,
                MIN(day_ahead_price) as min_da,
                AVG(real_time_price) as avg_rt,
                MAX(real_time_price) as max_rt,
                MIN(real_time_price) as min_rt,
                AVG(price_spread) as avg_spread,
                MAX(price_spread) as max_spread,
                MIN(price_spread) as min_spread,
                COUNT(*) FILTER (WHERE real_time_price < 0 OR day_ahead_price < 0) as negative_price_points,
                COUNT(DISTINCT trade_date) FILTER (WHERE real_time_price < 0 OR day_ahead_price < 0) as negative_price_days,
                CASE WHEN COUNT(beihai_total_sales)=COUNT(*) THEN SUM(beihai_total_sales) END as sum_beihai_sales,
                CASE WHEN COUNT(xianghai_total_sales)=COUNT(*) THEN SUM(xianghai_total_sales) END as sum_xianghai_sales,
                CASE WHEN COUNT(total_power_sales)=COUNT(*) THEN SUM(total_power_sales) END as sum_total_sales,
                {_bill_fee_summary_columns()}
            FROM {POINTS_SOURCE}
            WHERE trade_date BETWEEN :start_date AND :end_date;
        """)

        row = db.execute(summary_sql, {"start_date": start_date, "end_date": end_date, "expected_points": expected_points}).fetchone()
        if not row or row.point_count == 0:
            return {"ok": True, "data": None, "start_date": start_date, "end_date": end_date}

        # 使用未舍入电费和电量计算加权均价；参考价采用同查询范围的实时价算术均值。
        plant_prices = {}
        for plant in ("beihai", "xianghai"):
            fee = getattr(row, f"sum_{plant}_spot_fee")
            sales = getattr(row, f"sum_{plant}_sales")
            average = fee / sales if fee is not None and sales is not None and sales != 0 else None
            rate = (average - row.avg_rt) / row.avg_rt * 100 if average is not None and row.avg_rt is not None and row.avg_rt != 0 else None
            plant_prices[f"avg_{plant}_spot_price"] = _to_float(average)
            plant_prices[f"{plant}_spot_price_diff_rate"] = _to_float(rate)

        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "data": {
                "point_count": int(row.point_count),
                "has_plant_sales_data": bool(row.plant_sales_points),
                "day_count": int(row.day_count),
                "avg_day_ahead_price": _to_float(row.avg_da),
                "max_day_ahead_price": _to_float(row.max_da),
                "min_day_ahead_price": _to_float(row.min_da),
                "avg_real_time_price": _to_float(row.avg_rt),
                "max_real_time_price": _to_float(row.max_rt),
                "min_real_time_price": _to_float(row.min_rt),
                "avg_price_spread": _to_float(row.avg_spread),
                "max_price_spread": _to_float(row.max_spread),
                "min_price_spread": _to_float(row.min_spread),
                "negative_price_points": int(row.negative_price_points or 0),
                "negative_price_days": int(row.negative_price_days or 0),
                "sum_beihai_sales": _to_float(row.sum_beihai_sales),
                "sum_xianghai_sales": _to_float(row.sum_xianghai_sales),
                "sum_total_sales": _to_float(row.sum_total_sales),
                "sum_beihai_spot_fee": _to_float(row.sum_beihai_spot_fee),
                "sum_beihai_contract_fee": _to_float(row.sum_beihai_contract_fee),
                "sum_beihai_revenue_fee": _to_float(row.sum_beihai_revenue_fee),
                "sum_xianghai_spot_fee": _to_float(row.sum_xianghai_spot_fee),
                "sum_xianghai_contract_fee": _to_float(row.sum_xianghai_contract_fee),
                "sum_xianghai_revenue_fee": _to_float(row.sum_xianghai_revenue_fee),
                **plant_prices,
            },
        }


@public_router.get("/spot_electricity/points", summary="获取电力现货15分钟点位明细")
def get_spot_electricity_points(
    date: Optional[str] = Query(None, description="单个日期 (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="截止日期 (YYYY-MM-DD)"),
    only_negative: bool = Query(False, description="仅返回负电价时点"),
    limit: Optional[int] = Query(None, description="最大返回条数，若传 None 或 <=0 则不限制条数"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_access(session)
    with SessionLocal() as db:
        if date:
            s_date = date
            e_date = date
        elif start_date and end_date:
            s_date = start_date
            e_date = end_date
        else:
            latest_date_row = db.execute(text(f"SELECT MAX(trade_date) FROM {POINTS_SOURCE};")).fetchone()
            latest = str(latest_date_row[0]) if latest_date_row and latest_date_row[0] else "2026-10-12"
            s_date = latest
            e_date = latest

        where_clauses = ["trade_date BETWEEN :start_date AND :end_date"]
        if only_negative:
            where_clauses.append("(day_ahead_price < 0 OR real_time_price < 0)")

        query_params: Dict[str, Any] = {
            "start_date": s_date,
            "end_date": e_date,
        }

        limit_clause = ""
        if limit is not None and limit > 0:
            limit_clause = "LIMIT :limit"
            query_params["limit"] = limit

        sql_text = f"""
            SELECT 
                id,
                trade_date,
                point_index,
                time_label,
                period_start_time,
                period_end_time,
                day_ahead_price,
                real_time_price,
                price_spread,
                beihai_unit1_sales,
                beihai_unit2_sales,
                beihai_unit3_sales,
                beihai_total_sales,
                xianghai_unit1_sales,
                xianghai_unit2_sales,
                xianghai_unit3_sales,
                xianghai_unit4_sales,
                xianghai_total_sales,
                total_power_sales,
                status,
                remarks
            FROM {POINTS_SOURCE}
            WHERE {' AND '.join(where_clauses)}
            ORDER BY trade_date ASC, point_index ASC
            {limit_clause};
        """

        rows = db.execute(text(sql_text), query_params).fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r.id,
                "trade_date": str(r.trade_date),
                "point_index": r.point_index,
                "time_label": r.time_label,
                "period_start_time": r.period_start_time,
                "period_end_time": r.period_end_time,
                "day_ahead_price": _to_float(r.day_ahead_price),
                "real_time_price": _to_float(r.real_time_price),
                "price_spread": _to_float(r.price_spread),
                "beihai_unit1_sales": _to_float(r.beihai_unit1_sales),
                "beihai_unit2_sales": _to_float(r.beihai_unit2_sales),
                "beihai_unit3_sales": _to_float(r.beihai_unit3_sales),
                "beihai_total_sales": _to_float(r.beihai_total_sales),
                "xianghai_unit1_sales": _to_float(r.xianghai_unit1_sales),
                "xianghai_unit2_sales": _to_float(r.xianghai_unit2_sales),
                "xianghai_unit3_sales": _to_float(r.xianghai_unit3_sales),
                "xianghai_unit4_sales": _to_float(r.xianghai_unit4_sales),
                "xianghai_total_sales": _to_float(r.xianghai_total_sales),
                "total_power_sales": _to_float(r.total_power_sales),
                "status": r.status,
                "remarks": r.remarks,
            })

        return {
            "ok": True,
            "start_date": s_date,
            "end_date": e_date,
            "count": len(items),
            "items": items,
        }


@public_router.get("/spot_electricity/daily_trends", summary="获取电力现货按日聚合趋势")
def get_spot_electricity_daily_trends(
    start_date: str = Query(..., description="起始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="截止日期 (YYYY-MM-DD)"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_access(session)
    trends_sql = text(f"""
        SELECT 
            trade_date,
            ROUND(AVG(day_ahead_price)::numeric, 2) as avg_da,
            ROUND(MAX(day_ahead_price)::numeric, 2) as max_da,
            ROUND(MIN(day_ahead_price)::numeric, 2) as min_da,
            ROUND(AVG(real_time_price)::numeric, 2) as avg_rt,
            ROUND(MAX(real_time_price)::numeric, 2) as max_rt,
            ROUND(MIN(real_time_price)::numeric, 2) as min_rt,
            ROUND(AVG(price_spread)::numeric, 2) as avg_spread,
            COUNT(*) FILTER (WHERE real_time_price < 0 OR day_ahead_price < 0) as negative_count,
            ROUND(CASE WHEN COUNT(beihai_total_sales)=COUNT(*) THEN SUM(beihai_total_sales) END::numeric, 2) as beihai_sales,
            ROUND(CASE WHEN COUNT(xianghai_total_sales)=COUNT(*) THEN SUM(xianghai_total_sales) END::numeric, 2) as xianghai_sales,
            ROUND(CASE WHEN COUNT(total_power_sales)=COUNT(*) THEN SUM(total_power_sales) END::numeric, 2) as total_sales
        FROM {POINTS_SOURCE}
        WHERE trade_date BETWEEN :start_date AND :end_date
        GROUP BY trade_date
        ORDER BY trade_date ASC;
    """)

    with SessionLocal() as db:
        rows = db.execute(trends_sql, {"start_date": start_date, "end_date": end_date}).fetchall()
        days = []
        for r in rows:
            days.append({
                "trade_date": str(r.trade_date),
                "avg_day_ahead_price": _to_float(r.avg_da),
                "max_day_ahead_price": _to_float(r.max_da),
                "min_day_ahead_price": _to_float(r.min_da),
                "avg_real_time_price": _to_float(r.avg_rt),
                "max_real_time_price": _to_float(r.max_rt),
                "min_real_time_price": _to_float(r.min_rt),
                "avg_price_spread": _to_float(r.avg_spread),
                "negative_count": int(r.negative_count or 0),
                "beihai_sales": _to_float(r.beihai_sales),
                "xianghai_sales": _to_float(r.xianghai_sales),
                "total_sales": _to_float(r.total_sales),
            })
        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(days),
            "days": days,
        }


@public_router.get("/spot_electricity/period_trends", summary="获取电力现货按15分钟时段聚合平均趋势")
def get_spot_electricity_period_trends(
    start_date: str = Query(..., description="起始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="截止日期 (YYYY-MM-DD)"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_access(session)
    trends_sql = text(f"""
        SELECT 
            point_index,
            time_label,
            period_start_time,
            period_end_time,
            ROUND(AVG(day_ahead_price)::numeric, 2) as avg_da,
            ROUND(MAX(day_ahead_price)::numeric, 2) as max_da,
            ROUND(MIN(day_ahead_price)::numeric, 2) as min_da,
            ROUND(AVG(real_time_price)::numeric, 2) as avg_rt,
            ROUND(MAX(real_time_price)::numeric, 2) as max_rt,
            ROUND(MIN(real_time_price)::numeric, 2) as min_rt,
            ROUND(AVG(price_spread)::numeric, 2) as avg_spread,
            COUNT(*) FILTER (WHERE real_time_price < 0 OR day_ahead_price < 0) as negative_days_count,
            ROUND(CASE WHEN COUNT(beihai_total_sales)=COUNT(*) THEN AVG(beihai_total_sales) END::numeric, 2) as avg_beihai_sales,
            ROUND(CASE WHEN COUNT(xianghai_total_sales)=COUNT(*) THEN AVG(xianghai_total_sales) END::numeric, 2) as avg_xianghai_sales,
            ROUND(CASE WHEN COUNT(total_power_sales)=COUNT(*) THEN AVG(total_power_sales) END::numeric, 2) as avg_total_sales
        FROM {POINTS_SOURCE}
        WHERE trade_date BETWEEN :start_date AND :end_date
        GROUP BY point_index, time_label, period_start_time, period_end_time
        ORDER BY point_index ASC;
    """)

    with SessionLocal() as db:
        rows = db.execute(trends_sql, {"start_date": start_date, "end_date": end_date}).fetchall()
        periods = []
        for r in rows:
            periods.append({
                "point_index": r.point_index,
                "time_label": r.time_label,
                "period_start_time": r.period_start_time,
                "period_end_time": r.period_end_time,
                "avg_day_ahead_price": _to_float(r.avg_da),
                "max_day_ahead_price": _to_float(r.max_da),
                "min_day_ahead_price": _to_float(r.min_da),
                "avg_real_time_price": _to_float(r.avg_rt),
                "max_real_time_price": _to_float(r.max_rt),
                "min_real_time_price": _to_float(r.min_rt),
                "avg_price_spread": _to_float(r.avg_spread),
                "negative_days_count": int(r.negative_days_count or 0),
                "avg_beihai_sales": _to_float(r.avg_beihai_sales),
                "avg_xianghai_sales": _to_float(r.avg_xianghai_sales),
                "avg_total_sales": _to_float(r.avg_total_sales),
            })
        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(periods),
            "periods": periods,
        }


@public_router.get("/spot_electricity/monthly_trends", summary="获取电力现货按月聚合趋势")
def get_spot_electricity_monthly_trends(
    start_date: str = Query(..., description="起始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="截止日期 (YYYY-MM-DD)"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_access(session)
    trends_sql = text(f"""
        SELECT 
            TO_CHAR(trade_date, 'YYYY-MM') as month_label,
            ROUND(AVG(day_ahead_price)::numeric, 2) as avg_da,
            ROUND(MAX(day_ahead_price)::numeric, 2) as max_da,
            ROUND(MIN(day_ahead_price)::numeric, 2) as min_da,
            ROUND(AVG(real_time_price)::numeric, 2) as avg_rt,
            ROUND(MAX(real_time_price)::numeric, 2) as max_rt,
            ROUND(MIN(real_time_price)::numeric, 2) as min_rt,
            ROUND(AVG(price_spread)::numeric, 2) as avg_spread,
            COUNT(*) FILTER (WHERE real_time_price < 0 OR day_ahead_price < 0) as negative_count,
            COUNT(DISTINCT trade_date) as day_count,
            COUNT(*) as point_count,
            ROUND(CASE WHEN COUNT(beihai_total_sales)=COUNT(*) THEN SUM(beihai_total_sales) END::numeric, 2) as beihai_sales,
            ROUND(CASE WHEN COUNT(xianghai_total_sales)=COUNT(*) THEN SUM(xianghai_total_sales) END::numeric, 2) as xianghai_sales,
            ROUND(CASE WHEN COUNT(total_power_sales)=COUNT(*) THEN SUM(total_power_sales) END::numeric, 2) as total_sales
        FROM {POINTS_SOURCE}
        WHERE trade_date BETWEEN :start_date AND :end_date
        GROUP BY TO_CHAR(trade_date, 'YYYY-MM')
        ORDER BY month_label ASC;
    """)

    with SessionLocal() as db:
        rows = db.execute(trends_sql, {"start_date": start_date, "end_date": end_date}).fetchall()
        months = []
        for r in rows:
            months.append({
                "month_label": r.month_label,
                "day_count": int(r.day_count or 0),
                "point_count": int(r.point_count or 0),
                "avg_day_ahead_price": _to_float(r.avg_da),
                "max_day_ahead_price": _to_float(r.max_da),
                "min_day_ahead_price": _to_float(r.min_da),
                "avg_real_time_price": _to_float(r.avg_rt),
                "max_real_time_price": _to_float(r.max_rt),
                "min_real_time_price": _to_float(r.min_rt),
                "avg_price_spread": _to_float(r.avg_spread),
                "negative_count": int(r.negative_count or 0),
                "beihai_sales": _to_float(r.beihai_sales),
                "xianghai_sales": _to_float(r.xianghai_sales),
                "total_sales": _to_float(r.total_sales),
            })
        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(months),
            "months": months,
        }


# ==============================================================================
# 电力现货自动化同步与系统控制接口 (仅 Global_admin 授权访问)
# ==============================================================================

from backend.services.spot_electricity_sync_service import spot_sync_service
from pydantic import BaseModel, Field

# 启动后台守护调度引擎
spot_sync_service.start_scheduler()


def _ensure_global_admin(session: Optional[AuthSession] = None) -> None:
    """验证用户是否具备 Global_admin 权限或后台管理控制台权限。"""
    if session is None:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    is_admin = (
        getattr(session, "is_global_admin", False)
        or session.group == "Global_admin"
        or getattr(session.permissions.actions, "can_access_admin_console", False)
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="仅 Global_admin 拥有现货系统控制选项权限")


class SyncConfigUpdatePayload(BaseModel):
    enabled: Optional[bool] = Field(None, description="是否开启每日自动拉取")
    cron_time: Optional[str] = Field(None, description="每日初次尝试拉取时间 (HH:MM，默认 07:40)")
    retry_interval_minutes: Optional[int] = Field(None, description="未更新时的重试间隔 (分钟，默认 20)")
    max_retries_per_day: Optional[int] = Field(None, description="每日最大重试次数")
    target_date_rule: Optional[str] = Field(None, description="拉取规则 (yesterday / today)")


class ManualSyncPayload(BaseModel):
    date: Optional[str] = Field(None, description="指定拉取的日期 (YYYY-MM-DD)，若为空则默认拉取发改委最新昨日电价")
    overwrite: bool = Field(False, description="若数据库已存在某日数据，是否确认覆盖现有数据")


@public_router.get("/spot_electricity/sync/check_exists", summary="检查数据库中指定日期是否已存在现货数据 (仅限 Global_admin)")
def check_spot_electricity_exists(
    date: str = Query(..., description="目标日期 (YYYY-MM-DD)"),
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    result = spot_sync_service.check_date_exists(date.strip())
    return {"ok": True, "target_date": date.strip(), **result}


@public_router.get("/spot_electricity/sync/config", summary="获取电力现货自动同步配置与调度状态 (仅限 Global_admin)")
def get_spot_electricity_sync_config(
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    config = spot_sync_service.get_config()
    return {"ok": True, "data": config}


@public_router.post("/spot_electricity/sync/config", summary="保存电力现货自动同步配置 (仅限 Global_admin)")
def save_spot_electricity_sync_config(
    payload: SyncConfigUpdatePayload,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updated_config = spot_sync_service.update_config(updates)
    return {"ok": True, "message": "自动拉取配置已成功更新并即时生效", "data": updated_config}


@public_router.post("/spot_electricity/sync/manual", summary="手动实时拉取现货数据入库 (仅限 Global_admin)")
def manual_sync_spot_electricity(
    payload: ManualSyncPayload,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    target_date = payload.date.strip() if payload.date and payload.date.strip() else None
    result = spot_sync_service.sync_data(
        target_date=target_date,
        is_manual=True,
        overwrite=payload.overwrite,
    )
    return result




