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


def list_arrival_aggregates(show_date: str) -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(
                CASE
                    WHEN status <> 'cancelled'
                         AND COALESCE(arrived_qty, 0) > 0
                         AND arrived_confirm_at < :show_date
                        THEN COALESCE(received_qty, arrived_qty, shipped_qty)
                    ELSE 0
                END
            ) AS total_arrived_qty
        FROM tube.tube_delivery
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"show_date": str(show_date)}).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            key = f"{_normalize_text(row['station_id'])}::{_normalize_pipe_model_id(row['pipe_model_id'])}"
            result[key] = {
                "total_arrived_qty": float(row["total_arrived_qty"]) if row["total_arrived_qty"] is not None else 0,
            }
        return result
    finally:
        session.close()


def list_usage_totals(show_date: str) -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(usage_qty) AS total_usage_qty
        FROM tube.tube_daily_usage
        WHERE usage_date < :show_date
        GROUP BY station_id, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"show_date": str(show_date)}).mappings().all()
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
                "delivery_code": build_delivery_code(
                    int(row["id"]),
                    row["shipped_at"],
                    _normalize_text(row["supply_entity_id"]),
                ),
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


def build_delivery_code(
    delivery_id: int,
    shipped_at: Optional[datetime] = None,
    supply_entity_id: str = "",
    delivery_prefix: str = "",
) -> str:
    prefix = _normalize_text(delivery_prefix).upper()
    if not prefix:
        raw_prefix = _normalize_text(supply_entity_id).upper()
        if raw_prefix:
            parts = [part for part in raw_prefix.replace("-", "_").split("_") if part]
            if len(parts) >= 2:
                prefix = "".join(part[0] for part in parts if part[:1])
            else:
                prefix = "".join(ch for ch in raw_prefix if ch.isalnum())[:4]
    if not prefix:
        prefix = "DEL"
    date_part = shipped_at.strftime("%y%m%d") if shipped_at else ""
    seq_part = f"{int(delivery_id):03d}"
    if prefix and date_part:
        return f"{prefix}-{date_part}-{seq_part}"
    if prefix:
        return f"{prefix}-{seq_part}"
    if date_part:
        return f"DEL-{date_part}-{seq_part}"
    return f"DEL-{seq_part}"


def format_delivery_elapsed(
    shipped_at: Optional[datetime],
    now_at: Optional[datetime] = None,
    arrived_confirm_at: Optional[datetime] = None,
) -> str:
    if not shipped_at:
        return ""
    if arrived_confirm_at:
        if shipped_at.tzinfo is None or shipped_at.tzinfo.utcoffset(shipped_at) is None:
            current = arrived_confirm_at
            if current.tzinfo is not None and current.tzinfo.utcoffset(current) is not None:
                current = current.replace(tzinfo=None)
        else:
            current = arrived_confirm_at
            if current.tzinfo is None or current.tzinfo.utcoffset(current) is None:
                current = current.replace(tzinfo=shipped_at.tzinfo)
            else:
                current = current.astimezone(shipped_at.tzinfo)
    elif shipped_at.tzinfo is None or shipped_at.tzinfo.utcoffset(shipped_at) is None:
        current = now_at or datetime.now()
        if current.tzinfo is not None and current.tzinfo.utcoffset(current) is not None:
            current = current.replace(tzinfo=None)
    else:
        current = now_at or datetime.now(shipped_at.tzinfo)
        if current.tzinfo is None or current.tzinfo.utcoffset(current) is None:
            current = current.replace(tzinfo=shipped_at.tzinfo)
        else:
            current = current.astimezone(shipped_at.tzinfo)
    total_seconds = max(int((current - shipped_at).total_seconds()), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}天{hours}小时{minutes}分"
    if hours > 0:
        return f"{hours}小时{minutes}分"
    if minutes > 0:
        return f"{minutes}分{seconds}秒"
    return f"{seconds}秒"


def get_delivery_record_basic(delivery_id: int) -> Dict[str, Any]:
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
            status
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(sql, {"delivery_id": int(delivery_id)}).mappings().first()
        if not row:
            return {}
        return {
            "id": int(row["id"]),
            "supply_entity_id": _normalize_text(row["supply_entity_id"]),
            "station_id": _normalize_text(row["station_id"]),
            "pipe_model_id": _normalize_pipe_model_id(row["pipe_model_id"]),
            "shipped_qty": float(row["shipped_qty"]) if row["shipped_qty"] is not None else 0,
            "arrived_qty": float(row["arrived_qty"]) if row["arrived_qty"] is not None else None,
            "received_qty": float(row["received_qty"]) if row["received_qty"] is not None else None,
            "shipped_at": row["shipped_at"],
            "status": row["status"] or "",
        }
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


def update_delivery_arrival_record(
    delivery_id: int,
    operator: str,
    arrived_qty: float,
    remark: str = "",
) -> None:
    if arrived_qty < 0:
        raise HTTPException(status_code=422, detail="到货数量不能为负数")
    sql_get = text(
        """
        SELECT id, shipped_qty, status
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            arrived_qty = :arrived_qty,
            arrived_confirm_by = :arrived_confirm_by,
            arrived_confirm_at = NOW(),
            arrived_remark = :arrived_remark,
            status = 'pending_receive',
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
        if _normalize_text(row["status"]) != "pending_arrival":
            raise HTTPException(status_code=422, detail="仅“已发货待到货”状态允许确认到货")
        shipped_qty = float(row["shipped_qty"] or 0)
        normalized_arrived_qty = float(arrived_qty if arrived_qty is not None else shipped_qty)
        if normalized_arrived_qty <= 0:
            raise HTTPException(status_code=422, detail="到货数量必须大于 0")
        if normalized_arrived_qty > shipped_qty:
            raise HTTPException(status_code=422, detail="到货数量不能大于发货数量")
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "arrived_qty": normalized_arrived_qty,
                "arrived_confirm_by": operator,
                "arrived_remark": _normalize_text(remark),
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_delivery_receipt_record(
    delivery_id: int,
    operator: str,
    received_qty: float,
    remark: str = "",
) -> None:
    if received_qty < 0:
        raise HTTPException(status_code=422, detail="施工接收数量不能为负数")
    sql_get = text(
        """
        SELECT id, shipped_qty, arrived_qty, status
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            received_qty = :received_qty,
            received_confirm_by = :received_confirm_by,
            received_confirm_at = NOW(),
            received_remark = :received_remark,
            status = 'pending_warehouse',
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
        if _normalize_text(row["status"]) != "pending_receive":
            raise HTTPException(status_code=422, detail="仅“已到货待接收”状态允许施工接收")
        arrived_qty = float(row["arrived_qty"] if row["arrived_qty"] is not None else row["shipped_qty"] or 0)
        normalized_received_qty = float(received_qty if received_qty is not None else arrived_qty)
        if normalized_received_qty <= 0:
            raise HTTPException(status_code=422, detail="施工接收数量必须大于 0")
        if normalized_received_qty > arrived_qty:
            raise HTTPException(status_code=422, detail="施工接收数量不能大于到货数量")
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "received_qty": normalized_received_qty,
                "received_confirm_by": operator,
                "received_remark": _normalize_text(remark),
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_delivery_warehouse_record(
    delivery_id: int,
    operator: str,
    remark: str = "",
) -> None:
    sql_get = text(
        """
        SELECT id, status
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            status = 'completed',
            warehouse_confirm_by = :warehouse_confirm_by,
            warehouse_confirm_at = NOW(),
            warehouse_remark = :warehouse_remark,
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
        if _normalize_text(row["status"]) != "pending_warehouse":
            raise HTTPException(status_code=422, detail="仅“已接收待库管确认”状态允许库管确认")
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "warehouse_confirm_by": operator,
                "warehouse_remark": _normalize_text(remark),
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
