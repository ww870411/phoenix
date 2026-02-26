# -*- coding: utf-8 -*-
"""全局管理后台接口。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config import DATA_DIRECTORY
from backend.services import dashboard_cache
from backend.services.auth_manager import AuthSession, get_current_session
from backend.services.dashboard_cache_job import cache_publish_job_manager
from backend.services.dashboard_expression import evaluate_dashboard
from backend.services.project_data_paths import resolve_project_list_path
from backend.projects.daily_report_25_26.api.dashboard import PROJECT_KEY
from backend.projects.daily_report_25_26.api.legacy_full import (
    _can_manage_ai_settings,
    _ensure_manage_ai_settings_permission,
    _ensure_manage_validation_permission,
    _load_master_validation_config,
    _persist_ai_settings,
    _persist_master_validation_switch,
    _safe_read_ai_settings,
)


router = APIRouter(tags=["admin"])
DATA_ROOT = Path(DATA_DIRECTORY).resolve()
MAX_EDITABLE_FILE_SIZE = 2 * 1024 * 1024  # 2MB


class ValidationSwitchPayload(BaseModel):
    validation_enabled: bool


class AiSettingsPayload(BaseModel):
    api_keys: List[str]
    model: str
    instruction: str = ""
    report_mode: str = "full"
    enable_validation: bool = True
    allow_non_admin_report: bool = False


class FileSavePayload(BaseModel):
    path: str
    content: str


def _ensure_admin_console_access(session: AuthSession) -> None:
    if not session.permissions.actions.can_access_admin_console:
        raise HTTPException(status_code=403, detail="当前账号无全局后台访问权限。")


def _ensure_cache_operator(session: AuthSession) -> None:
    actions = session.get_project_action_flags(PROJECT_KEY)
    if not bool(actions.can_publish):
        raise HTTPException(status_code=403, detail="当前账号无缓存管理权限。")


def _resolve_safe_data_path(relative_path: str) -> Path:
    raw = str(relative_path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="缺少文件路径。")
    path_obj = Path(raw)
    if path_obj.is_absolute():
        raise HTTPException(status_code=400, detail="文件路径必须是 backend_data 下的相对路径。")
    resolved = (DATA_ROOT / path_obj).resolve()
    try:
        resolved.relative_to(DATA_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="不允许访问 backend_data 目录外文件。") from exc
    return resolved


def _load_project_entries() -> Dict[str, Dict[str, Any]]:
    path = resolve_project_list_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    entries: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            entries[key] = value
    return entries


def _mask_api_key(raw_key: str) -> str:
    key = str(raw_key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}***{key[-4:]}"


def _collect_ai_settings_summary() -> Dict[str, Any]:
    settings = _safe_read_ai_settings()
    raw_keys = settings.get("api_keys")
    api_keys: List[str] = raw_keys if isinstance(raw_keys, list) else []
    return {
        "model": str(settings.get("model") or ""),
        "report_mode": str(settings.get("report_mode") or "full"),
        "enable_validation": bool(settings.get("enable_validation", True)),
        "allow_non_admin_report": bool(settings.get("allow_non_admin_report", False)),
        "api_key_count": len([item for item in api_keys if str(item or "").strip()]),
        "api_keys_masked": [_mask_api_key(item) for item in api_keys[:3]],
    }


@router.get("/admin/overview", summary="获取全局管理后台概览")
def get_admin_overview(
    session: AuthSession = Depends(get_current_session),
    project_key: str = Query(default=PROJECT_KEY),
):
    _ensure_admin_console_access(session)
    normalized_project_key = str(project_key or "").strip()
    if normalized_project_key != PROJECT_KEY:
        return {
            "ok": True,
            "project_key": normalized_project_key,
            "supported": False,
            "message": "当前项目后台设定暂未接入。",
        }
    actions = session.get_project_action_flags(PROJECT_KEY)
    can_manage_validation = bool(actions.can_manage_validation)
    can_manage_ai = bool(_can_manage_ai_settings(session))
    can_publish = bool(actions.can_publish)

    validation_enabled = None
    if can_manage_validation:
        validation_enabled, _ = _load_master_validation_config()

    ai_settings_summary = None
    if can_manage_ai:
        ai_settings_summary = _collect_ai_settings_summary()

    cache_status = None
    cache_publish_job = None
    if can_publish:
        cache_status = dashboard_cache.get_cache_status(PROJECT_KEY)
        cache_publish_job = cache_publish_job_manager.snapshot()

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "supported": True,
        "actions": {
            "can_manage_validation": can_manage_validation,
            "can_manage_ai_settings": can_manage_ai,
            "can_publish_cache": can_publish,
        },
        "validation": {"master_enabled": validation_enabled},
        "ai_settings": ai_settings_summary,
        "dashboard_cache": cache_status,
        "cache_publish_job": cache_publish_job,
    }


@router.get("/admin/projects", summary="获取项目后台设定列表")
def list_admin_projects(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    entries = _load_project_entries()
    projects: List[Dict[str, str]] = []
    for project_key, cfg in entries.items():
        project_name = (
            cfg.get("project_name")
            or cfg.get("项目名称")
            or cfg.get("名称")
            or project_key
        )
        projects.append(
            {
                "project_key": project_key,
                "project_name": str(project_name),
            }
        )
    if not projects:
        projects = [{"project_key": PROJECT_KEY, "project_name": "2025-2026供暖期生产日报"}]
    return {"ok": True, "projects": projects}


@router.get("/admin/files/directories", summary="列出 backend_data 子目录")
def list_backend_data_directories(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    if not DATA_ROOT.exists() or not DATA_ROOT.is_dir():
        raise HTTPException(status_code=500, detail="backend_data 目录不存在。")
    directories = [
        item.name
        for item in sorted(DATA_ROOT.iterdir(), key=lambda p: p.name.lower())
        if item.is_dir()
    ]
    return {"ok": True, "directories": directories}


@router.get("/admin/files", summary="列出目录下可编辑文件")
def list_backend_files(
    session: AuthSession = Depends(get_current_session),
    directory: str = Query(default=""),
):
    _ensure_admin_console_access(session)
    target = _resolve_safe_data_path(directory)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在。")
    files: List[Dict[str, str]] = []
    for file_path in sorted(target.rglob("*"), key=lambda p: str(p).lower()):
        if not file_path.is_file():
            continue
        rel_path = file_path.relative_to(DATA_ROOT).as_posix()
        files.append({"path": rel_path, "name": file_path.name})
    return {"ok": True, "directory": target.relative_to(DATA_ROOT).as_posix(), "files": files}


@router.get("/admin/files/content", summary="读取文件内容")
def read_backend_file_content(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(...),
):
    _ensure_admin_console_access(session)
    target = _resolve_safe_data_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在。")
    if target.stat().st_size > MAX_EDITABLE_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大，不支持在线编辑。")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件不是 UTF-8 文本，无法在线编辑。") from exc
    return {"ok": True, "path": target.relative_to(DATA_ROOT).as_posix(), "content": content}


@router.post("/admin/files/content", summary="保存文件内容")
def save_backend_file_content(
    payload: FileSavePayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    target = _resolve_safe_data_path(payload.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在。")
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_EDITABLE_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件内容过大，拒绝保存。")
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": target.relative_to(DATA_ROOT).as_posix(), "size": len(encoded)}


@router.get("/admin/validation/master-switch", summary="获取全局校验总开关")
def get_validation_master_switch(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    _ensure_manage_validation_permission(session)
    flag, _ = _load_master_validation_config()
    return {"ok": True, "validation_enabled": flag}


@router.post("/admin/validation/master-switch", summary="更新全局校验总开关")
def update_validation_master_switch(
    payload: ValidationSwitchPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    _ensure_manage_validation_permission(session)
    updated = _persist_master_validation_switch(payload.validation_enabled)
    return {"ok": True, "validation_enabled": updated}


@router.get("/admin/ai-settings", summary="获取全局 AI 设置")
def get_ai_settings(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    _ensure_manage_ai_settings_permission(session)
    settings = _safe_read_ai_settings()
    return {"ok": True, **settings}


@router.post("/admin/ai-settings", summary="更新全局 AI 设置")
def update_ai_settings(
    payload: AiSettingsPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    _ensure_manage_ai_settings_permission(session)
    saved = _persist_ai_settings(
        payload.api_keys,
        payload.model.strip(),
        payload.instruction,
        payload.report_mode,
        payload.enable_validation,
        payload.allow_non_admin_report,
    )
    return {"ok": True, **saved}


@router.post("/admin/cache/publish", summary="发布看板缓存")
def publish_dashboard_cache(
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30),
):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    schedule = list(reversed(dashboard_cache.default_publish_dates(window=days, project_key=PROJECT_KEY)))
    snapshot, started = cache_publish_job_manager.start(PROJECT_KEY, schedule)
    return {"ok": True, "started": started, "days": days, "job": snapshot}


@router.get("/admin/cache/publish/status", summary="获取缓存发布任务状态")
def get_cache_publish_status(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    return {"ok": True, "job": cache_publish_job_manager.snapshot()}


@router.post("/admin/cache/publish/cancel", summary="停止缓存发布任务")
def cancel_cache_publish(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    return {"ok": True, "job": cache_publish_job_manager.request_cancel()}


@router.delete("/admin/cache", summary="禁用并清空缓存")
def disable_cache(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    status = dashboard_cache.disable_cache(PROJECT_KEY)
    return {
        "ok": True,
        "cache_disabled": status.get("disabled", True),
        "cache_updated_at": status.get("updated_at"),
    }


@router.post("/admin/cache/refresh", summary="刷新指定日期缓存")
def refresh_cache(
    session: AuthSession = Depends(get_current_session),
    show_date: str = Query(default=""),
):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = {"ok": True, **result.to_dict()}
    status = dashboard_cache.update_cache_entry(PROJECT_KEY, cache_key, payload)
    return {
        "ok": True,
        "cached_key": cache_key,
        "cache_disabled": status.get("disabled", False),
        "cache_updated_at": status.get("updated_at"),
    }
