# -*- coding: utf-8 -*-
"""
tube 项目需求侧服务。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Sequence

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_pipe_model_id(value: Any) -> str:
    return _normalize_text(value).upper()


def build_plan_dates(anchor_date: date) -> List[date]:
    return [anchor_date + timedelta(days=offset) for offset in range(3)]


def list_plan_records(station_id: str, plan_dates: Sequence[date]) -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            plan_date,
            pipe_model_id,
            plan_qty,
            remark
        FROM tube.tube_daily_plan
        WHERE station_id = :station_id
          AND plan_date = ANY(:plan_dates)
        ORDER BY plan_date, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"station_id": station_id, "plan_dates": list(plan_dates)}).mappings().all()
        result: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            date_key = row["plan_date"].isoformat()
            result[f"{_normalize_pipe_model_id(row['pipe_model_id'])}::{date_key}"] = {
                "plan_qty": float(row["plan_qty"]) if row["plan_qty"] is not None else None,
                "remark": row["remark"] or "",
            }
        return result
    finally:
        session.close()


def save_plan_records(station_id: str, records: Sequence[Dict[str, Any]], operator: str) -> int:
    if not records:
        return 0
    sql = text(
        """
        INSERT INTO tube.tube_daily_plan (
            plan_date,
            station_id,
            pipe_model_id,
            plan_qty,
            filled_by,
            filled_at,
            remark,
            updated_by,
            updated_at
        )
        VALUES (
            :plan_date,
            :station_id,
            :pipe_model_id,
            :plan_qty,
            :filled_by,
            NOW(),
            :remark,
            :updated_by,
            NOW()
        )
        ON CONFLICT (plan_date, station_id, pipe_model_id)
        DO UPDATE SET
            plan_qty = EXCLUDED.plan_qty,
            remark = EXCLUDED.remark,
            updated_by = EXCLUDED.updated_by,
            updated_at = NOW()
        """
    )
    session = SessionLocal()
    try:
        payloads = []
        for item in records:
            plan_qty = float(item["plan_qty"])
            if plan_qty < 0:
                raise HTTPException(status_code=422, detail="计划量不能为负数")
            payloads.append(
                {
                    "plan_date": item["plan_date"],
                    "station_id": station_id,
                    "pipe_model_id": _normalize_pipe_model_id(item["pipe_model_id"]),
                    "plan_qty": plan_qty,
                    "filled_by": operator,
                    "remark": _normalize_text(item.get("remark")),
                    "updated_by": operator,
                }
            )
        session.execute(sql, payloads)
        session.commit()
        return len(payloads)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_usage_records(station_id: str, usage_date: date) -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            pipe_model_id,
            usage_qty,
            remark
        FROM tube.tube_daily_usage
        WHERE station_id = :station_id
          AND usage_date = :usage_date
        ORDER BY pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"station_id": station_id, "usage_date": usage_date}).mappings().all()
        return {
            _normalize_pipe_model_id(row["pipe_model_id"]): {
                "usage_qty": float(row["usage_qty"]) if row["usage_qty"] is not None else None,
                "remark": row["remark"] or "",
            }
            for row in rows
        }
    finally:
        session.close()


def save_usage_records(station_id: str, usage_date: date, records: Sequence[Dict[str, Any]], operator: str) -> int:
    if not records:
        return 0
    sql = text(
        """
        INSERT INTO tube.tube_daily_usage (
            usage_date,
            station_id,
            pipe_model_id,
            usage_qty,
            filled_by,
            filled_at,
            remark,
            updated_by,
            updated_at
        )
        VALUES (
            :usage_date,
            :station_id,
            :pipe_model_id,
            :usage_qty,
            :filled_by,
            NOW(),
            :remark,
            :updated_by,
            NOW()
        )
        ON CONFLICT (usage_date, station_id, pipe_model_id)
        DO UPDATE SET
            usage_qty = EXCLUDED.usage_qty,
            remark = EXCLUDED.remark,
            updated_by = EXCLUDED.updated_by,
            updated_at = NOW()
        """
    )
    session = SessionLocal()
    try:
        payloads = []
        for item in records:
            usage_qty = float(item["usage_qty"])
            if usage_qty < 0:
                raise HTTPException(status_code=422, detail="实际使用量不能为负数")
            
            pipe_model_id = _normalize_pipe_model_id(item["pipe_model_id"])

            # 1. 累计到货量：非 cancelled 且已到现场确认的发货记录中可用量之和
            sql_arrived = text(
                """
                SELECT SUM(COALESCE(received_qty, arrived_qty, shipped_qty)) AS total
                FROM tube.tube_delivery
                WHERE station_id = :station_id
                  AND pipe_model_id = :pipe_model_id
                  AND status <> 'cancelled'
                  AND arrived_confirm_at IS NOT NULL
                """
            )
            arrived_row = session.execute(sql_arrived, {"station_id": station_id, "pipe_model_id": pipe_model_id}).first()
            total_arrived = float(arrived_row[0]) if arrived_row and arrived_row[0] is not None else 0.0

            # 2. 除去今日所填之外的历史累计使用量之和
            sql_usage_before = text(
                """
                SELECT SUM(usage_qty) AS total
                FROM tube.tube_daily_usage
                WHERE station_id = :station_id
                  AND pipe_model_id = :pipe_model_id
                  AND usage_date <> :usage_date
                """
            )
            usage_before_row = session.execute(
                sql_usage_before, 
                {"station_id": station_id, "pipe_model_id": pipe_model_id, "usage_date": usage_date}
            ).first()
            total_usage_before = float(usage_before_row[0]) if usage_before_row and usage_before_row[0] is not None else 0.0

            expected_total_usage = total_usage_before + usage_qty

            # 3. 负库存硬性拦截校验：累计消耗量不能大于账面累计到货量
            if expected_total_usage > total_arrived:
                # 计算在途待到货量
                sql_pending = text(
                    """
                    SELECT SUM(shipped_qty) AS total
                    FROM tube.tube_delivery
                    WHERE station_id = :station_id
                      AND pipe_model_id = :pipe_model_id
                      AND status = 'pending_arrival'
                    """
                )
                pending_row = session.execute(sql_pending, {"station_id": station_id, "pipe_model_id": pipe_model_id}).first()
                pending_arrival = float(pending_row[0]) if pending_row and pending_row[0] is not None else 0.0
                
                shortage = expected_total_usage - total_arrived
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"⚠️ 提交失败：现场可用账面库存不足！保温管规格【{pipe_model_id}】累计到货仅为 {total_arrived:.1f} 米，"
                        f"但若保存本次使用量填报，累计消耗将达到 {expected_total_usage:.1f} 米（账面超前亏空 {shortage:.1f} 米）。\n"
                        f"🚚 运输信息提示：当前正有 {pending_arrival:.1f} 米在途物资（已发货待到货确认）。"
                        f"请先对已到现场的物资执行【到货确认】以补充账面库存，再返回提交实际使用量！"
                    )
                )

            payloads.append(
                {
                    "usage_date": usage_date,
                    "station_id": station_id,
                    "pipe_model_id": pipe_model_id,
                    "usage_qty": usage_qty,
                    "filled_by": operator,
                    "remark": _normalize_text(item.get("remark")),
                    "updated_by": operator,
                }
            )
        session.execute(sql, payloads)
        session.commit()
        return len(payloads)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_pending_arrivals(station_id: str) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT
            id,
            supply_entity_id,
            station_id,
            pipe_model_id,
            shipped_qty,
            shipped_at,
            ship_contact_name,
            ship_contact_phone,
            ship_remark,
            status,
            abnormal_flag
        FROM tube.tube_delivery
        WHERE station_id = :station_id
          AND status = 'pending_arrival'
        ORDER BY shipped_at DESC, id DESC
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"station_id": station_id}).mappings().all()
        return [
            {
                "id": int(row["id"]),
                "supply_entity_id": _normalize_text(row["supply_entity_id"]),
                "station_id": _normalize_text(row["station_id"]),
                "pipe_model_id": _normalize_pipe_model_id(row["pipe_model_id"]),
                "shipped_qty": float(row["shipped_qty"]) if row["shipped_qty"] is not None else None,
                "shipped_at": row["shipped_at"].isoformat() if row["shipped_at"] else "",
                "ship_contact_name": row["ship_contact_name"] or "",
                "ship_contact_phone": row["ship_contact_phone"] or "",
                "ship_remark": row["ship_remark"] or "",
                "status": row["status"] or "",
                "abnormal_flag": bool(row["abnormal_flag"]),
            }
            for row in rows
        ]
    finally:
        session.close()
