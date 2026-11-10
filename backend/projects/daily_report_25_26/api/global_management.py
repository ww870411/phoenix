# -*- coding: utf-8 -*-
"""
daily_report_25_26 全局管理控制台专有 API：
包含业务操作记录检索、全网提交物理时间戳与 24h 操作计数统计。
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.daily_report_25_26.services.audit_log_service import (
    query_submission_logs,
    save_operation_log,
    PROJECT_KEY,
)

router = APIRouter()


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
