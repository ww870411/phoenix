# -*- coding: utf-8 -*-
"""
daily_report_25_26 项目路由入口（项目目录化过渡层）。

说明：
- 先按“功能块”把接口逐步下沉到项目目录；
- 未迁移部分仍复用旧实现，确保现网行为稳定。
"""

from fastapi import APIRouter

from .legacy_full import public_router as legacy_public_router
from .legacy_full import router as legacy_router

from .dashboard import public_router as dashboard_public_router
from .dashboard import router as dashboard_router
from .template_designer import router as template_designer_router

router = APIRouter()
router.include_router(legacy_router)
router.include_router(dashboard_router)
router.include_router(template_designer_router)

public_router = APIRouter()
public_router.include_router(legacy_public_router)
public_router.include_router(dashboard_public_router)

__all__ = ["router", "public_router"]
