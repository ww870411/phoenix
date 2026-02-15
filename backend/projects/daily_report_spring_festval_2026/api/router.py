# -*- coding: utf-8 -*-
"""
春节简化日报项目路由入口。
"""

from fastapi import APIRouter

from .temperature_trend import public_router as temperature_public_router
from .xlsx_extract import router as xlsx_extract_router

router = APIRouter()
router.include_router(xlsx_extract_router)

public_router = APIRouter()
public_router.include_router(temperature_public_router)

__all__ = ["router", "public_router"]
