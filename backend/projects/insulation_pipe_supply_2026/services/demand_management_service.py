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
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    load_tube_config,
    get_config_list,
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_pipe_model_id(value: Any) -> str:
    return _normalize_text(value).upper()


def _build_pipe_model_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    pipe_models = get_config_list(payload, "pipe_models")
    return {
        _normalize_pipe_model_id(item.get("pipe_model_id")): item
        for item in pipe_models
        if _normalize_pipe_model_id(item.get("pipe_model_id"))
    }


def _build_section_1_name_map(payload: Dict[str, Any]) -> Dict[str, str]:
    demand_entities = get_config_list(payload, "demand_entities")
    return {
        _normalize_text(item.get("section_1_id")): _normalize_text(item.get("section_1_name"))
        for item in demand_entities
        if _normalize_text(item.get("section_1_id"))
    }


_structures_checked = False


def _ensure_demand_table_structures() -> None:
    """
    自愈检查并保证 tube_daily_plan 和 tube_daily_usage 等表的唯一约束与自增序列存在。
    """
    global _structures_checked
    if _structures_checked:
        return

    ddl_statements = [
        # 1. tube_daily_plan 自增序列与唯一索引
        "CREATE SEQUENCE IF NOT EXISTS tube.tube_daily_plan_id_seq",
        "ALTER TABLE tube.tube_daily_plan ALTER COLUMN id SET DEFAULT nextval('tube.tube_daily_plan_id_seq')",
        "ALTER SEQUENCE tube.tube_daily_plan_id_seq OWNED BY tube.tube_daily_plan.id",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_plan_date_section_1_model ON tube.tube_daily_plan (plan_date, section_1_id, pipe_model_id)",

        # 2. tube_daily_usage 自增序列与唯一索引
        "CREATE SEQUENCE IF NOT EXISTS tube.tube_daily_usage_id_seq",
        "ALTER TABLE tube.tube_daily_usage ALTER COLUMN id SET DEFAULT nextval('tube.tube_daily_usage_id_seq')",
        "ALTER SEQUENCE tube.tube_daily_usage_id_seq OWNED BY tube.tube_daily_usage.id",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_usage_date_section_1_model ON tube.tube_daily_usage (usage_date, section_1_id, pipe_model_id)",

        # 3. 其他业务表序列自愈
        "CREATE SEQUENCE IF NOT EXISTS tube.tube_inventory_adjustment_id_seq",
        "ALTER TABLE tube.tube_inventory_adjustment ALTER COLUMN id SET DEFAULT nextval('tube.tube_inventory_adjustment_id_seq')",
        "ALTER SEQUENCE tube.tube_inventory_adjustment_id_seq OWNED BY tube.tube_inventory_adjustment.id",

        "CREATE SEQUENCE IF NOT EXISTS tube.tube_weather_daily_id_seq",
        "ALTER TABLE tube.tube_weather_daily ALTER COLUMN id SET DEFAULT nextval('tube.tube_weather_daily_id_seq')",
        "ALTER SEQUENCE tube.tube_weather_daily_id_seq OWNED BY tube.tube_weather_daily.id",

        "CREATE SEQUENCE IF NOT EXISTS tube.tube_weather_hourly_id_seq",
        "ALTER TABLE tube.tube_weather_hourly ALTER COLUMN id SET DEFAULT nextval('tube.tube_weather_hourly_id_seq')",
        "ALTER SEQUENCE tube.tube_weather_hourly_id_seq OWNED BY tube.tube_weather_hourly.id",

        "CREATE SEQUENCE IF NOT EXISTS tube.tube_gis_id_seq",
        "ALTER TABLE tube.tube_gis ALTER COLUMN id SET DEFAULT nextval('tube.tube_gis_id_seq')",
        "ALTER SEQUENCE tube.tube_gis_id_seq OWNED BY tube.tube_gis.id",
    ]
    session = SessionLocal()
    try:
        for stmt in ddl_statements:
            try:
                session.execute(text(stmt))
                session.commit()
            except Exception:
                session.rollback()
        _structures_checked = True
    finally:
        session.close()


def build_plan_dates(anchor_date: date) -> List[date]:
    return [anchor_date + timedelta(days=offset) for offset in range(3)]


def list_plan_records(section_1_id: str, plan_dates: Sequence[date]) -> Dict[str, Dict[str, Any]]:
    _ensure_demand_table_structures()
    sql = text(
        """
        SELECT
            plan_date,
            pipe_model_id,
            plan_qty,
            remark
        FROM tube.tube_daily_plan
        WHERE section_1_id = :section_1_id
          AND plan_date = ANY(:plan_dates)
        ORDER BY plan_date, pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"section_1_id": section_1_id, "plan_dates": list(plan_dates)}).mappings().all()
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


def save_plan_records(section_1_id: str, records: Sequence[Dict[str, Any]], operator: str) -> int:
    if not records:
        return 0
    _ensure_demand_table_structures()
    sql = text(
        """
        INSERT INTO tube.tube_daily_plan (
            plan_date,
            section_1_id,
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
            :section_1_id,
            :pipe_model_id,
            :plan_qty,
            :filled_by,
            NOW(),
            :remark,
            :updated_by,
            NOW()
        )
        ON CONFLICT (plan_date, section_1_id, pipe_model_id)
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
                    "section_1_id": section_1_id,
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


def list_usage_records(section_1_id: str, usage_date: date) -> Dict[str, Dict[str, Any]]:
    sql = text(
        """
        SELECT
            pipe_model_id,
            usage_qty,
            loss_qty,
            remark
        FROM tube.tube_daily_usage
        WHERE section_1_id = :section_1_id
          AND usage_date = :usage_date
        ORDER BY pipe_model_id
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"section_1_id": section_1_id, "usage_date": usage_date}).mappings().all()
        return {
            _normalize_pipe_model_id(row["pipe_model_id"]): {
                "usage_qty": float(row["usage_qty"]) if row["usage_qty"] is not None else None,
                "loss_qty": float(row["loss_qty"]) if row["loss_qty"] is not None else None,
                "remark": row["remark"] or "",
            }
            for row in rows
        }
    finally:
        session.close()


def save_usage_records(section_1_id: str, usage_date: date, records: Sequence[Dict[str, Any]], operator: str) -> int:
    if not records:
        return 0
    _ensure_demand_table_structures()
        
    from backend.projects.insulation_pipe_supply_2026.services.supply_management_service import auto_process_timeout_deliveries
    # 前置执行超时自动确认
    auto_process_timeout_deliveries()

    sql = text(
        """
        INSERT INTO tube.tube_daily_usage (
            usage_date,
            section_1_id,
            pipe_model_id,
            usage_qty,
            loss_qty,
            filled_by,
            filled_at,
            remark,
            updated_by,
            updated_at
        )
        VALUES (
            :usage_date,
            :section_1_id,
            :pipe_model_id,
            :usage_qty,
            :loss_qty,
            :filled_by,
            NOW(),
            :remark,
            :updated_by,
            NOW()
        )
        ON CONFLICT (usage_date, section_1_id, pipe_model_id)
        DO UPDATE SET
            usage_qty = EXCLUDED.usage_qty,
            loss_qty = EXCLUDED.loss_qty,
            remark = EXCLUDED.remark,
            updated_by = EXCLUDED.updated_by,
            updated_at = NOW()
        """
    )
    
    # 批量收集型号并正规化
    normalized_pipe_model_ids = []
    pipe_model_orig_map = {}
    for item in records:
        norm_id = _normalize_pipe_model_id(item["pipe_model_id"])
        normalized_pipe_model_ids.append(norm_id)
        pipe_model_orig_map[norm_id] = item["pipe_model_id"]

    # 1. 批量查询累计到货量：支持新的算法定义
    sql_arrived_batch = text(
        """
        SELECT pipe_model_id, SUM(
            CASE 
                WHEN status = 'pending_receive' THEN COALESCE(arrived_qty, shipped_qty)
                ELSE COALESCE(received_qty, arrived_qty, shipped_qty)
            END
        ) AS total
        FROM tube.tube_delivery
        WHERE section_1_id = :section_1_id
          AND pipe_model_id = ANY(:pipe_model_ids)
          AND status <> 'cancelled'
          AND arrived_confirm_at IS NOT NULL
        GROUP BY pipe_model_id
        """
    )
    
    # 2. 批量查询除去今日所填之外的历史累计使用量与损耗量之和
    sql_usage_before_batch = text(
        """
        SELECT pipe_model_id, SUM(usage_qty) AS total_use, SUM(loss_qty) AS total_loss
        FROM tube.tube_daily_usage
        WHERE section_1_id = :section_1_id
          AND pipe_model_id = ANY(:pipe_model_ids)
          AND usage_date <> :usage_date
        GROUP BY pipe_model_id
        """
    )
    
    # 3. 批量查询在途待到货量
    sql_pending_batch = text(
        """
        SELECT pipe_model_id, SUM(shipped_qty) AS total
        FROM tube.tube_delivery
        WHERE section_1_id = :section_1_id
          AND pipe_model_id = ANY(:pipe_model_ids)
          AND status = 'pending_arrival'
        GROUP BY pipe_model_id
        """
    )

    session = SessionLocal()
    try:
        # 执行批量拉取并转为字典
        arrived_rows = session.execute(
            sql_arrived_batch, 
            {"section_1_id": section_1_id, "pipe_model_ids": normalized_pipe_model_ids}
        ).all()
        arrived_map = {row.pipe_model_id: float(row.total or 0.0) for row in arrived_rows}
        
        usage_rows = session.execute(
            sql_usage_before_batch, 
            {"section_1_id": section_1_id, "pipe_model_ids": normalized_pipe_model_ids, "usage_date": usage_date}
        ).all()
        usage_before_map = {
            row.pipe_model_id: (float(row.total_use or 0.0), float(row.total_loss or 0.0)) 
            for row in usage_rows
        }
        
        pending_rows = session.execute(
            sql_pending_batch, 
            {"section_1_id": section_1_id, "pipe_model_ids": normalized_pipe_model_ids}
        ).all()
        pending_map = {row.pipe_model_id: float(row.total or 0.0) for row in pending_rows}

        payloads = []
        for item in records:
            usage_qty = float(item["usage_qty"])
            if usage_qty < 0:
                raise HTTPException(status_code=422, detail="实际使用量不能为负数")
            
            loss_qty = float(item.get("loss_qty") or 0.0)
            if loss_qty < 0:
                raise HTTPException(status_code=422, detail="实际损耗量不能为负数")
            
            pipe_model_id = _normalize_pipe_model_id(item["pipe_model_id"])
            orig_pipe_model_id = pipe_model_orig_map.get(pipe_model_id, pipe_model_id)

            total_arrived = arrived_map.get(pipe_model_id, 0.0)
            total_use_before, total_loss_before = usage_before_map.get(pipe_model_id, (0.0, 0.0))
            pending_arrival = pending_map.get(pipe_model_id, 0.0)

            expected_total_usage = total_use_before + usage_qty
            expected_total_loss = total_loss_before + loss_qty
            expected_total_consumption = expected_total_usage + expected_total_loss

            if expected_total_consumption > total_arrived:
                shortage = expected_total_consumption - total_arrived
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"⚠️ 提交失败：现场可用账面库存不足！保温管规格【{orig_pipe_model_id}】累计到货与接收可用仅为 {total_arrived:.1f} 米，"
                        f"但若保存本次填报，累计消耗将达到 {expected_total_consumption:.1f} 米（其中实际使用 {expected_total_usage:.1f} 米，"
                        f"实际损耗 {expected_total_loss:.1f} 米，账面超前亏空 {shortage:.1f} 米）。\n"
                        f"🚚 运输信息提示：当前正有 {pending_arrival:.1f} 米在途物资（已发货待到货确认）。"
                        f"请先对已到现场的物资执行【到货确认】以补充账面库存，再返回提交实际填报数据！"
                    )
                )

            payloads.append(
                {
                    "usage_date": usage_date,
                    "section_1_id": section_1_id,
                    "pipe_model_id": pipe_model_id,
                    "usage_qty": usage_qty,
                    "loss_qty": loss_qty,
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


def list_pending_arrivals(section_1_id: str) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT
            id,
            supply_entity_id,
            section_1_id,
            pipe_model_id,
            shipped_qty,
            shipped_at,
            ship_contact_name,
            ship_contact_phone,
            ship_remark,
            status,
            abnormal_flag
        FROM tube.tube_delivery
        WHERE section_1_id = :section_1_id
          AND status = 'pending_arrival'
        ORDER BY shipped_at DESC, id DESC
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, {"section_1_id": section_1_id}).mappings().all()
        return [
            {
                "id": int(row["id"]),
                "supply_entity_id": _normalize_text(row["supply_entity_id"]),
                "section_1_id": _normalize_text(row["section_1_id"]),
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


def list_pipe_usage_history(
    section_1_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """查询指定标段的直管实际使用与损耗历史流水记录"""
    payload = load_tube_config()
    pipe_model_map = _build_pipe_model_map(payload)
    section_1_name_map = _build_section_1_name_map(payload)

    conditions = ["u.section_1_id = :section_1_id"]
    params: Dict[str, Any] = {"section_1_id": section_1_id}

    if start_date:
        conditions.append("u.usage_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("u.usage_date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)
    sql = text(
        f"""
        SELECT
            u.id,
            u.usage_date,
            u.section_1_id,
            u.pipe_model_id,
            u.usage_qty,
            u.loss_qty,
            u.filled_by,
            u.filled_at,
            u.remark,
            u.updated_by,
            u.updated_at
        FROM tube.tube_daily_usage u
        WHERE {where_clause}
        ORDER BY u.usage_date DESC, u.pipe_model_id ASC, u.id DESC
        """
    )
    session = SessionLocal()
    try:
        rows = session.execute(sql, params).mappings().all()
        results = []
        for r in rows:
            pm_id = _normalize_pipe_model_id(r["pipe_model_id"])
            pm_info = pipe_model_map.get(pm_id) or {}
            pm_name = pm_info.get("pipe_model_name") or pm_id
            unit = pm_info.get("unit") or "米"

            usage_qty = float(r["usage_qty"] or 0)
            loss_qty = float(r["loss_qty"] or 0)
            total_qty = round(usage_qty + loss_qty, 2)

            item = {
                "id": r["id"],
                "usage_date": r["usage_date"].isoformat() if hasattr(r["usage_date"], "isoformat") else str(r["usage_date"]),
                "section_1_id": r["section_1_id"],
                "section_1_name": section_1_name_map.get(r["section_1_id"], r["section_1_id"]),
                "pipe_model_id": pm_id,
                "pipe_model_name": pm_name,
                "unit": unit,
                "usage_qty": usage_qty,
                "loss_qty": loss_qty,
                "total_qty": total_qty,
                "filled_by": r["filled_by"] or "施工现场",
                "filled_at": r["filled_at"].isoformat() if r["filled_at"] else "",
                "remark": r["remark"] or "",
                "updated_by": r["updated_by"] or "",
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else "",
            }
            if keyword:
                kw = str(keyword).lower().strip()
                match_text = f"{item['pipe_model_name']} {item['pipe_model_id']} {item['remark']} {item['filled_by']}".lower()
                if kw not in match_text:
                    continue
            results.append(item)
        return results
    finally:
        session.close()

