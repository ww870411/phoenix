"""
v1 版本业务路由

说明
- 仅提供系统通用路由；
- 规范化统一的版本前缀由 `main.py` 统一挂载到 `/api/v1`；
- 本项目统一到 `/api/v1/projects/daily_report_25_26` 前缀。
"""

from fastapi import APIRouter
from .daily_report_25_26 import router as project_router


router = APIRouter()


@router.get("/ping", summary="连通性测试", tags=["system"])
def ping():
    """用于最基本的连通性测试。"""
    return {"ok": True, "message": "pong"}


# 统一项目前缀：/api/v1/projects/daily_report_25_26
router.include_router(project_router, prefix="/projects/daily_report_25_26")
