# -*- coding: utf-8 -*-
"""smart_heating_platform 项目路由汇总入口。"""

from fastapi import APIRouter

from .dicts import router as dicts_router
from .faults import router as faults_router
from .reports import router as reports_router
from .settings import router as settings_router

router = APIRouter()
router.include_router(settings_router)
router.include_router(reports_router)
router.include_router(faults_router)
router.include_router(dicts_router)

public_router = APIRouter()

__all__ = ["router", "public_router"]
