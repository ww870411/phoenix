# -*- coding: utf-8 -*-
"""
系统消息中心服务 (System Message & Inbox Service)。

存储架构：
在 PostgreSQL 的 schema: logs 下管理 logs.system_messages 表。

核心能力：
1. 联合会审待办通知、结案通报自动生成；
2. 个人私信互相联络支持 (sender_username -> receiver_username)；
3. 管理员全网广播与按角色广播 (receiver_username = 'ALL' / 'ROLE:xxx')；
4. 消息已读状态跟踪、分类聚合、未读角标秒级统计。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_KEY = "insulation_pipe_supply_2026"

_TABLE_ENSURED = False


def _ensure_message_table_exist() -> None:
    """确保 logs.system_messages 消息中心数据表存在 (自动迁移与自愈)。"""
    global _TABLE_ENSURED
    if _TABLE_ENSURED:
        return

    session = SessionLocal()
    try:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS logs;"))
        session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS logs.system_messages (
                id BIGSERIAL PRIMARY KEY,
                project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
                msg_type VARCHAR(32) NOT NULL DEFAULT 'joint_review',
                category VARCHAR(32) NOT NULL DEFAULT 'work',
                sender_username VARCHAR(64) NOT NULL DEFAULT 'SYSTEM',
                sender_name VARCHAR(128) NOT NULL DEFAULT '系统消息',
                sender_role VARCHAR(64) NOT NULL DEFAULT 'SYSTEM',
                receiver_username VARCHAR(64) NOT NULL,
                receiver_entity_id VARCHAR(64),
                title VARCHAR(256) NOT NULL,
                content TEXT NOT NULL,
                action_url VARCHAR(512),
                biz_type VARCHAR(64),
                biz_id VARCHAR(128),
                extra_data JSONB DEFAULT '{}'::jsonb,
                is_read BOOLEAN NOT NULL DEFAULT FALSE,
                read_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_sys_msg_receiver ON logs.system_messages (receiver_username, is_read);
            CREATE INDEX IF NOT EXISTS idx_sys_msg_created ON logs.system_messages (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sys_msg_biz ON logs.system_messages (biz_type, biz_id);
            """
            )
        )
        session.commit()
        _TABLE_ENSURED = True
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"初始化 logs.system_messages 消息中心表失败: {exc}") from exc
    finally:
        session.close()


def create_system_message(
    receiver_username: str,
    title: str,
    content: str,
    msg_type: str = "joint_review",
    category: str = "work",
    sender_username: str = "SYSTEM",
    sender_name: str = "系统通知",
    sender_role: str = "SYSTEM",
    receiver_entity_id: Optional[str] = None,
    action_url: Optional[str] = None,
    biz_type: Optional[str] = None,
    biz_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    project_key: str = PROJECT_KEY,
) -> int:
    """写入单条系统/站内消息。"""
    _ensure_message_table_exist()
    session = SessionLocal()
    try:
        stmt = text(
            """
            INSERT INTO logs.system_messages (
                project_key, msg_type, category,
                sender_username, sender_name, sender_role,
                receiver_username, receiver_entity_id,
                title, content, action_url, biz_type, biz_id,
                extra_data, is_read, created_at
            ) VALUES (
                :project_key, :msg_type, :category,
                :sender_username, :sender_name, :sender_role,
                :receiver_username, :receiver_entity_id,
                :title, :content, :action_url, :biz_type, :biz_id,
                CAST(:extra_data AS jsonb), FALSE, NOW()
            ) RETURNING id;
            """
        )
        res = session.execute(
            stmt,
            {
                "project_key": project_key,
                "msg_type": msg_type,
                "category": category,
                "sender_username": sender_username,
                "sender_name": sender_name,
                "sender_role": sender_role,
                "receiver_username": receiver_username,
                "receiver_entity_id": receiver_entity_id,
                "title": title,
                "content": content,
                "action_url": action_url,
                "biz_type": biz_type,
                "biz_id": biz_id,
                "extra_data": json.dumps(extra_data or {}, ensure_ascii=False),
            },
        )
        row = res.fetchone()
        session.commit()
        return int(row[0]) if row else 0
    except Exception as exc:
        session.rollback()
        # 降级容错，确保不会阻塞主业务流转
        print(f"[system_message_service] 写入消息失败: {exc}")
        return 0
    finally:
        session.close()


def create_batch_system_messages(
    receivers: List[str],
    title: str,
    content: str,
    msg_type: str = "joint_review",
    category: str = "work",
    sender_username: str = "SYSTEM",
    sender_name: str = "系统通知",
    sender_role: str = "SYSTEM",
    action_url: Optional[str] = None,
    biz_type: Optional[str] = None,
    biz_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    project_key: str = PROJECT_KEY,
) -> int:
    """批量向多名用户发送消息。"""
    if not receivers:
        return 0
    _ensure_message_table_exist()
    session = SessionLocal()
    success_count = 0
    try:
        stmt = text(
            """
            INSERT INTO logs.system_messages (
                project_key, msg_type, category,
                sender_username, sender_name, sender_role,
                receiver_username, title, content, action_url,
                biz_type, biz_id, extra_data, is_read, created_at
            ) VALUES (
                :project_key, :msg_type, :category,
                :sender_username, :sender_name, :sender_role,
                :receiver_username, :title, :content, :action_url,
                :biz_type, :biz_id, CAST(:extra_data AS jsonb), FALSE, NOW()
            );
            """
        )
        for r_user in set(receivers):
            if not r_user:
                continue
            session.execute(
                stmt,
                {
                    "project_key": project_key,
                    "msg_type": msg_type,
                    "category": category,
                    "sender_username": sender_username,
                    "sender_name": sender_name,
                    "sender_role": sender_role,
                    "receiver_username": r_user,
                    "title": title,
                    "content": content,
                    "action_url": action_url,
                    "biz_type": biz_type,
                    "biz_id": biz_id,
                    "extra_data": json.dumps(extra_data or {}, ensure_ascii=False),
                },
            )
            success_count += 1
        session.commit()
        return success_count
    except Exception as exc:
        session.rollback()
        print(f"[system_message_service] 批量写入消息失败: {exc}")
        return 0
    finally:
        session.close()


def get_user_inbox_messages(
    username: str,
    user_group: str,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    msg_type: Optional[str] = None,
) -> Dict[str, Any]:
    """查询用户的收件箱列表与未读总数。"""
    _ensure_message_table_exist()
    session = SessionLocal()
    try:
        role_target = f"ROLE:{user_group}" if user_group else "NONE"
        base_where = """
            WHERE (receiver_username = :username OR receiver_username = 'ALL' OR receiver_username = :role_target)
        """
        params: Dict[str, Any] = {
            "username": username,
            "role_target": role_target,
        }

        if unread_only:
            base_where += " AND is_read = FALSE"
        if msg_type:
            base_where += " AND msg_type = :msg_type"
            params["msg_type"] = msg_type

        # 统计当前未读数
        unread_sql = text(
            """
            SELECT COUNT(*) FROM logs.system_messages
            WHERE (receiver_username = :username OR receiver_username = 'ALL' OR receiver_username = :role_target)
              AND is_read = FALSE;
            """
        )
        unread_count = session.execute(unread_sql, {"username": username, "role_target": role_target}).scalar() or 0

        # 总记录数
        count_sql = text(f"SELECT COUNT(*) FROM logs.system_messages {base_where};")
        total_count = session.execute(count_sql, params).scalar() or 0

        # 分页记录
        offset = max(0, (page - 1) * page_size)
        params["limit"] = page_size
        params["offset"] = offset

        query_sql = text(
            f"""
            SELECT id, project_key, msg_type, category,
                   sender_username, sender_name, sender_role,
                   receiver_username, receiver_entity_id,
                   title, content, action_url, biz_type, biz_id,
                   extra_data, is_read, read_at, created_at
            FROM logs.system_messages
            {base_where}
            ORDER BY is_read ASC, created_at DESC
            LIMIT :limit OFFSET :offset;
            """
        )
        rows = session.execute(query_sql, params).fetchall()

        items = []
        for r in rows:
            created_at_dt = r[17]
            created_at_str = created_at_dt.strftime("%Y-%m-%d %H:%M") if created_at_dt else "--"
            items.append(
                {
                    "id": r[0],
                    "project_key": r[1],
                    "msg_type": r[2],
                    "category": r[3],
                    "sender_username": r[4],
                    "sender_name": r[5],
                    "sender_role": r[6],
                    "receiver_username": r[7],
                    "receiver_entity_id": r[8],
                    "title": r[9],
                    "content": r[10],
                    "action_url": r[11],
                    "biz_type": r[12],
                    "biz_id": r[13],
                    "extra_data": r[14] if isinstance(r[14], dict) else {},
                    "is_read": bool(r[15]),
                    "read_at": r[16].strftime("%Y-%m-%d %H:%M") if r[16] else None,
                    "created_at": created_at_str,
                }
            )

        return {
            "ok": True,
            "unread_count": int(unread_count),
            "total_count": int(total_count),
            "page": page,
            "page_size": page_size,
            "items": items,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"查询收件箱消息失败: {exc}") from exc
    finally:
        session.close()


def mark_message_as_read(message_id: int, username: str) -> bool:
    """标记单条消息为已读。"""
    _ensure_message_table_exist()
    session = SessionLocal()
    try:
        stmt = text(
            """
            UPDATE logs.system_messages
            SET is_read = TRUE, read_at = NOW()
            WHERE id = :id AND (receiver_username = :username OR receiver_username = 'ALL' OR receiver_username LIKE 'ROLE:%');
            """
        )
        session.execute(stmt, {"id": message_id, "username": username})
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        print(f"[system_message_service] 标读失败: {exc}")
        return False
    finally:
        session.close()


def mark_all_messages_as_read(username: str, user_group: str) -> int:
    """一键标记该用户的所有未读消息为已读。"""
    _ensure_message_table_exist()
    session = SessionLocal()
    try:
        role_target = f"ROLE:{user_group}" if user_group else "NONE"
        stmt = text(
            """
            UPDATE logs.system_messages
            SET is_read = TRUE, read_at = NOW()
            WHERE (receiver_username = :username OR receiver_username = 'ALL' OR receiver_username = :role_target)
              AND is_read = FALSE;
            """
        )
        res = session.execute(stmt, {"username": username, "role_target": role_target})
        updated = res.rowcount
        session.commit()
        return updated
    except Exception as exc:
        session.rollback()
        print(f"[system_message_service] 全部标读失败: {exc}")
        return 0
    finally:
        session.close()


def get_unread_message_count(username: str, user_group: str) -> int:
    """快速获取未读消息总数 (极速轻量查询)。"""
    _ensure_message_table_exist()
    session = SessionLocal()
    try:
        role_target = f"ROLE:{user_group}" if user_group else "NONE"
        stmt = text(
            """
            SELECT COUNT(*) FROM logs.system_messages
            WHERE (receiver_username = :username OR receiver_username = 'ALL' OR receiver_username = :role_target)
              AND is_read = FALSE;
            """
        )
        cnt = session.execute(stmt, {"username": username, "role_target": role_target}).scalar() or 0
        return int(cnt)
    except Exception:
        return 0
    finally:
        session.close()
