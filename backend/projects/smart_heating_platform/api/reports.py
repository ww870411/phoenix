# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 阳面逐小时与每日精算报表 API
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import EAST_8
from backend.projects.smart_heating_platform.services.collector_engine import (
    run_merchant_daily_cycle,
    run_merchant_hourly_backfill,
    run_snapshot_cycle,
    run_table_bottom_calibration,
)
from backend.projects.smart_heating_platform.services.report_query_service import (
    build_daily_excel,
    build_hourly_excel,
    get_daily_report,
    get_hourly_report,
    get_station_temp_devices,
    get_upstream_point_24h,
)
from backend.services.auth_manager import AuthSession, get_current_session

router = APIRouter(prefix="/reports", tags=["smart_heating_platform_reports"])


def _require_admin(session: AuthSession) -> None:
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 访问")


class ManualCollectRequest(BaseModel):
    """手动触发采集/校准请求体。"""

    action: str = Field("snapshot", description="snapshot | calib | merchant")
    include_jumin: Optional[bool] = Field(True, description="快照采集时是否顺带采集 /jumin/")
    target_date: Optional[str] = Field(None, description="表底校准或商户日报的目标日期 YYYY-MM-DD")
    station_names: Optional[List[str]] = Field(None, description="可选：指定部分站点名称校准（不传则全量242站）")


@router.get("/hourly", summary="获取逐小时精细化运行报告")
def api_hourly_report(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时 0~23"),
    mode: str = Query("clean", description="数据口径: clean | raw"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    data = get_hourly_report(target_date_str=date, hour=hour, mode=mode)
    return {"ok": True, "data": data}


@router.get("/hourly/upstream-trend", summary="获取单个上游测点当日24小时趋势")
def api_upstream_trend(
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    data_zone: str = Query(..., description="后端内存数据区"),
    source_name: str = Query(..., description="源系统采集名称"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    rows = get_upstream_point_24h(date, data_zone, source_name)
    return {"ok": True, "data": rows}


@router.get("/hourly/station-temps", summary="下钻查看单个换热站下属居民室温明细")
def api_station_temps(
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    hour: int = Query(..., ge=0, le=23, description="小时 0~23"),
    station_id: str = Query(..., description="换热站主键ID"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    rows = get_station_temp_devices(date, hour, station_id)
    return {"ok": True, "data": rows}


@router.get("/hourly/export", summary="导出逐小时精细化运行报告 Excel")
def api_export_hourly(
    date: Optional[str] = Query(None),
    hour: Optional[int] = Query(None, ge=0, le=23),
    mode: str = Query("clean"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    report_data = get_hourly_report(target_date_str=date, hour=hour, mode=mode)
    excel_bytes = build_hourly_excel(report_data)
    filename = f"逐小时精细化运行报告_{report_data['meta']['date']}_{report_data['meta']['hour']:02d}时.xlsx"
    encoded = quote(filename)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/daily", summary="获取每日生产精算日报与手工日报双轨核对")
def api_daily_report(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    period_mode: str = Query("natural", description="natural (00:00~24:00) | shift (08:00~08:00)"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    data = get_daily_report(target_date_str=date, period_mode=period_mode)
    return {"ok": True, "data": data}


@router.get("/daily/export", summary="导出每日生产精算日报与双轨核对 Excel")
def api_export_daily(
    date: Optional[str] = Query(None),
    period_mode: str = Query("natural"),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    report_data = get_daily_report(target_date_str=date, period_mode=period_mode)
    excel_bytes = build_daily_excel(report_data)
    filename = f"每日生产精算日报_{report_data['meta']['date']}.xlsx"
    encoded = quote(filename)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.post("/collect-now", summary="手动触发一次实时快照/表底校准/商户采集")
def api_collect_now(
    payload: ManualCollectRequest = Body(default_factory=ManualCollectRequest),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    action = str(payload.action or "snapshot").lower()
    try:
        if action == "calib":
            res = run_table_bottom_calibration(
                target_date_str=payload.target_date,
                station_names=payload.station_names,
                trigger="MANUAL",
            )
        elif action == "merchant":
            res = run_merchant_daily_cycle(target_date_str=payload.target_date, trigger="MANUAL")
        elif action == "merchant_hourly_backfill":
            res = run_merchant_hourly_backfill(
                target_date_str=payload.target_date,
                merchant_names=payload.station_names,
                trigger="MANUAL",
            )
        else:
            res = run_snapshot_cycle(include_jumin=payload.include_jumin, trigger="MANUAL")
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"采集执行失败: {exc}") from exc


@router.get("/runs", summary="查询最近采集运行记录")
def api_collector_runs(
    limit: int = Query(20, ge=1, le=100),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT run_id, biz_hour, run_type, source_mode, started_at, finished_at, "
                "duration_ms, status, cookie_valid, summary_json, error_message "
                "FROM smart_heating_platform.fact_collector_run "
                "ORDER BY run_id DESC LIMIT :lim"
            ),
            {"lim": limit},
        ).fetchall()
    return {
        "ok": True,
        "data": [
            {
                "run_id": r.run_id,
                "biz_hour": r.biz_hour.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M"),
                "run_type": r.run_type,
                "source_mode": r.source_mode,
                "started_at": r.started_at.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S") if r.started_at else None,
                "finished_at": r.finished_at.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S") if r.finished_at else None,
                "duration_ms": r.duration_ms,
                "status": r.status,
                "cookie_valid": r.cookie_valid,
                "summary": r.summary_json,
                "error_message": r.error_message,
            }
            for r in rows
        ],
    }
