# -*- coding: utf-8 -*-
"""daily_report_25_26 项目目录化管理接口。"""

from __future__ import annotations

from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException

from backend.services.auth_manager import AuthSession, get_current_session
from backend.services.project_data_paths import (
    bootstrap_project_files,
    ensure_project_dirs,
    get_project_file_status,
)
from backend.services.project_modularization import (
    load_project_entry,
    resolve_project_modularization_files,
)


PROJECT_KEY = "daily_report_25_26"
router = APIRouter()


def _ensure_system_admin(session: AuthSession) -> None:
    group = (session.group or "").strip()
    allowed = {"系统管理员", "Global_admin"}
    if group not in allowed:
        raise HTTPException(status_code=403, detail="仅系统管理员可执行目录化迁移管理操作。")


def _resolve_files() -> Tuple[List[str], List[str]]:
    project_entry = load_project_entry(PROJECT_KEY)
    return resolve_project_modularization_files(PROJECT_KEY, project_entry)


@router.get(
    "/project/modularization/status",
    summary="查看项目目录化迁移状态",
    tags=["daily_report_25_26"],
)
def get_project_modularization_status(session: AuthSession = Depends(get_current_session)):
    _ensure_system_admin(session)
    config_files, runtime_files = _resolve_files()
    status = get_project_file_status(PROJECT_KEY, config_files, runtime_files)
    return {"ok": True, "status": status}


@router.post(
    "/project/modularization/bootstrap",
    summary="初始化项目目录并复制旧配置（仅缺失文件）",
    tags=["daily_report_25_26"],
)
def bootstrap_project_modularization(session: AuthSession = Depends(get_current_session)):
    _ensure_system_admin(session)
    config_files, runtime_files = _resolve_files()
    dirs = ensure_project_dirs(PROJECT_KEY)
    copied = bootstrap_project_files(PROJECT_KEY, config_files, runtime_files)
    status = get_project_file_status(PROJECT_KEY, config_files, runtime_files)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "dirs": dirs,
        "bootstrap": copied,
        "status": status,
    }
