"""
v1 版本业务路由

说明：
- 仅提供基础连通性路由；
- 与规范保持一致的版本前缀由 `main.py` 统一挂载到 `/api/v1`；
- 后续将按模块拆分到子路由文件（如 `template.py`/`submit.py`/`query.py`）。
"""

from fastapi import APIRouter
from .daily_report_25_26 import router as dr_25_26_router


router = APIRouter()


@router.get("/ping", summary="连通性测试", tags=["system"])
def ping():
    """用于基本连通性测试。"""
    return {"ok": True, "message": "pong"}

# 项目级前缀路由：/api/v1/daily_report_25_26
router.include_router(dr_25_26_router, prefix="/daily_report_25_26")
