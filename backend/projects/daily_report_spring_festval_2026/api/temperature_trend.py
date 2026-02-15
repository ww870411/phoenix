# -*- coding: utf-8 -*-
"""
春节看板气温趋势轻量接口。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.dashboard_expression import load_default_push_date

public_router = APIRouter(tags=["spring_festival"])


def _parse_iso_date(value: str) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _shift_year_safe(target: date, years: int) -> date:
    try:
        return target.replace(year=target.year + years)
    except ValueError:
        fallback = target.replace(year=target.year + years, month=3, day=1)
        return fallback - timedelta(days=1)


def _query_temperature_daily_avg_map(db_session, start_date: date, end_date: date) -> Dict[str, Optional[float]]:
    if start_date > end_date:
        return {}
    calc_stmt = text(
        """
        SELECT date, aver_temp
          FROM calc_temperature_data
         WHERE date BETWEEN :start_date AND :end_date
         ORDER BY date
        """,
    )
    rows = db_session.execute(
        calc_stmt,
        {"start_date": start_date, "end_date": end_date},
    ).all()

    # 兜底：当 calc_temperature_data 为空或未刷新时，直接从 temperature_data 按日聚合
    if not rows:
        raw_stmt = text(
            """
            SELECT CAST(date_time AS DATE) AS day_date, AVG(value) AS aver_temp
              FROM temperature_data
             WHERE CAST(date_time AS DATE) BETWEEN :start_date AND :end_date
             GROUP BY CAST(date_time AS DATE)
             ORDER BY day_date
            """,
        )
        rows = db_session.execute(
            raw_stmt,
            {"start_date": start_date, "end_date": end_date},
        ).all()

    result: Dict[str, Optional[float]] = {}
    for row_date, avg_temp in rows:
        if row_date is None:
            continue
        cast_date = row_date if isinstance(row_date, date) else _parse_iso_date(str(row_date))
        if cast_date is None:
            continue
        if avg_temp is None:
            result[cast_date.isoformat()] = None
            continue
        try:
            result[cast_date.isoformat()] = float(avg_temp)
        except (TypeError, ValueError):
            result[cast_date.isoformat()] = None
    return result


@public_router.get(
    "/spring-dashboard/temperature/trend",
    summary="获取春节看板轻量气温趋势数据（本期/同期）",
)
def get_spring_dashboard_temperature_trend(
    show_date: str = Query(
        default="",
        description="锚点日期，格式 YYYY-MM-DD；为空时使用 set_biz_date",
    ),
    start_date: str = Query(
        default="",
        description="本期起始日期（可选），格式 YYYY-MM-DD",
    ),
    end_date: str = Query(
        default="",
        description="本期结束日期（可选），格式 YYYY-MM-DD",
    ),
):
    anchor = _parse_iso_date(show_date) or _parse_iso_date(load_default_push_date())
    if anchor is None:
        raise HTTPException(status_code=400, detail="无效的 show_date，无法解析锚点日期。")

    parsed_start = _parse_iso_date(start_date)
    parsed_end = _parse_iso_date(end_date)
    current_start = parsed_start or (anchor - timedelta(days=120))
    current_end = parsed_end or (anchor + timedelta(days=7))
    if current_start > current_end:
        raise HTTPException(status_code=400, detail="start_date 不能晚于 end_date。")

    peer_start = _shift_year_safe(current_start, -1)
    peer_end = _shift_year_safe(current_end, -1)

    db_session = SessionLocal()
    try:
        main = _query_temperature_daily_avg_map(db_session, current_start, current_end)
        peer = _query_temperature_daily_avg_map(db_session, peer_start, peer_end)
    finally:
        db_session.close()

    return {
        "ok": True,
        "show_date": anchor.isoformat(),
        "start_date": current_start.isoformat(),
        "end_date": current_end.isoformat(),
        "main": main,
        "peer": peer,
    }
