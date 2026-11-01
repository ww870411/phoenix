"""每日简报专属接口；权限严格限定 Global_admin。"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session
from backend.services.workflow_status import workflow_status_manager
from ..services.daily_brief import PROJECT_KEY, build_daily_brief

router = APIRouter()


def list_data_dates(db):
    """从底表列举全部数据日期，发布状态不再限制管理员查询范围。"""
    return [day.isoformat() for day in db.execute(text(
        "SELECT DISTINCT date FROM daily_basic_data WHERE date IS NOT NULL ORDER BY date DESC"
    )).scalars().all()]


@router.get("/daily-brief", summary="获取每日简报")
def get_daily_brief(
    show_date: date | None = Query(default=None, description="业务日期，留空优先取最新发布日"),
    session: AuthSession = Depends(get_current_session),
):
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="每日简报仅限 Global_admin 访问")
    published = workflow_status_manager.list_published_dates(PROJECT_KEY)
    with SessionLocal() as db:
        # 保留已发布但底表被清理的历史日期，兼容已有入口；其余日期来自实际数据。
        available = sorted(set(list_data_dates(db)) | set(published), reverse=True)
        metadata = {"available_dates": available, "published_dates": published,
                    "latest_published_date": published[0] if published else None}
        if show_date is not None and show_date.isoformat() not in available:
            raise HTTPException(status_code=422, detail="所选日期暂无数据")
        if not available:
            return {"ok": True, "date": None, **metadata, "message": "暂无日报数据。"}
        target = show_date or date.fromisoformat(published[0] if published else available[0])
        result = build_daily_brief(db, target)
    return {**result, **metadata, "is_published": target.isoformat() in published}
