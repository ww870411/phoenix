from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.services.project_data_paths import get_project_root

PROJECT_KEY = "page_showcase"
ALLOWED_HTML_SUFFIXES = {".html", ".htm"}

router = APIRouter(tags=["page_showcase"])
public_router = APIRouter(tags=["page_showcase"])


class PageShowcaseItem(BaseModel):
    file_name: str
    page_name: str
    open_path: str
    size_bytes: int
    updated_at: str


def _workspace_root() -> Path:
    root = get_project_root(PROJECT_KEY)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_html_name(file_name: str) -> str:
    normalized = Path(str(file_name or "").strip()).name
    if not normalized:
        raise HTTPException(status_code=422, detail="HTML 文件名不能为空")
    suffix = Path(normalized).suffix.lower()
    if suffix not in ALLOWED_HTML_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_HTML_SUFFIXES))
        raise HTTPException(status_code=422, detail=f"仅支持以下页面格式：{allowed}")
    return normalized


def _resolve_html_file(file_name: str) -> Path:
    root = _workspace_root().resolve()
    safe_name = _safe_html_name(file_name)
    target = (root / safe_name).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=403, detail="非法页面路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="页面文件不存在")
    return target


def _list_html_pages() -> List[PageShowcaseItem]:
    root = _workspace_root()
    pages: List[PageShowcaseItem] = []
    for item in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file():
            continue
        if item.name.startswith("."):
            continue
        if item.suffix.lower() not in ALLOWED_HTML_SUFFIXES:
            continue
        stat = item.stat()
        pages.append(
            PageShowcaseItem(
                file_name=item.name,
                page_name=item.name,
                open_path=f"/projects/{PROJECT_KEY}/view/{quote(item.name)}",
                size_bytes=int(stat.st_size),
                updated_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            )
        )
    return pages


@router.get("/page-showcase/pages", summary="读取页面展示项目中的 HTML 页面列表")
def list_page_showcase_pages() -> Dict[str, object]:
    pages = _list_html_pages()
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "directory": str(_workspace_root()),
        "pages": [item.model_dump() for item in pages],
    }


@router.get("/page-showcase/html/{file_name}", summary="读取指定 HTML 页面内容")
def read_page_showcase_html(file_name: str) -> Dict[str, object]:
    target = _resolve_html_file(file_name)
    try:
        html = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="页面文件不是有效的 UTF-8 文本") from exc
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "file_name": target.name,
        "page_name": target.name,
        "html": html,
    }


@public_router.get(
    "/page-showcase/public-html/{file_name}",
    summary="公开访问指定 HTML 页面内容",
    response_class=HTMLResponse,
)
def public_page_showcase_html(file_name: str) -> HTMLResponse:
    target = _resolve_html_file(file_name)
    try:
        html = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="页面文件不是有效的 UTF-8 文本") from exc
    return HTMLResponse(content=html)
