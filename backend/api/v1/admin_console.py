# -*- coding: utf-8 -*-
"""全局管理后台接口。"""

from __future__ import annotations

import json
import platform
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from backend.config import DATA_DIRECTORY
from backend.services import audit_log
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
APP_START_TS = time.time()
MAX_EDITABLE_FILE_SIZE = 2 * 1024 * 1024  # 2MB
EDITABLE_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
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


class AuditEventPayload(BaseModel):
    category: str = "ui"
    action: str
    page: str = ""
    target: str = ""
    detail: Dict[str, Any] = Field(default_factory=dict)
    ts: str = ""


class AuditBatchPayload(BaseModel):
    events: List[AuditEventPayload] = Field(default_factory=list)


class SuperLoginPayload(BaseModel):
    username: str
    password: str


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


SUPER_SESSION_TTL_SECONDS = 12 * 60 * 60
SUPER_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}


def _get_super_credential_path() -> Path:
    return (DATA_ROOT / "shared" / "auth" / "super_admin.json").resolve()


def _load_super_credentials() -> Dict[str, str]:
    path = _get_super_credential_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                username = str(payload.get("username") or "").strip()
                password = str(payload.get("password") or "").strip()
                if username and password:
                    return {"username": username, "password": password}
        except Exception:
            pass
    return {"username": "root", "password": "root123456"}


def _prune_super_tokens() -> None:
    now = int(time.time())
    expired = [
        token
        for token, meta in SUPER_TOKEN_STORE.items()
        if int(meta.get("expires_at") or 0) <= now
    ]
    for token in expired:
        SUPER_TOKEN_STORE.pop(token, None)


def _issue_super_token(username: str) -> str:
    _prune_super_tokens()
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    SUPER_TOKEN_STORE[token] = {
        "username": username,
        "issued_at": now,
        "expires_at": now + SUPER_SESSION_TTL_SECONDS,
    }
    return token


def _require_super_token(
    x_super_admin_token: str = Header(default="", alias="X-Super-Admin-Token"),
) -> Dict[str, Any]:
    _prune_super_tokens()
    token = str(x_super_admin_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="缺少超级管理员令牌。")
    meta = SUPER_TOKEN_STORE.get(token)
    if not meta:
        raise HTTPException(status_code=401, detail="超级管理员令牌无效或已过期。")
    return meta


def _resolve_super_path(path: str) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="缺少路径参数。")
    return Path(raw).expanduser().resolve()


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
    client_ip = request.client.host if request.client else ""
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


@router.post("/admin/super/login", summary="超级管理员登录")
def super_admin_login(
    payload: SuperLoginPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_admin_console_access(session)
    credential = _load_super_credentials()
    username = str(payload.username or "").strip()
    password = str(payload.password or "").strip()
    if username != credential["username"] or password != credential["password"]:
        raise HTTPException(status_code=401, detail="超级管理员用户名或密码错误。")
    token = _issue_super_token(username)
    return {
        "ok": True,
        "token": token,
        "expires_in": SUPER_SESSION_TTL_SECONDS,
        "username": username,
    }


@router.post("/admin/super/terminal/exec", summary="执行终端命令")
def super_exec_command(
    payload: SuperExecPayload,
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
):
    _ensure_admin_console_access(session)
    command = str(payload.command or "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="命令不能为空。")
    timeout_seconds = int(payload.timeout_seconds or 20)
    timeout_seconds = max(1, min(timeout_seconds, 180))
    cwd = _resolve_super_path(payload.cwd) if str(payload.cwd or "").strip() else None
    if cwd is not None and not cwd.exists():
        raise HTTPException(status_code=400, detail="cwd 不存在。")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "timeout": True,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
            "returncode": None,
        }
    return {
        "ok": True,
        "timeout": False,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "returncode": result.returncode,
    }


@router.get("/admin/super/files/list", summary="列出文件/目录")
def super_list_files(
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
    path: str = Query(default="/"),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="路径不存在。")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="目标路径不是目录。")
    items: List[Dict[str, Any]] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        try:
            size = child.stat().st_size if child.is_file() else None
        except Exception:
            size = None
        items.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size": size,
            }
        )
    return {"ok": True, "path": str(target), "items": items}


@router.get("/admin/super/files/read", summary="读取文本文件")
def super_read_file(
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
    path: str = Query(...),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在。")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="该文件不是 UTF-8 文本。") from exc
    return {"ok": True, "path": str(target), "content": content}


@router.post("/admin/super/files/write", summary="写入文本文件")
def super_write_file(
    payload: SuperFileWritePayload,
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": str(target), "size": len(payload.content.encode("utf-8"))}


@router.post("/admin/super/files/mkdir", summary="创建目录")
def super_make_dir(
    payload: SuperMkdirPayload,
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(payload.path)
    target.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(target)}


@router.post("/admin/super/files/move", summary="移动或重命名")
def super_move_path(
    payload: SuperMovePayload,
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
):
    _ensure_admin_console_access(session)
    source = _resolve_super_path(payload.source)
    destination = _resolve_super_path(payload.destination)
    if not source.exists():
        raise HTTPException(status_code=404, detail="源路径不存在。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return {"ok": True, "source": str(source), "destination": str(destination)}


@router.delete("/admin/super/files", summary="删除文件或目录")
def super_delete_path(
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
    path: str = Query(...),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="目标路径不存在。")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": str(target)}


@router.post("/admin/super/files/upload", summary="上传文件到指定目录")
async def super_upload_files(
    session: AuthSession = Depends(get_current_session),
    _super: Dict[str, Any] = Depends(_require_super_token),
    target_dir: str = Query(...),
    files: List[UploadFile] = File(...),
):
    _ensure_admin_console_access(session)
    target = _resolve_super_path(target_dir)
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
                "path": str(destination),
                "size": len(content),
            }
        )
    return {"ok": True, "target_dir": str(target), "files": written, "count": len(written)}
