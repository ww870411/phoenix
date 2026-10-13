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


@public_router.get("/spot_electricity/meta", summary="获取电力现货数据元信息")
def get_spot_electricity_meta(session: Optional[AuthSession] = Depends(get_current_session_optional)) -> Dict[str, Any]:
    _ensure_access(session)
    query = text("""
        SELECT 
            MIN(trade_date) as min_date,
            MAX(trade_date) as max_date,
            COUNT(DISTINCT trade_date) as total_days,
            COUNT(*) as total_points
        FROM public.spot_electricity_15min_data;
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
            latest_date_row = db.execute(text("SELECT MAX(trade_date) FROM public.spot_electricity_15min_data;")).fetchone()
            latest = str(latest_date_row[0]) if latest_date_row and latest_date_row[0] else "2026-10-12"
            start_date = start_date or latest
            end_date = end_date or latest

        summary_sql = text("""
            SELECT 
                COUNT(*) as point_count,
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
                SUM(beihai_total_sales) as sum_beihai_sales,
                SUM(xianghai_total_sales) as sum_xianghai_sales,
                SUM(province_total_sales) as sum_province_sales,
                SUM(total_power_sales) as sum_total_sales,
                SUM(estimated_revenue) as sum_revenue
            FROM public.spot_electricity_15min_data
            WHERE trade_date BETWEEN :start_date AND :end_date;
        """)

        row = db.execute(summary_sql, {"start_date": start_date, "end_date": end_date}).fetchone()
        if not row or row.point_count == 0:
            return {"ok": True, "data": None, "start_date": start_date, "end_date": end_date}

        return {
            "ok": True,
            "start_date": start_date,
            "end_date": end_date,
            "data": {
                "point_count": int(row.point_count),
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
                "sum_province_sales": _to_float(row.sum_province_sales),
                "sum_total_sales": _to_float(row.sum_total_sales),
                "sum_estimated_revenue": _to_float(row.sum_revenue),
            },
        }


@public_router.get("/spot_electricity/points", summary="获取电力现货15分钟点位明细")
def get_spot_electricity_points(
    date: Optional[str] = Query(None, description="单个日期 (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="截止日期 (YYYY-MM-DD)"),
    only_negative: bool = Query(False, description="仅返回负电价时点"),
    limit: int = Query(5000, description="最大返回条数"),
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
            latest_date_row = db.execute(text("SELECT MAX(trade_date) FROM public.spot_electricity_15min_data;")).fetchone()
            latest = str(latest_date_row[0]) if latest_date_row and latest_date_row[0] else "2026-10-12"
            s_date = latest
            e_date = latest

        where_clauses = ["trade_date BETWEEN :start_date AND :end_date"]
        if only_negative:
            where_clauses.append("(day_ahead_price < 0 OR real_time_price < 0)")

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
                province_total_sales,
                total_power_sales,
                estimated_revenue,
                status,
                remarks
            FROM public.spot_electricity_15min_data
            WHERE {' AND '.join(where_clauses)}
            ORDER BY trade_date ASC, point_index ASC
            LIMIT :limit;
        """

        rows = db.execute(text(sql_text), {
            "start_date": s_date,
            "end_date": e_date,
            "limit": limit,
        }).fetchall()

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
                "province_total_sales": _to_float(r.province_total_sales),
                "total_power_sales": _to_float(r.total_power_sales),
                "estimated_revenue": _to_float(r.estimated_revenue),
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
    trends_sql = text("""
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
            ROUND(COALESCE(SUM(beihai_total_sales), 0)::numeric, 2) as beihai_sales,
            ROUND(COALESCE(SUM(xianghai_total_sales), 0)::numeric, 2) as xianghai_sales,
            ROUND(COALESCE(SUM(province_total_sales), 0)::numeric, 2) as province_sales,
            ROUND(COALESCE(SUM(total_power_sales), 0)::numeric, 2) as total_sales
        FROM public.spot_electricity_15min_data
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
                "province_sales": _to_float(r.province_sales),
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
    trends_sql = text("""
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
            ROUND(COALESCE(AVG(beihai_total_sales), 0)::numeric, 2) as avg_beihai_sales,
            ROUND(COALESCE(AVG(xianghai_total_sales), 0)::numeric, 2) as avg_xianghai_sales,
            ROUND(COALESCE(AVG(province_total_sales), 0)::numeric, 2) as avg_province_sales,
            ROUND(COALESCE(AVG(total_power_sales), 0)::numeric, 2) as avg_total_sales
        FROM public.spot_electricity_15min_data
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
                "avg_province_sales": _to_float(r.avg_province_sales),
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
    trends_sql = text("""
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
            ROUND(COALESCE(SUM(beihai_total_sales), 0)::numeric, 2) as beihai_sales,
            ROUND(COALESCE(SUM(xianghai_total_sales), 0)::numeric, 2) as xianghai_sales,
            ROUND(COALESCE(SUM(province_total_sales), 0)::numeric, 2) as province_sales,
            ROUND(COALESCE(SUM(total_power_sales), 0)::numeric, 2) as total_sales
        FROM public.spot_electricity_15min_data
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
                "province_sales": _to_float(r.province_sales),
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




