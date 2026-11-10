"""日报修正申请 API，不改变原有普通填报权限。"""
from datetime import date
from typing import Any, Literal, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.daily_report_25_26.services import data_correction as service

router = APIRouter(prefix="/data-corrections", tags=["数据修正申请"])


class CellChange(BaseModel):
    row_index: int = Field(ge=0)
    col_index: int = Field(ge=0)
    old_value: Any = None
    new_value: Any = None
    version: Optional[str] = None


class CorrectionPayload(BaseModel):
    sheet_key: str
    biz_date: date
    reason: str = Field(min_length=1, max_length=2000)
    changes: list[CellChange] = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value):
        if not value.strip():
            raise ValueError("请填写修正原因")
        return value.strip()


class ResolutionPayload(BaseModel):
    action: Literal["approve", "reject", "cancel"]
    note: str = Field(default="", max_length=2000)


@router.get("/snapshot")
def get_snapshot(sheet_key: str, biz_date: date, actor: AuthSession = Depends(get_current_session)):
    return service.snapshot(actor, sheet_key, biz_date)


@router.get("")
def get_records(status: Optional[Literal["pending", "approved", "rejected", "cancelled"]] = None,
                offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                actor: AuthSession = Depends(get_current_session)):
    return service.list_requests(actor, status, offset, limit)


@router.post("")
def create(payload: CorrectionPayload, actor: AuthSession = Depends(get_current_session)):
    return service.create_request(actor, payload)


@router.post("/{request_id}/resolve")
def resolve(request_id: int, payload: ResolutionPayload, actor: AuthSession = Depends(get_current_session)):
    return service.resolve_request(actor, request_id, payload.action, payload.note.strip())
