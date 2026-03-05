"""v1 版本业务路由."""

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from backend.services.project_data_paths import (
    bootstrap_project_files,
    ensure_project_dirs,
    get_project_file_status,
    resolve_project_list_path,
)
from backend.services.project_modularization import resolve_project_modularization_files

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from backend.services.auth_manager import AuthSession, get_current_session
from .auth import router as auth_router
from .admin_console import router as admin_console_router
from .project_router_registry import PROJECT_ROUTER_REGISTRY


router = APIRouter()
PROJECT_LIST_FILE = resolve_project_list_path()


def _load_project_entries() -> Tuple[Dict[str, Dict[str, Any]], Optional[JSONResponse]]:
    if not PROJECT_LIST_FILE.exists():
        return {}, JSONResponse(
            status_code=404,
            content={"ok": False, "message": "项目列表文件缺失"},
        )
    try:
        raw = PROJECT_LIST_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}, JSONResponse(
            status_code=500,
            content={"ok": False, "message": "项目列表文件格式错误"},
        )

    if not isinstance(data, dict):
        return {}, JSONResponse(
            status_code=500,
            content={"ok": False, "message": "项目列表需为对象（以项目ID为键）"},
        )

    # 仅保留字典值
    entries: Dict[str, Dict[str, Any]] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, dict):
            entries[key] = value

    if not entries:
        return {}, JSONResponse(
            status_code=404,
            content={"ok": False, "message": "项目列表为空"},
        )
    return entries, None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _normalize_pages(project_entry: Dict[str, Any]) -> List[Dict[str, str]]:
    pages_raw = project_entry.get("pages")
    pages: List[Dict[str, str]] = []
    if isinstance(pages_raw, dict):
        for page_url, meta in pages_raw.items():
            if not isinstance(page_url, str) or not isinstance(meta, dict):
                continue
            name = meta.get("页面名称") or meta.get("page_name") or page_url
            data_source = meta.get("数据源") or meta.get("data_source") or ""
            description = meta.get("页面描述") or meta.get("page_description") or ""
            slug_source = page_url
            slug_candidate = _slugify(slug_source) or _slugify(name) or "page"
            pages.append(
                {
                    "page_key": slug_candidate,  # 路由用的安全段
                    "page_name": name,
                    "config_file": data_source,
                    "page_url": page_url,
                    "data_source": data_source,
                    "page_description": description,
                    "description": description,
                }
            )
    elif isinstance(pages_raw, list):
        # 兼容旧格式：数组中每项为 { 页面名: 模板文件 }
        seen: Set[str] = set()
        fallback_counter = 0
        for entry in pages_raw:
            if not isinstance(entry, dict):
                continue
            for page_name, config_file in entry.items():
                if not isinstance(page_name, str) or not isinstance(config_file, str):
                    continue
                slug_source = Path(config_file).stem or page_name
                slug_candidate = _slugify(slug_source)
                if not slug_candidate:
                    slug_candidate = f"page_{fallback_counter}"
                    fallback_counter += 1
                slug = slug_candidate
                while slug in seen:
                    fallback_counter += 1
                    slug = f"{slug_candidate}_{fallback_counter}"
                seen.add(slug)
                pages.append(
                    {
                        "page_key": slug,
                        "page_name": page_name,
                        "config_file": config_file,
                        "page_url": slug,
                        "data_source": config_file,
                        "page_description": "",
                        "description": "",
                    }
                )
    return pages


def _is_project_enabled_for_group(project_entry: Dict[str, Any], group_name: str) -> bool:
    availability = project_entry.get("availability", True)

    if isinstance(availability, bool):
        return availability

    normalized_group = str(group_name or "").strip()
    if isinstance(availability, str):
        return normalized_group == availability.strip()

    if isinstance(availability, list):
        allowed_groups = {
            str(item).strip()
            for item in availability
            if isinstance(item, str) and str(item).strip()
        }
        return normalized_group in allowed_groups

    return bool(availability)


def _extract_json_response_message(error: JSONResponse, fallback: str) -> str:
    try:
        payload = json.loads(error.body.decode("utf-8"))
    except Exception:
        return fallback
    return str(payload.get("message") or fallback)


def _ensure_project_visible_and_accessible(
    project_id: str,
    project_entry: Dict[str, Any],
    session: AuthSession,
) -> None:
    if not _is_project_enabled_for_group(project_entry, session.group):
        raise HTTPException(status_code=403, detail=f"项目 {project_id} 当前不可用")
    if not session.has_project_access(project_id):
        raise HTTPException(status_code=403, detail=f"当前账号无项目 {project_id} 的访问权限")


def _build_project_access_dependency(project_id: str) -> Callable[..., None]:
    def _project_access_guard(session: AuthSession = Depends(get_current_session)) -> None:
        entries, error = _load_project_entries()
        if error:
            message = _extract_json_response_message(error, "项目列表不可用")
            raise HTTPException(status_code=error.status_code, detail=message)
        target = entries.get(project_id)
        if not isinstance(target, dict):
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 未配置")
        _ensure_project_visible_and_accessible(project_id, target, session)

    return _project_access_guard


def _ensure_project_modularization_permission(session: AuthSession, project_id: str) -> None:
    action_flags = session.get_project_action_flags(project_id)
    if not action_flags.can_manage_modularization:
        raise HTTPException(status_code=403, detail="当前账号无项目目录化操作权限。")


@router.get("/ping", summary="连通性测试", tags=["system"])
def ping():
    """用于最基本的连通性测试。"""
    return {"ok": True, "message": "pong"}


@router.get("/projects", summary="获取项目列表")
def list_projects(session: AuthSession = Depends(get_current_session)):
    entries, error = _load_project_entries()
    if error:
        return error

    projects = []
    for project_id, cfg in entries.items():
        if not isinstance(project_id, str) or not isinstance(cfg, dict):
            continue
        if not _is_project_enabled_for_group(cfg, session.group):
            continue
        # 允许多种命名回落
        project_name = (
            cfg.get("project_name")
            or cfg.get("项目名称")
            or cfg.get("名称")
            or project_id
        )
        if session.has_project_access(project_id):
            projects.append({"project_id": project_id, "project_name": project_name})

    if not projects:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": "项目列表为空"},
        )

    return {"projects": projects}


@router.get("/projects/{project_id}/pages", summary="获取项目页面列表")
def list_project_pages(
    project_id: str,
    session: AuthSession = Depends(get_current_session),
):
    entries, error = _load_project_entries()
    if error:
        return error

    target = entries.get(project_id)
    if not isinstance(target, dict):
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": f"项目 {project_id} 未配置"},
        )
    _ensure_project_visible_and_accessible(project_id, target, session)

    pages = _normalize_pages(target)
    if not pages:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": f"项目 {project_id} 未配置页面"},
        )

    allowed_pages = session.get_project_page_access(project_id)
    available_page_keys = {
        str(page.get("page_key") or "").strip()
        for page in pages
        if isinstance(page, dict)
    }
    has_project_override = project_id in session.permissions.projects
    if has_project_override and not allowed_pages:
        pages = []
    elif allowed_pages:
        pages = [page for page in pages if page.get("page_key") in allowed_pages]

    project_name = (
        target.get("project_name")
        or target.get("项目名称")
        or target.get("名称")
        or project_id
    )
    return {
        "project_id": project_id,
        "project_name": project_name,
        "pages": pages,
    }


@router.get("/projects/{project_id}/modularization/status", summary="查看项目目录化迁移状态")
def get_project_modularization_status(
    project_id: str,
    session: AuthSession = Depends(get_current_session),
):
    entries, error = _load_project_entries()
    if error:
        return error
    if project_id not in entries:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": f"项目 {project_id} 未配置"},
        )
    _ensure_project_visible_and_accessible(project_id, entries[project_id], session)
    _ensure_project_modularization_permission(session, project_id)
    project_entry = entries.get(project_id) or {}
    config_files, runtime_files = resolve_project_modularization_files(project_id, project_entry)
    status = get_project_file_status(project_id, config_files, runtime_files)
    return {
        "ok": True,
        "project_id": project_id,
        "config_files": config_files,
        "runtime_files": runtime_files,
        "status": status,
    }


@router.post("/projects/{project_id}/modularization/bootstrap", summary="初始化项目目录并复制旧配置")
def bootstrap_project_modularization(
    project_id: str,
    session: AuthSession = Depends(get_current_session),
):
    entries, error = _load_project_entries()
    if error:
        return error
    if project_id not in entries:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": f"项目 {project_id} 未配置"},
        )
    _ensure_project_visible_and_accessible(project_id, entries[project_id], session)
    _ensure_project_modularization_permission(session, project_id)
    project_entry = entries.get(project_id) or {}
    config_files, runtime_files = resolve_project_modularization_files(project_id, project_entry)
    dirs = ensure_project_dirs(project_id)
    bootstrap = bootstrap_project_files(project_id, config_files, runtime_files)
    status = get_project_file_status(project_id, config_files, runtime_files)
    return {
        "ok": True,
        "project_id": project_id,
        "dirs": dirs,
        "bootstrap": bootstrap,
        "status": status,
    }


# 认证路由
router.include_router(auth_router, prefix="/auth")
router.include_router(admin_console_router)

# 统一项目前缀：/api/v1/projects/<project_key>
for project_key, routers in PROJECT_ROUTER_REGISTRY.items():
    private_router = routers.get("router")
    public_router = routers.get("public_router")
    prefix = f"/projects/{project_key}"
    dependency = _build_project_access_dependency(project_key)
    if private_router is not None:
        router.include_router(private_router, prefix=prefix, dependencies=[Depends(dependency)])
    if public_router is not None:
        router.include_router(public_router, prefix=prefix, dependencies=[Depends(dependency)])
