# -*- coding: utf-8 -*-
"""
daily_report_25_26 全局管理控制台专有 API：
包含业务操作记录检索、全网提交物理时间戳与 24h 操作计数统计。
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.daily_report_25_26.services.audit_log_service import (
    CLIENT_REPORTABLE_ACTIONS,
    PROJECT_KEY,
    log_session_operation,
    query_submission_logs,
)

router = APIRouter()


class ClientOperationLogPayload(BaseModel):
    """前端纯客户端导出/关键操作上报载荷。"""

    action_type: str = Field(..., min_length=1, max_length=64, description="操作类型（需在白名单内）")
    action_desc: str = Field(..., min_length=1, max_length=500, description="操作说明")
    resource_id: Optional[str] = Field(default=None, max_length=128, description="关联资源标识")
    unit: Optional[str] = Field(default=None, max_length=128, description="可选覆盖所属单位")
    after_value: Optional[Dict[str, Any]] = Field(default=None, description="附加结构化详情")


@router.post("/global-management/operation-logs", summary="上报前端纯客户端业务操作日志")
def record_client_operation_log(
    payload: ClientOperationLogPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """
    接收浏览器端完成的纯前端导出动作（如看板 PDF、每日简报 PDF、展示表 Excel/截图），
    写入 logs.daily_report_operation_logs。
    """
    action_type = str(payload.action_type or "").strip()
    if action_type not in CLIENT_REPORTABLE_ACTIONS:
        raise HTTPException(status_code=422, detail=f"不支持的前端日志上报类型: {action_type}")

    log_session_operation(
        session=session,
        action_type=action_type,
        action_desc=str(payload.action_desc or "").strip(),
        request=request,
        unit=payload.unit,
        resource_id=str(payload.resource_id or "").strip() or None,
        after_value=payload.after_value,
    )
    return {"ok": True}


@router.get("/global-management/submission-logs", summary="读取业务操作记录")
def get_global_management_submission_logs(
    category: Optional[str] = Query(None, description="操作大类: submission | workflow | query"),
    entity_type: Optional[str] = Query(None, description="生产单位或主体分类"),
    action_type: Optional[str] = Query(None, description="具体操作行为类型"),
    operator: Optional[str] = Query(None, description="操作人/账号模糊查询"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页条数"),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """
    专门为全局管理中心提供业务操作记录列表与聚合看板指标。
    """
    offset = (page - 1) * limit
    result = query_submission_logs(
        category=category,
        entity_type=entity_type,
        action_type=action_type,
        operator=operator,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "total": result["total"],
        "page": page,
        "limit": limit,
        "latest_submitted_at": result.get("latest_submitted_at"),
        "recent_24h_count": result.get("recent_24h_count", 0),
        "submission_24h_count": result.get("submission_24h_count", 0),
        "workflow_24h_count": result.get("workflow_24h_count", 0),
        "query_24h_count": result.get("query_24h_count", 0),
        "rows": result["logs"],
    }
