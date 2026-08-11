"""管件发货、查询与确认的严格事务服务。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    get_config_list,
    load_tube_config,
)


BEIJING_TZ = __import__("zoneinfo").ZoneInfo("Asia/Shanghai")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _serialize_time(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=BEIJING_TZ)
        return value.astimezone(BEIJING_TZ).isoformat()
    return str(value)


def _positive_integer(value: Any, field_name: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name}必须是正整数") from exc
    if number <= 0 or not number.is_integer():
        raise HTTPException(status_code=422, detail=f"{field_name}必须是正整数")
    return int(number)


def normalize_delivery_ids(payload: Dict[str, Any]) -> List[int]:
    raw_ids = list(payload.get("ids") or [])
    if not raw_ids and payload.get("id") is not None:
        raw_ids = [payload.get("id")]
    result: List[int] = []
    seen: Set[int] = set()
    for raw_id in raw_ids:
        try:
            delivery_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"管件记录 ID 无效：{raw_id}") from exc
        if delivery_id <= 0:
            raise HTTPException(status_code=422, detail=f"管件记录 ID 无效：{raw_id}")
        if delivery_id not in seen:
            seen.add(delivery_id)
            result.append(delivery_id)
    if not result:
        raise HTTPException(status_code=422, detail="至少需要一条管件记录 ID")
    return result


def _write_audit_log(
    session,
    *,
    operator: str,
    operator_group: str,
    action_type: str,
    action_desc: str,
    resource_id: str,
    before_value: Optional[Dict[str, Any]] = None,
    after_value: Optional[Dict[str, Any]] = None,
) -> None:
    """审计写入失败时回滚业务，避免出现有状态、无凭证。"""
    session.execute(
        text(
            """
            INSERT INTO logs.tube_operation_logs (
                operator, operator_group, action_type, action_desc,
                resource_id, before_value, after_value
            ) VALUES (
                :operator, :operator_group, :action_type, :action_desc,
                :resource_id, CAST(:before_value AS JSONB), CAST(:after_value AS JSONB)
            )
            """
        ),
        {
            "operator": operator,
            "operator_group": operator_group,
            "action_type": action_type,
            "action_desc": action_desc,
            "resource_id": resource_id,
            "before_value": json.dumps(before_value or {}, ensure_ascii=False, default=str),
            "after_value": json.dumps(after_value or {}, ensure_ascii=False, default=str),
        },
    )


def _expand_aliases(values: Sequence[str], config_key: str, id_key: str) -> Set[str]:
    normalized = {_clean(value).lower() for value in values if _clean(value)}
    if not normalized:
        return set()
    config = load_tube_config()
    expanded = set(normalized)
    for item in get_config_list(config, config_key):
        item_id = _clean(item.get(id_key)).lower()
        item_code = _clean(item.get("code")).lower()
        if item_id in normalized or item_code in normalized:
            if item_id:
                expanded.add(item_id)
            if item_code:
                expanded.add(item_code)
    return expanded


def _resolve_filter(
    requested_csv: str,
    allowed_values: Optional[Sequence[str]],
    *,
    config_key: str,
    id_key: str,
) -> Optional[Set[str]]:
    requested = _expand_aliases(
        [part for part in str(requested_csv or "").split(",") if part.strip()],
        config_key,
        id_key,
    )
    if allowed_values is None:
        return requested or None
    allowed = _expand_aliases(list(allowed_values), config_key, id_key)
    if not allowed:
        return set()
    return requested.intersection(allowed) if requested else allowed


def _rows_for_update(session, delivery_ids: Sequence[int]) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT id, shipment_key, shipment_no, order_no, supply_entity_id,
                   section_1_id, shipped_qty, arrived_qty, status,
                   arrived_at, construction_confirmed_at, warehouse_confirmed_at
            FROM tube.tube_fitting_delivery
            WHERE id = ANY(:ids)
            ORDER BY id
            FOR UPDATE
            """
        ),
        {"ids": list(delivery_ids)},
    ).mappings().all()
    by_id = {int(row["id"]): dict(row) for row in rows}
    missing = [delivery_id for delivery_id in delivery_ids if delivery_id not in by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"管件记录不存在：{missing}")
    return [by_id[delivery_id] for delivery_id in delivery_ids]


def get_fitting_deliveries_by_ids(delivery_ids: Sequence[int]) -> List[Dict[str, Any]]:
    ids = sorted({int(value) for value in delivery_ids if int(value) > 0})
    if not ids:
        return []
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT id, shipment_key, shipment_no, supply_entity_id,
                       section_1_id, shipped_qty, arrived_qty, status
                FROM tube.tube_fitting_delivery
                WHERE id = ANY(:ids)
                ORDER BY id
                """
            ),
            {"ids": ids},
        ).mappings().all()
        return [dict(row) for row in rows]
    finally:
        session.close()


def submit_fitting_delivery(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
) -> Dict[str, Any]:
    supply_entity_input = _clean(payload.get("supply_entity_id"))
    section_1_id = _clean(payload.get("section_1_id"))
    vehicle_plate_no = _clean(payload.get("vehicle_plate_no"))
    raw_items = list(payload.get("items") or [])
    if not supply_entity_input or not section_1_id or not vehicle_plate_no:
        raise HTTPException(status_code=422, detail="供给主体、接收标段和车牌号均不能为空")
    if not raw_items:
        raise HTTPException(status_code=422, detail="至少需要一条管件发货明细")

    shipped_at_value = payload.get("shipped_at")
    try:
        shipped_at = shipped_at_value if isinstance(shipped_at_value, datetime) else datetime.fromisoformat(str(shipped_at_value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="发货时间格式不正确") from exc
    if shipped_at.tzinfo is None:
        shipped_at = shipped_at.replace(tzinfo=BEIJING_TZ)
    shipped_at = shipped_at.astimezone(BEIJING_TZ)

    supply_entity_id = supply_entity_input
    entity_code = "SA"
    config = load_tube_config()
    for entity in get_config_list(config, "supply_entities"):
        entity_id = _clean(entity.get("entity_id"))
        configured_code = _clean(entity.get("code"))
        if supply_entity_input.lower() in {entity_id.lower(), configured_code.lower()}:
            supply_entity_id = entity_id or supply_entity_input
            source_code = configured_code or entity_id
            compact_code = "".join(char for char in source_code if char.isalnum())
            entity_code = (compact_code + "X")[:2].upper()
            break

    validated_items: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_items, 1):
        fitting_type = _clean(item.get("fitting_type"))
        model_spec = _clean(item.get("model_spec"))
        if not fitting_type or not model_spec:
            raise HTTPException(status_code=422, detail=f"第 {index} 行必须填写管件类型和型号规格")
        validated_items.append(
            {
                "fitting_type": fitting_type,
                "model_spec": model_spec,
                "shipped_qty": _positive_integer(item.get("shipped_qty"), f"第 {index} 行发货数量"),
                "unit": "个",
                "remark": _clean(item.get("remark")),
            }
        )

    session = SessionLocal()
    try:
        sequence_number = int(
            session.execute(
                text(
                    """
                    INSERT INTO tube.tube_fitting_shipment_counter (
                        supply_entity_id, shipped_date, last_value
                    ) VALUES (:supply_entity_id, :shipped_date, 1)
                    ON CONFLICT (supply_entity_id, shipped_date)
                    DO UPDATE SET last_value = tube.tube_fitting_shipment_counter.last_value + 1
                    RETURNING last_value
                    """
                ),
                {"supply_entity_id": supply_entity_id, "shipped_date": shipped_at.date()},
            ).scalar_one()
        )
        date_part = shipped_at.strftime("%y%m%d")
        shipment_no = f"FS{entity_code}-{date_part}-{sequence_number:03d}"
        shipment_key = str(uuid4())
        session.execute(
            text(
                """
                INSERT INTO tube.tube_fitting_shipment_registry (
                    shipment_key, shipment_no, is_legacy
                ) VALUES (:shipment_key, :shipment_no, FALSE)
                """
            ),
            {"shipment_key": shipment_key, "shipment_no": shipment_no},
        )

        insert_sql = text(
            """
            INSERT INTO tube.tube_fitting_delivery (
                shipment_key, identifiers_locked, supply_entity_id, shipment_no,
                order_no, vehicle_plate_no, section_1_id, fitting_type, model_spec,
                shipped_qty, unit, shipped_at, ship_contact_name, ship_contact_phone,
                ship_remark, status, created_by, updated_by
            ) VALUES (
                :shipment_key, TRUE, :supply_entity_id, :shipment_no,
                :order_no, :vehicle_plate_no, :section_1_id, :fitting_type, :model_spec,
                :shipped_qty, '个', :shipped_at, :ship_contact_name, :ship_contact_phone,
                :ship_remark, 'shipped', :created_by, :updated_by
            )
            RETURNING id
            """
        )
        created_ids: List[int] = []
        section_code = section_1_id[:1].upper() or "X"
        for index, item in enumerate(validated_items, 1):
            order_no = f"FO{entity_code}-{section_code}-{date_part}-{sequence_number:03d}-{index:02d}"
            row_id = session.execute(
                insert_sql,
                {
                    "shipment_key": shipment_key,
                    "supply_entity_id": supply_entity_id,
                    "shipment_no": shipment_no,
                    "order_no": order_no,
                    "vehicle_plate_no": vehicle_plate_no,
                    "section_1_id": section_1_id,
                    "fitting_type": item["fitting_type"],
                    "model_spec": item["model_spec"],
                    "shipped_qty": item["shipped_qty"],
                    "shipped_at": shipped_at,
                    "ship_contact_name": _clean(payload.get("ship_contact_name")),
                    "ship_contact_phone": _clean(payload.get("ship_contact_phone")),
                    "ship_remark": item["remark"] or _clean(payload.get("ship_remark")),
                    "created_by": operator,
                    "updated_by": operator,
                },
            ).scalar_one()
            created_ids.append(int(row_id))

        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="SUBMIT_FITTING_DELIVERY",
            action_desc=f"提交管件发货单【{shipment_no}】，共 {len(created_ids)} 项明细",
            resource_id=shipment_no,
            after_value={
                "shipment_key": shipment_key,
                "shipment_no": shipment_no,
                "created_ids": created_ids,
                "supply_entity_id": supply_entity_id,
                "section_1_id": section_1_id,
                "vehicle_plate_no": vehicle_plate_no,
                "shipped_at": shipped_at.isoformat(),
                "items": validated_items,
            },
        )
        session.commit()
        return {
            "ok": True,
            "shipment_key": shipment_key,
            "shipment_no": shipment_no,
            "count": len(created_ids),
            "created_ids": created_ids,
        }
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"保存管件发货记录失败: {exc}") from exc
    finally:
        session.close()


def list_fitting_deliveries(
    *,
    section_1_id: str = "",
    supply_entity_id: str = "",
    start_date: str = "",
    end_date: str = "",
    search_keyword: str = "",
    page: int = 1,
    page_size: int = 200,
    allowed_section_ids: Optional[Sequence[str]] = None,
    allowed_supply_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    normalized_page = max(int(page), 1)
    normalized_page_size = min(max(int(page_size), 1), 500)
    section_filter = _resolve_filter(
        section_1_id,
        allowed_section_ids,
        config_key="demand_entities",
        id_key="section_1_id",
    )
    supply_filter = _resolve_filter(
        supply_entity_id,
        allowed_supply_ids,
        config_key="supply_entities",
        id_key="entity_id",
    )
    if section_filter == set() or supply_filter == set():
        return {"items": [], "total": 0, "page": normalized_page, "page_size": normalized_page_size, "has_more": False}

    clean_start = _clean(start_date)
    clean_end = _clean(end_date)
    clean_keyword = _clean(search_keyword)
    start_timestamp = f"{clean_start} 00:00:00+08:00" if clean_start else "1970-01-01 00:00:00+08:00"
    end_timestamp = f"{clean_end} 23:59:59.999999+08:00" if clean_end else "2099-12-31 23:59:59.999999+08:00"
    params = {
        "has_section_filter": section_filter is not None,
        "section_ids": sorted(section_filter or {""}),
        "has_supply_filter": supply_filter is not None,
        "supply_ids": sorted(supply_filter or {""}),
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "keyword": clean_keyword,
        "keyword_like": f"%{clean_keyword}%",
        "limit": normalized_page_size,
        "offset": (normalized_page - 1) * normalized_page_size,
    }
    where_sql = """
        WHERE (:has_section_filter = FALSE OR LOWER(TRIM(section_1_id)) = ANY(:section_ids))
          AND (:has_supply_filter = FALSE OR LOWER(TRIM(supply_entity_id)) = ANY(:supply_ids))
          AND shipped_at >= CAST(:start_timestamp AS TIMESTAMPTZ)
          AND shipped_at <= CAST(:end_timestamp AS TIMESTAMPTZ)
          AND (
            :keyword = '' OR shipment_no ILIKE :keyword_like OR order_no ILIKE :keyword_like OR
            vehicle_plate_no ILIKE :keyword_like OR fitting_type ILIKE :keyword_like OR
            model_spec ILIKE :keyword_like OR ship_remark ILIKE :keyword_like
          )
    """
    session = SessionLocal()
    try:
        # 迁移脚本可能与应用发布存在短暂时间差。列表读取保持向后兼容，
        # 避免仅因新增展示字段尚未落库而让全部历史发货记录不可见。
        existing_columns = set(
            session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'tube'
                      AND table_name = 'tube_fitting_delivery'
                    """
                )
            ).scalars()
        )
        shipment_key_select = (
            "shipment_key"
            if "shipment_key" in existing_columns
            else "'legacy-' || MD5(CONCAT_WS('|', shipment_no, supply_entity_id, "
            "section_1_id, vehicle_plate_no, shipped_at::TEXT)) AS shipment_key"
        )
        cancelled_at_select = (
            "cancelled_at" if "cancelled_at" in existing_columns else "NULL::TIMESTAMPTZ AS cancelled_at"
        )
        cancelled_by_select = (
            "cancelled_by" if "cancelled_by" in existing_columns else "NULL::TEXT AS cancelled_by"
        )
        cancel_reason_select = (
            "cancel_reason" if "cancel_reason" in existing_columns else "NULL::TEXT AS cancel_reason"
        )
        total = int(session.execute(text(f"SELECT COUNT(*) FROM tube.tube_fitting_delivery {where_sql}"), params).scalar_one())
        rows = session.execute(
            text(
                f"""
                SELECT id, {shipment_key_select}, supply_entity_id, shipment_no, order_no,
                       vehicle_plate_no, section_1_id, fitting_type, model_spec,
                       shipped_qty, unit, shipped_at, ship_contact_name,
                       ship_contact_phone, ship_remark, status, created_at, created_by,
                       arrived_qty, arrived_at, arrived_by, arrival_remark,
                       construction_confirmed_at, construction_confirmed_by, construction_remark,
                       warehouse_confirmed_at, warehouse_confirmed_by, warehouse_remark,
                       {cancelled_at_select}, {cancelled_by_select}, {cancel_reason_select}
                FROM tube.tube_fitting_delivery
                {where_sql}
                ORDER BY shipped_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        items = []
        for row in rows:
            items.append(
                {
                    "id": int(row["id"]),
                    "shipment_key": _clean(row["shipment_key"]),
                    "supply_entity_id": _clean(row["supply_entity_id"]),
                    "shipment_no": _clean(row["shipment_no"]),
                    "order_no": _clean(row["order_no"]),
                    "vehicle_plate_no": _clean(row["vehicle_plate_no"]),
                    "section_1_id": _clean(row["section_1_id"]),
                    "fitting_type": _clean(row["fitting_type"]),
                    "model_spec": _clean(row["model_spec"]),
                    "shipped_qty": float(row["shipped_qty"]),
                    "unit": _clean(row["unit"]),
                    "shipped_at": _serialize_time(row["shipped_at"]),
                    "ship_contact_name": _clean(row["ship_contact_name"]),
                    "ship_contact_phone": _clean(row["ship_contact_phone"]),
                    "ship_remark": _clean(row["ship_remark"]),
                    "status": _clean(row["status"]),
                    "created_at": _serialize_time(row["created_at"]),
                    "created_by": _clean(row["created_by"]),
                    "operator": _clean(row["created_by"]),
                    "arrived_qty": float(row["arrived_qty"]) if row["arrived_qty"] is not None else None,
                    "arrived_at": _serialize_time(row["arrived_at"]),
                    "arrived_by": _clean(row["arrived_by"]),
                    "arrival_remark": _clean(row["arrival_remark"]),
                    "construction_confirmed_at": _serialize_time(row["construction_confirmed_at"]),
                    "construction_confirmed_by": _clean(row["construction_confirmed_by"]),
                    "construction_remark": _clean(row["construction_remark"]),
                    "warehouse_confirmed_at": _serialize_time(row["warehouse_confirmed_at"]),
                    "warehouse_confirmed_by": _clean(row["warehouse_confirmed_by"]),
                    "warehouse_remark": _clean(row["warehouse_remark"]),
                    "cancelled_at": _serialize_time(row["cancelled_at"]),
                    "cancelled_by": _clean(row["cancelled_by"]),
                    "cancel_reason": _clean(row["cancel_reason"]),
                }
            )
        return {
            "items": items,
            "total": total,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "has_more": normalized_page * normalized_page_size < total,
        }
    finally:
        session.close()


def confirm_fitting_delivery_arrival(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    quantity_map = dict(payload.get("arrived_qty_map") or {})
    remark = _clean(payload.get("remark"))
    now = datetime.now(BEIJING_TZ)
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        quantities: Dict[str, int] = {}
        for row in rows:
            if _clean(row["status"]) != "shipped":
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 当前状态为 {row['status']}，仅待到货记录允许确认")
            shipped_qty = _positive_integer(row["shipped_qty"], f"记录 {row['id']} 发货数量")
            raw_quantity = quantity_map[str(row["id"])] if str(row["id"]) in quantity_map else quantity_map.get(row["id"], shipped_qty)
            arrived_qty = _positive_integer(raw_quantity, f"记录 {row['id']} 到货数量")
            if arrived_qty > shipped_qty:
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 到货数量不能大于发货数量 {shipped_qty}")
            quantities[str(row["id"])] = arrived_qty

        for row in rows:
            result = session.execute(
                text(
                    """
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'arrived', arrived_qty = :arrived_qty,
                        arrived_at = :confirmed_at, arrived_by = :operator,
                        arrival_remark = :remark, updated_by = :operator, updated_at = NOW()
                    WHERE id = :id AND status = 'shipped'
                    """
                ),
                {"id": row["id"], "arrived_qty": quantities[str(row["id"])], "confirmed_at": now, "operator": operator, "remark": remark},
            )
            if result.rowcount != 1:
                raise HTTPException(status_code=409, detail=f"记录 {row['id']} 状态已变化，请刷新后重试")

        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="CONFIRM_FITTING_ARRIVAL",
            action_desc=f"确认 {len(rows)} 项管件到货",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "arrived_qty_map": quantities, "remark": remark, "arrived_at": now.isoformat()},
        )
        session.commit()
        return {"ok": True, "updated_count": len(rows)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"确认管件到货失败: {exc}") from exc
    finally:
        session.close()


def _confirm_simple_transition(
    payload: Dict[str, Any],
    *,
    operator: str,
    operator_group: str,
    expected_status: str,
    new_status: str,
    timestamp_column: str,
    operator_column: str,
    remark_column: str,
    action_type: str,
    action_desc: str,
) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    remark = _clean(payload.get("remark"))
    now = datetime.now(BEIJING_TZ)
    allowed_columns = {
        "construction_confirmed_at",
        "construction_confirmed_by",
        "construction_remark",
        "warehouse_confirmed_at",
        "warehouse_confirmed_by",
        "warehouse_remark",
    }
    if {timestamp_column, operator_column, remark_column} - allowed_columns:
        raise RuntimeError("管件确认字段配置无效")
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        for row in rows:
            if _clean(row["status"]) != expected_status:
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 当前状态为 {row['status']}，不能执行本次确认")
        update_sql = text(
            f"""
            UPDATE tube.tube_fitting_delivery
            SET status = :new_status, {timestamp_column} = :confirmed_at,
                {operator_column} = :operator, {remark_column} = :remark,
                updated_by = :operator, updated_at = NOW()
            WHERE id = :id AND status = :expected_status
            """
        )
        for row in rows:
            result = session.execute(
                update_sql,
                {"id": row["id"], "new_status": new_status, "expected_status": expected_status, "confirmed_at": now, "operator": operator, "remark": remark},
            )
            if result.rowcount != 1:
                raise HTTPException(status_code=409, detail=f"记录 {row['id']} 状态已变化，请刷新后重试")
        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type=action_type,
            action_desc=f"{action_desc}：共 {len(rows)} 项",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "status": new_status, "remark": remark, "confirmed_at": now.isoformat()},
        )
        session.commit()
        return {"ok": True, "updated_count": len(rows)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"{action_desc}失败: {exc}") from exc
    finally:
        session.close()


def confirm_fitting_delivery_construction(payload: Dict[str, Any], operator: str, operator_group: str) -> Dict[str, Any]:
    return _confirm_simple_transition(
        payload,
        operator=operator,
        operator_group=operator_group,
        expected_status="arrived",
        new_status="construction_confirmed",
        timestamp_column="construction_confirmed_at",
        operator_column="construction_confirmed_by",
        remark_column="construction_remark",
        action_type="CONFIRM_FITTING_CONSTRUCTION",
        action_desc="施工单位确认接收管件",
    )


def confirm_fitting_delivery_warehouse(payload: Dict[str, Any], operator: str, operator_group: str) -> Dict[str, Any]:
    return _confirm_simple_transition(
        payload,
        operator=operator,
        operator_group=operator_group,
        expected_status="construction_confirmed",
        new_status="warehouse_confirmed",
        timestamp_column="warehouse_confirmed_at",
        operator_column="warehouse_confirmed_by",
        remark_column="warehouse_remark",
        action_type="CONFIRM_FITTING_WAREHOUSE",
        action_desc="库管确认管件入库",
    )


def cancel_fitting_delivery(payload: Dict[str, Any], operator: str, operator_group: str) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    reason = _clean(payload.get("remark"))
    if len(reason) < 2:
        raise HTTPException(status_code=422, detail="撤销管件发货必须填写原因")
    now = datetime.now(BEIJING_TZ)
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        for row in rows:
            if _clean(row["status"]) != "shipped":
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 已进入确认流程，仅待到货记录允许撤销")
        for row in rows:
            result = session.execute(
                text(
                    """
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'cancelled', cancelled_at = :cancelled_at,
                        cancelled_by = :operator, cancel_reason = :reason,
                        updated_by = :operator, updated_at = NOW()
                    WHERE id = :id AND status = 'shipped'
                    """
                ),
                {"id": row["id"], "cancelled_at": now, "operator": operator, "reason": reason},
            )
            if result.rowcount != 1:
                raise HTTPException(status_code=409, detail=f"记录 {row['id']} 状态已变化，请刷新后重试")
        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="CANCEL_FITTING_DELIVERY",
            action_desc=f"撤销 {len(rows)} 项管件发货记录",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "status": "cancelled", "cancel_reason": reason, "cancelled_at": now.isoformat()},
        )
        session.commit()
        return {"ok": True, "updated_count": len(rows)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"撤销管件发货失败: {exc}") from exc
    finally:
        session.close()
