# -*- coding: utf-8 -*-
"""daily_report_25_26 数据看板相关接口。"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services import dashboard_cache
from backend.services.auth_manager import EAST_8, AuthSession, get_current_session
from backend.services.dashboard_cache_job import cache_publish_job_manager
from backend.services.dashboard_expression import evaluate_dashboard, load_default_push_date
from backend.services.weather_importer import (
    WeatherImporterError,
    compare_with_existing,
    fetch_hourly_temperatures,
    persist_hourly_temperatures,
)


PROJECT_KEY = "daily_report_25_26"
router = APIRouter()
public_router = APIRouter()


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
    stmt = text(
        """
        SELECT date, aver_temp
          FROM calc_temperature_data
         WHERE date BETWEEN :start_date AND :end_date
         ORDER BY date
        """,
    )
    rows = db_session.execute(
        stmt,
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


def _ensure_cache_operator(session: AuthSession) -> None:
    action_flags = session.get_project_action_flags(PROJECT_KEY)
    can_publish = getattr(action_flags, "can_publish", False)
    if not can_publish:
        raise HTTPException(status_code=403, detail="当前账号无权操作数据看板缓存。")


def _build_dashboard_payload(result) -> Dict[str, Any]:
    base = result.to_dict()
    payload = {"ok": True}
    payload.update(base)
    return payload


def _attach_cache_metadata(
    payload: Dict[str, Any],
    cache_status: Dict[str, Any],
    cache_hit: bool,
    cache_key: str,
) -> Dict[str, Any]:
    enriched = copy.deepcopy(payload)
    enriched["cache_hit"] = cache_hit
    enriched["cache_disabled"] = cache_status.get("disabled", False)
    enriched["cache_dates"] = cache_status.get("available_dates", [])
    enriched["cache_updated_at"] = cache_status.get("updated_at")
    enriched["cache_key"] = cache_key
    return enriched


@public_router.get(
    "/dashboard",
    summary="获取数据看板配置数据",
    tags=["daily_report_25_26"],
)
def get_dashboard_data(
    show_date: str = Query(
        default="",
        description="展示日期，格式为 YYYY-MM-DD；留空时返回默认配置",
    ),
):
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    cached_payload, cache_status = dashboard_cache.get_cached_payload(PROJECT_KEY, cache_key)
    if cached_payload is not None:
        return _attach_cache_metadata(cached_payload, cache_status, cache_hit=True, cache_key=cache_key)

    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = _build_dashboard_payload(result)
    if cache_status.get("disabled"):
        return _attach_cache_metadata(payload, cache_status, cache_hit=False, cache_key=cache_key)
    cache_status = dashboard_cache.update_cache_entry(PROJECT_KEY, cache_key, payload)
    return _attach_cache_metadata(payload, cache_status, cache_hit=False, cache_key=cache_key)


@public_router.get(
    "/dashboard/date",
    summary="获取当前 set_biz_date",
    tags=["daily_report_25_26"],
)
def get_dashboard_date():
    return {
        "ok": True,
        "set_biz_date": load_default_push_date(),
    }


@public_router.get(
    "/dashboard/temperature/trend",
    summary="获取轻量气温趋势数据（本期/同期）",
    tags=["daily_report_25_26"],
)
def get_dashboard_temperature_trend(
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


@router.post(
    "/dashboard/cache/publish",
    summary="批量发布数据看板缓存（默认最近 7 日，可按 days 指定）",
    tags=["daily_report_25_26"],
)
def publish_dashboard_cache(
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30, description="发布窗口天数（含 set_biz_date 当天）"),
):
    _ensure_cache_operator(session)
    target_dates = list(reversed(dashboard_cache.default_publish_dates(window=days, project_key=PROJECT_KEY)))
    schedule = target_dates
    snapshot, started = cache_publish_job_manager.start(PROJECT_KEY, schedule)
    return {
        "ok": True,
        "started": started,
        "days": days,
        "job": snapshot,
    }


@router.delete(
    "/dashboard/cache",
    summary="禁用并清空数据看板缓存",
    tags=["daily_report_25_26"],
)
def disable_dashboard_cache_endpoint(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    status = dashboard_cache.disable_cache(PROJECT_KEY)
    return {
        "ok": True,
        "cache_disabled": status.get("disabled", True),
        "cache_updated_at": status.get("updated_at"),
    }


@router.post(
    "/dashboard/temperature/import",
    summary="获取 Open-Meteo 气温数据（仅预览，不写库）",
    tags=["daily_report_25_26"],
)
def import_dashboard_temperature(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    db_session = SessionLocal()
    try:
        result = fetch_hourly_temperatures()
        tz_name = (result.get("source") or {}).get("timezone")
        compare_result = compare_with_existing(db_session, result.get("hourly", []), tz_name)
    except WeatherImporterError as exc:
        db_session.close()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        db_session.close()
    fetched_at = datetime.now(tz=EAST_8).isoformat()
    return {
        "ok": True,
        "fetched_at": fetched_at,
        "source": result.get("source"),
        "summary": result.get("summary"),
        "dates": result.get("dates", []),
        "hourly": result.get("hourly", []),
        "overlap": compare_result.get("overlap"),
        "differences": compare_result.get("differences", []),
        "overlap_records": compare_result.get("overlap_records", []),
    }


@router.post(
    "/dashboard/temperature/import/commit",
    summary="获取 Open-Meteo 气温数据并写入 temperature_data（覆盖同一时间段）",
    tags=["daily_report_25_26"],
)
def commit_dashboard_temperature(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    db_session = SessionLocal()
    try:
        result = fetch_hourly_temperatures()
        tz_name = (result.get("source") or {}).get("timezone")
        persist_result = persist_hourly_temperatures(db_session, result.get("hourly", []), tz_name)
    except WeatherImporterError as exc:
        db_session.close()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db_session.rollback()
        db_session.close()
        raise
    fetched_at = datetime.now(tz=EAST_8).isoformat()
    db_session.close()
    return {
        "ok": True,
        "fetched_at": fetched_at,
        "source": result.get("source"),
        "summary": result.get("summary"),
        "dates": result.get("dates", []),
        "write_result": persist_result,
    }


@router.get(
    "/dashboard/cache/publish/status",
    summary="查询缓存发布任务状态",
    tags=["daily_report_25_26"],
)
def get_cache_publish_status():
    snapshot = cache_publish_job_manager.snapshot()
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/publish/cancel",
    summary="停止正在运行的缓存发布任务",
    tags=["daily_report_25_26"],
)
def cancel_cache_publish(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    snapshot = cache_publish_job_manager.request_cancel()
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/refresh",
    summary="刷新指定日期的数据看板缓存",
    tags=["daily_report_25_26"],
)
def refresh_dashboard_cache(
    show_date: str = Query(
        default="",
        description="目标展示日期，格式 YYYY-MM-DD；留空刷新默认缓存",
    ),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = _build_dashboard_payload(result)
    status = dashboard_cache.update_cache_entry(PROJECT_KEY, cache_key, payload)
    return {
        "ok": True,
        "cached_key": cache_key,
        "cache_disabled": status.get("disabled", False),
        "cache_updated_at": status.get("updated_at"),
    }
