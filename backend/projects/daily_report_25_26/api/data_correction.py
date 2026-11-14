"""日报修正申请 API，不改变原有普通填报权限。"""
from datetime import date
from typing import Any, Literal, Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.daily_report_25_26.services import data_correction as service
from backend.projects.daily_report_25_26.services.audit_log_service import (
    log_session_operation,
)

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
def create(payload: CorrectionPayload, request: Request, actor: AuthSession = Depends(get_current_session)):
    res = service.create_request(actor, payload)
    log_session_operation(
        actor,
        "SUBMIT_CORRECTION",
        f"提交日报数据修正申请 #{res.get('id')}（{res.get('sheet_name') or payload.sheet_key}，业务日 {payload.biz_date.isoformat()}，原因：{payload.reason}）",
        request=request,
        unit=res.get("unit_id") or getattr(actor, "unit", None),
        resource_id=f"correction:{res.get('id')}",
        after_value={"sheet_key": payload.sheet_key, "biz_date": payload.biz_date.isoformat(), "changes_count": len(res.get("changes") or [])},
    )
    return res


@router.post("/{request_id}/resolve")
def resolve(request_id: int, payload: ResolutionPayload, request: Request, actor: AuthSession = Depends(get_current_session)):
    res = service.resolve_request(actor, request_id, payload.action, payload.note.strip())
    action_type = "APPROVE_CORRECTION" if payload.action == "approve" else "REJECT_CORRECTION"
    verb = {"approve": "确认并执行", "reject": "驳回", "cancel": "取消"}[payload.action]
    log_session_operation(
        actor,
        action_type,
        f"{verb}数据修正申请 #{request_id}（{res.get('sheet_name') or res.get('sheet_key')}，业务日 {res.get('biz_date')}）",
        request=request,
        unit=res.get("unit_id") or getattr(actor, "unit", None),
        resource_id=f"correction:{request_id}",
        after_value={"action": payload.action, "status": res.get("status"), "note": payload.note.strip()},
    )
    return res
