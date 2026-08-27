"""管件发货、查询与确认的严格事务服务。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
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


_structures_checked = False


def _ensure_fitting_table_structures() -> None:
    """自愈检查并保证 tube_fitting_delivery 表的主键、序列与核心索引存在。"""
    global _structures_checked
    if _structures_checked:
        return
    ddls = [
        "CREATE SEQUENCE IF NOT EXISTS tube.tube_fitting_delivery_id_seq",
        "ALTER TABLE tube.tube_fitting_delivery ALTER COLUMN id SET DEFAULT nextval('tube.tube_fitting_delivery_id_seq')",
        "ALTER SEQUENCE tube.tube_fitting_delivery_id_seq OWNED BY tube.tube_fitting_delivery.id",
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'tube.tube_fitting_delivery'::regclass AND contype = 'p') THEN ALTER TABLE tube.tube_fitting_delivery ADD PRIMARY KEY (id); END IF; END $$;",
        "ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS is_timeout_receive BOOLEAN DEFAULT FALSE",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_delivery_order_no ON tube.tube_fitting_delivery (order_no)",
        "CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipment_no ON tube.tube_fitting_delivery (shipment_no)",
        "CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_section_1_status ON tube.tube_fitting_delivery (section_1_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipped_at ON tube.tube_fitting_delivery (shipped_at)",
        "SELECT setval('tube.tube_fitting_delivery_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_fitting_delivery), 0) + 1, false)",
        "CREATE SEQUENCE IF NOT EXISTS logs.tube_operation_logs_id_seq",
        "ALTER TABLE logs.tube_operation_logs ALTER COLUMN id SET DEFAULT nextval('logs.tube_operation_logs_id_seq')",
        "SELECT setval('logs.tube_operation_logs_id_seq', COALESCE((SELECT MAX(id) FROM logs.tube_operation_logs), 0) + 1, false)",
    ]
    session = SessionLocal()
    try:
        for stmt in ddls:
            try:
                session.execute(text(stmt))
                session.commit()
            except Exception:
                session.rollback()
        _structures_checked = True
    finally:
        session.close()


def auto_process_timeout_fitting_deliveries(session=None) -> None:
    """管件超出指定小时数未施工接收，系统强制确认为到货量并推进到待入库。设定为 -1 则关闭。"""
    is_local_session = False
    if session is None:
        session = SessionLocal()
        is_local_session = True
    try:
        config = load_tube_config()
        raw_timeout = config.get("auto_receive_timeout_hours", 12)
        try:
            timeout_hours = float(raw_timeout)
        except (TypeError, ValueError):
            timeout_hours = 12.0

        if timeout_hours < 0:
            return

        timeout_hours_str = f"{timeout_hours:g}"
        remark_text = f"🕒 [系统超时确认] 超出{timeout_hours_str}小时未接收，系统强制确认为到货量。"

        sql = text(
            """
            UPDATE tube.tube_fitting_delivery
            SET
                status = 'pending_warehouse',
                arrived_qty = COALESCE(arrived_qty, shipped_qty),
                received_confirm_by = 'SYSTEM_TIMEOUT',
                received_confirm_at = COALESCE(arrived_confirm_at, NOW()) + (:hours || ' hours')::INTERVAL,
                received_remark = :remark,
                is_timeout_receive = TRUE,
                updated_by = 'SYSTEM_TIMEOUT',
                updated_at = NOW()
            WHERE status = 'pending_receive'
              AND arrived_confirm_at IS NOT NULL
              AND arrived_confirm_at < NOW() - (:hours || ' hours')::INTERVAL
            """
        )
        session.execute(sql, {"hours": timeout_hours_str, "remark": remark_text})
        if is_local_session:
            session.commit()
    except Exception:
        if is_local_session:
            session.rollback()
        raise
    finally:
        if is_local_session:
            session.close()


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
    raw_ids = list(payload.get("ids") or payload.get("delivery_ids") or [])
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
    client_ip: Optional[str] = None,
) -> None:
    """审计写入失败时回滚业务，避免出现有状态、无凭证。"""
    session.execute(
        text(
            """
            INSERT INTO logs.tube_operation_logs (
                operator, operator_group, action_type, action_desc,
                resource_id, before_value, after_value, client_ip
            ) VALUES (
                :operator, :operator_group, :action_type, :action_desc,
                :resource_id, CAST(:before_value AS JSONB), CAST(:after_value AS JSONB), :client_ip
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
            "client_ip": client_ip,
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
            SELECT id, shipment_no, order_no, supply_entity_id,
                   section_1_id, shipped_qty, arrived_qty, status,
                   arrived_confirm_at, received_confirm_at, warehouse_confirm_at
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
                SELECT id, shipment_no, supply_entity_id,
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


def check_recent_fitting_shipment(
    *,
    vehicle_plate_no: str,
    section_1_id: str,
    supply_entity_id: str,
    time_window_minutes: int = 60,
) -> Dict[str, Any]:
    """预检指定车牌在过去指定分钟数（默认1小时/60分钟）内是否存在相同供给主体、相同标段且处于在途待到货状态的车次。"""
    plate = _clean(vehicle_plate_no)
    sec_id = _clean(section_1_id)
    entity_id = _clean(supply_entity_id).upper()
    if not plate or not sec_id or not entity_id:
        return {"has_recent": False}

    _ensure_fitting_table_structures()
    session = SessionLocal()
    try:
        rows = session.execute(
            text(
                """
                SELECT id, shipment_no, order_no, vehicle_plate_no, section_1_id,
                       supply_entity_id, fitting_type, model_spec, shipped_qty, unit,
                       shipped_at, created_at, status, ship_remark
                FROM tube.tube_fitting_delivery
                WHERE UPPER(vehicle_plate_no) = UPPER(:plate)
                  AND UPPER(supply_entity_id) = UPPER(:entity_id)
                  AND section_1_id = :sec_id
                  AND status IN ('pending_arrival', 'shipped')
                  AND (created_at >= NOW() - (:minutes || ' minutes')::INTERVAL OR shipped_at >= NOW() - (:minutes || ' minutes')::INTERVAL)
                ORDER BY created_at DESC, id DESC
                """
            ),
            {"plate": plate, "entity_id": entity_id, "sec_id": sec_id, "minutes": str(time_window_minutes)},
        ).mappings().all()

        if not rows:
            return {"has_recent": False}

        recent_shipment_no = _clean(rows[0]["shipment_no"])
        shipment_rows = [r for r in rows if _clean(r["shipment_no"]) == recent_shipment_no]
        if not shipment_rows:
            return {"has_recent": False}

        first_row = shipment_rows[0]
        created_at_dt = first_row["created_at"]
        shipped_at_dt = first_row["shipped_at"]

        now_utc = datetime.now(BEIJING_TZ)
        dt_ref = created_at_dt or shipped_at_dt
        if dt_ref:
            if dt_ref.tzinfo is None:
                dt_ref = dt_ref.replace(tzinfo=BEIJING_TZ)
            minutes_ago = max(0, int((now_utc - dt_ref.astimezone(BEIJING_TZ)).total_seconds() / 60))
        else:
            minutes_ago = 0

        items_summary = [
            f"{r['fitting_type']} ({r['model_spec']}) × {int(r['shipped_qty']) if float(r['shipped_qty']).is_integer() else r['shipped_qty']}{r['unit'] or '个'}"
            for r in shipment_rows
        ]

        return {
            "has_recent": True,
            "shipment_no": recent_shipment_no,
            "minutes_ago": minutes_ago,
            "vehicle_plate_no": first_row["vehicle_plate_no"],
            "section_1_id": first_row["section_1_id"],
            "supply_entity_id": first_row["supply_entity_id"],
            "shipped_at": _serialize_time(shipped_at_dt),
            "created_at": _serialize_time(created_at_dt),
            "items_count": len(shipment_rows),
            "total_qty": sum(float(r["shipped_qty"]) for r in shipment_rows),
            "items_summary": items_summary,
        }
    finally:
        session.close()


def submit_fitting_delivery(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    supply_entity_input = _clean(payload.get("supply_entity_id"))
    section_1_id = _clean(payload.get("section_1_id"))
    vehicle_plate_no = _clean(payload.get("vehicle_plate_no"))
    raw_items = list(payload.get("items") or [])
    if not supply_entity_input or not section_1_id or not vehicle_plate_no:
        raise HTTPException(status_code=422, detail="供给主体、接收标段和车牌号均不能为空")
    if not raw_items:
        raise HTTPException(status_code=422, detail="至少需要一条管件发货明细")

    norm_group = str(operator_group or "").strip().lower()
    is_admin = norm_group in {"global_admin", "dev_admin"}
    shipped_at_value = payload.get("shipped_at")
    if is_admin and shipped_at_value:
        try:
            shipped_at = shipped_at_value if isinstance(shipped_at_value, datetime) else datetime.fromisoformat(str(shipped_at_value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="发货时间格式不正确") from exc
        if shipped_at.tzinfo is None:
            shipped_at = shipped_at.replace(tzinfo=BEIJING_TZ)
        shipped_at = shipped_at.astimezone(BEIJING_TZ)
    else:
        # 非 Global_admin 用户或未指定时间时，强制记录为当前实际的东八区时间
        shipped_at = datetime.now(BEIJING_TZ)

    supply_entity_id = supply_entity_input.upper()
    entity_code = "SA"
    config = load_tube_config()
    for entity in get_config_list(config, "supply_entities"):
        entity_id = _clean(entity.get("entity_id"))
        configured_code = _clean(entity.get("code"))
        if supply_entity_input.lower() in {entity_id.lower(), configured_code.lower()}:
            supply_entity_id = (entity_id or supply_entity_input).upper()
            source_code = configured_code or entity_id
            compact_code = "".join(char for char in source_code if char.isalnum())
            entity_code = (compact_code + "X")[:2].upper()
            break

    fitting_cfg = (config or {}).get("fitting_config") or {}
    allowed_units = set(fitting_cfg.get("allowed_units") or ["个", "套"])

    validated_items: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_items, 1):
        fitting_type = _clean(item.get("fitting_type"))
        model_spec = _clean(item.get("model_spec"))
        if not fitting_type or not model_spec:
            raise HTTPException(status_code=422, detail=f"第 {index} 行必须填写管件类型和型号规格")
        unit = _clean(item.get("unit")) or "个"
        if unit not in allowed_units:
            allowed_str = " / ".join(sorted(list(allowed_units)))
            raise HTTPException(status_code=422, detail=f"第 {index} 行【单位】必须为'{allowed_str}'")
        validated_items.append(
            {
                "fitting_type": fitting_type,
                "model_spec": model_spec,
                "shipped_qty": _positive_integer(item.get("shipped_qty"), f"第 {index} 行发货数量"),
                "unit": unit,
                "remark": _clean(item.get("remark")),
            }
        )

    _ensure_fitting_table_structures()
    session = SessionLocal()
    try:
        date_part = shipped_at.strftime("%y%m%d")
        shipment_prefix = f"FS{entity_code}-{date_part}-"

        insert_sql = text(
            """
            INSERT INTO tube.tube_fitting_delivery (
                supply_entity_id, shipment_no, order_no, vehicle_plate_no,
                section_1_id, fitting_type, model_spec, shipped_qty, unit,
                shipped_at, ship_contact_name, ship_contact_phone, ship_remark,
                status, created_by, updated_by
            ) VALUES (
                :supply_entity_id, :shipment_no, :order_no, :vehicle_plate_no,
                :section_1_id, :fitting_type, :model_spec, :shipped_qty, :unit,
                :shipped_at, :ship_contact_name, :ship_contact_phone, :ship_remark,
                'pending_arrival', :created_by, :updated_by
            )
            RETURNING id
            """
        )

        merge_to_shipment_no = _clean(payload.get("merge_to_shipment_no"))
        if merge_to_shipment_no:
            # 模式 A：合并追加至既有在途车次
            existing_rows = session.execute(
                text(
                    """
                    SELECT id, shipment_no, order_no, vehicle_plate_no, section_1_id,
                           supply_entity_id, status, shipped_at, ship_contact_name, ship_contact_phone
                    FROM tube.tube_fitting_delivery
                    WHERE shipment_no = :shipment_no
                    ORDER BY id ASC
                    FOR UPDATE
                    """
                ),
                {"shipment_no": merge_to_shipment_no},
            ).mappings().all()

            if not existing_rows:
                raise HTTPException(status_code=404, detail=f"指定合并的车次【{merge_to_shipment_no}】不存在")

            first_existing = existing_rows[0]
            for r in existing_rows:
                if _clean(r["status"]) not in ("pending_arrival", "shipped"):
                    raise HTTPException(
                        status_code=422,
                        detail=f"车次【{merge_to_shipment_no}】当前状态为【{r['status']}】，现场已处理或已签收，不能再合并追加，请作为独立车次发货",
                    )

            if _clean(first_existing["section_1_id"]) != section_1_id:
                raise HTTPException(status_code=422, detail="合并车次的接收标段不一致，无法合并")
            if _clean(first_existing["supply_entity_id"]).upper() != supply_entity_id.upper():
                raise HTTPException(status_code=422, detail="合并车次的供给主体不一致，无法合并")

            max_sub_seq = 0
            base_order_prefix = None
            for r in existing_rows:
                ord_no = _clean(r["order_no"])
                if ord_no and "-" in ord_no:
                    parts = ord_no.split("-")
                    base_order_prefix = "-".join(parts[:-1])
                    try:
                        seq_val = int(parts[-1])
                        if seq_val > max_sub_seq:
                            max_sub_seq = seq_val
                    except ValueError:
                        pass

            if not base_order_prefix:
                section_code = section_1_id[:1].upper() or "X"
                base_order_prefix = f"FO{entity_code}-{section_code}-{date_part}-001"

            target_shipped_at = first_existing["shipped_at"] or shipped_at
            ship_contact_name = _clean(payload.get("ship_contact_name")) or _clean(first_existing["ship_contact_name"])
            ship_contact_phone = _clean(payload.get("ship_contact_phone")) or _clean(first_existing["ship_contact_phone"])

            created_ids: List[int] = []
            for offset, item in enumerate(validated_items, 1):
                cur_sub_seq = max_sub_seq + offset
                order_no = f"{base_order_prefix}-{cur_sub_seq:02d}"
                row_id = session.execute(
                    insert_sql,
                    {
                        "supply_entity_id": supply_entity_id,
                        "shipment_no": merge_to_shipment_no,
                        "order_no": order_no,
                        "vehicle_plate_no": vehicle_plate_no,
                        "section_1_id": section_1_id,
                        "fitting_type": item["fitting_type"],
                        "model_spec": item["model_spec"],
                        "shipped_qty": item["shipped_qty"],
                        "unit": item["unit"],
                        "shipped_at": target_shipped_at,
                        "ship_contact_name": ship_contact_name,
                        "ship_contact_phone": ship_contact_phone,
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
                action_type="MERGE_APPEND_FITTING_DELIVERY",
                action_desc=f"向既有车次【{merge_to_shipment_no}】合并追加 {len(created_ids)} 项管件明细",
                resource_id=merge_to_shipment_no,
                after_value={
                    "shipment_no": merge_to_shipment_no,
                    "created_ids": created_ids,
                    "items": validated_items,
                },
                client_ip=client_ip,
            )
            session.commit()
            return {
                "ok": True,
                "merged": True,
                "shipment_no": merge_to_shipment_no,
                "count": len(created_ids),
                "created_ids": created_ids,
            }

        # 模式 B：生成全新独立车次
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # 基于物理主表 tube_fitting_delivery 计算递增车次号（带正则类型校验防崩溃）
                db_max_seq = session.execute(
                    text(
                        """
                        SELECT COALESCE(MAX(CAST(RIGHT(shipment_no, 3) AS INTEGER)), 0)
                        FROM tube.tube_fitting_delivery
                        WHERE shipment_no LIKE :prefix
                          AND RIGHT(shipment_no, 3) ~ '^[0-9]{3}$'
                        """
                    ),
                    {"prefix": f"{shipment_prefix}%"},
                ).scalar() or 0

                sequence_number = int(db_max_seq) + 1 + attempt
                shipment_no = f"{shipment_prefix}{sequence_number:03d}"

                created_ids: List[int] = []
                section_code = section_1_id[:1].upper() or "X"
                for index, item in enumerate(validated_items, 1):
                    order_no = f"FO{entity_code}-{section_code}-{date_part}-{sequence_number:03d}-{index:02d}"
                    row_id = session.execute(
                        insert_sql,
                        {
                            "supply_entity_id": supply_entity_id,
                            "shipment_no": shipment_no,
                            "order_no": order_no,
                            "vehicle_plate_no": vehicle_plate_no,
                            "section_1_id": section_1_id,
                            "fitting_type": item["fitting_type"],
                            "model_spec": item["model_spec"],
                            "shipped_qty": item["shipped_qty"],
                            "unit": item["unit"],
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
                        "shipment_no": shipment_no,
                        "created_ids": created_ids,
                        "supply_entity_id": supply_entity_id,
                        "section_1_id": section_1_id,
                        "vehicle_plate_no": vehicle_plate_no,
                        "shipped_at": shipped_at.isoformat(),
                        "items": validated_items,
                    },
                    client_ip=client_ip,
                )
                session.commit()
                return {
                    "ok": True,
                    "merged": False,
                    "shipment_no": shipment_no,
                    "count": len(created_ids),
                    "created_ids": created_ids,
                }
            except Exception as insert_err:
                session.rollback()
                if attempt == max_attempts - 1:
                    raise HTTPException(status_code=500, detail=f"保存管件发货记录失败: {insert_err}") from insert_err
                err_str = str(insert_err).lower()
                if attempt < max_attempts - 1 and ("unique" in err_str or "duplicate" in err_str or "uq_" in err_str):
                    continue
                raise
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
    status: str = "",
    exclude_cancelled: bool = False,
    start_date: str = "",
    end_date: str = "",
    search_keyword: str = "",
    page: int = 1,
    page_size: int = 200,
    allowed_section_ids: Optional[Sequence[str]] = None,
    allowed_supply_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    _ensure_fitting_table_structures()
    auto_process_timeout_fitting_deliveries()
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
    clean_status = _clean(status)
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
        "status": clean_status,
        "limit": normalized_page_size,
        "offset": (normalized_page - 1) * normalized_page_size,
    }
    status_clause = ""
    if exclude_cancelled:
        status_clause = " AND status != 'cancelled'"
    elif clean_status:
        status_clause = " AND status = :status"
    where_sql = f"""
        WHERE (:has_section_filter = FALSE OR LOWER(TRIM(section_1_id)) = ANY(:section_ids))
          AND (:has_supply_filter = FALSE OR LOWER(TRIM(supply_entity_id)) = ANY(:supply_ids))
          AND shipped_at >= CAST(:start_timestamp AS TIMESTAMPTZ)
          AND shipped_at <= CAST(:end_timestamp AS TIMESTAMPTZ)
          {status_clause}
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
        cancelled_at_select = (
            "cancel_at" if "cancel_at" in existing_columns else ("cancelled_at" if "cancelled_at" in existing_columns else "NULL::TIMESTAMPTZ AS cancel_at")
        )
        cancelled_by_select = (
            "cancel_by" if "cancel_by" in existing_columns else ("cancelled_by" if "cancelled_by" in existing_columns else "NULL::TEXT AS cancel_by")
        )
        cancel_reason_select = (
            "cancel_reason" if "cancel_reason" in existing_columns else "NULL::TEXT AS cancel_reason"
        )
        timeout_receive_select = (
            "is_timeout_receive" if "is_timeout_receive" in existing_columns else "FALSE AS is_timeout_receive"
        )
        total = int(session.execute(text(f"SELECT COUNT(*) FROM tube.tube_fitting_delivery {where_sql}"), params).scalar_one())
        rows = session.execute(
            text(
                f"""
                SELECT id, supply_entity_id, shipment_no, order_no,
                       vehicle_plate_no, section_1_id, fitting_type, model_spec,
                       shipped_qty, unit, shipped_at, ship_contact_name,
                       ship_contact_phone, ship_remark, status, created_at, created_by,
                       arrived_qty, arrived_confirm_at, arrived_confirm_by, arrived_remark,
                       received_confirm_at, received_confirm_by, received_remark,
                       warehouse_confirm_at, warehouse_confirm_by, warehouse_remark,
                       {cancelled_at_select}, {cancelled_by_select}, {cancel_reason_select},
                       {timeout_receive_select}
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
                    "shipment_key": _clean(row["shipment_no"]),
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
                    "is_timeout_receive": bool(row.get("is_timeout_receive")),
                    "arrived_qty": float(row["arrived_qty"]) if row["arrived_qty"] is not None else None,
                    "arrived_at": _serialize_time(row.get("arrived_confirm_at") or row.get("arrived_at")),
                    "arrived_by": _clean(row.get("arrived_confirm_by") or row.get("arrived_by")),
                    "arrival_remark": _clean(row.get("arrived_remark") or row.get("arrival_remark")),
                    "construction_confirmed_at": _serialize_time(row.get("received_confirm_at") or row.get("construction_confirmed_at")),
                    "construction_confirmed_by": _clean(row.get("received_confirm_by") or row.get("construction_confirmed_by")),
                    "construction_remark": _clean(row.get("received_remark") or row.get("construction_remark")),
                    "warehouse_confirmed_at": _serialize_time(row.get("warehouse_confirm_at") or row.get("warehouse_confirmed_at")),
                    "warehouse_confirmed_by": _clean(row.get("warehouse_confirm_by") or row.get("warehouse_confirmed_by")),
                    "warehouse_remark": _clean(row.get("warehouse_remark")),
                    "cancelled_at": _serialize_time(row.get("cancel_at") or row.get("cancelled_at")),
                    "cancelled_by": _clean(row.get("cancel_by") or row.get("cancelled_by")),
                    "cancel_reason": _clean(row.get("cancel_reason")),
                    "arrived_confirm_at": _serialize_time(row.get("arrived_confirm_at")),
                    "arrived_confirm_by": _clean(row.get("arrived_confirm_by")),
                    "arrived_remark": _clean(row.get("arrived_remark")),
                    "received_confirm_at": _serialize_time(row.get("received_confirm_at")),
                    "received_confirm_by": _clean(row.get("received_confirm_by")),
                    "received_remark": _clean(row.get("received_remark")),
                    "warehouse_confirm_at": _serialize_time(row.get("warehouse_confirm_at")),
                    "warehouse_confirm_by": _clean(row.get("warehouse_confirm_by")),
                    "cancel_at": _serialize_time(row.get("cancel_at")),
                    "cancel_by": _clean(row.get("cancel_by")),
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
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    quantity_map = dict(payload.get("arrived_qty_map") or {})
    remark = _clean(payload.get("remark"))
    now = datetime.now(BEIJING_TZ)
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        valid_rows = []
        quantities: Dict[str, int] = {}
        for row in rows:
            st = _clean(row["status"])
            if st in ("pending_arrival", "shipped"):
                shipped_qty = _positive_integer(row["shipped_qty"], f"记录 {row['id']} 发货数量")
                raw_quantity = quantity_map[str(row["id"])] if str(row["id"]) in quantity_map else quantity_map.get(row["id"], shipped_qty)
                arrived_qty = _positive_integer(raw_quantity, f"记录 {row['id']} 到货数量")
                if arrived_qty > shipped_qty:
                    raise HTTPException(status_code=422, detail=f"记录 {row['id']} 到货数量不能大于发货数量 {shipped_qty}")
                quantities[str(row["id"])] = arrived_qty
                valid_rows.append(row)
            elif st in ("pending_receive", "pending_warehouse", "completed"):
                # 已成功到货过，允许幂等兼容
                pass
            else:
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 当前状态为 {st}，仅待到货记录允许确认")

        for row in valid_rows:
            result = session.execute(
                text(
                    """
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'pending_receive', arrived_qty = :arrived_qty,
                        arrived_confirm_at = :confirmed_at, arrived_confirm_by = :operator,
                        arrived_remark = :remark, updated_by = :operator, updated_at = NOW()
                    WHERE id = :id AND status IN ('pending_arrival', 'shipped')
                    """
                ),
                {"id": row["id"], "arrived_qty": quantities[str(row["id"])], "confirmed_at": now, "operator": operator, "remark": remark},
            )
            if result.rowcount < 1:
                raise HTTPException(status_code=409, detail=f"记录 {row['id']} 状态已变化，请刷新后重试")

        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="CONFIRM_FITTING_ARRIVAL",
            action_desc=f"现场确认管件到货：共 {len(valid_rows)} 项（涉及单号: {', '.join(shipment_numbers[:3])}）",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "arrived_qty_map": quantities, "remark": remark, "arrived_at": now.isoformat()},
            client_ip=client_ip,
        )
        session.commit()
        return {"ok": True, "updated_count": len(valid_rows)}
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
    expected_statuses: Sequence[str],
    new_status: str,
    timestamp_column: str,
    operator_column: str,
    remark_column: str,
    action_type: str,
    action_desc: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    remark = _clean(payload.get("remark"))
    now = datetime.now(BEIJING_TZ)
    allowed_columns = {
        "received_confirm_at",
        "received_confirm_by",
        "received_remark",
        "warehouse_confirm_at",
        "warehouse_confirm_by",
        "warehouse_remark",
        "construction_confirmed_at",
        "construction_confirmed_by",
        "construction_remark",
        "warehouse_confirmed_at",
        "warehouse_confirmed_by",
    }
    if {timestamp_column, operator_column, remark_column} - allowed_columns:
        raise RuntimeError("管件确认字段配置无效")
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        valid_rows = []
        for row in rows:
            st = _clean(row["status"])
            if st in expected_statuses:
                valid_rows.append(row)
            elif new_status == "pending_warehouse" and st in ("pending_arrival", "shipped"):
                # 整车施工接收时，若存在落后的待到货明细，纳入自愈队列
                valid_rows.append(row)
            elif new_status == "completed" and st in ("pending_arrival", "shipped", "pending_receive", "arrived"):
                # 整车库管归档时，若存在落后的在途/待接收明细，纳入自愈队列
                valid_rows.append(row)
            elif st == new_status or st in ("completed", "warehouse_confirmed"):
                # 幂等放行
                pass
            else:
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 当前状态为 {st}，不能执行本次确认")

        for row in valid_rows:
            st = _clean(row["status"])
            shipped_qty = _positive_integer(row["shipped_qty"], f"记录 {row['id']} 发货数量")
            
            if new_status == "pending_warehouse":
                # 推进到待库管入库：确保必须具有到货凭证
                cur_arrived_qty = row.get("arrived_qty") or shipped_qty
                cur_arrived_at = row.get("arrived_confirm_at") or now
                cur_arrived_by = _clean(row.get("arrived_confirm_by")) or operator
                
                session.execute(
                    text(
                        f"""
                        UPDATE tube.tube_fitting_delivery
                        SET status = 'pending_warehouse',
                            arrived_qty = COALESCE(arrived_qty, :arrived_qty),
                            arrived_confirm_at = COALESCE(arrived_confirm_at, :arrived_confirm_at),
                            arrived_confirm_by = COALESCE(arrived_confirm_by, :arrived_confirm_by),
                            {timestamp_column} = :confirmed_at,
                            {operator_column} = :operator,
                            {remark_column} = :remark,
                            updated_by = :operator,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row["id"],
                        "arrived_qty": cur_arrived_qty,
                        "arrived_confirm_at": cur_arrived_at,
                        "arrived_confirm_by": cur_arrived_by,
                        "confirmed_at": now,
                        "operator": operator,
                        "remark": remark,
                    },
                )
            elif new_status == "completed":
                # 推进到已结清归档：确保到货凭证和施工接收凭证全齐
                cur_arrived_qty = row.get("arrived_qty") or shipped_qty
                cur_arrived_at = row.get("arrived_confirm_at") or now
                cur_arrived_by = _clean(row.get("arrived_confirm_by")) or operator
                cur_received_at = row.get("received_confirm_at") or now
                cur_received_by = _clean(row.get("received_confirm_by")) or operator

                session.execute(
                    text(
                        f"""
                        UPDATE tube.tube_fitting_delivery
                        SET status = 'completed',
                            arrived_qty = COALESCE(arrived_qty, :arrived_qty),
                            arrived_confirm_at = COALESCE(arrived_confirm_at, :arrived_confirm_at),
                            arrived_confirm_by = COALESCE(arrived_confirm_by, :arrived_confirm_by),
                            received_confirm_at = COALESCE(received_confirm_at, :received_confirm_at),
                            received_confirm_by = COALESCE(received_confirm_by, :received_confirm_by),
                            {timestamp_column} = :confirmed_at,
                            {operator_column} = :operator,
                            {remark_column} = :remark,
                            updated_by = :operator,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row["id"],
                        "arrived_qty": cur_arrived_qty,
                        "arrived_confirm_at": cur_arrived_at,
                        "arrived_confirm_by": cur_arrived_by,
                        "received_confirm_at": cur_received_at,
                        "received_confirm_by": cur_received_by,
                        "confirmed_at": now,
                        "operator": operator,
                        "remark": remark,
                    },
                )
            else:
                session.execute(
                    text(
                        f"""
                        UPDATE tube.tube_fitting_delivery
                        SET status = :new_status,
                            {timestamp_column} = :confirmed_at,
                            {operator_column} = :operator,
                            {remark_column} = :remark,
                            updated_by = :operator,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row["id"],
                        "new_status": new_status,
                        "confirmed_at": now,
                        "operator": operator,
                        "remark": remark,
                    },
                )
        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type=action_type,
            action_desc=f"{action_desc}：共 {len(valid_rows)} 项",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "status": new_status, "remark": remark, "confirmed_at": now.isoformat()},
            client_ip=client_ip,
        )
        session.commit()
        return {"ok": True, "updated_count": len(valid_rows)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"{action_desc}失败: {exc}") from exc
    finally:
        session.close()


def confirm_fitting_delivery_construction(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    return _confirm_simple_transition(
        payload,
        operator=operator,
        operator_group=operator_group,
        expected_statuses=["pending_receive", "arrived"],
        new_status="pending_warehouse",
        timestamp_column="received_confirm_at",
        operator_column="received_confirm_by",
        remark_column="received_remark",
        action_type="CONFIRM_FITTING_CONSTRUCTION",
        action_desc="施工单位确认接收管件",
        client_ip=client_ip,
    )


def confirm_fitting_delivery_warehouse(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    return _confirm_simple_transition(
        payload,
        operator=operator,
        operator_group=operator_group,
        expected_statuses=["pending_warehouse", "construction_confirmed"],
        new_status="completed",
        timestamp_column="warehouse_confirm_at",
        operator_column="warehouse_confirm_by",
        remark_column="warehouse_remark",
        action_type="CONFIRM_FITTING_WAREHOUSE",
        action_desc="管件库管确认",
        client_ip=client_ip,
    )


def cancel_fitting_delivery(
    payload: Dict[str, Any],
    operator: str,
    operator_group: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    delivery_ids = normalize_delivery_ids(payload)
    reason = _clean(payload.get("remark"))
    if len(reason) < 2:
        raise HTTPException(status_code=422, detail="撤销管件发货必须填写原因")
    now = datetime.now(BEIJING_TZ)
    session = SessionLocal()
    try:
        rows = _rows_for_update(session, delivery_ids)
        valid_rows = []
        for row in rows:
            st = _clean(row["status"])
            if st in ("pending_arrival", "shipped"):
                valid_rows.append(row)
            elif st == "cancelled":
                # 已经撤销，幂等放行
                pass
            else:
                raise HTTPException(status_code=422, detail=f"记录 {row['id']} 已进入确认流程，仅待到货记录允许撤销")
        for row in valid_rows:
            result = session.execute(
                text(
                    """
                    UPDATE tube.tube_fitting_delivery
                    SET status = 'cancelled', cancel_at = :cancelled_at,
                        cancel_by = :operator, cancel_reason = :reason,
                        updated_by = :operator, updated_at = NOW()
                    WHERE id = :id AND status IN ('pending_arrival', 'shipped')
                    """
                ),
                {"id": row["id"], "cancelled_at": now, "operator": operator, "reason": reason},
            )
            if result.rowcount < 1:
                raise HTTPException(status_code=409, detail=f"记录 {row['id']} 状态已变化，请刷新后重试")
        shipment_numbers = sorted({_clean(row["shipment_no"]) for row in rows})
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="CANCEL_FITTING_DELIVERY",
            action_desc=f"撤销 {len(valid_rows)} 项管件发货记录",
            resource_id=", ".join(shipment_numbers),
            before_value={"items": rows},
            after_value={"ids": delivery_ids, "status": "cancelled", "cancel_reason": reason, "cancelled_at": now.isoformat()},
            client_ip=client_ip,
        )
        session.commit()
        return {"ok": True, "updated_count": len(valid_rows)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"撤销管件发货失败: {exc}") from exc
    finally:
        session.close()


def super_update_fitting_delivery_record(
    *,
    delivery_id: int,
    section_1_id: str,
    fitting_type: str,
    model_spec: str,
    shipped_qty: float,
    unit: str = "个",
    shipped_at: datetime,
    supply_entity_id: str = "",
    vehicle_plate_no: str = "",
    ship_contact_name: str = "",
    ship_contact_phone: str = "",
    ship_remark: str = "",
    status: str,
    order_no: str = "",
    shipment_no: str = "",
    arrived_qty: Optional[float] = None,
    arrived_confirm_at: Optional[datetime] = None,
    arrived_confirm_by: Optional[str] = None,
    arrived_remark: Optional[str] = None,
    received_confirm_at: Optional[datetime] = None,
    received_confirm_by: Optional[str] = None,
    received_remark: Optional[str] = None,
    warehouse_confirm_at: Optional[datetime] = None,
    warehouse_confirm_by: Optional[str] = None,
    warehouse_remark: Optional[str] = None,
    cancel_at: Optional[datetime] = None,
    cancel_by: Optional[str] = None,
    cancel_reason: Optional[str] = None,
    operator: str,
    operator_group: str,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """超级管理员与供给方管理员强力覆写更新管件发货记录（全维度数据修正通道）。"""
    _ensure_fitting_table_structures()
    now_bj = datetime.now(BEIJING_TZ)
    session = SessionLocal()
    try:
        check_sql = text(
            """
            SELECT id, supply_entity_id, shipment_no, order_no, vehicle_plate_no, section_1_id,
                   fitting_type, model_spec, shipped_qty, unit, shipped_at,
                   ship_contact_name, ship_contact_phone, ship_remark, status,
                   created_by, created_at, updated_by, updated_at,
                   arrived_qty, arrived_confirm_at, arrived_confirm_by, arrived_remark,
                   received_confirm_at, received_confirm_by, received_remark,
                   warehouse_confirm_at, warehouse_confirm_by, warehouse_remark,
                   cancel_at, cancel_by, cancel_reason
            FROM tube.tube_fitting_delivery
            WHERE id = :id
            FOR UPDATE
            """
        )
        orig_row = session.execute(check_sql, {"id": delivery_id}).mappings().first()
        if not orig_row:
            raise HTTPException(status_code=404, detail="管件发货记录不存在，无法更新")

        orig_record = dict(orig_row)

        # 基础字段清洗与校验
        val_sec = _clean(section_1_id)
        if not val_sec:
            raise HTTPException(status_code=422, detail="装车接收需求主体不能为空")

        val_ftype = _clean(fitting_type)
        if not val_ftype:
            raise HTTPException(status_code=422, detail="管件类型不能为空")

        val_spec = _clean(model_spec)
        if not val_spec:
            raise HTTPException(status_code=422, detail="型号规格描述不能为空")

        val_unit = _clean(unit) or "个"
        val_supply_entity = _clean(supply_entity_id) or _clean(orig_record.get("supply_entity_id")) or "default_supplier"
        val_order_no = _clean(order_no) or _clean(orig_record.get("order_no"))
        val_shipment_no = _clean(shipment_no) or _clean(orig_record.get("shipment_no"))
        val_plate = _clean(vehicle_plate_no) or _clean(orig_record.get("vehicle_plate_no"))
        val_cname = _clean(ship_contact_name)
        val_cphone = _clean(ship_contact_phone)
        val_ship_remark = _clean(ship_remark)

        # 发货数量校验（严格正整数）
        try:
            val_shipped_qty = float(shipped_qty)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="发货件数必须为正整数") from exc
        if val_shipped_qty <= 0 or not val_shipped_qty.is_integer():
            raise HTTPException(status_code=422, detail="发货件数必须为正整数")
        val_shipped_qty = int(val_shipped_qty)

        # 发货时间校验与时区归一化
        dt_shipped_at = shipped_at
        if dt_shipped_at is None:
            dt_shipped_at = now_bj
        elif dt_shipped_at.tzinfo is None:
            dt_shipped_at = dt_shipped_at.replace(tzinfo=BEIJING_TZ)
        else:
            dt_shipped_at = dt_shipped_at.astimezone(BEIJING_TZ)

        # 规整状态枚举
        normalized_st = _clean(status).lower()
        if normalized_st in ("shipped", "pending_arrival"):
            normalized_st = "pending_arrival"
        elif normalized_st in ("arrived", "pending_receive"):
            normalized_st = "pending_receive"
        elif normalized_st in ("construction_confirmed", "received", "pending_warehouse"):
            normalized_st = "pending_warehouse"
        elif normalized_st in ("warehouse_confirmed", "completed"):
            normalized_st = "completed"
        elif normalized_st == "cancelled":
            normalized_st = "cancelled"
        else:
            raise HTTPException(status_code=422, detail=f"无效的管件流转状态: {status}")

        def _ensure_tz(dt_val: Optional[datetime]) -> Optional[datetime]:
            if dt_val is None:
                return None
            if dt_val.tzinfo is None:
                return dt_val.replace(tzinfo=BEIJING_TZ)
            return dt_val.astimezone(BEIJING_TZ)

        dt_arrived_confirm_at = _ensure_tz(arrived_confirm_at)
        dt_received_confirm_at = _ensure_tz(received_confirm_at)
        dt_warehouse_confirm_at = _ensure_tz(warehouse_confirm_at)
        dt_cancel_at = _ensure_tz(cancel_at)

        # 提取原记录历史各节点真实时间快照（用于回退或已有状态保持）
        orig_arrived_at = _ensure_tz(orig_record.get("arrived_confirm_at"))
        orig_received_at = _ensure_tz(orig_record.get("received_confirm_at"))
        orig_warehouse_at = _ensure_tz(orig_record.get("warehouse_confirm_at"))
        orig_cancel_at = _ensure_tz(orig_record.get("cancel_at"))

        # 状态机与物理证据链严格不变量校准 (chk_tube_fitting_state_evidence)
        if normalized_st == "pending_arrival":
            # 1. 待到货状态：清空所有后续节点凭证
            out_arrived_qty = None
            out_arrived_confirm_at = None
            out_arrived_confirm_by = None
            out_arrived_remark = None

            out_received_confirm_at = None
            out_received_confirm_by = None
            out_received_remark = None

            out_warehouse_confirm_at = None
            out_warehouse_confirm_by = None
            out_warehouse_remark = None

            out_cancel_at = None
            out_cancel_by = None
            out_cancel_reason = None

        elif normalized_st == "pending_receive":
            # 2. 待施工接收状态：必须有到货凭证
            if arrived_qty is not None and float(arrived_qty) > 0:
                out_arrived_qty = min(int(float(arrived_qty)), val_shipped_qty)
            else:
                out_arrived_qty = val_shipped_qty

            # 时间戳规则：传入指定时间 > 历史已有时间 > 点击保存当前时间(now_bj)
            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = orig_arrived_at or now_bj
            if dt_arrived_confirm_at < dt_shipped_at:
                dt_arrived_confirm_at = dt_shipped_at
            out_arrived_confirm_at = dt_arrived_confirm_at
            out_arrived_confirm_by = _clean(arrived_confirm_by) or _clean(orig_record.get("arrived_confirm_by")) or operator
            out_arrived_remark = _clean(arrived_remark) or _clean(orig_record.get("arrived_remark")) or None

            out_received_confirm_at = None
            out_received_confirm_by = None
            out_received_remark = None

            out_warehouse_confirm_at = None
            out_warehouse_confirm_by = None
            out_warehouse_remark = None

            out_cancel_at = None
            out_cancel_by = None
            out_cancel_reason = None

        elif normalized_st == "pending_warehouse":
            # 3. 待库管确认状态：必须有到货与施工接收凭证
            if arrived_qty is not None and float(arrived_qty) > 0:
                out_arrived_qty = min(int(float(arrived_qty)), val_shipped_qty)
            else:
                out_arrived_qty = val_shipped_qty

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = orig_arrived_at or now_bj
            if dt_arrived_confirm_at < dt_shipped_at:
                dt_arrived_confirm_at = dt_shipped_at
            out_arrived_confirm_at = dt_arrived_confirm_at
            out_arrived_confirm_by = _clean(arrived_confirm_by) or _clean(orig_record.get("arrived_confirm_by")) or operator
            out_arrived_remark = _clean(arrived_remark) or _clean(orig_record.get("arrived_remark")) or None

            if dt_received_confirm_at is None:
                dt_received_confirm_at = orig_received_at or now_bj
            if dt_received_confirm_at < out_arrived_confirm_at:
                dt_received_confirm_at = out_arrived_confirm_at
            out_received_confirm_at = dt_received_confirm_at
            out_received_confirm_by = _clean(received_confirm_by) or _clean(orig_record.get("received_confirm_by")) or operator
            out_received_remark = _clean(received_remark) or _clean(orig_record.get("received_remark")) or None

            out_warehouse_confirm_at = None
            out_warehouse_confirm_by = None
            out_warehouse_remark = None

            out_cancel_at = None
            out_cancel_by = None
            out_cancel_reason = None

        elif normalized_st == "completed":
            # 4. 已结清状态：必须有到货、施工接收与库管入库凭证
            if arrived_qty is not None and float(arrived_qty) > 0:
                out_arrived_qty = min(int(float(arrived_qty)), val_shipped_qty)
            else:
                out_arrived_qty = val_shipped_qty

            if dt_arrived_confirm_at is None:
                dt_arrived_confirm_at = orig_arrived_at or now_bj
            if dt_arrived_confirm_at < dt_shipped_at:
                dt_arrived_confirm_at = dt_shipped_at
            out_arrived_confirm_at = dt_arrived_confirm_at
            out_arrived_confirm_by = _clean(arrived_confirm_by) or _clean(orig_record.get("arrived_confirm_by")) or operator
            out_arrived_remark = _clean(arrived_remark) or _clean(orig_record.get("arrived_remark")) or None

            if dt_received_confirm_at is None:
                dt_received_confirm_at = orig_received_at or now_bj
            if dt_received_confirm_at < out_arrived_confirm_at:
                dt_received_confirm_at = out_arrived_confirm_at
            out_received_confirm_at = dt_received_confirm_at
            out_received_confirm_by = _clean(received_confirm_by) or _clean(orig_record.get("received_confirm_by")) or operator
            out_received_remark = _clean(received_remark) or _clean(orig_record.get("received_remark")) or None

            if dt_warehouse_confirm_at is None:
                dt_warehouse_confirm_at = orig_warehouse_at or now_bj
            if dt_warehouse_confirm_at < out_received_confirm_at:
                dt_warehouse_confirm_at = out_received_confirm_at
            out_warehouse_confirm_at = dt_warehouse_confirm_at
            out_warehouse_confirm_by = _clean(warehouse_confirm_by) or _clean(orig_record.get("warehouse_confirm_by")) or operator
            out_warehouse_remark = _clean(warehouse_remark) or _clean(orig_record.get("warehouse_remark")) or None

            out_cancel_at = None
            out_cancel_by = None
            out_cancel_reason = None

        elif normalized_st == "cancelled":
            # 5. 已撤销状态：清空所有确认流转，必须有撤销时间与原因
            out_arrived_qty = None
            out_arrived_confirm_at = None
            out_arrived_confirm_by = None
            out_arrived_remark = None

            out_received_confirm_at = None
            out_received_confirm_by = None
            out_received_remark = None

            out_warehouse_confirm_at = None
            out_warehouse_confirm_by = None
            out_warehouse_remark = None

            out_cancel_at = dt_cancel_at or orig_cancel_at or now_bj
            out_cancel_by = _clean(cancel_by) or _clean(orig_record.get("cancel_by")) or operator
            out_cancel_reason = _clean(cancel_reason) or _clean(orig_record.get("cancel_reason")) or "超级管理员编辑覆盖撤销"

        # 执行数据库物理层强力 UPDATE
        update_sql = text(
            """
            UPDATE tube.tube_fitting_delivery
            SET supply_entity_id = :supply_entity_id,
                shipment_no = :shipment_no,
                order_no = :order_no,
                vehicle_plate_no = :vehicle_plate_no,
                section_1_id = :section_1_id,
                fitting_type = :fitting_type,
                model_spec = :model_spec,
                shipped_qty = :shipped_qty,
                unit = :unit,
                shipped_at = :shipped_at,
                ship_contact_name = :ship_contact_name,
                ship_contact_phone = :ship_contact_phone,
                ship_remark = :ship_remark,
                status = :status,
                updated_by = :operator,
                updated_at = NOW(),
                arrived_qty = :arrived_qty,
                arrived_confirm_at = :arrived_confirm_at,
                arrived_confirm_by = :arrived_confirm_by,
                arrived_remark = :arrived_remark,
                received_confirm_at = :received_confirm_at,
                received_confirm_by = :received_confirm_by,
                received_remark = :received_remark,
                warehouse_confirm_at = :warehouse_confirm_at,
                warehouse_confirm_by = :warehouse_confirm_by,
                warehouse_remark = :warehouse_remark,
                cancel_at = :cancel_at,
                cancel_by = :cancel_by,
                cancel_reason = :cancel_reason
            WHERE id = :id
            """
        )
        update_params = {
            "id": delivery_id,
            "supply_entity_id": val_supply_entity,
            "shipment_no": val_shipment_no,
            "order_no": val_order_no,
            "vehicle_plate_no": val_plate,
            "section_1_id": val_sec,
            "fitting_type": val_ftype,
            "model_spec": val_spec,
            "shipped_qty": val_shipped_qty,
            "unit": val_unit,
            "shipped_at": dt_shipped_at,
            "ship_contact_name": val_cname,
            "ship_contact_phone": val_cphone,
            "ship_remark": val_ship_remark,
            "status": normalized_st,
            "operator": operator,
            "arrived_qty": out_arrived_qty,
            "arrived_confirm_at": out_arrived_confirm_at,
            "arrived_confirm_by": out_arrived_confirm_by,
            "arrived_remark": out_arrived_remark,
            "received_confirm_at": out_received_confirm_at,
            "received_confirm_by": out_received_confirm_by,
            "received_remark": out_received_remark,
            "warehouse_confirm_at": out_warehouse_confirm_at,
            "warehouse_confirm_by": out_warehouse_confirm_by,
            "warehouse_remark": out_warehouse_remark,
            "cancel_at": out_cancel_at,
            "cancel_by": out_cancel_by,
            "cancel_reason": out_cancel_reason,
        }
        session.execute(update_sql, update_params)

        # 读取更新后完整快照用于审计记录
        after_row = session.execute(check_sql, {"id": delivery_id}).mappings().first()
        after_record = dict(after_row) if after_row else update_params

        # 写入高精细审计日志
        _write_audit_log(
            session,
            operator=operator,
            operator_group=operator_group,
            action_type="SUPER_UPDATE_FITTING_DELIVERY",
            action_desc=f"超级管理员强力覆写管件发货单: 订单号 {val_order_no} ({val_ftype} {val_spec} {val_shipped_qty}{val_unit})",
            resource_id=val_shipment_no or str(delivery_id),
            before_value=orig_record,
            after_value=after_record,
            client_ip=client_ip,
        )

        session.commit()
        return {
            "ok": True,
            "detail": "管件发货记录已成功编辑覆盖保存",
            "delivery_id": delivery_id,
            "record": after_record,
        }
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"管件编辑覆盖保存失败: {exc}") from exc
    finally:
        session.close()

