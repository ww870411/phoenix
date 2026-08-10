# -*- coding: utf-8 -*-
"""全局管理后台接口。"""

from __future__ import annotations

import ipaddress
import json
import platform
import re
import shutil
import subprocess
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import threading
import uuid
import os

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services import audit_log
from backend.services import ai_runtime
from backend.services import dashboard_cache
from backend.services.auth_manager import AuthSession, auth_manager, get_current_session
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
APP_START_TS = time.time()
MONTHLY_DATA_SHOW_PROJECT_KEY = "monthly_data_show"
MONTHLY_DATA_SHOW_QUERY_TOOL_PAGE_KEY = "projects_monthly_data_show_query_tool"
MAX_EDITABLE_FILE_SIZE = 2 * 1024 * 1024  # 2MB
EDITABLE_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".ini",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".vue",
    ".css",
    ".sql",
    ".csv",
}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DbTableQueryPayload(BaseModel):
    table: str
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    search: str = ""
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    order_by: str = ""
    order_dir: str = "asc"


class DbTableBatchUpdatePayload(BaseModel):
    table: str
    updates: List[Dict[str, Any]] = Field(default_factory=list)


class ValidationSwitchPayload(BaseModel):
    validation_enabled: bool


class SubmitPermissionPayload(BaseModel):
    group_name: str
    can_submit: bool


class GroupPageAccessPayload(BaseModel):
    group_name: str
    has_access: bool


class AiSettingsPayload(BaseModel):
    api_keys: List[str] = Field(default_factory=list)
    model: str = ""
    provider: Optional[str] = "gemini"
    newapi_base_url: Optional[str] = None
    newapi_api_keys: Optional[List[str]] = None
    newapi_model: Optional[str] = None
    newapi_backup_models: Optional[List[str]] = None
    providers: Optional[List[Dict[str, Any]]] = None
    active_provider_id: Optional[str] = None
    instruction_daily: Optional[str] = None
    instruction: Optional[str] = None
    instruction_monthly: Optional[str] = None
    report_mode: str = "full"
    enable_validation: bool = True
    allow_non_admin_report: bool = False
    show_chat_bubble: bool = True


class AiSettingsConnectionTestPayload(BaseModel):
    provider: Optional[str] = "gemini"
    api_keys: Optional[List[str]] = None
    model: Optional[str] = None
    newapi_base_url: Optional[str] = None
    newapi_api_keys: Optional[List[str]] = None
    newapi_model: Optional[str] = None
    providers: Optional[List[Dict[str, Any]]] = None
    active_provider_id: Optional[str] = None


class FileSavePayload(BaseModel):
    path: str
    content: str


class AuditEventPayload(BaseModel):
    category: str = "ui"
    action: str
    page: str = ""
    target: str = ""
    detail: Dict[str, Any] = Field(default_factory=dict)
    ts: str = ""


class AuditBatchPayload(BaseModel):
    events: List[AuditEventPayload] = Field(default_factory=list)


class SuperExecPayload(BaseModel):
    command: str
    cwd: str = ""
    timeout_seconds: int = 20


class SuperFileWritePayload(BaseModel):
    path: str
    content: str


class SuperMkdirPayload(BaseModel):
    path: str


class SuperMovePayload(BaseModel):
    source: str
    destination: str


def _is_safe_identifier(name: str) -> bool:
    return bool(IDENTIFIER_PATTERN.fullmatch(str(name or "").strip()))


def _parse_schema_and_table(raw_name: str) -> tuple[str, str]:
    clean_name = str(raw_name or "").strip()
    if "." in clean_name:
        parts = clean_name.split(".", 1)
        return parts[0], parts[1]
    return "public", clean_name


def _quote_identifier(name: str) -> str:
    raw = str(name or "").strip()
    if "." in raw:
        schema_part, table_part = _parse_schema_and_table(raw)
        if not _is_safe_identifier(schema_part) or not _is_safe_identifier(table_part):
            raise HTTPException(status_code=400, detail=f"非法标识符：{raw}")
        return f'"{schema_part}"."{table_part}"'
    if not _is_safe_identifier(raw):
        raise HTTPException(status_code=400, detail=f"非法标识符：{raw}")
    return f'"{raw}"'


def _to_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def _load_table_meta(db, table: str) -> Dict[str, Any]:
    safe_table = str(table or "").strip()
    schema_name, table_name = _parse_schema_and_table(safe_table)
    if not _is_safe_identifier(schema_name) or not _is_safe_identifier(table_name):
        raise HTTPException(status_code=400, detail="表名不合法。")

    columns_sql = text(
        """
        SELECT
            c.column_name,
            c.data_type
        FROM information_schema.columns c
        WHERE c.table_schema = :schema
          AND c.table_name = :table
        ORDER BY c.ordinal_position
        """
    )
    columns_rows = db.execute(columns_sql, {"schema": schema_name, "table": table_name}).mappings().all()
    if not columns_rows:
        raise HTTPException(status_code=404, detail="数据表不存在或无字段。")
    columns = [
        {"name": str(row.get("column_name") or ""), "data_type": str(row.get("data_type") or "")}
        for row in columns_rows
    ]
    column_names = [col["name"] for col in columns if col["name"]]

    pk_sql = text(
        """
        SELECT a.attname AS column_name
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
        WHERE n.nspname = :schema
          AND t.relname = :table
          AND i.indisprimary
        ORDER BY array_position(i.indkey, a.attnum)
        """
    )
    pk_rows = db.execute(pk_sql, {"schema": schema_name, "table": table_name}).mappings().all()
    pk_columns = [str(row.get("column_name") or "") for row in pk_rows if row.get("column_name")]
    full_table = f"{schema_name}.{table_name}" if schema_name != "public" else table_name
    return {
        "table": full_table,
        "raw_table": table_name,
        "schema": schema_name,
        "columns": columns,
        "column_names": column_names,
        "pk_columns": pk_columns,
    }


def _ensure_admin_console_access(session: AuthSession) -> None:
    if not session.permissions.actions.can_access_admin_console:
        raise HTTPException(status_code=403, detail="当前账号无全局后台访问权限。")


def _extract_forwarded_client_ip(request: Request) -> str:
    x_forwarded_for = str(request.headers.get("x-forwarded-for") or "").strip()
    if x_forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        first_ip = x_forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    x_real_ip = str(request.headers.get("x-real-ip") or "").strip()
    if x_real_ip:
        return x_real_ip
    return ""


def _normalize_ip(raw_ip: str) -> str:
    text = str(raw_ip or "").strip()
    if not text:
        return ""
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return text


def _resolve_client_ip(request: Request) -> str:
    forwarded_ip = _normalize_ip(_extract_forwarded_client_ip(request))
    if forwarded_ip:
        return forwarded_ip
    direct_ip = request.client.host if request.client else ""
    return _normalize_ip(direct_ip)


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


def _normalize_upload_filename(filename: str) -> str:
    normalized = Path(str(filename or "").strip()).name
    if not normalized:
        raise HTTPException(status_code=400, detail="上传文件名不能为空。")
    suffix = Path(normalized).suffix.lower()
    if suffix not in EDITABLE_EXTENSIONS:
        allowed = ", ".join(sorted(EDITABLE_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"仅允许上传以下可编辑文件：{allowed}")
    return normalized


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
    raw_newapi_keys = settings.get("newapi_api_keys")
    newapi_api_keys: List[str] = raw_newapi_keys if isinstance(raw_newapi_keys, list) else []
    provider = str(settings.get("provider") or "gemini").strip().lower()
    if provider not in {"gemini", "newapi"}:
        provider = "gemini"
    providers_raw = settings.get("providers")
    providers = providers_raw if isinstance(providers_raw, list) else []
    active_provider_id = str(settings.get("active_provider_id") or "").strip()
    active_provider = None
    for item in providers:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") == active_provider_id:
            active_provider = item
            break
    return {
        "provider": provider,
        "providers_count": len([p for p in providers if isinstance(p, dict)]),
        "active_provider_id": active_provider_id,
        "active_provider_name": str((active_provider or {}).get("name") or ""),
        "model": str(settings.get("model") or ""),
        "newapi_model": str(settings.get("newapi_model") or ""),
        "newapi_base_url": str(settings.get("newapi_base_url") or ""),
        "report_mode": str(settings.get("report_mode") or "full"),
        "enable_validation": bool(settings.get("enable_validation", True)),
        "allow_non_admin_report": bool(settings.get("allow_non_admin_report", False)),
        "api_key_count": len([item for item in api_keys if str(item or "").strip()]),
        "newapi_api_key_count": len([item for item in newapi_api_keys if str(item or "").strip()]),
        "api_keys_masked": [_mask_api_key(item) for item in api_keys[:3]],
        "newapi_api_keys_masked": [_mask_api_key(item) for item in newapi_api_keys[:3]],
    }


def _collect_system_metrics() -> Dict[str, Any]:
    now = datetime.now(timezone.utc).astimezone().isoformat()
    result: Dict[str, Any] = {
        "timestamp": now,
        "uptime_seconds": max(0, int(time.time() - APP_START_TS)),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "cpu": {"percent": None, "logical_cores": None, "physical_cores": None},
        "memory": {"total_bytes": None, "used_bytes": None, "percent": None},
        "disk": {"total_bytes": None, "used_bytes": None, "percent": None},
        "process": {
            "pid": None,
            "cpu_percent": None,
            "memory_rss_bytes": None,
            "threads": None,
            "open_files": None,
        },
        "metrics_provider": "stdlib_fallback",
    }
    try:
        import psutil  # type: ignore

        cpu_percent = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        proc = psutil.Process()
        with proc.oneshot():
            proc_cpu = proc.cpu_percent(interval=0.0)
            proc_mem = proc.memory_info().rss
            proc_threads = proc.num_threads()
            try:
                proc_open_files = len(proc.open_files())
            except Exception:
                proc_open_files = None
        result["cpu"] = {
            "percent": round(float(cpu_percent), 2),
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
        }
        result["memory"] = {
            "total_bytes": int(vm.total),
            "used_bytes": int(vm.used),
            "percent": round(float(vm.percent), 2),
        }
        result["disk"] = {
            "total_bytes": int(disk.total),
            "used_bytes": int(disk.used),
            "percent": round(float(disk.percent), 2),
        }
        result["process"] = {
            "pid": int(proc.pid),
            "cpu_percent": round(float(proc_cpu), 2),
            "memory_rss_bytes": int(proc_mem),
            "threads": int(proc_threads),
            "open_files": proc_open_files if proc_open_files is None else int(proc_open_files),
        }
        result["metrics_provider"] = "psutil"
    except Exception:
        pass
    return result


def _normalize_local_path(path: str) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="缺少路径参数。")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _render_local_path(path_obj: Path) -> str:
    return str(path_obj)


def _exec_local_command(command: str, cwd: str, timeout_seconds: int) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=(str(_normalize_local_path(cwd)) if str(cwd or "").strip() else None),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "ok": True,
            "timeout": False,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "returncode": int(completed.returncode),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "timeout": True,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
            "returncode": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "timeout": False,
            "stdout": "",
            "stderr": str(exc),
            "returncode": None,
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
        cache_publish_job = cache_publish_job_manager.snapshot(PROJECT_KEY)

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "supported": True,
        "actions": {
            "can_manage_validation": can_manage_validation,
            "can_manage_ai_settings": can_manage_ai,
            "can_publish_cache": can_publish,
            "can_manage_submit_permissions": True,
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


@router.get("/admin/projects/{project_key}/submit-permissions", summary="获取项目提交权限列表")
def list_project_submit_permissions(
    project_key: str,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    normalized_project_key = str(project_key or "").strip()
    if normalized_project_key != PROJECT_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持日报项目提交权限管理。")
    return {
        "ok": True,
        "project_key": normalized_project_key,
        "groups": auth_manager.list_project_submit_groups(normalized_project_key),
    }


@router.post("/admin/projects/{project_key}/submit-permissions", summary="更新用户组项目提交权限")
def update_project_submit_permission(
    project_key: str,
    payload: SubmitPermissionPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    normalized_project_key = str(project_key or "").strip()
    if normalized_project_key != PROJECT_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持日报项目提交权限管理。")
    updated = auth_manager.update_group_project_action(
        group_name=payload.group_name,
        project_key=normalized_project_key,
        action_key="can_submit",
        enabled=payload.can_submit,
    )
    return {
        "ok": True,
        "project_key": normalized_project_key,
        **updated,
    }


@router.get("/admin/projects/{project_key}/page-access-groups", summary="获取项目页面访问用户组列表")
def list_project_page_access_groups(
    project_key: str,
    page_key: str = Query(..., description="页面访问权限键"),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    normalized_project_key = str(project_key or "").strip()
    normalized_page_key = str(page_key or "").strip()
    if normalized_project_key != MONTHLY_DATA_SHOW_PROJECT_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持月度查询页访问权限管理。")
    if normalized_page_key != MONTHLY_DATA_SHOW_QUERY_TOOL_PAGE_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持月度查询工具页面访问权限管理。")
    return {
        "ok": True,
        "project_key": normalized_project_key,
        "page_key": normalized_page_key,
        "groups": auth_manager.list_group_page_access(normalized_project_key, normalized_page_key),
    }


@router.post("/admin/projects/{project_key}/page-access-groups", summary="更新项目页面访问用户组权限")
def update_project_page_access_group(
    project_key: str,
    payload: GroupPageAccessPayload,
    page_key: str = Query(..., description="页面访问权限键"),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    normalized_project_key = str(project_key or "").strip()
    normalized_page_key = str(page_key or "").strip()
    if normalized_project_key != MONTHLY_DATA_SHOW_PROJECT_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持月度查询页访问权限管理。")
    if normalized_page_key != MONTHLY_DATA_SHOW_QUERY_TOOL_PAGE_KEY:
        raise HTTPException(status_code=400, detail="当前仅支持月度查询工具页面访问权限管理。")
    updated = auth_manager.update_group_page_access(
        group_name=payload.group_name,
        project_key=normalized_project_key,
        page_key=normalized_page_key,
        enabled=payload.has_access,
    )
    return {
        "ok": True,
        "project_key": normalized_project_key,
        "page_key": normalized_page_key,
        **updated,
    }


@router.get("/admin/files/directories", summary="列出 backend_data 子目录")
def list_backend_data_directories(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    if not DATA_ROOT.exists() or not DATA_ROOT.is_dir():
        raise HTTPException(status_code=500, detail="backend_data 目录不存在。")
    directories = [
        item.relative_to(DATA_ROOT).as_posix()
        for item in sorted(DATA_ROOT.rglob("*"), key=lambda p: str(p).lower())
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
        if file_path.suffix.lower() not in EDITABLE_EXTENSIONS:
            continue
        if file_path.stat().st_size > MAX_EDITABLE_FILE_SIZE:
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


@router.post("/admin/files/upload", summary="上传后台可编辑文件")
async def upload_backend_file(
    session: AuthSession = Depends(get_current_session),
    directory: str = Query(default="", description="backend_data 下的目标目录相对路径"),
    file: UploadFile = File(..., description="待上传的可编辑文件"),
):
    _ensure_admin_console_access(session)
    target_dir = _resolve_safe_data_path(directory)
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="目标目录不存在。")
    if not file.filename:
        raise HTTPException(status_code=400, detail="上传文件名为空。")
    safe_name = _normalize_upload_filename(file.filename)
    target = (target_dir / safe_name).resolve()
    try:
        target.relative_to(target_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="不允许写入目标目录外文件。") from exc
    content = await file.read()
    if len(content) > MAX_EDITABLE_FILE_SIZE:
        raise HTTPException(status_code=400, detail="上传文件过大，拒绝写入。")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="仅支持 UTF-8 文本文件上传。") from exc
    existed = target.exists()
    target.write_bytes(content)
    return {
        "ok": True,
        "path": target.relative_to(DATA_ROOT).as_posix(),
        "size": len(content),
        "overwritten": existed,
    }


@router.delete("/admin/files", summary="删除后台文件")
def delete_backend_file(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(..., description="backend_data 下待删除文件的相对路径"),
):
    _ensure_admin_console_access(session)
    target = _resolve_safe_data_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在。")
    target.unlink()
    return {"ok": True, "path": target.relative_to(DATA_ROOT).as_posix()}


@router.delete("/admin/files/directories", summary="删除后台目录")
def delete_backend_directory(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(..., description="backend_data 下待删除目录的相对路径"),
):
    _ensure_admin_console_access(session)
    target = _resolve_safe_data_path(path)
    if target == DATA_ROOT:
        raise HTTPException(status_code=400, detail="不允许删除 backend_data 根目录。")
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="目录不存在。")
    if any(target.iterdir()):
        raise HTTPException(status_code=400, detail="目录非空，请先删除目录内文件。")
    target.rmdir()
    return {"ok": True, "path": target.relative_to(DATA_ROOT).as_posix()}


@router.get("/admin/db/tables", summary="获取可编辑数据库表清单")
def list_database_tables(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    with SessionLocal() as db:
        stmt = text(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
            """
        )
        rows = db.execute(stmt).mappings().all()

    tables: List[str] = []
    schemas_map: Dict[str, List[str]] = {}
    for row in rows:
        schema = str(row.get("table_schema") or "public")
        table_name = str(row.get("table_name") or "")
        if not table_name:
            continue
        full_name = f"{schema}.{table_name}" if schema != "public" else table_name
        tables.append(full_name)
        if schema not in schemas_map:
            schemas_map[schema] = []
        schemas_map[schema].append(table_name)

    return {
        "ok": True,
        "tables": tables,
        "schemas": list(schemas_map.keys()),
        "schema_tables_map": schemas_map,
    }


@router.post("/admin/db/table/query", summary="查询数据表内容")
def query_database_table(
    payload: DbTableQueryPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    with SessionLocal() as db:
        meta = _load_table_meta(db, payload.table)
        table_ident = _quote_identifier(meta["table"])
        column_names = list(meta["column_names"])
        if not column_names:
            return {
                "ok": True,
                "table": meta["table"],
                "columns": meta["columns"],
                "pk_columns": meta["pk_columns"],
                "total": 0,
                "rows": [],
            }

        select_cols = ", ".join(_quote_identifier(name) for name in column_names)
        where_clauses: List[str] = []
        query_params: Dict[str, Any] = {"limit": int(payload.limit), "offset": int(payload.offset)}

        search_text = str(payload.search or "").strip()
        if search_text:
            search_param = f"%{search_text}%"
            search_parts: List[str] = []
            for idx, col in enumerate(column_names):
                param_name = f"search_{idx}"
                search_parts.append(f"CAST({_quote_identifier(col)} AS TEXT) ILIKE :{param_name}")
                query_params[param_name] = search_param
            if search_parts:
                where_clauses.append("(" + " OR ".join(search_parts) + ")")

        allowed_ops = {
            "eq",
            "ne",
            "contains",
            "starts_with",
            "ends_with",
            "gt",
            "gte",
            "lt",
            "lte",
            "is_null",
            "not_null",
        }
        for idx, item in enumerate(payload.filters or []):
            if not isinstance(item, dict):
                continue
            col_name = str(item.get("column") or "").strip()
            op = str(item.get("op") or "").strip().lower()
            raw_value = item.get("value")
            if not col_name or col_name not in column_names or op not in allowed_ops:
                continue
            ident = _quote_identifier(col_name)
            param_name = f"flt_{idx}"
            if op == "is_null":
                where_clauses.append(f"{ident} IS NULL")
                continue
            if op == "not_null":
                where_clauses.append(f"{ident} IS NOT NULL")
                continue
            if op == "eq":
                where_clauses.append(f"{ident} = :{param_name}")
                query_params[param_name] = raw_value
                continue
            if op == "ne":
                where_clauses.append(f"{ident} <> :{param_name}")
                query_params[param_name] = raw_value
                continue
            if op == "contains":
                where_clauses.append(f"CAST({ident} AS TEXT) ILIKE :{param_name}")
                query_params[param_name] = f"%{'' if raw_value is None else str(raw_value)}%"
                continue
            if op == "starts_with":
                where_clauses.append(f"CAST({ident} AS TEXT) ILIKE :{param_name}")
                query_params[param_name] = f"{'' if raw_value is None else str(raw_value)}%"
                continue
            if op == "ends_with":
                where_clauses.append(f"CAST({ident} AS TEXT) ILIKE :{param_name}")
                query_params[param_name] = f"%{'' if raw_value is None else str(raw_value)}"
                continue
            if op == "gt":
                where_clauses.append(f"{ident} > :{param_name}")
                query_params[param_name] = raw_value
                continue
            if op == "gte":
                where_clauses.append(f"{ident} >= :{param_name}")
                query_params[param_name] = raw_value
                continue
            if op == "lt":
                where_clauses.append(f"{ident} < :{param_name}")
                query_params[param_name] = raw_value
                continue
            if op == "lte":
                where_clauses.append(f"{ident} <= :{param_name}")
                query_params[param_name] = raw_value

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        order_by = str(payload.order_by or "").strip()
        order_dir = str(payload.order_dir or "asc").strip().lower()
        if order_by and order_by in column_names:
            order_cols = [order_by]
        else:
            order_cols = meta["pk_columns"] or column_names[:1]
        safe_order_dir = "DESC" if order_dir == "desc" else "ASC"
        order_sql = ", ".join(f"{_quote_identifier(name)} {safe_order_dir}" for name in order_cols)
        query_stmt = text(
            f"""
            SELECT {select_cols}
            FROM {table_ident}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :offset
            """
        )
        count_stmt = text(f"SELECT COUNT(*) AS total FROM {table_ident} {where_sql}")
        raw_rows = db.execute(query_stmt, query_params).mappings().all()
        total = int(db.execute(count_stmt, query_params).scalar() or 0)

    rows: List[Dict[str, Any]] = []
    for row in raw_rows:
        normalized: Dict[str, Any] = {}
        for col in column_names:
            normalized[col] = _to_json_value(row.get(col))
        rows.append(normalized)

    return {
        "ok": True,
        "table": meta["table"],
        "columns": meta["columns"],
        "pk_columns": meta["pk_columns"],
        "total": total,
        "limit": int(payload.limit),
        "offset": int(payload.offset),
        "rows": rows,
        "search": search_text,
        "order_by": order_by,
        "order_dir": safe_order_dir.lower(),
    }


@router.post("/admin/db/table/batch-update", summary="批量保存数据表修改")
def batch_update_database_table(
    payload: DbTableBatchUpdatePayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    updates = payload.updates if isinstance(payload.updates, list) else []
    if not updates:
        return {"ok": True, "updated": 0, "matched": 0, "skipped": 0, "failed": []}

    with SessionLocal() as db:
        meta = _load_table_meta(db, payload.table)
        table_ident = _quote_identifier(meta["table"])
        pk_columns = list(meta["pk_columns"])
        if not pk_columns:
            raise HTTPException(status_code=400, detail="该表没有主键，暂不支持在线保存修改。")
        all_columns = set(meta["column_names"])

        updated = 0
        matched = 0
        skipped = 0
        failed: List[Dict[str, Any]] = []

        for idx, item in enumerate(updates):
            key = item.get("key") if isinstance(item, dict) else None
            changes = item.get("changes") if isinstance(item, dict) else None
            if not isinstance(key, dict) or not isinstance(changes, dict):
                failed.append({"index": idx, "reason": "key/changes 结构错误"})
                continue
            missing_pk = [col for col in pk_columns if col not in key]
            if missing_pk:
                failed.append({"index": idx, "reason": f"主键缺失: {', '.join(missing_pk)}"})
                continue

            effective_changes: Dict[str, Any] = {}
            for col_name, value in changes.items():
                if col_name in pk_columns:
                    continue
                if col_name not in all_columns:
                    continue
                effective_changes[col_name] = value
            if not effective_changes:
                skipped += 1
                continue

            set_parts = []
            where_parts = []
            params: Dict[str, Any] = {}
            for col_name, value in effective_changes.items():
                param_name = f"set_{col_name}"
                set_parts.append(f"{_quote_identifier(col_name)} = :{param_name}")
                params[param_name] = value
            for pk_name in pk_columns:
                param_name = f"pk_{pk_name}"
                where_parts.append(f"{_quote_identifier(pk_name)} = :{param_name}")
                params[param_name] = key.get(pk_name)

            stmt = text(
                f"""
                UPDATE {table_ident}
                SET {', '.join(set_parts)}
                WHERE {' AND '.join(where_parts)}
                """
            )
            result = db.execute(stmt, params)
            affected = int(result.rowcount or 0)
            matched += affected
            if affected > 0:
                updated += 1

        db.commit()

    return {
        "ok": True,
        "table": meta["table"],
        "updated": updated,
        "matched": matched,
        "skipped": skipped,
        "failed": failed,
    }


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
        payload.provider,
        payload.newapi_base_url,
        payload.newapi_api_keys or [],
        payload.newapi_model,
        payload.newapi_backup_models or [],
        payload.providers,
        payload.active_provider_id,
        payload.instruction_daily.strip()
        if isinstance(payload.instruction_daily, str)
        else (payload.instruction.strip() if isinstance(payload.instruction, str) else None),
        payload.instruction_monthly.strip()
        if isinstance(payload.instruction_monthly, str)
        else None,
        payload.report_mode,
        payload.enable_validation,
        payload.allow_non_admin_report,
        payload.show_chat_bubble,
    )
    return {"ok": True, **saved}


@router.post("/admin/ai-settings/test", summary="测试全局 AI 连接")
def test_admin_ai_settings(
    payload: AiSettingsConnectionTestPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    _ensure_manage_ai_settings_permission(session)
    try:
        result = ai_runtime.run_ai_connection_test(
            {
                "provider": payload.provider,
                "api_keys": payload.api_keys or [],
                "model": str(payload.model or ""),
                "newapi_base_url": str(payload.newapi_base_url or ""),
                "newapi_api_keys": payload.newapi_api_keys or [],
                "newapi_model": str(payload.newapi_model or ""),
                "providers": payload.providers or [],
                "active_provider_id": str(payload.active_provider_id or ""),
            }
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **result}


@router.post("/admin/cache/publish", summary="发布看板缓存")
def publish_dashboard_cache(
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30),
    preset: str | None = Query(default=None),
):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    try:
        target_dates, selection_label = dashboard_cache.resolve_publish_schedule(
            window=days,
            project_key=PROJECT_KEY,
            preset=preset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    schedule = list(reversed(target_dates))
    snapshot, started = cache_publish_job_manager.start(PROJECT_KEY, schedule)
    return {
        "ok": True,
        "started": started,
        "days": days,
        "preset": preset,
        "selection_label": selection_label,
        "job": snapshot,
    }


@router.get("/admin/cache/publish/status", summary="获取缓存发布任务状态")
def get_cache_publish_status(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    return {"ok": True, "job": cache_publish_job_manager.snapshot(PROJECT_KEY)}


@router.post("/admin/cache/publish/cancel", summary="停止缓存发布任务")
def cancel_cache_publish(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    _ensure_cache_operator(session)
    return {"ok": True, "job": cache_publish_job_manager.request_cancel(PROJECT_KEY)}


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


@router.get("/admin/system/metrics", summary="获取服务器性能指标")
def get_system_metrics(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    return {"ok": True, "metrics": _collect_system_metrics()}


@router.post("/audit/events", summary="上报用户审计事件")
def collect_audit_events(
    payload: AuditBatchPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
):
    events = payload.events or []
    if not events:
        return {"ok": True, "accepted": 0}
    user_agent = request.headers.get("user-agent", "")
    client_ip = _resolve_client_ip(request)
    normalized: List[Dict[str, Any]] = []
    for event in events[:200]:
        normalized.append(
            {
                "ts": event.ts,
                "category": str(event.category or "ui").strip() or "ui",
                "action": str(event.action or "").strip() or "unknown",
                "page": str(event.page or "").strip(),
                "target": str(event.target or "").strip(),
                "detail": event.detail if isinstance(event.detail, dict) else {},
                "username": session.username,
                "group": session.group,
                "unit": session.unit or "",
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )
    written = audit_log.append_events(normalized)
    return {"ok": True, "accepted": len(normalized), "written": written}


@router.get("/admin/audit/events", summary="查询审计日志")
def list_audit_events(
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30),
    username: str = Query(default=""),
    category: str = Query(default=""),
    action: str = Query(default=""),
    keyword: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
):
    _ensure_admin_console_access(session)
    rows = audit_log.query_events(
        days=days,
        username=username,
        category=category,
        action=action,
        keyword=keyword,
        limit=limit,
    )
    return {"ok": True, "events": rows}


@router.get("/admin/audit/stats", summary="获取审计日志分类统计")
def get_audit_stats(
    session: AuthSession = Depends(get_current_session),
    days: int = Query(default=7, ge=1, le=30),
):
    _ensure_admin_console_access(session)
    stats = audit_log.build_stats(days=days)
    return {"ok": True, "stats": stats}


@router.post("/admin/super/login", summary="服务器管理员登录（兼容占位）")
def super_admin_login(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    return {
        "ok": True,
        "token": "",
        "expires_in": 0,
        "message": "当前版本无需页面内服务器管理员登录，直接使用当前服务进程权限执行。",
    }


@router.post("/admin/super/terminal/exec", summary="执行终端命令")
def super_exec_command(
    payload: SuperExecPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    command = str(payload.command or "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="命令不能为空。")
    timeout_seconds = int(payload.timeout_seconds or 20)
    timeout_seconds = max(1, min(timeout_seconds, 180))
    return _exec_local_command(command, str(payload.cwd or ""), timeout_seconds)


@router.get("/admin/super/files/list", summary="列出文件/目录")
def super_list_files(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(default="/"),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(path)
    try:
        if not target.exists():
            raise HTTPException(status_code=404, detail="路径不存在。")
        if not target.is_dir():
            raise HTTPException(status_code=400, detail="目标路径不是目录。")
        items: List[Dict[str, Any]] = []
        children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for child in children:
            items.append(
                {
                    "name": child.name,
                    "path": _render_local_path(child),
                    "is_dir": child.is_dir(),
                    "size": None if child.is_dir() else int(child.stat().st_size),
                }
            )
        return {"ok": True, "path": _render_local_path(target), "items": items}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="路径不存在。") from exc


@router.get("/admin/super/files/read", summary="读取文本文件")
def super_read_file(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(...),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(path)
    try:
        if not target.exists():
            raise HTTPException(status_code=404, detail="文件不存在。")
        if target.is_dir():
            raise HTTPException(status_code=400, detail="目标路径是目录，不能读取文本。")
        content = target.read_text(encoding="utf-8")
        return {"ok": True, "path": _render_local_path(target), "content": content}
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="该文件不是 UTF-8 文本。") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="文件不存在。") from exc


@router.post("/admin/super/files/write", summary="写入文本文件")
def super_write_file(
    payload: SuperFileWritePayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = payload.content.encode("utf-8")
    target.write_bytes(encoded)
    return {"ok": True, "path": _render_local_path(target), "size": len(encoded)}


@router.post("/admin/super/files/mkdir", summary="创建目录")
def super_make_dir(
    payload: SuperMkdirPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": _render_local_path(target)}


@router.post("/admin/super/files/move", summary="移动或重命名")
def super_move_path(
    payload: SuperMovePayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    source = _normalize_local_path(payload.source)
    destination = _normalize_local_path(payload.destination)
    try:
        if not source.exists():
            raise FileNotFoundError(str(source))
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        return {
            "ok": True,
            "source": _render_local_path(source),
            "destination": _render_local_path(destination),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="源路径不存在。") from exc


@router.delete("/admin/super/files", summary="删除文件或目录")
def super_delete_path(
    session: AuthSession = Depends(get_current_session),
    path: str = Query(...),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(path)
    try:
        if not target.exists():
            raise FileNotFoundError(str(target))
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"ok": True, "path": _render_local_path(target)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="目标路径不存在。") from exc


@router.post("/admin/super/files/upload", summary="上传文件到指定目录")
async def super_upload_files(
    session: AuthSession = Depends(get_current_session),
    target_dir: str = Query(...),
    files: List[UploadFile] = File(...),
):
    _ensure_admin_console_access(session)
    target = _normalize_local_path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="target_dir 不是目录。")
    written: List[Dict[str, Any]] = []
    for upload in files[:50]:
        filename = Path(str(upload.filename or "")).name
        if not filename:
            continue
        destination = target / filename
        content = await upload.read()
        destination.write_bytes(content)
        written.append(
            {
                "name": filename,
                "path": _render_local_path(destination),
                "size": len(content),
            }
        )
    return {
        "ok": True,
        "target_dir": _render_local_path(target),
        "files": written,
        "count": len(written),
    }


# ================================================================== #
# 账户与权限管理大盘扩展 API (2026-07-02 多角色重塑版)
# ================================================================== #
from pydantic import BaseModel, Field as PydanticField
from typing import Dict, Any, List, Optional

class AccountSavePayload(BaseModel):
    username: str
    password: str
    group: Optional[str] = None
    groups: Optional[List[str]] = PydanticField(default_factory=list)
    unit: Optional[str] = None
    project_roles: Optional[Dict[str, str]] = PydanticField(default_factory=dict)

class PermissionMatrixUpdatePayload(BaseModel):
    group_name: str
    project_key: str
    type: str  # "page" or "action"
    key: str   # page_key or action_key
    enabled: bool

@router.get("/admin/accounts", summary="获取账户列表及关联元数据")
def list_accounts_metadata(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    auth_manager._ensure_loaded()
    
    # 提取所有用户信息，返回 groups 数组
    accounts_list = []
    for username, record in auth_manager._users_by_name.items():
        accounts_list.append({
            "username": record.username,
            "password": record.password,
            "group": record.group,
            "groups": record.groups,
            "unit": record.unit,
            "project_roles": record.project_roles
        })
        
    # 可选组（全局定义的组）
    available_groups = list(auth_manager._groups.keys())
    
    # 已知单位
    available_units = sorted(list(auth_manager._known_units))
    
    # 子项目列表
    permissions_dir = auth_manager._permissions_path.parent / "permissions"
    available_projects = []
    if permissions_dir.exists() and permissions_dir.is_dir():
        for f in permissions_dir.glob("*.json"):
            if f.name != "global.json":
                available_projects.append(f.stem)
    if not available_projects:
        for group_perm in auth_manager._groups.values():
            for p_key in group_perm.projects.keys():
                if p_key not in available_projects:
                    available_projects.append(p_key)
                    
    return {
        "ok": True,
        "accounts": accounts_list,
        "available_groups": available_groups,
        "available_units": available_units,
        "available_projects": sorted(available_projects)
    }

@router.post("/admin/accounts", summary="新建或保存账户信息")
def save_account_info(
    payload: AccountSavePayload,
    session: AuthSession = Depends(get_current_session)
):
    _ensure_admin_console_access(session)
    
    username = str(payload.username).strip()
    password = str(payload.password).strip()
    group_name = str(payload.group).strip() if payload.group else ""
    unit = str(payload.unit).strip() if payload.unit else None
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码为必填项")
        
    accounts_path = auth_manager._accounts_path
    if not accounts_path.exists():
        raise HTTPException(status_code=500, detail="用户账户配置文件缺失")
        
    try:
        data = json.loads(accounts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"解析账户文件失败: {exc}") from exc
        
    users_raw = data.get("users")
    if not isinstance(users_raw, dict):
        users_raw = {}
        data["users"] = users_raw
        
    # 自适应迁移升级：检查并转换旧的嵌套组列表格式
    is_old_format = False
    for k, v in users_raw.items():
        if isinstance(v, list):
            is_old_format = True
            break
            
    if is_old_format:
        new_users_dict = {}
        for g_name, entries in users_raw.items():
            if isinstance(entries, list):
                for entry in entries:
                    uname = str(entry.get("username", "")).strip()
                    if uname:
                        new_users_dict[uname] = {
                            "password": str(entry.get("password", "")).strip(),
                            "groups": [g_name],
                            "unit": entry.get("unit"),
                            "project_roles": entry.get("project_roles") or {}
                        }
        users_raw = new_users_dict
        data["users"] = users_raw
        
    # 优先读取多选的 groups，如果为空则取兜底
    submitted_groups = payload.groups if (payload.groups is not None and len(payload.groups) > 0) else []
    if not submitted_groups and group_name:
        submitted_groups = [group_name]
    if not submitted_groups:
        submitted_groups = ["unit_filler"]
        
    submitted_groups = [str(g).strip() for g in submitted_groups if g]
    
    users_raw[username] = {
        "password": password,
        "groups": submitted_groups,
        "unit": unit,
        "project_roles": {}
    }
    
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path = accounts_path.with_name(accounts_path.name + ".tmp")
    try:
        temp_path.write_text(serialized + "\n", encoding="utf-8")
        temp_path.replace(accounts_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="保存账户配置失败") from exc
        
    auth_manager._accounts_mtime = None
    auth_manager._ensure_loaded()
    
    return {"ok": True, "message": f"账户 {username} 保存成功"}

@router.delete("/admin/accounts/{username}", summary="物理删除某一用户")
def delete_account_info(
    username: str,
    session: AuthSession = Depends(get_current_session)
):
    _ensure_admin_console_access(session)
    username = str(username).strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
        
    if username == session.username:
        raise HTTPException(status_code=400, detail="无法删除自己当前正在登录 of 账号")
        
    accounts_path = auth_manager._accounts_path
    if not accounts_path.exists():
        raise HTTPException(status_code=500, detail="用户账户配置文件缺失")
        
    try:
        data = json.loads(accounts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"解析账户文件失败: {exc}") from exc
        
    users_raw = data.get("users")
    if not isinstance(users_raw, dict):
        raise HTTPException(status_code=500, detail="账户配置格式异常")
        
    is_old_format = False
    for k, v in users_raw.items():
        if isinstance(v, list):
            is_old_format = True
            break
            
    found = False
    if is_old_format:
        for g_name, user_list in users_raw.items():
            if isinstance(user_list, list):
                new_list = [u for u in user_list if str(u.get("username", "")).strip() != username]
                if len(new_list) < len(user_list):
                    found = True
                users_raw[g_name] = new_list
    else:
        if username in users_raw:
            users_raw.pop(username)
            found = True
            
    if not found:
        raise HTTPException(status_code=404, detail=f"未找到用户 {username}")
        
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path = accounts_path.with_name(accounts_path.name + ".tmp")
    try:
        temp_path.write_text(serialized + "\n", encoding="utf-8")
        temp_path.replace(accounts_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="保存账户配置失败") from exc
        
    auth_manager._accounts_mtime = None
    auth_manager._ensure_loaded()
    
    return {"ok": True, "message": f"账户 {username} 已物理删除"}

@router.get("/admin/permissions/matrix", summary="获取项目与角色的权限矩阵大盘")
def get_permissions_matrix(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    auth_manager._ensure_loaded()
    
    roles_data = {}
    for group_name, g_perm in auth_manager._groups.items():
        proj_perms_dict = {}
        for proj_key, p_perm in g_perm.projects.items():
            proj_perms_dict[proj_key] = {
                "page_access": sorted(list(p_perm.page_access)),
                "actions": {
                    "can_submit": bool(p_perm.actions.can_submit),
                    "can_approve": bool(p_perm.actions.can_approve),
                    "can_revoke": bool(p_perm.actions.can_revoke),
                    "can_publish": bool(p_perm.actions.can_publish),
                    "can_manage_modularization": bool(p_perm.actions.can_manage_modularization),
                    "can_manage_validation": bool(p_perm.actions.can_manage_validation),
                    "can_manage_ai_settings": bool(p_perm.actions.can_manage_ai_settings),
                    "can_manage_ai_sheet_switch": bool(p_perm.actions.can_manage_ai_sheet_switch),
                    "can_extract_xlsx": bool(p_perm.actions.can_extract_xlsx),
                    "can_unlimited_ai_usage": bool(p_perm.actions.can_unlimited_ai_usage),
                    "can_access_admin_console": bool(p_perm.actions.can_access_admin_console)
                }
            }
        roles_data[group_name] = {
            "hierarchy": g_perm.hierarchy,
            "global_pages": sorted(list(g_perm.page_access)),
            "global_actions": {
                "can_submit": bool(g_perm.actions.can_submit),
                "can_approve": bool(g_perm.actions.can_approve),
                "can_revoke": bool(g_perm.actions.can_revoke),
                "can_publish": bool(g_perm.actions.can_publish),
                "can_manage_modularization": bool(g_perm.actions.can_manage_modularization),
                "can_manage_validation": bool(g_perm.actions.can_manage_validation),
                "can_manage_ai_settings": bool(g_perm.actions.can_manage_ai_settings),
                "can_manage_ai_sheet_switch": bool(g_perm.actions.can_manage_ai_sheet_switch),
                "can_extract_xlsx": bool(g_perm.actions.can_extract_xlsx),
                "can_unlimited_ai_usage": bool(g_perm.actions.can_unlimited_ai_usage),
                "can_access_admin_console": bool(g_perm.actions.can_access_admin_console)
            },
            "projects": proj_perms_dict
        }
    
    project_metadata = {}
    all_projects = set()
    for g_perm in auth_manager._groups.values():
        all_projects.update(g_perm.projects.keys())
    
    all_projects_list = ["global"] + sorted(list(all_projects))
    core_actions = ["can_submit", "can_approve", "can_revoke"]
    
    for proj in all_projects_list:
        p_pages = set()
        p_actions = set(core_actions)
        for g_perm in auth_manager._groups.values():
            if proj == "global":
                p_pages.update(g_perm.page_access)
                for k, v in g_perm.actions.__dict__.items():
                    if v:
                        p_actions.add(k)
            else:
                p_perm = g_perm.projects.get(proj)
                if p_perm:
                    p_pages.update(p_perm.page_access)
                    for k, v in p_perm.actions.__dict__.items():
                        if v is not None:
                            p_actions.add(k)
                            
        project_metadata[proj] = {
            "pages": sorted(list(p_pages)),
            "actions": sorted(list(p_actions))
        }
        
    return {
        "ok": True,
        "roles": roles_data,
        "project_metadata": project_metadata,
        "available_projects": all_projects_list
    }

@router.post("/admin/permissions/matrix", summary="更新角色项目级特定权限开关")
def update_permission_matrix_item(
    payload: PermissionMatrixUpdatePayload,
    session: AuthSession = Depends(get_current_session)
):
    _ensure_admin_console_access(session)
    
    group_name = str(payload.group_name).strip()
    project_key = str(payload.project_key).strip()
    p_type = str(payload.type).strip().lower()
    key = str(payload.key).strip()
    enabled = bool(payload.enabled)
    
    if not group_name or not project_key or p_type not in ("page", "action") or not key:
        raise HTTPException(status_code=400, detail="非法的矩阵权限更新参数")
        
    if p_type == "page":
        updated = auth_manager.update_group_page_access(
            group_name=group_name,
            project_key=project_key,
            page_key=key,
            enabled=enabled
        )
    else:
        updated = auth_manager.update_group_project_action(
            group_name=group_name,
            project_key=project_key,
            action_key=key,
            enabled=enabled
        )
        
    return {
        "ok": True,
        "project_key": project_key,
        "group_name": group_name,
        **updated
    }


# --------------------------------------------------------------------------
# 数据库全量备份与按选恢复支持 (PostgreSQL Custom .dump)
# --------------------------------------------------------------------------
DB_BACKUP_DIR = DATA_ROOT / "shared" / "db_backup"
DB_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

class DatabaseRestorePayload(BaseModel):
    filename: str = Field(..., description="备份文件名")
    restore_mode: str = Field("full", description="full | schema_only | data_only")
    clean_first: bool = Field(True, description="还原前清除原对象 (--clean --if-exists)")
    selected_schemas: Optional[List[str]] = Field(default=None, description="要恢复的Schema集合")
    selected_tables: Optional[List[str]] = Field(default=None, description="要恢复的表集合")

class DatabaseInspectPayload(BaseModel):
    filename: str = Field(..., description="备份文件名")

class RestoreJob:
    def __init__(self, job_id: str, filename: str, cmd: List[str], env: dict):
        self.job_id = job_id
        self.filename = filename
        self.cmd = cmd
        self.env = env
        self.status = "running"
        self.logs: List[str] = []
        self.returncode: Optional[int] = None
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.finished_at: Optional[str] = None
        self.lock = threading.Lock()

RESTORE_JOBS: Dict[str, RestoreJob] = {}

def _find_pg_tool(tool_name: str) -> str:
    """寻找 pg_dump / pg_restore 可执行文件路径"""
    found = shutil.which(tool_name)
    if found:
        return found
    possible_paths = [
        rf"D:\Program Files\PostgreSQL\18\bin\{tool_name}.exe",
        rf"D:\Program Files\PostgreSQL\17\bin\{tool_name}.exe",
        rf"D:\Program Files\PostgreSQL\16\bin\{tool_name}.exe",
        rf"D:\Program Files\PostgreSQL\15\bin\{tool_name}.exe",
        rf"C:\Program Files\PostgreSQL\18\bin\{tool_name}.exe",
        rf"C:\Program Files\PostgreSQL\16\bin\{tool_name}.exe",
        rf"C:\Program Files\PostgreSQL\15\bin\{tool_name}.exe",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return tool_name

def _get_pg_env_and_args():
    from backend.db.database_daily_report_25_26 import DATABASE_URL
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"
    dbname = parsed.path.lstrip("/") or "phoenix"
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return host, port, user, password, dbname, env

EAST_8 = timezone(timedelta(hours=8))

@router.get("/admin/database/backups", summary="获取全局数据库备份目录文件列表")
def list_database_backups(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    items = []
    if DB_BACKUP_DIR.exists():
        for p in DB_BACKUP_DIR.iterdir():
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in (".dump", ".sql", ".gz", ".tar", ".custom", ".bak", ""):
                st = p.stat()
                size_mb = st.st_size / (1024 * 1024)
                size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{st.st_size / 1024:.1f} KB"
                mtime = datetime.fromtimestamp(st.st_mtime, tz=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
                items.append({
                    "filename": p.name,
                    "filepath": str(p),
                    "file_size": st.st_size,
                    "file_size_h": size_str,
                    "format": "sql" if p.suffix.lower() == ".sql" else "custom",
                    "created_at": mtime,
                })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "ok": True,
        "backup_dir": str(DB_BACKUP_DIR),
        "backups": items
    }

@router.post("/admin/database/backup", summary="立即创建全量 Custom 格式数据库备份 (.dump)")
def create_database_backup(session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    dump_exe = _find_pg_tool("pg_dump")
    host, port, user, password, dbname, env = _get_pg_env_and_args()
    
    timestamp = datetime.now(tz=EAST_8).strftime("%Y%m%d_%H%M%S")
    filename = f"phoenix_backup_{timestamp}.dump"
    target_path = DB_BACKUP_DIR / filename
    
    cmd = [
        dump_exe,
        "-h", str(host),
        "-p", str(port),
        "-U", str(user),
        "-Fc",
        "-f", str(target_path),
        str(dbname)
    ]
    
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        if res.returncode != 0:
            raise HTTPException(status_code=500, detail=f"数据库备份失败: {res.stderr}")
        
        st = target_path.stat()
        size_mb = st.st_size / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{st.st_size / 1024:.1f} KB"
        
        audit_log.append_events([{
            "actor_user_id": session.username,
            "actor_display_name": getattr(session, 'unit', session.username),
            "action": "database_backup",
            "target_type": "database",
            "target_id": filename,
            "detail": {"filename": filename, "size": size_str}
        }])
        return {
            "ok": True,
            "filename": filename,
            "filepath": str(target_path),
            "file_size": st.st_size,
            "file_size_h": size_str,
            "created_at": datetime.now(tz=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行数据库备份发生异常: {str(e)}")

@router.get("/admin/database/backup/download/{filename}", summary="下载指定数据库备份文件")
def download_database_backup(
    filename: str, 
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None)
):
    auth_token = None
    if authorization and authorization.lower().startswith("bearer "):
        auth_token = authorization.split()[1]
    elif token:
        auth_token = token
        
    if not auth_token:
        raise HTTPException(status_code=401, detail="缺少认证信息")
        
    session = auth_manager.require_session(auth_token)
    _ensure_admin_console_access(session)
    
    safe_filename = Path(filename).name
    target_path = DB_BACKUP_DIR / safe_filename
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="指定备份文件不存在")
    return FileResponse(
        path=target_path,
        filename=safe_filename,
        media_type="application/octet-stream"
    )

@router.delete("/admin/database/backup/{filename}", summary="删除指定数据库备份文件")
def delete_database_backup(filename: str, session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    safe_filename = Path(filename).name
    target_path = DB_BACKUP_DIR / safe_filename
    if target_path.exists() and target_path.is_file():
        target_path.unlink()
        audit_log.append_events([{
            "actor_user_id": session.username,
            "actor_display_name": getattr(session, 'unit', session.username),
            "action": "database_backup_delete",
            "target_type": "database",
            "target_id": safe_filename,
            "detail": {"filename": safe_filename}
        }])
        return {"ok": True, "message": f"成功删除备份文件 {safe_filename}"}
    raise HTTPException(status_code=404, detail="备份文件不存在")

@router.post("/admin/database/upload", summary="上传本地备份文件到备份目录")
def upload_database_backup(file: UploadFile = File(...), session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    safe_name = Path(file.filename).name
    # 若用户上传的文件没有扩展名（如 DBeaver 导出的备份），自动追加 .dump 后缀名
    if not Path(safe_name).suffix:
        safe_name = f"{safe_name}.dump"
    
    dest_path = DB_BACKUP_DIR / safe_name
    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        st = dest_path.stat()
        size_mb = st.st_size / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{st.st_size / 1024:.1f} KB"
        
        audit_log.append_events([{
            "actor_user_id": session.username,
            "actor_display_name": getattr(session, 'unit', session.username),
            "action": "database_backup_upload",
            "target_type": "database",
            "target_id": safe_name,
            "detail": {"filename": safe_name, "size": size_str}
        }])
        return {
            "ok": True,
            "filename": safe_name,
            "file_size": st.st_size,
            "file_size_h": size_str,
            "created_at": datetime.now(tz=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存上传备份文件失败: {str(e)}")

@router.post("/admin/database/inspect", summary="解析备份文件包含的 Schema 与数据表结构")
def inspect_database_backup(payload: DatabaseInspectPayload, session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    safe_name = Path(payload.filename).name
    target_path = DB_BACKUP_DIR / safe_name
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    
    # 只要不是纯文本 .sql 文件，默认作为 PostgreSQL Custom Format 二进制包进行 pg_restore -l 解析
    if not safe_name.lower().endswith(".sql"):
        restore_exe = _find_pg_tool("pg_restore")
        cmd = [restore_exe, "-l", str(target_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            schemas = set()
            tables = []
            for line in res.stdout.splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith(";"):
                    continue
                parts = line_str.split()
                if len(parts) >= 7 and parts[-4] in ("TABLE", "VIEW", "SEQUENCE", "MATERIALIZED VIEW"):
                    schema = parts[-3]
                    tbl_name = parts[-2]
                    if schema and schema not in ("pg_catalog", "information_schema", "-"):
                        schemas.add(schema)
                        if parts[-4] == "TABLE" and tbl_name and not tbl_name.isdigit():
                            tables.append({
                                "schema": schema,
                                "name": tbl_name,
                                "full_name": f"{schema}.{tbl_name}"
                            })
            unique_tables = []
            seen = set()
            for t in tables:
                if t["full_name"] not in seen:
                    seen.add(t["full_name"])
                    unique_tables.append(t)
                    
            return {
                "ok": True,
                "filename": safe_name,
                "is_custom_dump": True,
                "schemas": sorted(list(schemas)),
                "tables": unique_tables
            }
        except Exception as e:
            return {"ok": True, "filename": safe_name, "is_custom_dump": False, "schemas": [], "tables": [], "warning": str(e)}
    else:
        return {
            "ok": True,
            "filename": safe_name,
            "is_custom_dump": False,
            "schemas": ["public", "tube"],
            "tables": []
        }

def _run_restore_thread(job: RestoreJob):
    try:
        proc = subprocess.Popen(
            job.cmd,
            env=job.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        with proc.stdout:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    with job.lock:
                        job.logs.append(line.rstrip())
        proc.wait()
        with job.lock:
            job.returncode = proc.returncode
            job.status = "completed" if proc.returncode == 0 or proc.returncode is None else "completed"
            job.finished_at = datetime.now(tz=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
            job.logs.append(f"▶ 恢复流程结束，进程退出代码: {proc.returncode}")
    except Exception as ex:
        with job.lock:
            job.status = "failed"
            job.finished_at = datetime.now(tz=EAST_8).strftime("%Y-%m-%d %H:%M:%S")
            job.logs.append(f"❌ 恢复过程捕获系统异常: {str(ex)}")

@router.post("/admin/database/restore", summary="启动高级数据库恢复任务")
def start_database_restore(payload: DatabaseRestorePayload, session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    safe_name = Path(payload.filename).name
    target_path = DB_BACKUP_DIR / safe_name
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="指定的恢复备份文件不存在")
    
    host, port, user, password, dbname, env = _get_pg_env_and_args()
    
    if not safe_name.lower().endswith(".sql"):
        restore_exe = _find_pg_tool("pg_restore")
        cmd = [
            restore_exe,
            "-h", str(host),
            "-p", str(port),
            "-U", str(user),
            "-d", str(dbname),
            "--no-owner",
            "-v"
        ]
        if payload.clean_first:
            cmd.extend(["--clean", "--if-exists"])
        if payload.restore_mode == "schema_only":
            cmd.append("-s")
        elif payload.restore_mode == "data_only":
            cmd.append("-a")
            
        if payload.selected_tables:
            for t in payload.selected_tables:
                if t.strip():
                    tbl_name = t.split(".")[-1]
                    cmd.extend(["-t", tbl_name])
        elif payload.selected_schemas:
            for s in payload.selected_schemas:
                if s.strip():
                    cmd.extend(["-n", s.strip()])
                    
        cmd.append(str(target_path))
    else:
        psql_exe = _find_pg_tool("psql")
        cmd = [
            psql_exe,
            "-h", str(host),
            "-p", str(port),
            "-U", str(user),
            "-d", str(dbname),
            "-f", str(target_path)
        ]
        
    job_id = f"restore_{uuid.uuid4().hex[:8]}"
    job = RestoreJob(job_id, safe_name, cmd, env)
    RESTORE_JOBS[job_id] = job
    
    thread = threading.Thread(target=_run_restore_thread, args=(job,), daemon=True)
    thread.start()
    
    audit_log.append_events([{
        "actor_user_id": session.username,
        "actor_display_name": getattr(session, 'unit', session.username),
        "action": "database_restore_start",
        "target_type": "database",
        "target_id": safe_name,
        "detail": {"job_id": job_id, "filename": safe_name, "restore_mode": payload.restore_mode}
    }])
    
    return {
        "ok": True,
        "job_id": job_id,
        "filename": safe_name,
        "status": "running",
        "created_at": job.created_at
    }

@router.get("/admin/database/restore/job/{job_id}", summary="获取数据库恢复任务进度与增量控制台日志")
def get_database_restore_job_status(job_id: str, session: AuthSession = Depends(get_current_session)):
    _ensure_admin_console_access(session)
    job = RESTORE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="恢复任务不存在")
    
    with job.lock:
        logs_copy = list(job.logs)
        status = job.status
        returncode = job.returncode
        created_at = job.created_at
        finished_at = job.finished_at
        filename = job.filename
        
    return {
        "ok": True,
        "job_id": job_id,
        "filename": filename,
        "status": status,
        "returncode": returncode,
        "logs": logs_copy,
        "created_at": created_at,
        "finished_at": finished_at
    }


