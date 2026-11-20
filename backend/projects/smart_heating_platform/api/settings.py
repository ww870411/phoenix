# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 采集配置与 Cookie 设置 API
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.smart_heating_platform.services.collector_config_service import (
    get_collector_settings_view,
    test_collector_connectivity,
    update_collector_settings,
)

router = APIRouter(prefix="/settings", tags=["smart_heating_platform_settings"])


def _require_global_admin(session: AuthSession) -> None:
    """采集配置与 Cookie 管理严格仅限 Global_admin 访问。"""
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 访问采集设置")


class CollectorSettingsUpdateRequest(BaseModel):
    """采集配置与 Cookie 保存请求体。"""

    source_mode: Optional[str] = Field(None, description="源站连接模式: public / intranet / custom")
    custom_base_url: Optional[str] = Field(None, description="自定义源站基地址")
    cookie: Optional[str] = Field(None, description="源站登录 Session Cookie（留空或不传则保持原值不变）")
    clear_cookie: Optional[bool] = Field(False, description="是否清空已保存 Cookie")
    scheduler_enabled: Optional[bool] = Field(None, description="是否启用定时采集开关")
    snapshot_interval_minutes: Optional[int] = Field(None, description="批量采样间隔分钟数 (5 / 15 / 30 / 60)")
    hourly_offset_minutes: Optional[int] = Field(None, description="整点后延迟采集分钟数 (0~59)")
    max_workers: Optional[int] = Field(None, description="并行采集工作线程数 (1~16)")
    request_interval_seconds: Optional[float] = Field(None, description="单线程请求间隔秒数 (0.5~5.0)")
    request_timeout_seconds: Optional[float] = Field(None, description="单次请求超时秒数 (3~60)")
    table_bottom_sync_hours: Optional[int] = Field(None, description="累计表底校准间隔小时数 (1~24)")
    auto_gap_recovery: Optional[bool] = Field(None, description="是否开启停机真空期自动检测与补采")
    gap_recovery_start_date: Optional[str] = Field(None, description="真空期自动检查起始日期 YYYY-MM-DD（默认 2026-11-01）")
    auto_heat_audit_fix: Optional[bool] = Field(None, description="是否开启每日定时数据回看检测与自动修正")
    heat_audit_time: Optional[str] = Field(None, description="每日回看检测修正执行时刻 HH:MM（默认 00:00）")
    heat_audit_lookback_days: Optional[int] = Field(None, description="每次定时回看检测的天数 1~30（默认 3 天）")


class CollectorTestRequest(BaseModel):
    """源站连通性与 Cookie 有效性探测请求体。"""

    cookie: Optional[str] = Field(None, description="待临时测试的 Cookie；不传则使用已保存 Cookie")
    source_mode: Optional[str] = Field(None, description="临时测试使用的连接模式")
    custom_base_url: Optional[str] = Field(None, description="临时测试使用的自定义基地址")


@router.get("/collector", summary="读取采集配置与 Cookie 脱敏状态")
def get_collector_settings(session: AuthSession = Depends(get_current_session)):
    """查询采集配置（Cookie 脱敏展示）。"""
    _require_global_admin(session)
    data = get_collector_settings_view()
    return {"ok": True, "data": data}


@router.put("/collector", summary="保存或修改采集配置与 Cookie")
def save_collector_settings(
    payload: CollectorSettingsUpdateRequest = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    """保存或修改采集配置与源站 Session Cookie。"""
    _require_global_admin(session)
    try:
        data = update_collector_settings(payload.model_dump(), operator=session.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "message": "采集配置已保存", "data": data}


@router.post("/collector/test", summary="测试源站连通性与 Cookie 有效性")
def test_collector_settings(
    payload: CollectorTestRequest = Body(default_factory=CollectorTestRequest),
    session: AuthSession = Depends(get_current_session),
):
    """执行只读接口单线程连通性及 Cookie 有效性测试。"""
    _require_global_admin(session)
    try:
        result = test_collector_connectivity(
            override_cookie=payload.cookie,
            override_source_mode=payload.source_mode,
            override_custom_base_url=payload.custom_base_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "data": result}
