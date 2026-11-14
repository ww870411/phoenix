# -*- coding: utf-8 -*-
"""daily_report_25_26 数据看板相关接口。"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.daily_report_25_26.services.audit_log_service import (
    log_session_operation,
)
from backend.services import dashboard_cache
from backend.services.auth_manager import EAST_8, AuthSession, get_current_session, get_current_session_optional
from backend.services.dashboard_cache_job import cache_publish_job_manager
from backend.services.dashboard_expression import evaluate_dashboard, load_default_push_date, normalize_show_date
from backend.services.ensemble_weather_service import (
    EnsembleWeatherError,
    load_ensemble_weather_import_config,
    save_ensemble_weather_import_config,
)
from backend.services.weather_auto_import_service import (
    ensemble_weather_auto_import_service,
    weather_auto_import_service,
)
from backend.services.weather_importer import (
    WeatherImporterError,
    compare_with_existing,
    fetch_hourly_temperatures,
    persist_hourly_temperatures,
    load_weather_import_config,
    save_weather_import_config,
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
    try:
        from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
        return DailyDashboardEngine(db_session).get_temperature_daily_avg_map(start_date, end_date)
    except Exception:
        pass
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
    is_global_admin = (
        session.group == "Global_admin"
        or bool(getattr(session.permissions.actions, "can_access_admin_console", False))
    )
    if not is_global_admin:
        raise HTTPException(status_code=403, detail="仅系统超级管理员（Global_admin）可操作数据看板缓存。")


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
    # 默认展示日也按真实日期命中手动生成的缓存。
    show_date = normalize_show_date(show_date) or load_default_push_date(PROJECT_KEY)
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    cached_payload, cache_status = dashboard_cache.get_cached_payload(PROJECT_KEY, cache_key)
    if cached_payload is not None:
        return _attach_cache_metadata(cached_payload, cache_status, cache_hit=True, cache_key=cache_key)

    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = _build_dashboard_payload(result)
    # 查询不写缓存，避免已清除的日期因查看看板而重新生成。
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


class DashboardDateRequest(BaseModel):
    set_biz_date: Optional[str] = Field(default=None, description="业务基准日期，格式 YYYY-MM-DD")
    biz_date: Optional[str] = Field(default=None, description="业务基准日期别名，格式 YYYY-MM-DD")

    def get_target_date(self) -> str:
        target = self.set_biz_date or self.biz_date
        if not target:
            raise ValueError("必须提供 set_biz_date 或 biz_date")
        return target


@public_router.post(
    "/dashboard/date",
    summary="设置当前全局基准业务日期 set_biz_date",
    tags=["daily_report_25_26"],
)
def update_dashboard_date(
    payload: DashboardDateRequest,
    request: Request,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
):
    from backend.services import heating_season_service
    try:
        target_date = payload.get_target_date()
        res = heating_season_service.set_business_date(PROJECT_KEY, target_date)
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            f"更新全局基准业务日期为【{target_date}】",
            request=request,
            resource_id=f"biz_date:{target_date}",
            after_value={"set_biz_date": target_date},
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存业务日期失败: {exc}") from exc


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


@public_router.get(
    "/dashboard/network_water_dumbbell",
    summary="获取各单位热网耗水量哑铃图数据（当日/本月/供暖期）",
    tags=["daily_report_25_26"],
)
def get_dashboard_network_water_dumbbell(
    show_date: str = Query(
        default="",
        description="展示日期，格式为 YYYY-MM-DD；留空时自动回退至全局基准日期",
    ),
):
    from backend.projects.daily_report_25_26.services.network_water_service import (
        get_network_water_dumbbell,
    )
    return get_network_water_dumbbell(PROJECT_KEY, show_date=show_date)


@router.post(
    "/dashboard/cache/publish",
    summary="按日期区间生成看板缓存（保留区间外缓存）",
    tags=["daily_report_25_26"],
)
def publish_dashboard_cache(
    request: Request,
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30, description="发布窗口天数（含 set_biz_date 当天）"),
    preset: str | None = Query(default=None, description="缓存发布预设档位"),
    start_date: str | None = Query(default=None, description="缓存开始日期，含当天"),
    end_date: str | None = Query(default=None, description="缓存结束日期，含当天"),
):
    _ensure_cache_operator(session)
    try:
        target_dates, selection_label = dashboard_cache.resolve_publish_schedule(
            window=days,
            project_key=PROJECT_KEY,
            preset=preset,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    schedule = list(reversed(target_dates))
    snapshot, started = cache_publish_job_manager.start(PROJECT_KEY, schedule)
    log_session_operation(
        session,
        "UPDATE_CONFIG",
        f"发起数据看板缓存生成任务（范围：{selection_label or f'{len(target_dates)}天'}）",
        request=request,
        resource_id="dashboard_cache:publish",
        after_value={"days": len(target_dates), "preset": preset, "selection_label": selection_label},
    )
    return {
        "ok": True,
        "started": started,
        "days": len(target_dates),
        "preset": preset,
        "selection_label": selection_label,
        "job": snapshot,
    }


@router.get("/dashboard/cache/status", summary="查询已有缓存日期和发布任务")
def get_dashboard_cache_inventory(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    from backend.services.heating_season_service import get_season_config
    cfg = get_season_config(PROJECT_KEY)
    return {"ok": True, **dashboard_cache.get_cache_status(PROJECT_KEY), "job": cache_publish_job_manager.snapshot(PROJECT_KEY), "default_range": {"start_date": cfg["start_date"], "end_date": cfg["end_date"]}}


@router.delete("/dashboard/cache/range", summary="只清除指定日期区间的缓存")
def delete_dashboard_cache_range(
    request: Request,
    start_date: str = Query(...),
    end_date: str = Query(...),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    if cache_publish_job_manager.snapshot(PROJECT_KEY).get("status") == "running":
        raise HTTPException(status_code=409, detail="缓存生成任务正在运行，请先停止任务再清除")
    try:
        status = dashboard_cache.delete_cache_range(PROJECT_KEY, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_session_operation(
        session,
        "UPDATE_CONFIG",
        f"清除数据看板指定区间缓存（{start_date} ~ {end_date}）",
        request=request,
        resource_id=f"dashboard_cache:{start_date}_{end_date}",
    )
    return {"ok": True, **status}


@router.delete(
    "/dashboard/cache",
    summary="禁用数据看板缓存（保留历史文件）",
    tags=["daily_report_25_26"],
)
def disable_dashboard_cache_endpoint(
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    status = dashboard_cache.disable_cache(PROJECT_KEY)
    log_session_operation(
        session,
        "UPDATE_CONFIG",
        "禁用数据看板缓存模式",
        request=request,
        resource_id="dashboard_cache:disable",
    )
    return {
        "ok": True,
        "cache_disabled": status.get("disabled", True),
        "cache_updated_at": status.get("updated_at"),
    }


class WeatherImportConfigPayload(BaseModel):
    """全局管理中心维护的逐小时气温来源。"""

    api_url: str


class WeatherAutoImportConfigPayload(BaseModel):
    """全局管理中心维护的气温自动定时获取配置。"""

    enabled: bool = Field(default=True, description="是否启用定时自动获取气温")
    schedule_times: List[str] = Field(default_factory=list, description="每日定时获取时间列表（HH:MM）")


@router.get("/dashboard/temperature/config", summary="读取气温导入 API 配置")
def get_temperature_import_config(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    try:
        return {"ok": True, "data": load_weather_import_config()}
    except WeatherImporterError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/dashboard/temperature/config", summary="保存气温导入 API 配置")
def update_temperature_import_config(
    payload: WeatherImportConfigPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    try:
        saved = save_weather_import_config(payload.api_url)
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            "更新近端实况气温导入 API 来源配置",
            request=request,
            unit="集团生产调度中心",
            resource_id="weather_config:near",
            after_value={"api_url": saved.get("api_url")},
        )
        return {"ok": True, "data": saved}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="保存气温 API 配置失败，请检查运行时目录是否可写。") from exc


@router.get("/dashboard/temperature/auto-import/status", summary="读取气温自动导入配置与最近成功/失败状态")
def get_temperature_auto_import_status(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    return {"ok": True, "data": weather_auto_import_service.get_status()}


@router.put("/dashboard/temperature/auto-import/config", summary="保存气温自动导入时间配置")
def update_temperature_auto_import_config(
    payload: WeatherAutoImportConfigPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    try:
        data = weather_auto_import_service.update_config(
            enabled=payload.enabled,
            schedule_times=payload.schedule_times,
        )
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            f"保存近端气温自动导入定时设置（启用：{'是' if payload.enabled else '否'}，时点：{', '.join(payload.schedule_times) or '无'}）",
            request=request,
            unit="集团生产调度中心",
            resource_id="weather_auto_import:near",
            after_value={"enabled": payload.enabled, "schedule_times": payload.schedule_times},
        )
        return {"ok": True, "message": "气温自动获取时间配置已保存并立即生效。", "data": data}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="保存气温自动获取配置失败，请检查运行时目录是否可写。") from exc


@router.post("/dashboard/temperature/auto-import/run", summary="立即执行一次气温获取与入库并记录状态")
def run_temperature_auto_import_now(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    operator = getattr(session, "username", None) or "global_admin"
    result = weather_auto_import_service.run_import_once(
        trigger="manual_admin",
        operator=operator,
    )
    if result.get("busy"):
        raise HTTPException(status_code=409, detail=result.get("message") or "当前已有气温导入任务正在执行。")
    return result


@router.get("/dashboard/temperature/ensemble/config", summary="读取 35 天集合气温预报 API 配置")
def get_ensemble_temperature_import_config(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    try:
        return {"ok": True, "data": load_ensemble_weather_import_config()}
    except EnsembleWeatherError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/dashboard/temperature/ensemble/config", summary="保存 35 天集合气温预报 API 配置")
def update_ensemble_temperature_import_config(
    payload: WeatherImportConfigPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    try:
        saved = save_ensemble_weather_import_config(payload.api_url)
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            "更新 35 天集合气温预报 API 来源配置",
            request=request,
            unit="集团生产调度中心",
            resource_id="weather_config:far",
            after_value={"api_url": saved.get("api_url")},
        )
        return {"ok": True, "data": saved}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="保存 35 天预报 API 配置失败，请检查运行时目录是否可写。") from exc


@router.get("/dashboard/temperature/ensemble/auto-import/status", summary="读取 35 天集合气温预报自动导入状态")
def get_ensemble_temperature_auto_import_status(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    return {"ok": True, "data": ensemble_weather_auto_import_service.get_status()}


@router.put("/dashboard/temperature/ensemble/auto-import/config", summary="保存 35 天集合气温预报自动导入时间配置")
def update_ensemble_temperature_auto_import_config(
    payload: WeatherAutoImportConfigPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    try:
        data = ensemble_weather_auto_import_service.update_config(
            enabled=payload.enabled,
            schedule_times=payload.schedule_times,
        )
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            f"保存 35 天集合气温预报自动导入定时设置（启用：{'是' if payload.enabled else '否'}，时点：{', '.join(payload.schedule_times) or '无'}）",
            request=request,
            unit="集团生产调度中心",
            resource_id="weather_auto_import:far",
            after_value={"enabled": payload.enabled, "schedule_times": payload.schedule_times},
        )
        return {"ok": True, "message": "35 天集合预报自动获取时间配置已保存并立即生效。", "data": data}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="保存 35 天预报自动获取配置失败，请检查运行时目录是否可写。") from exc


@router.post("/dashboard/temperature/ensemble/auto-import/run", summary="立即执行一次 35 天集合气温预报获取与入库")
def run_ensemble_temperature_auto_import_now(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    operator = getattr(session, "username", None) or "global_admin"
    result = ensemble_weather_auto_import_service.run_import_once(
        trigger="manual_admin",
        operator=operator,
    )
    if result.get("busy"):
        raise HTTPException(status_code=409, detail=result.get("message") or "当前已有 35 天预报导入任务正在执行。")
    return result


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
    request: Request,
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
        try:
            weather_auto_import_service.record_external_import_outcome(
                ok=False,
                trigger="manual_dashboard",
                message=f"气温获取或入库失败：{exc}",
            )
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        db_session.rollback()
        db_session.close()
        try:
            weather_auto_import_service.record_external_import_outcome(
                ok=False,
                trigger="manual_dashboard",
                message=f"气温获取或入库失败：{exc}",
            )
        except Exception:
            pass
        raise
    fetched_at = datetime.now(tz=EAST_8).isoformat()
    db_session.close()
    dates = list(result.get("dates", []) or [])
    total_hours = int((result.get("summary") or {}).get("total_hours") or len(result.get("hourly", [])))
    inserted = int((persist_result or {}).get("inserted") or 0)
    replaced = int((persist_result or {}).get("replaced") or 0)
    date_span = f"{dates[0]} ~ {dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "—")
    try:
        weather_auto_import_service.record_external_import_outcome(
            ok=True,
            trigger="manual_dashboard",
            message=f"气温获取并入库成功：共拉取 {total_hours} 小时，写入 {inserted} 条、覆盖 {replaced} 条（日期范围：{date_span}）。",
            summary={
                "total_hours": total_hours,
                "inserted": inserted,
                "replaced": replaced,
                "start": (persist_result or {}).get("start"),
                "end": (persist_result or {}).get("end"),
                "dates": dates,
            },
        )
    except Exception:
        pass
    log_session_operation(
        session,
        "IMPORT_TEMPERATURE",
        f"数据看板手动导入并覆盖气温数据：共拉取 {total_hours} 小时，写入 {inserted} 条、覆盖 {replaced} 条（日期范围：{date_span}）",
        request=request,
        unit="集团生产调度中心",
        resource_id=f"weather:near:{dates[-1] if dates else 'manual'}",
        after_value={"total_hours": total_hours, "inserted": inserted, "replaced": replaced, "dates": dates},
    )
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
    snapshot = cache_publish_job_manager.snapshot(PROJECT_KEY)
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/publish/cancel",
    summary="停止正在运行的缓存发布任务",
    tags=["daily_report_25_26"],
)
def cancel_cache_publish(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    snapshot = cache_publish_job_manager.request_cancel(PROJECT_KEY)
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/refresh",
    summary="刷新指定日期的数据看板缓存",
    tags=["daily_report_25_26"],
)
def refresh_dashboard_cache(
    request: Request,
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
    log_session_operation(
        session,
        "UPDATE_CONFIG",
        f"手动刷新数据看板缓存（目标日期：{cache_key}）",
        request=request,
        resource_id=f"dashboard_cache:{cache_key}",
    )
    return {
        "ok": True,
        "cached_key": cache_key,
        "cache_disabled": status.get("disabled", False),
        "cache_updated_at": status.get("updated_at"),
    }


class SandboxRequest(BaseModel):
    biz_date: str = Field(default="", description="业务日期 YYYY-MM-DD")
    company: str = Field(default="JinZhou", description="单位代码")
    item: str = Field(default="rate_std_coal_per_heat", description="指标标识")


@public_router.get(
    "/metrics/catalog",
    summary="获取生产指标与算法规范元数据字典",
    tags=["daily_report_25_26"],
)
def get_metrics_catalog():
    from backend.services.heating_metrics.catalog_data import get_catalog_categories, get_full_catalog
    return {
        "ok": True,
        "categories": get_catalog_categories(),
        "catalog": get_full_catalog(),
    }


@public_router.post(
    "/metrics/sandbox",
    summary="在线拆解验算指标计算逻辑与过程",
    tags=["daily_report_25_26"],
)
def run_metric_sandbox(payload: SandboxRequest):
    from backend.services.heating_metrics.sandbox_service import explain_metric_calculation
    with SessionLocal() as session:
        return explain_metric_calculation(
            session=session,
            biz_date_str=payload.biz_date,
            company=payload.company,
            item=payload.item,
        )


class SeasonConfigRequest(BaseModel):
    active_period: str = Field(..., description="激活供暖期编码，如 25-26、26-27")
    biz_date: Optional[str] = Field(default=None, description="联动设置的业务基准日期 YYYY-MM-DD")
    start_date: Optional[str] = Field(default=None, description="供暖季开栓起始日")
    end_date: Optional[str] = Field(default=None, description="供暖季停热结束日")
    description: Optional[str] = Field(default=None, description="调整说明")
    temperature_start_date: Optional[str] = Field(default=None, description="本期平均气温起算日，默认11月1日")
    peer_start_date: Optional[str] = Field(default=None, description="同期日报统计开始日")
    peer_end_date: Optional[str] = Field(default=None, description="同期日报统计结束日")
    peer_temperature_start_date: Optional[str] = Field(default=None, description="同期平均气温起算日")


@public_router.get(
    "/season/config",
    summary="获取当前供暖期全局运行配置",
    tags=["daily_report_25_26"],
)
def get_season_configuration():
    from backend.services import heating_season_service
    cfg = heating_season_service.get_season_config(PROJECT_KEY)
    return {"ok": True, **cfg}


@public_router.post(
    "/season/config",
    summary="手动修改或滚动切换供暖期",
    tags=["daily_report_25_26"],
)
def update_season_configuration(
    payload: SeasonConfigRequest,
    request: Request,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
):
    from backend.services import heating_season_service
    try:
        updated = heating_season_service.update_season_config(
            project_key=PROJECT_KEY,
            active_period=payload.active_period,
            biz_date=payload.biz_date,
            start_date=payload.start_date,
            end_date=payload.end_date,
            description=payload.description,
            temperature_start_date=payload.temperature_start_date,
            peer_start_date=payload.peer_start_date,
            peer_end_date=payload.peer_end_date,
            peer_temperature_start_date=payload.peer_temperature_start_date,
        )
        log_session_operation(
            session,
            "UPDATE_CONFIG",
            f"更新供暖期配置：当前供暖期 {payload.active_period}（同期 {updated.get('peer_period')}，业务日 {payload.biz_date or updated.get('biz_date') or '-'}）",
            request=request,
            resource_id=f"season:{payload.active_period}",
            after_value={"active_period": payload.active_period, "biz_date": payload.biz_date, "start_date": payload.start_date, "end_date": payload.end_date},
        )
        return {
            "ok": True,
            "message": f"供暖期已成功切换为 {payload.active_period}（同期自动对齐为 {updated.get('peer_period')}）",
            **updated,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存供暖期配置失败: {exc}") from exc

