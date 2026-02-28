# -*- coding: utf-8 -*-
"""
monthly_data_pull 项目路由入口。
"""

from fastapi import APIRouter

from .workspace import public_router as workspace_public_router
from .workspace import router as workspace_router

router = APIRouter()
router.include_router(workspace_router)

public_router = APIRouter()
public_router.include_router(workspace_public_router)

__all__ = ["router", "public_router"]

