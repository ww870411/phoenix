# -*- coding: utf-8 -*-
"""主城区供热运行联合评价模型接口；面向所有有权访问生产日报项目的用户组开放。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session
from ..services.joint_evaluation import build_joint_evaluation

router = APIRouter()


@router.get("/joint-evaluation", summary="获取主城区供热联合评价模型测算结果")
def get_joint_evaluation(
    mode: str = Query(default="single", description="评价模式：single（单日）、rolling（周期滚动）、range（自定义时段）"),
    biz_date: Optional[date] = Query(default=None, description="单日模式目标日期（留空默认取当前业务日期）"),
    start_date: Optional[date] = Query(default=None, description="自定义时段起始日期"),
    end_date: Optional[date] = Query(default=None, description="自定义时段/滚动模式截止日期"),
    period_days: int = Query(default=1, ge=1, le=60, description="滚动模式下单个周期包含的有效天数"),
    period_count: int = Query(default=7, ge=1, le=60, description="显示周期数量（单日模式控制附带轨迹天数）"),
    session: AuthSession = Depends(get_current_session),
):
    """允许所有具备 daily_report_25_26 项目访问权限的用户组访问主城区供热联合评价接口。"""
    has_project_access = getattr(session, "has_project_access", None)
    if callable(has_project_access) and not has_project_access("daily_report_25_26"):
        raise HTTPException(status_code=403, detail="当前账号无权访问主城区供热联合评价模型")

    try:
        with SessionLocal() as db:
            return build_joint_evaluation(
                db,
                mode=mode,
                biz_date=biz_date,
                start_date=start_date,
                end_date=end_date,
                period_days=period_days,
                period_count=period_count,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
