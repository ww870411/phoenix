# -*- coding: utf-8 -*-
"""
系统消息中心 API (System Message & Inbox REST Endpoints)。

提供：
1. 个人收件箱消息列表分页查询；
2. 极速未读消息数统计 (供顶栏收件箱 Badge 实时轮询)；
3. 标记已读 / 一键全部标为已读；
4. 管理员广播与站内信发送接口 (为未来联络与广播功能就绪)。
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.insulation_pipe_supply_2026.services.system_message_service import (
    create_system_message,
    get_unread_message_count,
    get_user_inbox_messages,
    mark_all_messages_as_read,
    mark_message_as_read,
)

router = APIRouter(prefix="/system-messages", tags=["System Messages & Inbox"])

DEFAULT_PROJECT_KEY = "insulation_pipe_supply_2026"


class SendDirectMessagePayload(BaseModel):
    receiver_username: str = Field(..., description="接收人用户名")
    title: str = Field(..., min_length=1, max_length=256, description="消息标题")
    content: str = Field(..., min_length=1, description="消息内容正文")
    category: str = Field("chat", description="分类")
    action_url: Optional[str] = Field(None, description="快捷跳转链接")


class BroadcastMessagePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=256, description="广播标题")
    content: str = Field(..., min_length=1, description="广播内容正文")
    target: str = Field("ALL", description="广播目标: 'ALL' 或 'ROLE:xxx'")
    category: str = Field("broadcast", description="分类")


@router.get("/my")
async def get_my_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    msg_type: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """获取当前登录用户的收件箱列表。"""
    return get_user_inbox_messages(
        username=session.username,
        user_group=session.group,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        msg_type=msg_type,
    )


@router.get("/unread-count")
async def get_my_unread_count(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """极速获取当前登录用户的未读消息数。"""
    count = get_unread_message_count(username=session.username, user_group=session.group)
    return {"ok": True, "unread_count": count}


@router.post("/{message_id}/read")
async def mark_read(
    message_id: int,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """标记单条消息为已读。"""
    success = mark_message_as_read(message_id=message_id, username=session.username)
    return {"ok": success}


@router.post("/read-all")
async def mark_all_read(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """一键标记收件箱所有消息为已读。"""
    updated_count = mark_all_messages_as_read(username=session.username, user_group=session.group)
    return {"ok": True, "updated_count": updated_count}


@router.post("/send-direct")
async def send_direct_message(
    payload: SendDirectMessagePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """站内人员互相联络发信接口 (为协同联络功能就绪)。"""
    msg_id = create_system_message(
        receiver_username=payload.receiver_username,
        title=payload.title,
        content=payload.content,
        msg_type="direct_chat",
        category=payload.category,
        sender_username=session.username,
        sender_name=session.unit or session.username,
        sender_role=session.group,
        action_url=payload.action_url,
        project_key=DEFAULT_PROJECT_KEY,
    )
    return {"ok": True, "message_id": msg_id}


@router.post("/broadcast")
async def broadcast_message(
    payload: BroadcastMessagePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    """管理员发布系统公告广播。"""
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅全局超级管理员有权发布广播")

    msg_id = create_system_message(
        receiver_username=payload.target,
        title=f"📢 {payload.title}",
        content=payload.content,
        msg_type="broadcast",
        category="broadcast",
        sender_username=session.username,
        sender_name="系统管理员",
        sender_role=session.group,
        project_key=DEFAULT_PROJECT_KEY,
    )
    return {"ok": True, "message_id": msg_id}
