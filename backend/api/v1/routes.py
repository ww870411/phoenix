"""v1 版本业务路由."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from .daily_report_25_26 import router as project_router


router = APIRouter()
PROJECT_LIST_FILE = Path(__file__).resolve().parents[3] / "backend_data" / "项目列表.json"


@router.get("/ping", summary="连通性测试", tags=["system"])
def ping():
    """用于最基本的连通性测试。"""
    return {"ok": True, "message": "pong"}


@router.get("/projects", summary="获取项目列表")
def list_projects():
    if not PROJECT_LIST_FILE.exists():
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": "项目列表文件缺失"},
        )
    try:
        raw = PROJECT_LIST_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "项目列表文件格式错误"},
        )

    if not isinstance(data, list):
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "项目列表需为数组"},
        )

    projects = []
    for item in data:
        if not isinstance(item, dict):
            continue
        project_id = item.get("project_id")
        project_name = item.get("project_name") or project_id
        if project_id:
            projects.append({"project_id": project_id, "project_name": project_name})

    if not projects:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "message": "项目列表为空"},
        )

    return {"projects": projects}


# 统一项目前缀：/api/v1/projects/daily_report_25_26
router.include_router(project_router, prefix="/projects/daily_report_25_26")
