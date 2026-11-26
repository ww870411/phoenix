# -*- coding: utf-8 -*-
"""会议排座助手项目路由（严格仅限 Global_admin 访问）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.projects.meeting_seating.services.profile_store import (
    activate_profile,
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    rename_profile,
    update_profile,
)
from backend.services.auth_manager import AuthSession, get_current_session, get_session_groups

router = APIRouter(tags=["meeting_seating"])
public_router = None


def _require_global_admin(session: AuthSession) -> None:
    """严格校验会话属于 Global_admin 用户组。"""
    groups = get_session_groups(session)
    if session.group != "Global_admin" and "Global_admin" not in groups:
        raise HTTPException(status_code=403, detail="会议排座助手仅限 Global_admin 访问")


class CreateProfileRequest(BaseModel):
    """新建布局存档请求体。"""

    name: str = Field(..., min_length=1, max_length=60, description="新存档名称")
    layout: Optional[Dict[str, Any]] = Field(None, description="可选初始布局数据")
    source_profile_id: Optional[str] = Field(None, description="可选复制来源存档 ID")
    activate: bool = Field(True, description="创建后是否立即切换为当前激活存档")


class UpdateProfileRequest(BaseModel):
    """更新布局存档请求体。"""

    name: Optional[str] = Field(None, min_length=1, max_length=60, description="可选存档名称")
    layout: Optional[Dict[str, Any]] = Field(None, description="布局数据")


class RenameProfileRequest(BaseModel):
    """重命名布局存档请求体。"""

    name: str = Field(..., min_length=1, max_length=60, description="新存档名称")


@router.get("/profiles", summary="获取所有会议排座布局存档及当前激活方案")
def api_list_profiles(session: AuthSession = Depends(get_current_session)):
    _require_global_admin(session)
    return {"ok": True, **list_profiles()}


@router.get("/profiles/{profile_id}", summary="读取指定会议排座布局存档")
def api_get_profile(profile_id: str, session: AuthSession = Depends(get_current_session)):
    _require_global_admin(session)
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="目标存档不存在")
    return {"ok": True, "profile": profile}


@router.post("/profiles", summary="新建会议排座布局存档")
def api_create_profile(
    payload: CreateProfileRequest = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_global_admin(session)
    try:
        result = create_profile(
            name=payload.name,
            layout=payload.layout,
            source_profile_id=payload.source_profile_id,
            activate=payload.activate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.put("/profiles/{profile_id}", summary="保存更新指定会议排座布局存档")
def api_update_profile(
    profile_id: str,
    payload: UpdateProfileRequest = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_global_admin(session)
    try:
        result = update_profile(profile_id=profile_id, layout=payload.layout, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.patch("/profiles/{profile_id}/rename", summary="重命名会议排座布局存档")
def api_rename_profile(
    profile_id: str,
    payload: RenameProfileRequest = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_global_admin(session)
    try:
        result = rename_profile(profile_id=profile_id, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/profiles/{profile_id}/activate", summary="切换当前激活的会议排座布局存档")
def api_activate_profile(profile_id: str, session: AuthSession = Depends(get_current_session)):
    _require_global_admin(session)
    try:
        result = activate_profile(profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.delete("/profiles/{profile_id}", summary="删除指定会议排座布局存档")
def api_delete_profile(profile_id: str, session: AuthSession = Depends(get_current_session)):
    _require_global_admin(session)
    try:
        result = delete_profile(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **result}
