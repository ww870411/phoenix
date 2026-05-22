# -*- coding: utf-8 -*-
"""
tube 项目供给侧服务。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_pipe_model_id(value: Any) -> str:
    return _normalize_text(value).upper()


def list_baseline_rows_all() -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            design_qty,
            purchase_plan_qty,
            remark
        FROM tube.tube_baseline_quantity
        WHERE status = 'active'
        ORDER BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}"
            result[key] = {
                "design_qty": float(row["design_qty"]) if row["design_qty"] is not None else 0,
                "purchase_plan_qty": float(row["purchase_plan_qty"]) if row["purchase_plan_qty"] is not None else 0,
                "remark": row["remark"] or "",
            }
        return result
    finally:
        session.close()


def list_plan_totals(plan_dates: Sequence[date]) -> Dict[str, float]:
    if not plan_dates:
        return {}
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(plan_qty) AS total_plan_qty
        FROM tube.tube_daily_plan
        WHERE plan_date = ANY(:plan_dates)
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"plan_dates": list(plan_dates)}).mappings().all()
        return {
            f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}":
            float(row["total_plan_qty"]) if row["total_plan_qty"] is not None else 0
            for row in rows
        }
    finally:
        session.close()


def list_delivery_aggregates() -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(CASE WHEN status = 'pending_arrival' THEN shipped_qty ELSE 0 END) AS pending_arrival_qty,
            SUM(CASE WHEN status = 'pending_receive' THEN COALESCE(arrived_qty, shipped_qty) ELSE 0 END) AS pending_receive_qty,
            SUM(CASE WHEN status = 'pending_warehouse' THEN COALESCE(received_qty, 0) ELSE 0 END) AS pending_warehouse_qty,
            SUM(CASE WHEN status = 'completed' THEN COALESCE(received_qty, 0) ELSE 0 END) AS completed_qty,
            SUM(CASE WHEN status <> 'cancelled' THEN shipped_qty ELSE 0 END) AS total_shipped_qty
        FROM tube.tube_delivery
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}"
            result[key] = {
                "pending_arrival_qty": float(row["pending_arrival_qty"]) if row["pending_arrival_qty"] is not None else 0,
                "pending_receive_qty": float(row["pending_receive_qty"]) if row["pending_receive_qty"] is not None else 0,
                "pending_warehouse_qty": float(row["pending_warehouse_qty"]) if row["pending_warehouse_qty"] is not None else 0,
                "completed_qty": float(row["completed_qty"]) if row["completed_qty"] is not None else 0,
                "total_shipped_qty": float(row["total_shipped_qty"]) if row["total_shipped_qty"] is not None else 0,
            }
        return result
    finally:
        session.close()


def list_arrival_aggregates() -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(
                CASE
                    WHEN status IN ('pending_receive', 'pending_warehouse', 'completed')
                        THEN COALESCE(arrived_qty, received_qty, shipped_qty)
                    ELSE 0
                END
            ) AS total_arrived_qty
        FROM tube.tube_delivery
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}"
            result[key] = {
                "total_arrived_qty": float(row["total_arrived_qty"]) if row["total_arrived_qty"] is not None else 0,
            }
        return result
    finally:
        session.close()


def list_usage_totals() -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(usage_qty) AS total_usage_qty
        FROM tube.tube_daily_usage
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}"
            result[key] = {
                "total_usage_qty": float(row["total_usage_qty"]) if row["total_usage_qty"] is not None else 0,
            }
        return result
    finally:
        session.close()


def list_delivery_records(
    supply_entity_ids: Sequence[str],
    station_id: str = "",
    status: str = "",
) -> List[Dict[str, Any]]:
    normalized_entity_ids = [item for item in (_normalize_text(value) for value in supply_entity_ids) if item]
    if not normalized_entity_ids:
        return []
    sql = text(
        """
        SELECT
            id,
            supply_entity_id,
            station_id,
            pipe_model_id,
            shipped_qty,
            arrived_qty,
            received_qty,
            shipped_at,
            ship_contact_name,
            ship_contact_phone,
            ship_remark,
            arrived_confirm_by,
            arrived_confirm_at,
            arrived_remark,
            received_confirm_by,
            received_confirm_at,
            received_remark,
            warehouse_confirm_by,
            warehouse_confirm_at,
            warehouse_remark,
            status,
            abnormal_flag,
            cancel_by,
            cancel_at,
            cancel_reason,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM tube.tube_delivery
        WHERE supply_entity_id = ANY(:supply_entity_ids)
          AND (:station_id = '' OR station_id = :station_id)
          AND (:status = '' OR status = :status)
        ORDER BY shipped_at DESC, id DESC
        LIMIT 500
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(
            sql,
            {
                "supply_entity_ids": normalized_entity_ids,
                "station_id": _normalize_text(station_id),
                "status": _normalize_text(status),
            },
        ).mappings().all()
        return [
            {
                "id": int(row["id"]),
                "supply_entity_id": _normalize_text(row["supply_entity_id"]),
                "station_id": _normalize_text(row["station_id"]),
                "pipe_model_id": _normalize_pipe_model_id(row["pipe_model_id"]),
                "shipped_qty": float(row["shipped_qty"]) if row["shipped_qty"] is not None else 0,
                "arrived_qty": float(row["arrived_qty"]) if row["arrived_qty"] is not None else None,
                "received_qty": float(row["received_qty"]) if row["received_qty"] is not None else None,
                "shipped_at": row["shipped_at"].isoformat() if row["shipped_at"] else "",
                "ship_contact_name": row["ship_contact_name"] or "",
                "ship_contact_phone": row["ship_contact_phone"] or "",
                "ship_remark": row["ship_remark"] or "",
                "arrived_confirm_by": row["arrived_confirm_by"] or "",
                "arrived_confirm_at": row["arrived_confirm_at"].isoformat() if row["arrived_confirm_at"] else "",
                "arrived_remark": row["arrived_remark"] or "",
                "received_confirm_by": row["received_confirm_by"] or "",
                "received_confirm_at": row["received_confirm_at"].isoformat() if row["received_confirm_at"] else "",
                "received_remark": row["received_remark"] or "",
                "warehouse_confirm_by": row["warehouse_confirm_by"] or "",
                "warehouse_confirm_at": row["warehouse_confirm_at"].isoformat() if row["warehouse_confirm_at"] else "",
                "warehouse_remark": row["warehouse_remark"] or "",
                "status": row["status"] or "",
                "abnormal_flag": bool(row["abnormal_flag"]),
                "cancel_by": row["cancel_by"] or "",
                "cancel_at": row["cancel_at"].isoformat() if row["cancel_at"] else "",
                "cancel_reason": row["cancel_reason"] or "",
                "created_by": row["created_by"] or "",
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "updated_by": row["updated_by"] or "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else "",
            }
            for row in rows
        ]
    finally:
        session.close()


def create_delivery_record(
    *,
    supply_entity_id: str,
    station_id: str,
    pipe_model_id: str,
    shipped_qty: float,
    shipped_at: datetime,
    ship_contact_name: str,
    ship_contact_phone: str,
    ship_remark: str,
    operator: str,
) -> int:
    if shipped_qty <= 0:
        raise HTTPException(status_code=422, detail="发货量必须大于 0")
    sql = text(
        """
        INSERT INTO tube.tube_delivery (
            supply_entity_id,
            station_id,
            pipe_model_id,
            shipped_qty,
            shipped_at,
            ship_contact_name,
            ship_contact_phone,
            ship_remark,
            status,
            created_by,
            created_at,
            updated_by,
            updated_at
        )
        VALUES (
            :supply_entity_id,
            :station_id,
            :pipe_model_id,
            :shipped_qty,
            :shipped_at,
            :ship_contact_name,
            :ship_contact_phone,
            :ship_remark,
            'pending_arrival',
            :created_by,
            NOW(),
            :updated_by,
            NOW()
        )
        RETURNING id
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(
            sql,
            {
                "supply_entity_id": _normalize_text(supply_entity_id),
                "station_id": _normalize_text(station_id),
                "pipe_model_id": _normalize_pipe_model_id(pipe_model_id),
                "shipped_qty": float(shipped_qty),
                "shipped_at": shipped_at,
                "ship_contact_name": _normalize_text(ship_contact_name),
                "ship_contact_phone": _normalize_text(ship_contact_phone),
                "ship_remark": _normalize_text(ship_remark),
                "created_by": operator,
                "updated_by": operator,
            },
        ).mappings().first()
        session.commit()
        return int(row["id"]) if row and row["id"] is not None else 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def cancel_delivery_record(
    delivery_id: int,
    allowed_supply_entity_ids: Sequence[str],
    operator: str,
    cancel_reason: str,
) -> None:
    normalized_entity_ids = [item for item in (_normalize_text(value) for value in allowed_supply_entity_ids) if item]
    if not normalized_entity_ids:
        raise HTTPException(status_code=403, detail="当前账号无可操作的供给主体")
    sql_get = text(
        """
        SELECT id, supply_entity_id, status
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            status = 'cancelled',
            cancel_by = :cancel_by,
            cancel_at = NOW(),
            cancel_reason = :cancel_reason,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE id = :delivery_id
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(sql_get, {"delivery_id": int(delivery_id)}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"发货记录不存在：{delivery_id}")
        supply_entity_id = _normalize_text(row["supply_entity_id"])
        if supply_entity_id not in normalized_entity_ids:
            raise HTTPException(status_code=403, detail="当前账号无权撤销该发货记录")
        if _normalize_text(row["status"]) != "pending_arrival":
            raise HTTPException(status_code=422, detail="仅“已发货待到货”状态允许撤销")
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "cancel_by": operator,
                "cancel_reason": _normalize_text(cancel_reason) or "供给侧撤销发货",
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
