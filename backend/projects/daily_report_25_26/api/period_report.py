"""生产运行汇报接口；初版沿用每日简报管理员可见范围。"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session
from .daily_brief import list_data_dates
from ..services.period_report import build_period_report, validate_period

router = APIRouter()


@router.get('/period-report')
def period_report(start: date | None = None, end: date | None = None, include_prev: bool = True,
                  session: AuthSession = Depends(get_current_session)):
    if session.group != 'Global_admin':
        raise HTTPException(403, '生产运行汇报仅限 Global_admin 访问')
    if (start is None) != (end is None):
        raise HTTPException(422, '请同时提供起止日期')
    if start is not None:
        try:
            validate_period(start, end)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    with SessionLocal() as db:
        if start is None:
            dates = list_data_dates(db)
            return {'latestDate': dates[0] if dates else None}
        return build_period_report(db, start, end, include_prev)
