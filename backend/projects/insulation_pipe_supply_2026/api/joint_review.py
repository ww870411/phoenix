# -*- coding: utf-8 -*-
"""
保温管与管件物流链：多方联合会审 API 路由 (Joint Review API Router)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.insulation_pipe_supply_2026.services.joint_review_service import (
    admin_arbitrate_joint_review,
    cancel_joint_review,
    create_joint_review,
    get_joint_review_detail,
    get_pending_review_notifications,
    list_joint_reviews,
    vote_joint_review,
)

router = APIRouter(prefix="/joint-reviews", tags=["insulation_pipe_supply_2026_joint_review"])


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


class CreateJointReviewPayload(BaseModel):
    order_category: str = Field(..., description="物料大类: pipe (直管) 或 fitting (管件)")
    delivery_id: int = Field(..., ge=1, description="原发货单 ID")
    proposed_patch: Dict[str, Any] = Field(..., description="拟修正数据字典")
    review_reason: str = Field(..., min_length=2, description="提请会审事由说明")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="凭证附件列表")


class VoteJointReviewPayload(BaseModel):
    vote_decision: str = Field(..., description="表决意见: approve (同意) 或 reject (不同意)")
    vote_opinion: Optional[str] = Field(default="", description="表决补充说明或不同意理由")
    target_entity_type: Optional[str] = Field(default=None, description="管理员代为表决的目标主体类型 (例如 supplier, site_manager, construction_unit)")
    target_entity_id: Optional[str] = Field(default=None, description="管理员代为表决的目标主体 ID")


class CancelJointReviewPayload(BaseModel):
    cancel_reason: Optional[str] = Field(default="", description="撤回会审理由")


class ArbitrateJointReviewPayload(BaseModel):
    arbitration_decision: str = Field(..., description="仲裁决策: force_approve (强制通过) 或 force_reject (强制终止)")
    arbitration_reason: str = Field(..., min_length=2, description="管理员仲裁理由依据")


@router.post("/create", summary="发起多方联合会审")
def handle_create_joint_review(
    payload: CreateJointReviewPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    client_ip = _get_client_ip(request)
    display_name = session.unit or session.username
    return create_joint_review(
        order_category=payload.order_category,
        delivery_id=payload.delivery_id,
        proposed_patch=payload.proposed_patch,
        review_reason=payload.review_reason,
        attachments=payload.attachments,
        operator_username=session.username,
        operator_name=display_name,
        operator_group=session.group,
        client_ip=client_ip,
    )


@router.post("/{review_id}/vote", summary="责任主体签署会审意见")
def handle_vote_joint_review(
    review_id: int,
    payload: VoteJointReviewPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    client_ip = _get_client_ip(request)
    display_name = session.unit or session.username
    return vote_joint_review(
        review_id=review_id,
        vote_decision=payload.vote_decision,
        vote_opinion=payload.vote_opinion or "",
        session_username=session.username,
        session_name=display_name,
        session_group=session.group,
        client_ip=client_ip,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
    )


@router.post("/{review_id}/cancel", summary="发起人撤回联合会审")
def handle_cancel_joint_review(
    review_id: int,
    payload: CancelJointReviewPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    client_ip = _get_client_ip(request)
    return cancel_joint_review(
        review_id=review_id,
        cancel_reason=payload.cancel_reason or "",
        session_username=session.username,
        session_group=session.group,
        client_ip=client_ip,
    )


@router.post("/{review_id}/admin-arbitrate", summary="超级管理员终局裁决仲裁")
def handle_admin_arbitrate_joint_review(
    review_id: int,
    payload: ArbitrateJointReviewPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    client_ip = _get_client_ip(request)
    return admin_arbitrate_joint_review(
        review_id=review_id,
        arbitration_decision=payload.arbitration_decision,
        arbitration_reason=payload.arbitration_reason,
        session_username=session.username,
        session_group=session.group,
        client_ip=client_ip,
    )


@router.get("/list", summary="查询联合会审列表")
def handle_list_joint_reviews(
    tab: str = Query("all", description="分类: all | pending_my_vote | my_initiated | history"),
    order_category: Optional[str] = Query(None, description="物料类别: pipe | fitting"),
    section_1_id: Optional[str] = Query(None, description="需求标段 ID"),
    supply_entity_id: Optional[str] = Query(None, description="供给主体 ID"),
    review_status: Optional[str] = Query(None, description="状态: voting | approved | rejected | cancelled"),
    search: Optional[str] = Query(None, description="单号/理由/经办人关键字"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    return list_joint_reviews(
        tab=tab,
        order_category=order_category,
        section_1_id=section_1_id,
        supply_entity_id=supply_entity_id,
        review_status=review_status,
        search=search,
        page=page,
        limit=limit,
        session_username=session.username,
        session_group=session.group,
    )


@router.get("/notifications", summary="获取待办会审通知与红点")
def handle_get_review_notifications(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    return get_pending_review_notifications(
        session_username=session.username,
        session_group=session.group,
    )


@router.get("/{review_id}", summary="获取单笔联合会审完整详情")
def handle_get_joint_review_detail(
    review_id: int,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    return get_joint_review_detail(
        review_id=review_id,
        session_username=session.username,
        session_group=session.group,
    )
