# -*- coding: utf-8 -*-
"""
insulation_pipe_supply_2026 项目路由入口。
"""

from fastapi import APIRouter

from .workspace import public_router as workspace_public_router
from .workspace import router as workspace_router
from .joint_review import router as joint_review_router
from .system_messages import router as system_messages_router

router = APIRouter()
router.include_router(workspace_router)
router.include_router(joint_review_router)
router.include_router(system_messages_router)

public_router = APIRouter()
public_router.include_router(workspace_public_router)

__all__ = ["router", "public_router"]

