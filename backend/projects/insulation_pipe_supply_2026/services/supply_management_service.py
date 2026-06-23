# -*- coding: utf-8 -*-
"""
tube 项目供给侧服务。
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal


BEIJING_TZ = timezone(timedelta(hours=8))


def _to_beijing_time(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(BEIJING_TZ)
    return dt


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


def auto_process_timeout_deliveries(session=None) -> None:
    is_local_session = False
    if session is None:
        session = SessionLocal()
        is_local_session = True
    try:
        sql = text(
            """
            UPDATE tube.tube_delivery
            SET
                received_qty = COALESCE(arrived_qty, shipped_qty),
                status = 'pending_warehouse',
                received_confirm_by = 'SYSTEM_TIMEOUT',
                received_confirm_at = COALESCE(arrived_confirm_at, NOW()) + INTERVAL '12 hours',
                received_remark = '🕒 [系统超时确认] 超出12小时未接收，系统强制确认为到货量。',
                is_timeout_receive = TRUE,
                updated_by = 'SYSTEM_TIMEOUT',
                updated_at = NOW()
            WHERE status = 'pending_receive'
              AND arrived_confirm_at IS NOT NULL
              AND arrived_confirm_at < NOW() - INTERVAL '12 hours'
            """
        )
        session.execute(sql)
        if is_local_session:
            session.commit()
    except Exception:
        if is_local_session:
            session.rollback()
        raise
    finally:
        if is_local_session:
            session.close()


def list_delivery_aggregates() -> Dict[str, Dict[str, Any]]:
    auto_process_timeout_deliveries()
    sql = text(
        """
        SELECT
            station_id,
            pipe_model_id,
            SUM(CASE WHEN status = 'pending_arrival' THEN shipped_qty ELSE 0 END) AS pending_arrival_qty,
            SUM(CASE WHEN status = 'pending_receive' THEN COALESCE(arrived_qty, shipped_qty) ELSE 0 END) AS pending_receive_qty,
            SUM(CASE WHEN status = 'pending_warehouse' OR status = 'pending_diff_approve' THEN COALESCE(received_qty, 0) ELSE 0 END) AS pending_warehouse_qty,
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
    auto_process_timeout_deliveries()
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
                        THEN 
                            CASE 
                                WHEN status = 'pending_receive' THEN COALESCE(arrived_qty, shipped_qty)
                                ELSE COALESCE(received_qty, arrived_qty, shipped_qty)
                            END
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
            SUM(usage_qty) AS total_usage_qty,
            SUM(loss_qty) AS total_loss_qty
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
                "total_usage_qty": float(row["total_usage_qty"]) if row["total_usage_qty"] is not None else 0.0,
                "total_loss_qty": float(row["total_loss_qty"]) if row["total_loss_qty"] is not None else 0.0,
            }
        return result
    finally:
        session.close()


def list_delivery_records(
    supply_entity_ids: Sequence[str],
    station_id: str = "",
    status: str = "",
) -> List[Dict[str, Any]]:
    auto_process_timeout_deliveries()
    normalized_entity_ids = [item for item in (_normalize_text(value) for value in supply_entity_ids) if item]
    if not normalized_entity_ids:
        return []
    sql = text(
        """
        SELECT
            id,
            supply_entity_id,
            order_no,
            shipment_no,
            vehicle_plate_no,
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
            updated_at,
            diff_approve_by,
            diff_approve_at,
            diff_approve_remark,
            is_timeout_receive
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
                "order_no": _normalize_text(row["order_no"]),
                "shipment_no": _normalize_text(row["shipment_no"]),
                "vehicle_plate_no": _normalize_text(row["vehicle_plate_no"]),
                "delivery_code": _normalize_text(row["order_no"]) or build_delivery_code(
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
                "diff_approve_by": row["diff_approve_by"] or "",
                "diff_approve_at": row["diff_approve_at"].isoformat() if row["diff_approve_at"] else "",
                "diff_approve_remark": row["diff_approve_remark"] or "",
                "is_timeout_receive": bool(row["is_timeout_receive"]),
            }
            for row in rows
        ]
    finally:
        session.close()


def create_delivery_record(
    *,
    supply_entity_id: str,
    order_no: str,
    shipment_no: str,
    vehicle_plate_no: str,
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
            order_no,
            shipment_no,
            vehicle_plate_no,
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
            :order_no,
            :shipment_no,
            :vehicle_plate_no,
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
                "order_no": _normalize_text(order_no),
                "shipment_no": _normalize_text(shipment_no),
                "vehicle_plate_no": _normalize_text(vehicle_plate_no),
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


def update_delivery_identifiers(
    delivery_id: int,
    order_no: str,
    shipment_no: str,
    operator: str,
) -> None:
    sql = text(
        """
        UPDATE tube.tube_delivery
        SET
            order_no = :order_no,
            shipment_no = :shipment_no,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE id = :delivery_id
        """
    )
    session = SessionLocal()
    try:
        session.execute(
            sql,
            {
                "delivery_id": int(delivery_id),
                "order_no": _normalize_text(order_no),
                "shipment_no": _normalize_text(shipment_no),
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def sync_shipment_vehicle_plate(
    shipment_no: str,
    vehicle_plate_no: str,
    operator: str,
) -> None:
    normalized_shipment_no = _normalize_text(shipment_no)
    if not normalized_shipment_no:
        return
    sql = text(
        """
        UPDATE tube.tube_delivery
        SET
            vehicle_plate_no = :vehicle_plate_no,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE shipment_no = :shipment_no
        """
    )
    session = SessionLocal()
    try:
        session.execute(
            sql,
            {
                "shipment_no": normalized_shipment_no,
                "vehicle_plate_no": _normalize_text(vehicle_plate_no),
                "updated_by": operator,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_shipment_owner(shipment_no: str) -> Dict[str, Any]:
    normalized_shipment_no = _normalize_text(shipment_no)
    if not normalized_shipment_no:
        return {}
    sql = text(
        """
        SELECT
            shipment_no,
            supply_entity_id,
            MAX(NULLIF(TRIM(vehicle_plate_no), '')) AS vehicle_plate_no,
            COUNT(*) AS record_count
        FROM tube.tube_delivery
        WHERE shipment_no = :shipment_no
        GROUP BY shipment_no, supply_entity_id
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(sql, {"shipment_no": normalized_shipment_no}).mappings().first()
        if not row:
            return {}
        return {
            "shipment_no": _normalize_text(row["shipment_no"]),
            "supply_entity_id": _normalize_text(row["supply_entity_id"]),
            "vehicle_plate_no": _normalize_text(row["vehicle_plate_no"]),
            "record_count": int(row["record_count"] or 0),
        }
    finally:
        session.close()


def get_next_shipment_sequence(
    *,
    supply_code: str = "",
    shipped_at: Optional[datetime] = None,
) -> int:
    normalized_supply_code = _normalize_text(supply_code).upper() or "XX"
    beijing_shipped_at = _to_beijing_time(shipped_at)
    date_part = beijing_shipped_at.strftime("%y%m%d") if beijing_shipped_at else ""
    if not date_part:
        return 1
    shipment_prefix = f"S{normalized_supply_code}-{date_part}-"
    sql = text(
        """
        SELECT shipment_no
        FROM tube.tube_delivery
        WHERE shipment_no LIKE :shipment_prefix
        ORDER BY shipment_no DESC
        LIMIT 1
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(sql, {"shipment_prefix": f"{shipment_prefix}%"}).mappings().first()
        if not row:
            return 1
        shipment_no = _normalize_text(row["shipment_no"])
        if not shipment_no.startswith(shipment_prefix):
            return 1
        seq_text = shipment_no.rsplit("-", 1)[-1]
        seq_value = int(seq_text)
        return max(seq_value + 1, 1)
    except Exception:
        return 1
    finally:
        session.close()


def get_next_order_sequence(
    *,
    supply_code: str = "",
    shipped_at: Optional[datetime] = None,
) -> int:
    normalized_supply_code = _normalize_text(supply_code).upper() or "XX"
    beijing_shipped_at = _to_beijing_time(shipped_at)
    date_part = beijing_shipped_at.strftime("%y%m%d") if beijing_shipped_at else ""
    if not date_part:
        return 1
    order_prefix_pattern = f"O{normalized_supply_code}-%-{date_part}-%"
    sql = text(
        """
        SELECT order_no
        FROM tube.tube_delivery
        WHERE order_no LIKE :pattern
        ORDER BY order_no DESC
        LIMIT 1
        """
    )
    session = SessionLocal()
    try:
        row = session.execute(sql, {"pattern": order_prefix_pattern}).mappings().first()
        if not row:
            return 1
        order_no = _normalize_text(row["order_no"])
        seq_text = order_no.rsplit("-", 1)[-1]
        seq_value = int(seq_text)
        return max(seq_value + 1, 1)
    except Exception:
        return 1
    finally:
        session.close()


def build_order_no(
    sequence_no: int,
    shipped_at: Optional[datetime] = None,
    supply_code: str = "",
    station_code: str = "",
) -> str:
    normalized_supply_code = _normalize_text(supply_code).upper() or "XX"
    normalized_station_code = _normalize_text(station_code).upper() or "X"
    beijing_shipped_at = _to_beijing_time(shipped_at)
    date_part = beijing_shipped_at.strftime("%y%m%d") if beijing_shipped_at else ""
    seq_part = f"{int(sequence_no):03d}"
    if date_part:
        return f"O{normalized_supply_code}-{normalized_station_code}-{date_part}-{seq_part}"
    return f"O{normalized_supply_code}-{normalized_station_code}-{seq_part}"


def build_shipment_no(
    sequence_no: int,
    shipped_at: Optional[datetime] = None,
    supply_code: str = "",
) -> str:
    normalized_supply_code = _normalize_text(supply_code).upper() or "XX"
    beijing_shipped_at = _to_beijing_time(shipped_at)
    date_part = beijing_shipped_at.strftime("%y%m%d") if beijing_shipped_at else ""
    seq_part = f"{int(sequence_no):03d}"
    if date_part:
        return f"S{normalized_supply_code}-{date_part}-{seq_part}"
    return f"S{normalized_supply_code}-{seq_part}"


def build_delivery_code(
    delivery_id: int,
    shipped_at: Optional[datetime] = None,
    supply_entity_id: str = "",
    delivery_prefix: str = "",
) -> str:
    return build_order_no(
        delivery_id,
        shipped_at=shipped_at,
        supply_code=delivery_prefix or supply_entity_id,
        station_code="X",
    )


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
            order_no,
            shipment_no,
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
            "order_no": _normalize_text(row["order_no"]),
            "shipment_no": _normalize_text(row["shipment_no"]),
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
            abnormal_flag = :abnormal_flag,
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
        abnormal_flag = normalized_arrived_qty < shipped_qty
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "arrived_qty": normalized_arrived_qty,
                "abnormal_flag": abnormal_flag,
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
) -> str:
    if received_qty < 0:
        raise HTTPException(status_code=422, detail="施工接收数量不能为负数")
    sql_get = text(
        """
        SELECT id, shipped_qty, arrived_qty, status
               , abnormal_flag
        FROM tube.tube_delivery
        WHERE id = :delivery_id
        """
    )
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            received_qty = :received_qty,
            abnormal_flag = :abnormal_flag,
            received_confirm_by = :received_confirm_by,
            received_confirm_at = NOW(),
            received_remark = :received_remark,
            status = :new_status,
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
        
        is_diff = normalized_received_qty < arrived_qty
        if is_diff:
            clean_remark = str(remark or "").strip()
            if len(clean_remark) < 10:
                raise HTTPException(status_code=422, detail="检测到少到货/少接收差异，必须填写不少于10个字符的备注说明理由")
            new_status = 'pending_diff_approve'
        else:
            new_status = 'pending_warehouse'
            
        abnormal_flag = bool(row["abnormal_flag"]) or is_diff
        session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "received_qty": normalized_received_qty,
                "abnormal_flag": abnormal_flag,
                "received_confirm_by": operator,
                "received_remark": _normalize_text(remark),
                "new_status": new_status,
                "updated_by": operator,
            },
        )
        session.commit()
        return new_status
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


def super_update_delivery_record(
    *,
    delivery_id: int,
    station_id: str,
    pipe_model_id: str,
    shipped_qty: float,
    shipped_at: datetime,
    vehicle_plate_no: str,
    ship_remark: str,
    status: str,
    order_no: str,
    shipment_no: str,
    arrived_qty: Optional[float] = None,
    received_qty: Optional[float] = None,
    arrived_confirm_at: Optional[datetime] = None,
    received_confirm_at: Optional[datetime] = None,
    warehouse_confirm_at: Optional[datetime] = None,
    operator: str,
) -> None:
    session = SessionLocal()
    try:
        check_sql = text(
            """
            SELECT id, status, arrived_confirm_by, received_confirm_by, warehouse_confirm_by, ship_remark,
                   diff_approve_by, diff_approve_at, diff_approve_remark, is_timeout_receive
            FROM tube.tube_delivery WHERE id = :id
            """
        )
        orig_record = session.execute(check_sql, {"id": delivery_id}).mappings().first()
        if not orig_record:
            raise HTTPException(status_code=404, detail="发货记录不存在，无法更新")
        
        # 规整状态名称映射
        normalized_status = _normalize_text(status).lower()
        if normalized_status == "arrived":
            normalized_status = "pending_receive"
        elif normalized_status == "received":
            normalized_status = "pending_warehouse"

        val_shipped_qty = max(float(shipped_qty), 0.01)
        val_arrived_qty = float(arrived_qty) if arrived_qty is not None else None
        val_received_qty = float(received_qty) if received_qty is not None else None

        dt_arrived_confirm_at = arrived_confirm_at
        dt_received_confirm_at = received_confirm_at
        dt_warehouse_confirm_at = warehouse_confirm_at

        # 从数据库中拉取历史操作人，如果为空则默认为当前管理员
        op_arrived_by = orig_record["arrived_confirm_by"] or operator
        op_received_by = orig_record["received_confirm_by"] or operator
        op_warehouse_by = orig_record["warehouse_confirm_by"] or operator

        # 继承或重置差异审批/超时接收元数据状态
        val_diff_approve_by = orig_record["diff_approve_by"]
        val_diff_approve_at = orig_record["diff_approve_at"]
        val_diff_approve_remark = orig_record["diff_approve_remark"]
        val_is_timeout_receive = bool(orig_record["is_timeout_receive"])

        # 根据目标状态执行逆向级联不变量校准
        if normalized_status in {"pending_arrival", "cancelled"}:
            # 在途或已撤销，清空一切子状态数据
            val_arrived_qty = None
            val_received_qty = None
            dt_arrived_confirm_at = None
            dt_received_confirm_at = None
            dt_warehouse_confirm_at = None
            op_arrived_by = None
            op_received_by = None
            op_warehouse_by = None
            
            # 清空差异审批与超时状态
            val_diff_approve_by = None
            val_diff_approve_at = None
            val_diff_approve_remark = None
            val_is_timeout_receive = False

        elif normalized_status == "pending_receive":
            # 已到货待接收，必有到货数据凭证
            if val_arrived_qty is None or val_arrived_qty <= 0:
                val_arrived_qty = val_shipped_qty
            val_arrived_qty = min(val_arrived_qty, val_shipped_qty)

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=12)
            if dt_arrived_confirm_at < shipped_at:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=1)

            val_received_qty = None
            dt_received_confirm_at = None
            dt_warehouse_confirm_at = None
            op_received_by = None
            op_warehouse_by = None
            
            # 清空差异审批与超时状态
            val_diff_approve_by = None
            val_diff_approve_at = None
            val_diff_approve_remark = None
            val_is_timeout_receive = False

        elif normalized_status == "pending_diff_approve":
            # 待差异审批：到货与施工接收凭证必齐，且实收必须严格小于到货
            if val_arrived_qty is None or val_arrived_qty <= 0:
                val_arrived_qty = val_shipped_qty
            val_arrived_qty = min(val_arrived_qty, val_shipped_qty)

            if val_received_qty is None:
                val_received_qty = max(val_arrived_qty - 1.0, 0.0)
            else:
                val_received_qty = min(val_received_qty, max(val_arrived_qty - 0.01, 0.0))

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=12)
            if dt_arrived_confirm_at < shipped_at:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=1)

            if dt_received_confirm_at is None:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=6)
            if dt_received_confirm_at < dt_arrived_confirm_at:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=1)

            dt_warehouse_confirm_at = None
            op_warehouse_by = None
            
            # 挂起待审批，清空已审批信息
            val_diff_approve_by = None
            val_diff_approve_at = None
            val_diff_approve_remark = None

        elif normalized_status == "pending_warehouse":
            # 已接收待库管确认，必有到货与施工接收凭证
            if val_arrived_qty is None or val_arrived_qty <= 0:
                val_arrived_qty = val_shipped_qty
            val_arrived_qty = min(val_arrived_qty, val_shipped_qty)

            if val_received_qty is None or val_received_qty <= 0:
                val_received_qty = val_arrived_qty
            val_received_qty = min(val_received_qty, val_arrived_qty)

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=12)
            if dt_arrived_confirm_at < shipped_at:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=1)

            if dt_received_confirm_at is None:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=6)
            if dt_received_confirm_at < dt_arrived_confirm_at:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=1)

            dt_warehouse_confirm_at = None
            op_warehouse_by = None

            # 校验少接收确认是否具有审批凭证
            if val_received_qty == val_arrived_qty:
                val_diff_approve_by = None
                val_diff_approve_at = None
                val_diff_approve_remark = None
                val_is_timeout_receive = False
            else:
                # 确实少收了，如果原本没有审批信息，自动补上虚拟系统审批
                if not val_diff_approve_by:
                    val_diff_approve_by = operator
                    val_diff_approve_at = dt_received_confirm_at + timedelta(minutes=30)
                    val_diff_approve_remark = "[管理员强改修正，自动补全差异确认手续]"

        elif normalized_status == "completed":
            # 已入库结清，必有完整的时空与数量时序链
            if val_arrived_qty is None or val_arrived_qty <= 0:
                val_arrived_qty = val_shipped_qty
            val_arrived_qty = min(val_arrived_qty, val_shipped_qty)

            if val_received_qty is None or val_received_qty <= 0:
                val_received_qty = val_arrived_qty
            val_received_qty = min(val_received_qty, val_arrived_qty)

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=12)
            if dt_arrived_confirm_at < shipped_at:
                dt_arrived_confirm_at = shipped_at + timedelta(hours=1)

            if dt_received_confirm_at is None:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=6)
            if dt_received_confirm_at < dt_arrived_confirm_at:
                dt_received_confirm_at = dt_arrived_confirm_at + timedelta(hours=1)

            if dt_warehouse_confirm_at is None:
                dt_warehouse_confirm_at = dt_received_confirm_at + timedelta(hours=2)
            if dt_warehouse_confirm_at < dt_received_confirm_at:
                dt_warehouse_confirm_at = dt_received_confirm_at + timedelta(hours=1)

            # 校验少接收确认是否具有审批凭证
            if val_received_qty == val_arrived_qty:
                val_diff_approve_by = None
                val_diff_approve_at = None
                val_diff_approve_remark = None
                val_is_timeout_receive = False
            else:
                if not val_diff_approve_by:
                    val_diff_approve_by = operator
                    val_diff_approve_at = dt_received_confirm_at + timedelta(minutes=30)
                    val_diff_approve_remark = "[管理员强改修正，自动补全差异确认手续]"

        # 智能重新评估 abnormal_flag
        new_abnormal_flag = False
        if normalized_status not in {"pending_arrival", "cancelled"}:
            if val_arrived_qty is not None and val_arrived_qty < val_shipped_qty:
                new_abnormal_flag = True
            if val_received_qty is not None and val_arrived_qty is not None and val_received_qty < val_arrived_qty:
                new_abnormal_flag = True

        # 判定已取消撤销信息的流转
        new_cancel_by = None
        new_cancel_at = None
        new_cancel_reason = None
        
        cancel_info_sql = text("SELECT cancel_by, cancel_at, cancel_reason FROM tube.tube_delivery WHERE id = :id")
        orig_cancel = session.execute(cancel_info_sql, {"id": delivery_id}).mappings().first()

        if normalized_status == "cancelled":
            new_cancel_by = orig_cancel["cancel_by"] if orig_cancel and orig_cancel["cancel_by"] else operator
            new_cancel_at = orig_cancel["cancel_at"] if orig_cancel and orig_cancel["cancel_at"] else datetime.now()
            new_cancel_reason = orig_cancel["cancel_reason"] if orig_cancel and orig_cancel["cancel_reason"] else (_normalize_text(ship_remark) or "超级管理员编辑覆盖撤销")

        # 格式化自动审计备注打标
        audit_tag = f" | 状态强改至 {normalized_status}, 操作人: {operator}"
        clean_remark = _normalize_text(ship_remark)
        # 去除可能存在的历史系统备注打标，防止备注无限长
        if " | 状态强改至" in clean_remark:
            clean_remark = clean_remark.split(" | 状态强改至")[0]
        final_remark = clean_remark + audit_tag

        update_sql = text(
            """
            UPDATE tube.tube_delivery
            SET station_id = :station_id,
                pipe_model_id = :pipe_model_id,
                shipped_qty = :shipped_qty,
                shipped_at = :shipped_at,
                vehicle_plate_no = :vehicle_plate_no,
                ship_remark = :ship_remark,
                status = :status,
                order_no = :order_no,
                shipment_no = :shipment_no,
                arrived_qty = :arrived_qty,
                received_qty = :received_qty,
                arrived_confirm_by = :arrived_confirm_by,
                arrived_confirm_at = :arrived_confirm_at,
                received_confirm_by = :received_confirm_by,
                received_confirm_at = :received_confirm_at,
                warehouse_confirm_by = :warehouse_confirm_by,
                warehouse_confirm_at = :warehouse_confirm_at,
                abnormal_flag = :abnormal_flag,
                cancel_by = :cancel_by,
                cancel_at = :cancel_at,
                cancel_reason = :cancel_reason,
                diff_approve_by = :diff_approve_by,
                diff_approve_at = :diff_approve_at,
                diff_approve_remark = :diff_approve_remark,
                is_timeout_receive = :is_timeout_receive,
                updated_by = :operator,
                updated_at = NOW()
            WHERE id = :id
            """
        )
        session.execute(
            update_sql,
            {
                "id": delivery_id,
                "station_id": _normalize_text(station_id),
                "pipe_model_id": _normalize_pipe_model_id(pipe_model_id),
                "shipped_qty": val_shipped_qty,
                "shipped_at": shipped_at,
                "vehicle_plate_no": _normalize_text(vehicle_plate_no),
                "ship_remark": final_remark,
                "status": normalized_status,
                "order_no": _normalize_text(order_no),
                "shipment_no": _normalize_text(shipment_no),
                "arrived_qty": val_arrived_qty,
                "received_qty": val_received_qty,
                "arrived_confirm_by": op_arrived_by,
                "arrived_confirm_at": dt_arrived_confirm_at,
                "received_confirm_by": op_received_by,
                "received_confirm_at": dt_received_confirm_at,
                "warehouse_confirm_by": op_warehouse_by,
                "warehouse_confirm_at": dt_warehouse_confirm_at,
                "abnormal_flag": new_abnormal_flag,
                "cancel_by": new_cancel_by,
                "cancel_at": new_cancel_at,
                "cancel_reason": new_cancel_reason,
                "diff_approve_by": val_diff_approve_by,
                "diff_approve_at": val_diff_approve_at,
                "diff_approve_remark": val_diff_approve_remark,
                "is_timeout_receive": val_is_timeout_receive,
                "operator": operator,
            }
        )
        session.commit()
    except Exception as e:
        session.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"超级管理员强力更新数据失败: {str(e)}")
    finally:
        session.close()


