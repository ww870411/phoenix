# -*- coding: utf-8 -*-
"""主城区供热运行联合评价模型接口；严格限定 Global_admin 访问。"""

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
    """仅允许 Global_admin 访问的主城区供热联合评价计算接口。"""
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="主城区供热联合评价模型仅限 Global_admin 访问")

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
