# -*- coding: utf-8 -*-
"""
保温管与管件物资流转：多方联合会审服务 (Joint Review Service)。

核心职责：
1. 会审主单表 (tube.tube_order_reviews) 与 表决明细表 (tube.tube_review_votes) 数据自愈与生命周期管理；
2. 提请联合会审：白名单字段安全校验、状态互斥锁判定、场景主体动态编排；
3. 多方表决会签：主体按 Entity/角色归一化核验、全票同意原子修单、异议公开挂起；
4. 发起人撤回与管理员终局仲裁；
5. 待办消息汇总与每日提醒。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.audit_log_service import save_operation_log
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    get_config_list,
    load_tube_config,
)

def _json_serialize_default(obj: Any) -> Any:
    """处理 json.dumps 无法直接序列化的 Decimal、datetime、date 等对象。"""
    if isinstance(obj, Decimal):
        return float(obj) if (obj % 1 > 0) else int(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def _dumps_json(data: Any) -> str:
    """安全地将任意字典/列表对象序列化为 JSON 字符串。"""
    return json.dumps(data, default=_json_serialize_default, ensure_ascii=False)

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_KEY = "insulation_pipe_supply_2026"

# 终局裁决/仲裁权默认白名单（首批特许裁决人员）
DEFAULT_ARBITRATOR_ACCOUNTS: Set[str] = {"王玮", "李绍", "张亮"}


def get_arbitrator_accounts() -> Set[str]:
    """获取拥有联合会审终局裁决/仲裁权的用户账号列表（支持 tube_config.json 动态配置 + 默认底线兜底）。"""
    accounts = set(DEFAULT_ARBITRATOR_ACCOUNTS)
    try:
        from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config
        cfg = load_tube_config() or {}
        custom_accounts = (
            cfg.get("arbitration_config", {}).get("arbitrator_accounts")
            or cfg.get("arbitrator_accounts")
            or cfg.get("joint_review_config", {}).get("arbitrators")
            or []
        )
        if isinstance(custom_accounts, list):
            for acc in custom_accounts:
                if acc and isinstance(acc, str):
                    accounts.add(acc.strip())
    except Exception as e:
        logger.warning(f"读取裁决员配置失败，使用默认底线名单: {e}")
    return accounts


def check_user_can_arbitrate(session_username: str, session_group: str) -> bool:
    """判定用户是否具备联合会审终局裁决/仲裁权（超级管理员或特许裁决员）。"""
    if session_group in ("Global_admin", "dev_admin"):
        return True
    if session_username and session_username.strip() in get_arbitrator_accounts():
        return True
    return False

# 修正字段白名单
PIPE_ALLOWED_PATCH_FIELDS = {
    "shipped_qty",
    "pipe_model_id",
    "vehicle_plate_no",
    "ship_contact_name",
    "ship_contact_phone",
    "ship_remark",
}

FITTING_ALLOWED_PATCH_FIELDS = {
    "shipped_qty",
    "fitting_type",
    "model_spec",
    "unit",
    "vehicle_plate_no",
    "ship_contact_name",
    "ship_contact_phone",
    "ship_remark",
    "items",
}

# 绝对禁止修改的字段（冻结）
FROZEN_FIELDS = {"order_no", "shipment_no", "supply_entity_id", "section_1_id"}

_tables_initialized = False


def ensure_joint_review_tables() -> None:
    """初始化检查并确保联合会审相关数据表与索引存在。"""
    global _tables_initialized
    if _tables_initialized:
        return

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS tube.tube_order_reviews (
            id BIGSERIAL PRIMARY KEY,
            review_no VARCHAR(64) UNIQUE NOT NULL,
            project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
            order_category VARCHAR(32) NOT NULL,
            delivery_id BIGINT NOT NULL,
            order_no VARCHAR(64) NOT NULL,
            section_1_id VARCHAR(64) NOT NULL,
            supply_entity_id VARCHAR(64) NOT NULL,
            trigger_scene VARCHAR(32) NOT NULL,
            pre_status VARCHAR(32) NOT NULL,
            review_status VARCHAR(32) NOT NULL DEFAULT 'voting',
            initiator_role VARCHAR(64) NOT NULL,
            initiator_name VARCHAR(128) NOT NULL,
            initiator_username VARCHAR(128) NOT NULL,
            review_reason TEXT NOT NULL,
            attachments JSONB DEFAULT '[]'::jsonb,
            original_snapshot JSONB NOT NULL,
            proposed_patch JSONB NOT NULL,
            required_entities JSONB NOT NULL,
            approved_entities JSONB DEFAULT '[]'::jsonb,
            rejected_entities JSONB DEFAULT '[]'::jsonb,
            resolution_summary TEXT,
            finalized_at TIMESTAMPTZ,
            finalized_by VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_order_reviews_delivery ON tube.tube_order_reviews(order_category, delivery_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_order_reviews_status ON tube.tube_order_reviews(review_status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_order_reviews_sec_sup ON tube.tube_order_reviews(section_1_id, supply_entity_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS tube.tube_review_votes (
            id BIGSERIAL PRIMARY KEY,
            review_id BIGINT NOT NULL REFERENCES tube.tube_order_reviews(id) ON DELETE CASCADE,
            entity_type VARCHAR(64) NOT NULL,
            entity_id VARCHAR(64) NOT NULL,
            voter_username VARCHAR(128) NOT NULL,
            voter_name VARCHAR(128) NOT NULL,
            vote_decision VARCHAR(32) NOT NULL,
            vote_opinion TEXT,
            voted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_tube_review_vote_entity UNIQUE(review_id, entity_type, entity_id)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_review_votes_review_id ON tube.tube_review_votes(review_id);
        """,
        """
        ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS pre_review_status VARCHAR(32);
        """,
        """
        ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS pre_review_status VARCHAR(32);
        """,
    ]

    session = SessionLocal()
    try:
        for stmt in ddl_statements:
            session.execute(text(stmt))
        _ensure_status_constraints(session)
        session.commit()
        _tables_initialized = True
    except Exception as exc:
        session.rollback()
        import logging
        logging.getLogger("uvicorn.error").warning(f"联合会审数据表初始化异常: {exc}")
    finally:
        session.close()


def _ensure_status_constraints(session) -> None:
    """确保 tube_delivery 与 tube_fitting_delivery 的状态 CHECK 约束包含 'under_review'。"""
    try:
        # 1. 检查 tube.tube_delivery 状态约束
        res_del = session.execute(text("""
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'tube' AND c.conname = 'chk_tube_delivery_status';
        """)).scalar()
        if res_del and "'under_review'" not in res_del:
            session.execute(text("ALTER TABLE tube.tube_delivery DROP CONSTRAINT IF EXISTS chk_tube_delivery_status;"))
            session.execute(text("""
                ALTER TABLE tube.tube_delivery ADD CONSTRAINT chk_tube_delivery_status
                    CHECK (status IN (
                        'pending_arrival',
                        'cancelled',
                        'pending_receive',
                        'pending_warehouse',
                        'completed',
                        'pending_diff_approve',
                        'under_review'
                    ));
            """))

        # 2. 检查 tube.tube_fitting_delivery 状态约束
        res_fit_st = session.execute(text("""
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'tube' AND c.conname = 'chk_tube_fitting_status';
        """)).scalar()
        if res_fit_st and "'under_review'" not in res_fit_st:
            session.execute(text("ALTER TABLE tube.tube_fitting_delivery DROP CONSTRAINT IF EXISTS chk_tube_fitting_status;"))
            session.execute(text("""
                ALTER TABLE tube.tube_fitting_delivery ADD CONSTRAINT chk_tube_fitting_status
                    CHECK (status IN (
                        'pending_arrival',
                        'pending_receive',
                        'pending_warehouse',
                        'completed',
                        'cancelled',
                        'pending_diff_approve',
                        'under_review'
                    ));
            """))

        # 3. 检查 tube.tube_fitting_delivery 状态证据约束
        res_fit_ev = session.execute(text("""
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'tube' AND c.conname = 'chk_tube_fitting_state_evidence';
        """)).scalar()
        if res_fit_ev and "under_review" not in res_fit_ev:
            session.execute(text("ALTER TABLE tube.tube_fitting_delivery DROP CONSTRAINT IF EXISTS chk_tube_fitting_state_evidence;"))
            session.execute(text("""
                ALTER TABLE tube.tube_fitting_delivery ADD CONSTRAINT chk_tube_fitting_state_evidence
                    CHECK (
                        (status = 'under_review') OR
                        (status = 'pending_arrival' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
                        (status = 'pending_receive' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
                        (status = 'pending_warehouse' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
                        (status = 'completed' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NOT NULL AND cancel_at IS NULL) OR
                        (status = 'cancelled' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NOT NULL)
                    );
            """))
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").warning(f"状态约束自愈检查异常: {exc}")


ensure_joint_review_tables()


def _generate_review_no() -> str:
    """生成带日期的唯一会审单号，例如 REV-20261008-123456。"""
    now = datetime.now(BEIJING_TZ)
    date_str = now.strftime("%Y%m%d")
    micro_str = now.strftime("%H%M%S%f")[:8]
    return f"REV-{date_str}-{micro_str}"


def _get_delivery_info(session, order_category: str, delivery_id: int) -> Optional[Dict[str, Any]]:
    """查询指定直管或管件发货单详情。"""
    if order_category == "pipe":
        sql = text("""
            SELECT id, supply_entity_id, order_no, shipment_no, vehicle_plate_no,
                   section_1_id, pipe_model_id, shipped_qty, arrived_qty, received_qty,
                   shipped_at, ship_contact_name, ship_contact_phone, ship_remark,
                   status, pre_review_status
            FROM tube.tube_delivery
            WHERE id = :id
        """)
    else:
        sql = text("""
            SELECT id, supply_entity_id, order_no, shipment_no, vehicle_plate_no,
                   section_1_id, fitting_type, model_spec, shipped_qty, arrived_qty,
                   shipped_at, ship_contact_name, ship_contact_phone, ship_remark,
                   unit, status, pre_review_status
            FROM tube.tube_fitting_delivery
            WHERE id = :id
        """)
    row = session.execute(sql, {"id": delivery_id}).mappings().first()
    return dict(row) if row else None


def _resolve_supplier_name(cfg: Dict[str, Any], entity_id: str) -> str:
    for item in get_config_list(cfg, "supply_entities"):
        sid = str(item.get("entity_id") or "").strip()
        if sid.lower() == entity_id.lower():
            return str(item.get("entity_name") or sid)
    return entity_id


def _resolve_section_name(cfg: Dict[str, Any], section_1_id: str) -> str:
    for item in get_config_list(cfg, "demand_entities"):
        sid = str(item.get("section_1_id") or "").strip()
        if sid.lower() == section_1_id.lower():
            return str(item.get("section_1_name") or sid)
    return section_1_id


def create_joint_review(
    order_category: str,
    delivery_id: int,
    proposed_patch: Dict[str, Any],
    review_reason: str,
    attachments: Optional[List[Dict[str, Any]]],
    operator_username: str,
    operator_name: str,
    operator_group: str,
    client_ip: str = "",
) -> Dict[str, Any]:
    """
    发起联合会审核心逻辑：
    1. 校验订单存在性与当前状态互斥锁；
    2. 校验发起人角色与场景权责匹配；
    3. 校验 proposed_patch 白名单与合法性；
    4. 编排必审主体清单（场景 3 精准排除施工方）；
    5. 原单挂起状态置为 'under_review'，创建会审记录。
    """
    ensure_joint_review_tables()
    order_category = order_category.strip().lower()
    if order_category not in ("pipe", "fitting"):
        raise HTTPException(status_code=400, detail="物料类别必须为 pipe (直管) 或 fitting (管件)")

    if not review_reason or len(review_reason.strip()) < 4:
        raise HTTPException(status_code=422, detail="提请联合会审必须填写充分的事由说明（不少于4个字符）")

    # 白名单字段校验
    allowed_keys = PIPE_ALLOWED_PATCH_FIELDS if order_category == "pipe" else FITTING_ALLOWED_PATCH_FIELDS
    for k in proposed_patch.keys():
        if k in FROZEN_FIELDS:
            raise HTTPException(status_code=422, detail=f"严禁在会审中修改核心标识字段: {k}")
        if k not in allowed_keys:
            raise HTTPException(status_code=422, detail=f"不支持修改字段: {k}")

    # 数量校验
    if "shipped_qty" in proposed_patch:
        try:
            qty_val = float(proposed_patch["shipped_qty"])
            if qty_val <= 0:
                raise ValueError()
            proposed_patch["shipped_qty"] = qty_val
        except Exception:
            raise HTTPException(status_code=422, detail="发货数量必须大于 0")

    # 管件订单明细校验
    if "items" in proposed_patch and proposed_patch["items"]:
        if not isinstance(proposed_patch["items"], list):
            raise HTTPException(status_code=422, detail="管件订单明细更正项必须为列表格式")
        for it in proposed_patch["items"]:
            if not isinstance(it, dict) or not it.get("id"):
                raise HTTPException(status_code=422, detail="管件订单明细更正项必须包含有效的订单记录 ID")
            if "shipped_qty" in it and it["shipped_qty"] is not None:
                try:
                    q = float(it["shipped_qty"])
                    if q <= 0:
                        raise ValueError()
                    it["shipped_qty"] = q
                except Exception:
                    raise HTTPException(status_code=422, detail=f"订单 {it.get('order_no') or it.get('id')} 发货数量必须大于 0")

    db_session = SessionLocal()
    try:
        # 查询原单
        delivery = _get_delivery_info(db_session, order_category, delivery_id)
        if not delivery:
            raise HTTPException(status_code=404, detail="关联的发货单据不存在")

        current_status = delivery.get("status") or ""
        if current_status == "under_review":
            raise HTTPException(status_code=409, detail="该单据已处于联合会审中，请勿重复提请")
        if current_status == "completed":
            raise HTTPException(status_code=422, detail="该单据已完成库管最终归档，全生命周期已闭环，无需发起会审")
        if current_status == "cancelled":
            raise HTTPException(status_code=422, detail="已撤销作废的单据无法发起会审")
        if current_status not in ("pending_arrival", "pending_receive", "pending_diff_approve", "pending_warehouse"):
            raise HTTPException(status_code=422, detail=f"当前单据状态 [{current_status}] 不支持发起会审")

        # 检查是否已有未办结的会审
        active_review_sql = text("""
            SELECT id, review_no FROM tube.tube_order_reviews
            WHERE order_category = :cat AND delivery_id = :did AND review_status = 'voting'
            LIMIT 1
        """)
        active_rev = db_session.execute(active_review_sql, {"cat": order_category, "did": delivery_id}).mappings().first()
        if active_rev:
            raise HTTPException(status_code=409, detail=f"已存在正在进行的联合会审 [{active_rev['review_no']}]，不能重复发起")

        # 场景界定与发起人资格校验
        is_global_admin = operator_group in ("Global_admin", "dev_admin")
        cfg = load_tube_config() or {}
        sup_name = _resolve_supplier_name(cfg, delivery["supply_entity_id"])
        sec_name = _resolve_section_name(cfg, delivery["section_1_id"])

        if current_status == "pending_arrival":
            # 场景 1：待确认到货 -> 现场负责人发起
            if not is_global_admin and operator_group != "tube_site_manager":
                raise HTTPException(status_code=403, detail="待到货阶段仅限现场负责人（Site Manager）发起联合会审")
            trigger_scene = "scene_1_arrival"
            initiator_role = "现场负责人"
            # 必需主体：仅供货厂家
            required_entities = [
                {
                    "entity_type": "supplier",
                    "entity_id": delivery["supply_entity_id"],
                    "entity_name": sup_name,
                    "role_desc": "供货厂家",
                }
            ]
        elif current_status in ("pending_receive", "pending_diff_approve"):
            # 场景 2：待施工接收 -> 施工单位发起
            if not is_global_admin and operator_group not in ("tube_construction_unit", "tube_site_manager"):
                raise HTTPException(status_code=403, detail="待施工接收阶段仅限施工单位或现场主管发起联合会审")
            trigger_scene = "scene_2_receive"
            initiator_role = "施工单位"
            # 必需主体：供货厂家 + 现场负责人
            required_entities = [
                {
                    "entity_type": "supplier",
                    "entity_id": delivery["supply_entity_id"],
                    "entity_name": sup_name,
                    "role_desc": "供货厂家",
                },
                {
                    "entity_type": "site_manager",
                    "entity_id": "site_manager",
                    "entity_name": "标段现场主管",
                    "role_desc": "现场负责人",
                },
            ]
        elif current_status == "pending_warehouse":
            # 场景 3：待库管确认 -> 库管员发起
            if not is_global_admin and operator_group not in ("tube_warehouse_keeper", "tube_warehouse_admin"):
                raise HTTPException(status_code=403, detail="待库管确认阶段仅限库管员发起联合会审")
            trigger_scene = "scene_3_warehouse"
            initiator_role = "责任库管员"
            # 必需主体：供货厂家 + 现场负责人（精准排除施工方！）
            required_entities = [
                {
                    "entity_type": "supplier",
                    "entity_id": delivery["supply_entity_id"],
                    "entity_name": sup_name,
                    "role_desc": "供货厂家",
                },
                {
                    "entity_type": "site_manager",
                    "entity_id": "site_manager",
                    "entity_name": "标段现场主管",
                    "role_desc": "现场负责人",
                },
            ]
        else:
            raise HTTPException(status_code=400, detail="不支持的触发节点")

        review_no = _generate_review_no()
        pre_status = current_status

        # 序列化原始快照
        original_snapshot = {}
        for k, v in delivery.items():
            if isinstance(v, (datetime, date)):
                original_snapshot[k] = v.isoformat()
            elif isinstance(v, Decimal):
                original_snapshot[k] = float(v) if (v % 1 > 0) else int(v)
            else:
                original_snapshot[k] = v

        # 1. 插入会审主单
        insert_review_sql = text("""
            INSERT INTO tube.tube_order_reviews (
                review_no, project_key, order_category, delivery_id, order_no,
                section_1_id, supply_entity_id, trigger_scene, pre_status, review_status,
                initiator_role, initiator_name, initiator_username, review_reason,
                attachments, original_snapshot, proposed_patch, required_entities,
                approved_entities, rejected_entities, created_at, updated_at
            ) VALUES (
                :review_no, :project_key, :order_category, :delivery_id, :order_no,
                :section_1_id, :supply_entity_id, :trigger_scene, :pre_status, 'voting',
                :initiator_role, :initiator_name, :initiator_username, :review_reason,
                :attachments, :original_snapshot, :proposed_patch, :required_entities,
                '[]'::jsonb, '[]'::jsonb, NOW(), NOW()
            ) RETURNING id;
        """)

        res = db_session.execute(insert_review_sql, {
            "review_no": review_no,
            "project_key": PROJECT_KEY,
            "order_category": order_category,
            "delivery_id": delivery_id,
            "order_no": delivery["order_no"],
            "section_1_id": delivery["section_1_id"],
            "supply_entity_id": delivery["supply_entity_id"],
            "trigger_scene": trigger_scene,
            "pre_status": pre_status,
            "initiator_role": initiator_role,
            "initiator_name": operator_name or operator_username,
            "initiator_username": operator_username,
            "review_reason": review_reason.strip(),
            "attachments": _dumps_json(attachments or []),
            "original_snapshot": _dumps_json(original_snapshot),
            "proposed_patch": _dumps_json(proposed_patch),
            "required_entities": _dumps_json(required_entities),
        })
        review_id = res.scalar()

        # 2. 挂起原发货单：修改 status 为 'under_review'，记录 pre_review_status
        if order_category == "pipe":
            update_delivery_sql = text("""
                UPDATE tube.tube_delivery
                SET status = 'under_review',
                    pre_review_status = :pre_status,
                    updated_at = NOW()
                WHERE id = :delivery_id
            """)
            db_session.execute(update_delivery_sql, {
                "pre_status": pre_status,
                "delivery_id": delivery_id,
            })
        else:
            # Fitting: 如果属于整车车次，批量挂起该车次下的全部订单明细
            if delivery.get("shipment_no"):
                update_delivery_sql = text("""
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'under_review',
                        pre_review_status = :pre_status,
                        updated_at = NOW()
                    WHERE shipment_no = :s_no AND (status = :pre_status OR status = 'under_review')
                """)
                db_session.execute(update_delivery_sql, {
                    "pre_status": pre_status,
                    "s_no": delivery["shipment_no"],
                })
            else:
                update_delivery_sql = text("""
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'under_review',
                        pre_review_status = :pre_status,
                        updated_at = NOW()
                    WHERE id = :delivery_id
                """)
                db_session.execute(update_delivery_sql, {
                    "pre_status": pre_status,
                    "delivery_id": delivery_id,
                })

        db_session.commit()

        # 审计日志
        save_operation_log(
            operator=operator_username,
            operator_group=operator_group,
            action_type="INITIATE_JOINT_REVIEW",
            action_desc=f"提请多方联合会审 [{review_no}]: 单号 {delivery['order_no']} (标段: {sec_name}, 厂家: {sup_name})，事由: {review_reason.strip()}",
            resource_id=str(review_id),
            before_value={"delivery_status": pre_status, "snapshot": original_snapshot},
            after_value={"review_no": review_no, "patch": proposed_patch, "required_entities": required_entities},
            client_ip=client_ip,
        )

        # 同步写入 logs.system_messages 消息中心收件箱
        try:
            from backend.projects.insulation_pipe_supply_2026.services.system_message_service import create_system_message
            for ent in required_entities:
                target_user = ent.get("entity_id") or "ALL"
                if ent.get("entity_type") == "site_manager":
                    recv = "ROLE:tube_site_manager"
                elif ent.get("entity_type") == "supplier":
                    recv = f"ENTITY:{target_user}"
                else:
                    recv = "ROLE:Global_admin"

                create_system_message(
                    receiver_username=recv,
                    receiver_entity_id=target_user,
                    title=f"【联合会审待办】订单 {delivery['order_no']} 提请会签",
                    content=f"【{initiator_name}】就订单 {delivery['order_no']}（{sec_name}）提请了联合会审。事由：{review_reason.strip()}。请及时在联合会审大厅会签表决。",
                    msg_type="joint_review",
                    category="work",
                    sender_username=operator_username,
                    sender_name=initiator_name,
                    sender_role=initiator_role,
                    action_url=f"/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote&review_id={review_id}",
                    biz_type="joint_review",
                    biz_id=str(review_id),
                    extra_data={"review_no": review_no, "order_no": delivery["order_no"]},
                )
        except Exception as msg_err:
            print(f"[joint_review] 写入系统消息中心异常: {msg_err}")

        return {
            "ok": True,
            "review_id": review_id,
            "review_no": review_no,
            "order_no": delivery["order_no"],
            "trigger_scene": trigger_scene,
            "required_entities": required_entities,
            "message": "联合会审提请成功，单据已挂起并向各前序责任主体派发表决任务",
        }
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _check_user_can_vote_entity(
    required_entity: Dict[str, Any],
    session_username: str,
    session_group: str,
    cfg: Dict[str, Any],
) -> bool:
    """核验当前登录人是否代表必审主体表决。"""
    if session_group in ("Global_admin", "dev_admin"):
        return True

    ent_type = required_entity.get("entity_type")
    ent_id = str(required_entity.get("entity_id") or "").strip().lower()

    if ent_type == "supplier":
        if session_group not in ("tube_supplier_admin", "tube_supplier"):
            return False
        # 匹配厂家 entity_id
        from backend.projects.insulation_pipe_supply_2026.api.workspace import resolve_accessible_supply_entity_ids
        accessible = resolve_accessible_supply_entity_ids(cfg, session_username, session_group)
        accessible_low = {s.lower() for s in accessible}
        return ent_id in accessible_low

    if ent_type == "site_manager":
        return session_group in ("tube_site_manager", "Global_admin")

    if ent_type == "construction_unit":
        return session_group in ("tube_construction_unit", "tube_site_manager", "Global_admin")

    return False


def _revert_review_order_status(db_session, review: Dict[str, Any]) -> None:
    """会审撤销或强制终止时，将订单状态从 under_review 恢复为 pre_review_status。"""
    order_cat = review["order_category"]
    deliv_id = review["delivery_id"]
    pre_status = review["pre_status"]

    if order_cat == "pipe":
        revert_sql = text("""
            UPDATE tube.tube_delivery
            SET status = :pre_status, updated_at = NOW()
            WHERE id = :deliv_id AND status = 'under_review'
        """)
        db_session.execute(revert_sql, {"pre_status": pre_status, "deliv_id": deliv_id})
    else:
        deliv = _get_delivery_info(db_session, "fitting", deliv_id)
        if deliv and deliv.get("shipment_no"):
            revert_sql = text("""
                UPDATE tube.tube_fitting_delivery
                SET status = :pre_status, updated_at = NOW()
                WHERE shipment_no = :s_no AND status = 'under_review'
            """)
            db_session.execute(revert_sql, {"pre_status": pre_status, "s_no": deliv["shipment_no"]})
        else:
            revert_sql = text("""
                UPDATE tube.tube_fitting_delivery
                SET status = :pre_status, updated_at = NOW()
                WHERE id = :deliv_id AND status = 'under_review'
            """)
            db_session.execute(revert_sql, {"pre_status": pre_status, "deliv_id": deliv_id})


def _apply_review_patch_to_order(db_session, review: Dict[str, Any], patch: Dict[str, Any], resolution_text: str) -> None:
    """会审全票通过或管理员强制通过后，原子更新业务订单（保温直管单条或管件整车车次/多明细）。"""
    order_cat = review["order_category"]
    deliv_id = review["delivery_id"]
    pre_status = review["pre_status"]

    if order_cat == "pipe":
        orig_sql = text("SELECT ship_remark FROM tube.tube_delivery WHERE id = :id")
        orig_remark = db_session.execute(orig_sql, {"id": deliv_id}).scalar() or ""
        merged_remark = f"{orig_remark}\n{resolution_text}".strip()

        update_clauses = ["status = :restored_status", "ship_remark = :merged_remark", "updated_at = NOW()"]
        update_params: Dict[str, Any] = {
            "restored_status": pre_status,
            "merged_remark": merged_remark,
            "deliv_id": deliv_id,
        }
        for field_name, field_val in patch.items():
            if field_name in ("ship_remark", "items"):
                continue
            update_clauses.append(f"{field_name} = :{field_name}")
            update_params[field_name] = field_val

        db_session.execute(text(f"UPDATE tube.tube_delivery SET {', '.join(update_clauses)} WHERE id = :deliv_id"), update_params)
    else:
        # 管件 (fitting): 支持整车车牌公共属性与各订单细项独立修正
        delivery = _get_delivery_info(db_session, "fitting", deliv_id)
        shipment_no = delivery.get("shipment_no") if delivery else None

        # 1. 更新整车车牌
        if "vehicle_plate_no" in patch and patch["vehicle_plate_no"]:
            if shipment_no:
                db_session.execute(text("""
                    UPDATE tube.tube_fitting_delivery
                    SET vehicle_plate_no = :v_plate, updated_at = NOW()
                    WHERE shipment_no = :s_no
                """), {"v_plate": patch["vehicle_plate_no"], "s_no": shipment_no})
            else:
                db_session.execute(text("""
                    UPDATE tube.tube_fitting_delivery
                    SET vehicle_plate_no = :v_plate, updated_at = NOW()
                    WHERE id = :deliv_id
                """), {"v_plate": patch["vehicle_plate_no"], "deliv_id": deliv_id})

        # 2. 更新具体订单细项
        if "items" in patch and isinstance(patch["items"], list):
            for it in patch["items"]:
                it_id = it.get("id")
                if not it_id:
                    continue
                it_clauses = ["updated_at = NOW()"]
                it_params = {"it_id": it_id}
                for col in ("fitting_type", "model_spec", "shipped_qty", "unit"):
                    if col in it and it[col] is not None:
                        it_clauses.append(f"{col} = :{col}")
                        it_params[col] = it[col]
                db_session.execute(text(f"""
                    UPDATE tube.tube_fitting_delivery
                    SET {', '.join(it_clauses)}
                    WHERE id = :it_id
                """), it_params)
        else:
            single_clauses = ["updated_at = NOW()"]
            single_params = {"deliv_id": deliv_id}
            for col in ("fitting_type", "model_spec", "shipped_qty", "unit"):
                if col in patch and patch[col] is not None:
                    single_clauses.append(f"{col} = :{col}")
                    single_params[col] = patch[col]
            if len(single_clauses) > 1:
                db_session.execute(text(f"""
                    UPDATE tube.tube_fitting_delivery
                    SET {', '.join(single_clauses)}
                    WHERE id = :deliv_id
                """), single_params)

        # 3. 恢复订单流转状态并合并决议备注
        if shipment_no:
            orig_remark = db_session.execute(text("SELECT ship_remark FROM tube.tube_fitting_delivery WHERE shipment_no = :s_no LIMIT 1"), {"s_no": shipment_no}).scalar() or ""
            merged_remark = f"{orig_remark}\n{resolution_text}".strip()
            db_session.execute(text("""
                UPDATE tube.tube_fitting_delivery
                SET status = :restored_status,
                    ship_remark = :merged_remark,
                    updated_at = NOW()
                WHERE shipment_no = :s_no
            """), {"restored_status": pre_status, "merged_remark": merged_remark, "s_no": shipment_no})
        else:
            orig_remark = db_session.execute(text("SELECT ship_remark FROM tube.tube_fitting_delivery WHERE id = :id"), {"id": deliv_id}).scalar() or ""
            merged_remark = f"{orig_remark}\n{resolution_text}".strip()
            db_session.execute(text("""
                UPDATE tube.tube_fitting_delivery
                SET status = :restored_status,
                    ship_remark = :merged_remark,
                    updated_at = NOW()
                WHERE id = :deliv_id
            """), {"restored_status": pre_status, "merged_remark": merged_remark, "deliv_id": deliv_id})


def vote_joint_review(
    review_id: int,
    vote_decision: str,  # 'approve' | 'reject'
    vote_opinion: str,
    session_username: str,
    session_name: str,
    session_group: str,
    client_ip: str = "",
) -> Dict[str, Any]:
    """
    责任主体表决会签：
    1. 校验当前主体合法性；
    2. 记录表决结果；
    3. 全票同意时自动触发原子修单并恢复待办状态；
    4. 存在异议时保持会审挂起。
    """
    ensure_joint_review_tables()
    vote_decision = vote_decision.strip().lower()
    if vote_decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="表决意见必须为 approve (同意) 或 reject (不同意)")

    if vote_decision == "reject" and (not vote_opinion or len(vote_opinion.strip()) < 2):
        raise HTTPException(status_code=422, detail="选择不同意时，必须填写具体的不同意理由说明")

    db_session = SessionLocal()
    try:
        sql = text("SELECT * FROM tube.tube_order_reviews WHERE id = :id FOR UPDATE")
        review = db_session.execute(sql, {"id": review_id}).mappings().first()
        if not review:
            raise HTTPException(status_code=404, detail="会审单不存在")

        if review["review_status"] != "voting":
            raise HTTPException(status_code=422, detail=f"该会审已办结或撤销（当前状态: {review['review_status']}），无法重复表决")

        cfg = load_tube_config() or {}
        required_entities = review["required_entities"] or []
        if isinstance(required_entities, str):
            required_entities = json.loads(required_entities)

        # 查找当前用户能代表的必审主体
        matched_entity = None
        for ent in required_entities:
            if _check_user_can_vote_entity(ent, session_username, session_group, cfg):
                matched_entity = ent
                break

        if not matched_entity:
            raise HTTPException(status_code=403, detail="您当前登录的角色不属于本次会审的必审主体，无表决权限")

        ent_type = matched_entity["entity_type"]
        ent_id = matched_entity["entity_id"]
        voter_display_name = session_name or session_username

        # 检查是否已表决
        existing_vote_sql = text("""
            SELECT id, vote_decision FROM tube.tube_review_votes
            WHERE review_id = :rid AND entity_type = :etype AND entity_id = :eid
        """)
        exist_vote = db_session.execute(existing_vote_sql, {
            "rid": review_id,
            "etype": ent_type,
            "eid": ent_id,
        }).mappings().first()

        if exist_vote:
            update_vote_sql = text("""
                UPDATE tube.tube_review_votes
                SET voter_username = :uname,
                    voter_name = :vname,
                    vote_decision = :dec,
                    vote_opinion = :opn,
                    voted_at = NOW()
                WHERE id = :vid
            """)
            db_session.execute(update_vote_sql, {
                "uname": session_username,
                "vname": voter_display_name,
                "dec": vote_decision,
                "opn": vote_opinion or "",
                "vid": exist_vote["id"],
            })
        else:
            insert_vote_sql = text("""
                INSERT INTO tube.tube_review_votes (
                    review_id, entity_type, entity_id, voter_username,
                    voter_name, vote_decision, vote_opinion, voted_at
                ) VALUES (
                    :rid, :etype, :eid, :uname, :vname, :dec, :opn, NOW()
                )
            """)
            db_session.execute(insert_vote_sql, {
                "rid": review_id,
                "etype": ent_type,
                "eid": ent_id,
                "uname": session_username,
                "vname": voter_display_name,
                "dec": vote_decision,
                "opn": vote_opinion or "",
            })

        # 重新统计各主体表决
        votes_sql = text("SELECT entity_type, entity_id, vote_decision, vote_opinion, voter_name FROM tube.tube_review_votes WHERE review_id = :rid")
        all_votes = db_session.execute(votes_sql, {"rid": review_id}).mappings().all()

        vote_map = {f"{v['entity_type']}::{v['entity_id']}": v for v in all_votes}

        approved_list = []
        rejected_list = []
        for ent in required_entities:
            key = f"{ent['entity_type']}::{ent['entity_id']}"
            if key in vote_map:
                v = vote_map[key]
                if v["vote_decision"] == "approve":
                    approved_list.append(ent)
                else:
                    rejected_list.append({**ent, "opinion": v["vote_opinion"], "voter": v["voter_name"]})

        # 判断是否全票通过
        is_all_approved = len(approved_list) == len(required_entities) and len(rejected_list) == 0

        if is_all_approved:
            # 🚀 全票通过：执行订单自动修正
            pre_status = review.get("pre_status") or "pending_arrival"
            patch = review["proposed_patch"]
            if isinstance(patch, str):
                patch = json.loads(patch)

            summary_parts = []
            if "vehicle_plate_no" in patch:
                summary_parts.append(f"车牌={patch['vehicle_plate_no']}")
            if "items" in patch and isinstance(patch["items"], list):
                for it in patch["items"]:
                    summary_parts.append(f"单号{it.get('order_no') or it.get('id')}: {it.get('fitting_type','')}{it.get('model_spec','')} {it.get('shipped_qty','')}{it.get('unit','件')}")
            else:
                for k, v in patch.items():
                    if k not in ("items", "ship_remark"):
                        summary_parts.append(f"{k}={v}")

            patch_summary_str = "; ".join(summary_parts) if summary_parts else "现场核验更正一致"
            resolution_text = (
                f"【联合会审全票通过更正】单号: {review['review_no']} | "
                f"发起人: {review['initiator_name']}({review['initiator_role']}) | "
                f"事由: {review['review_reason']} | "
                f"更正项: [{patch_summary_str}] | "
                f"会审决议: 全票一致同意通过 (生效时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')})"
            )

            # 原子更新业务订单
            _apply_review_patch_to_order(db_session, review, patch, resolution_text)

            # 更新会审单为 approved
            update_rev_sql = text("""
                UPDATE tube.tube_order_reviews
                SET review_status = 'approved',
                    approved_entities = :app_list,
                    rejected_entities = '[]'::jsonb,
                    resolution_summary = :res_sum,
                    finalized_at = NOW(),
                    finalized_by = 'SYSTEM_CONSENSUS',
                    updated_at = NOW()
                WHERE id = :rid
            """)
            db_session.execute(update_rev_sql, {
                "app_list": _dumps_json(approved_list),
                "res_sum": resolution_text,
                "rid": review_id,
            })

            db_session.commit()

            save_operation_log(
                operator=session_username,
                operator_group=session_group,
                action_type="JOINT_REVIEW_APPROVED",
                action_desc=f"联合会审全票通过并自动修正订单: 会审单 [{review['review_no']}] 对应订单 {review['order_no']}，更正为 [{patch_summary_str}]，单据已恢复为待办 [{pre_status}]",
                resource_id=str(review_id),
                before_value={"patch": patch, "status": "under_review"},
                after_value={"new_status": pre_status, "resolution": resolution_text},
                client_ip=client_ip,
            )

            # 向发起人发送会审全票通过更正通知
            try:
                from backend.projects.insulation_pipe_supply_2026.services.system_message_service import create_system_message
                create_system_message(
                    receiver_username=review["initiator_username"],
                    title=f"🎉【联合会审全票通过】订单 {review['order_no']} 修正生效！",
                    content=f"您就订单 {review['order_no']} 发起的会审已获得所有主体全票同意！数据已自动修正，单据已恢复待办状态【{pre_status}】，请及时办理。",
                    msg_type="joint_review",
                    category="work",
                    sender_username="SYSTEM",
                    sender_name="联合会审大厅",
                    action_url=f"/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=history&review_id={review_id}",
                    biz_type="joint_review",
                    biz_id=str(review_id),
                )
            except Exception as notify_err:
                print(f"[joint_review] 写入通过通知失败: {notify_err}")

            return {
                "ok": True,
                "review_id": review_id,
                "review_no": review["review_no"],
                "review_status": "approved",
                "is_finalized": True,
                "restored_status": pre_status,
                "message": "恭喜！所有必审主体已全票同意，数据已自动更正生效，单据已恢复为发起前待办状态，可继续常规办理！",
            }
        else:
            # 存在异议或尚未全部表决：保持 voting
            update_rev_sql = text("""
                UPDATE tube.tube_order_reviews
                SET approved_entities = :app_list,
                    rejected_entities = :rej_list,
                    updated_at = NOW()
                WHERE id = :rid
            """)
            db_session.execute(update_rev_sql, {
                "app_list": _dumps_json(approved_list),
                "rej_list": _dumps_json(rejected_list),
                "rid": review_id,
            })
            db_session.commit()

            action_type = "JOINT_REVIEW_REJECTED_VOTE" if vote_decision == "reject" else "JOINT_REVIEW_APPROVED_VOTE"
            save_operation_log(
                operator=session_username,
                operator_group=session_group,
                action_type=action_type,
                action_desc=f"联合会审表决登记: 主体 [{matched_entity.get('entity_name')}] 投票 [{vote_decision}] (附言: {vote_opinion or '无'})，单号 {review['review_no']}",
                resource_id=str(review_id),
                after_value={"decision": vote_decision, "opinion": vote_opinion, "approved_count": len(approved_list), "total_count": len(required_entities)},
                client_ip=client_ip,
            )

            msg = "表决已登记成功。"
            if vote_decision == "reject":
                msg += " 由于您提出了异议，该会审将保持挂起状态，所有参与方均可查阅您的异议说明以继续协商。"
            else:
                msg += f" 当前已同意 {len(approved_list)}/{len(required_entities)} 方，待其他主体表决。"

            return {
                "ok": True,
                "review_id": review_id,
                "review_no": review["review_no"],
                "review_status": "voting",
                "is_finalized": False,
                "approved_count": len(approved_list),
                "total_required": len(required_entities),
                "message": msg,
            }
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def cancel_joint_review(
    review_id: int,
    cancel_reason: str,
    session_username: str,
    session_group: str,
    client_ip: str = "",
) -> Dict[str, Any]:
    """发起人主动撤回会审：订单无损恢复原貌。"""
    ensure_joint_review_tables()
    db_session = SessionLocal()
    try:
        sql = text("SELECT * FROM tube.tube_order_reviews WHERE id = :id FOR UPDATE")
        review = db_session.execute(sql, {"id": review_id}).mappings().first()
        if not review:
            raise HTTPException(status_code=404, detail="会审单不存在")

        if review["review_status"] != "voting":
            raise HTTPException(status_code=422, detail=f"该会审当前状态为 [{review['review_status']}]，无法执行撤销")

        is_admin = session_group in ("Global_admin", "dev_admin")
        is_initiator = review["initiator_username"] == session_username

        if not is_admin and not is_initiator:
            raise HTTPException(status_code=403, detail="仅发起人或超级管理员有权撤销本次联合会审")

        order_cat = review["order_category"]
        deliv_id = review["delivery_id"]
        pre_status = review["pre_status"]

        # 1. 恢复原发货单状态
        _revert_review_order_status(db_session, review)

        # 2. 会审单置为 cancelled
        final_summary = f"【发起人主动撤销会审】经办人: {session_username} | 理由: {cancel_reason or '自愿撤销'}"
        update_rev_sql = text("""
            UPDATE tube.tube_order_reviews
            SET review_status = 'cancelled',
                resolution_summary = :res_sum,
                finalized_at = NOW(),
                finalized_by = :fby,
                updated_at = NOW()
            WHERE id = :rid
        """)
        db_session.execute(update_rev_sql, {
            "res_sum": final_summary,
            "fby": session_username,
            "rid": review_id,
        })

        db_session.commit()

        save_operation_log(
            operator=session_username,
            operator_group=session_group,
            action_type="CANCEL_JOINT_REVIEW",
            action_desc=f"撤回联合会审 [{review['review_no']}]: 关联订单 {review['order_no']} 已无损恢复为 [{pre_status}]",
            resource_id=str(review_id),
            before_value={"review_status": "voting"},
            after_value={"review_status": "cancelled", "restored_status": pre_status},
            client_ip=client_ip,
        )

        return {
            "ok": True,
            "review_id": review_id,
            "review_no": review["review_no"],
            "review_status": "cancelled",
            "restored_status": pre_status,
            "message": "联合会审已成功撤销，原单据已恢复至发起前的流转状态。",
        }
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def admin_arbitrate_joint_review(
    review_id: int,
    arbitration_decision: str,  # 'force_approve' | 'force_reject'
    arbitration_reason: str,
    session_username: str,
    session_group: str,
    client_ip: str = "",
) -> Dict[str, Any]:
    """终局裁决：防止死锁的一锤定音特权通道（超级管理员及特许裁决员）。"""
    ensure_joint_review_tables()
    if not check_user_can_arbitrate(session_username, session_group):
        raise HTTPException(status_code=403, detail="您没有终局裁决权限（仅系统超级管理员或特许裁决员拥有该权限）")

    if not arbitration_reason or len(arbitration_reason.strip()) < 3:
        raise HTTPException(status_code=422, detail="终局裁决必须填写详细的裁决理由依据")

    arbitration_decision = arbitration_decision.strip().lower()
    if arbitration_decision not in ("force_approve", "force_reject"):
        raise HTTPException(status_code=400, detail="裁决指令必须为 force_approve (强制通过) 或 force_reject (强制终止)")

    db_session = SessionLocal()
    try:
        sql = text("SELECT * FROM tube.tube_order_reviews WHERE id = :id FOR UPDATE")
        review = db_session.execute(sql, {"id": review_id}).mappings().first()
        if not review:
            raise HTTPException(status_code=404, detail="会审单不存在")

        if review["review_status"] != "voting":
            raise HTTPException(status_code=422, detail=f"该会审单已办结，无法裁决（当前状态: {review['review_status']}）")

        order_cat = review["order_category"]
        deliv_id = review["delivery_id"]
        pre_status = review["pre_status"]
        target_table = "tube.tube_delivery" if order_cat == "pipe" else "tube.tube_fitting_delivery"

        if arbitration_decision == "force_approve":
            patch = review["proposed_patch"]
            if isinstance(patch, str):
                patch = json.loads(patch)

            summary_parts = []
            if "vehicle_plate_no" in patch:
                summary_parts.append(f"车牌={patch['vehicle_plate_no']}")
            if "items" in patch and isinstance(patch["items"], list):
                for it in patch["items"]:
                    summary_parts.append(f"单号{it.get('order_no') or it.get('id')}: {it.get('fitting_type','')}{it.get('model_spec','')} {it.get('shipped_qty','')}{it.get('unit','件')}")
            else:
                for k, v in patch.items():
                    if k not in ("items", "ship_remark"):
                        summary_parts.append(f"{k}={v}")

            patch_summary_str = "; ".join(summary_parts) if summary_parts else "裁决人员核实更正一致"
            resolution_text = (
                f"【终局裁决强制通过】单号: {review['review_no']} | "
                f"裁决人: {session_username} | 理由: {arbitration_reason.strip()} | "
                f"更正项: [{patch_summary_str}] | "
                f"生效时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # 原子更新业务订单
            _apply_review_patch_to_order(db_session, review, patch, resolution_text)

            update_rev_sql = text("""
                UPDATE tube.tube_order_reviews
                SET review_status = 'approved',
                    resolution_summary = :res_sum,
                    finalized_at = NOW(),
                    finalized_by = :fby,
                    updated_at = NOW()
                WHERE id = :rid
            """)
            db_session.execute(update_rev_sql, {"res_sum": resolution_text, "fby": session_username, "rid": review_id})
            db_session.commit()

            save_operation_log(
                operator=session_username,
                operator_group=session_group,
                action_type="ADMIN_ARBITRATE_APPROVE",
                action_desc=f"终局裁决强制通过会审 [{review['review_no']}]: 关联订单 {review['order_no']}，更正为 [{patch_summary_str}]",
                resource_id=str(review_id),
                after_value={"decision": "force_approve", "reason": arbitration_reason},
                client_ip=client_ip,
            )

            return {
                "ok": True,
                "review_id": review_id,
                "review_status": "approved",
                "message": "终局裁决已强制生效，数据已修正并恢复原待办状态。",
            }
        else:
            # force_reject
            _revert_review_order_status(db_session, review)

            resolution_text = f"【终局裁决终止驳回】裁决人: {session_username} | 理由: {arbitration_reason.strip()}"
            update_rev_sql = text("""
                UPDATE tube.tube_order_reviews
                SET review_status = 'rejected',
                    resolution_summary = :res_sum,
                    finalized_at = NOW(),
                    finalized_by = :fby,
                    updated_at = NOW()
                WHERE id = :rid
            """)
            db_session.execute(update_rev_sql, {"res_sum": resolution_text, "fby": session_username, "rid": review_id})
            db_session.commit()

            save_operation_log(
                operator=session_username,
                operator_group=session_group,
                action_type="ADMIN_ARBITRATE_REJECT",
                action_desc=f"终局裁决终止驳回会审 [{review['review_no']}]: 关联订单 {review['order_no']}，原单已恢复为 [{pre_status}]",
                resource_id=str(review_id),
                after_value={"decision": "force_reject", "reason": arbitration_reason},
                client_ip=client_ip,
            )

            return {
                "ok": True,
                "review_id": review_id,
                "review_status": "rejected",
                "message": "终局裁决已驳回并关闭会审，原单已恢复为发起前待办状态。",
            }
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def list_joint_reviews(
    tab: str = "all",  # 'pending_my_vote' | 'my_initiated' | 'history' | 'all'
    order_category: Optional[str] = None,
    section_1_id: Optional[str] = None,
    supply_entity_id: Optional[str] = None,
    review_status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    session_username: str = "",
    session_group: str = "",
) -> Dict[str, Any]:
    """多维分页查询联合会审列表。"""
    ensure_joint_review_tables()
    cfg = load_tube_config() or {}
    db_session = SessionLocal()
    try:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if order_category:
            where_clauses.append("r.order_category = :order_category")
            params["order_category"] = order_category.strip().lower()

        if section_1_id:
            where_clauses.append("r.section_1_id = :section_1_id")
            params["section_1_id"] = section_1_id.strip()

        if supply_entity_id:
            where_clauses.append("LOWER(r.supply_entity_id) = :supply_entity_id")
            params["supply_entity_id"] = supply_entity_id.strip().lower()

        if review_status:
            where_clauses.append("r.review_status = :review_status")
            params["review_status"] = review_status.strip().lower()

        if tab == "my_initiated":
            where_clauses.append("r.initiator_username = :my_user")
            params["my_user"] = session_username
        elif tab == "history":
            where_clauses.append("r.review_status IN ('approved', 'rejected', 'cancelled')")
        elif tab == "pending_my_vote":
            where_clauses.append("r.review_status = 'voting'")

        if search:
            kw = f"%{search.strip()}%"
            where_clauses.append("""
                (r.review_no ILIKE :kw OR r.order_no ILIKE :kw OR r.review_reason ILIKE :kw
                 OR r.initiator_name ILIKE :kw OR r.resolution_summary ILIKE :kw)
            """)
            params["kw"] = kw

        where_sql = " AND ".join(where_clauses)

        # 统计总数
        count_sql = text(f"SELECT COUNT(*) FROM tube.tube_order_reviews r WHERE {where_sql}")
        total = db_session.execute(count_sql, params).scalar() or 0

        # 分页查询
        offset = max(0, (page - 1) * limit)
        params["limit"] = limit
        params["offset"] = offset

        list_sql = text(f"""
            SELECT r.*
            FROM tube.tube_order_reviews r
            WHERE {where_sql}
            ORDER BY r.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = db_session.execute(list_sql, params).mappings().all()

        # 批量查表决明细
        review_ids = [r["id"] for r in rows]
        votes_map: Dict[int, List[Dict[str, Any]]] = {}
        if review_ids:
            votes_sql = text("""
                SELECT review_id, entity_type, entity_id, voter_username,
                       voter_name, vote_decision, vote_opinion, voted_at
                FROM tube.tube_review_votes
                WHERE review_id = ANY(:rids)
                ORDER BY voted_at ASC
            """)
            v_rows = db_session.execute(votes_sql, {"rids": review_ids}).mappings().all()
            for v in v_rows:
                rid = v["review_id"]
                if rid not in votes_map:
                    votes_map[rid] = []
                v_dict = dict(v)
                if v_dict.get("voted_at"):
                    v_dict["voted_at"] = v_dict["voted_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
                votes_map[rid].append(v_dict)

        items = []
        is_global_admin = session_group in ("Global_admin", "dev_admin")
        can_arbitrate_user = check_user_can_arbitrate(session_username, session_group)

        for r in rows:
            r_dict = dict(r)
            rid = r_dict["id"]
            r_votes = votes_map.get(rid, [])

            # JSON 字段解析
            for j_key in ("attachments", "original_snapshot", "proposed_patch", "required_entities", "approved_entities", "rejected_entities"):
                val = r_dict.get(j_key)
                if isinstance(val, str):
                    try:
                        r_dict[j_key] = json.loads(val)
                    except Exception:
                        pass

            r_dict["votes"] = r_votes
            r_dict["section_1_name"] = _resolve_section_name(cfg, r_dict["section_1_id"])
            r_dict["supply_entity_name"] = _resolve_supplier_name(cfg, r_dict["supply_entity_id"])

            # 丰富各主体表决记录展示元数据
            req_ents = r_dict.get("required_entities") or []
            ent_lookup = {f"{e.get('entity_type')}_{e.get('entity_id')}": e for e in req_ents}
            for v in r_votes:
                k = f"{v.get('entity_type')}_{v.get('entity_id')}"
                if k in ent_lookup:
                    v["entity_name"] = ent_lookup[k].get("entity_name")
                    v["role_desc"] = ent_lookup[k].get("role_desc")
                else:
                    v["entity_name"] = v.get("voter_name")
                    v["role_desc"] = "协同核验方"

            if r_dict.get("created_at"):
                r_dict["created_at"] = r_dict["created_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
            if r_dict.get("finalized_at"):
                r_dict["finalized_at"] = r_dict["finalized_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
            if r_dict.get("updated_at"):
                r_dict["updated_at"] = r_dict["updated_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

            # 判断当前用户是否需要表决
            needs_my_vote = False
            can_i_vote = False
            my_voted = False
            my_vote_decision = None

            if r_dict["review_status"] == "voting":
                req_ents = r_dict.get("required_entities") or []
                for ent in req_ents:
                    if _check_user_can_vote_entity(ent, session_username, session_group, cfg):
                        can_i_vote = True
                        # 检查该主体是否已投过票
                        voted_for_this = any(v["entity_type"] == ent["entity_type"] and v["entity_id"] == ent["entity_id"] for v in r_votes)
                        if not voted_for_this:
                            needs_my_vote = True
                        else:
                            my_voted = True
                            for v in r_votes:
                                if v["entity_type"] == ent["entity_type"] and v["entity_id"] == ent["entity_id"]:
                                    my_vote_decision = v["vote_decision"]

            r_dict["can_i_vote"] = can_i_vote
            r_dict["needs_my_vote"] = needs_my_vote
            r_dict["my_voted"] = my_voted
            r_dict["my_vote_decision"] = my_vote_decision
            r_dict["is_mine"] = r_dict["initiator_username"] == session_username
            r_dict["can_cancel"] = (r_dict["is_mine"] or is_global_admin) and r_dict["review_status"] == "voting"
            r_dict["can_arbitrate"] = can_arbitrate_user and r_dict["review_status"] == "voting"

            # 客户端过滤 tab == 'pending_my_vote'
            if tab == "pending_my_vote" and not needs_my_vote:
                continue

            items.append(r_dict)

        return {
            "ok": True,
            "total": total if tab != "pending_my_vote" else len(items),
            "page": page,
            "limit": limit,
            "items": items,
        }
    finally:
        db_session.close()


def get_joint_review_detail(review_id: int, session_username: str = "", session_group: str = "") -> Dict[str, Any]:
    """查询单笔会审详情。"""
    res = list_joint_reviews(tab="all", search=None, page=1, limit=1, session_username=session_username, session_group=session_group)
    db_session = SessionLocal()
    try:
        sql = text("SELECT r.* FROM tube.tube_order_reviews r WHERE r.id = :id")
        r = db_session.execute(sql, {"id": review_id}).mappings().first()
        if not r:
            raise HTTPException(status_code=404, detail="会审单不存在")

        cfg = load_tube_config() or {}
        r_dict = dict(r)

        for j_key in ("attachments", "original_snapshot", "proposed_patch", "required_entities", "approved_entities", "rejected_entities"):
            val = r_dict.get(j_key)
            if isinstance(val, str):
                try:
                    r_dict[j_key] = json.loads(val)
                except Exception:
                    pass

        # 查表决
        v_sql = text("SELECT * FROM tube.tube_review_votes WHERE review_id = :rid ORDER BY voted_at ASC")
        votes = [dict(v) for v in db_session.execute(v_sql, {"rid": review_id}).mappings().all()]
        req_ents = r_dict.get("required_entities") or []
        ent_lookup = {f"{e.get('entity_type')}_{e.get('entity_id')}": e for e in req_ents}
        for v in votes:
            if v.get("voted_at"):
                v["voted_at"] = v["voted_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
            k = f"{v.get('entity_type')}_{v.get('entity_id')}"
            if k in ent_lookup:
                v["entity_name"] = ent_lookup[k].get("entity_name")
                v["role_desc"] = ent_lookup[k].get("role_desc")
            else:
                v["entity_name"] = v.get("voter_name")
                v["role_desc"] = "协同核验方"

        r_dict["votes"] = votes
        r_dict["section_1_name"] = _resolve_section_name(cfg, r_dict["section_1_id"])
        r_dict["supply_entity_name"] = _resolve_supplier_name(cfg, r_dict["supply_entity_id"])

        if r_dict.get("created_at"):
            r_dict["created_at"] = r_dict["created_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        if r_dict.get("finalized_at"):
            r_dict["finalized_at"] = r_dict["finalized_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        if r_dict.get("updated_at"):
            r_dict["updated_at"] = r_dict["updated_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

        is_global_admin = session_group in ("Global_admin", "dev_admin")
        can_i_vote = False
        needs_my_vote = False
        if r_dict["review_status"] == "voting":
            for ent in r_dict.get("required_entities") or []:
                if _check_user_can_vote_entity(ent, session_username, session_group, cfg):
                    can_i_vote = True
                    if not any(v["entity_type"] == ent["entity_type"] and v["entity_id"] == ent["entity_id"] for v in votes):
                        needs_my_vote = True

        r_dict["can_i_vote"] = can_i_vote
        r_dict["needs_my_vote"] = needs_my_vote
        r_dict["can_cancel"] = (r_dict["initiator_username"] == session_username or is_global_admin) and r_dict["review_status"] == "voting"
        r_dict["can_arbitrate"] = check_user_can_arbitrate(session_username, session_group) and r_dict["review_status"] == "voting"

        return {"ok": True, "data": r_dict}
    finally:
        db_session.close()


def get_pending_review_notifications(session_username: str, session_group: str) -> Dict[str, Any]:
    """
    轻量拉取当前主体待办会审数量与简要列表（驱动顶栏红点与每日弹窗）。
    """
    ensure_joint_review_tables()
    cfg = load_tube_config() or {}
    db_session = SessionLocal()
    try:
        # 查询所有 voting 中的会审
        sql = text("""
            SELECT r.id, r.review_no, r.order_category, r.order_no, r.section_1_id,
                   r.supply_entity_id, r.initiator_name, r.initiator_role, r.review_reason,
                   r.required_entities, r.created_at
            FROM tube.tube_order_reviews r
            WHERE r.review_status = 'voting'
            ORDER BY r.created_at DESC
        """)
        rows = db_session.execute(sql).mappings().all()

        if not rows:
            return {"ok": True, "pending_count": 0, "pending_items": []}

        # 查所有已表决
        v_sql = text("SELECT review_id, entity_type, entity_id FROM tube.tube_review_votes")
        v_rows = db_session.execute(v_sql).mappings().all()
        voted_set = {f"{v['review_id']}::{v['entity_type']}::{v['entity_id']}" for v in v_rows}

        pending_for_me = []
        for r in rows:
            req_ents = r["required_entities"] or []
            if isinstance(req_ents, str):
                try:
                    req_ents = json.loads(req_ents)
                except Exception:
                    req_ents = []

            for ent in req_ents:
                if _check_user_can_vote_entity(ent, session_username, session_group, cfg):
                    key = f"{r['id']}::{ent['entity_type']}::{ent['entity_id']}"
                    if key not in voted_set:
                        sec_name = _resolve_section_name(cfg, r["section_1_id"])
                        sup_name = _resolve_supplier_name(cfg, r["supply_entity_id"])
                        cat_label = "保温直管" if r["order_category"] == "pipe" else "管件/阀门"
                        c_at = r["created_at"].astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M") if r["created_at"] else ""
                        pending_for_me.append({
                            "review_id": r["id"],
                            "review_no": r["review_no"],
                            "order_no": r["order_no"],
                            "order_category": r["order_category"],
                            "category_label": cat_label,
                            "section_1_name": sec_name,
                            "supply_entity_name": sup_name,
                            "initiator_name": r["initiator_name"],
                            "initiator_role": r["initiator_role"],
                            "review_reason": r["review_reason"],
                            "created_at": c_at,
                        })
                        break

        return {
            "ok": True,
            "pending_count": len(pending_for_me),
            "pending_items": pending_for_me[:10],
        }
    finally:
        db_session.close()
