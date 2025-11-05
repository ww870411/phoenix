"""v1 版本业务路由."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.config import DATA_DIRECTORY

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from backend.services.auth_manager import AuthSession, get_current_session
from .auth import router as auth_router
from .daily_report_25_26 import router as project_router, public_router as public_project_router


router = APIRouter()
PROJECT_LIST_FILE = DATA_DIRECTORY / "项目列表.json"


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


@router.get("/ping", summary="连通性测试", tags=["system"])
def ping():
    """用于最基本的连通性测试。"""
    return {"ok": True, "message": "pong"}


@router.get("/projects", summary="获取项目列表")
def list_projects():
    entries, error = _load_project_entries()
    if error:
        return error

    projects = []
    for project_id, cfg in entries.items():
        if not isinstance(project_id, str) or not isinstance(cfg, dict):
            continue
        # 允许多种命名回落
        project_name = (
            cfg.get("project_name")
            or cfg.get("项目名称")
            or cfg.get("名称")
            or project_id
        )
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

    pages = _normalize_pages(target)
    if not pages:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": f"项目 {project_id} 未配置页面"},
        )

    allowed_pages = session.permissions.page_access
    if allowed_pages:
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


# 认证路由
router.include_router(auth_router, prefix="/auth")

# 统一项目前缀：/api/v1/projects/daily_report_25_26
router.include_router(project_router, prefix="/projects/daily_report_25_26")
router.include_router(public_project_router, prefix="/projects/daily_report_25_26")
