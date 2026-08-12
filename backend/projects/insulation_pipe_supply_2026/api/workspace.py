# -*- coding: utf-8 -*-
"""
insulation_pipe_supply_2026 工作台基础接口。
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from pydantic import BaseModel, ConfigDict, Field, conint

def _get_client_ip(request: Optional[Request]) -> str:
    if not request:
        return "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for") if hasattr(request, "headers") and request.headers else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if hasattr(request, "client") and request.client else "unknown"

from backend.services.auth_manager import AuthSession, get_current_session, get_current_session_optional
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    CONFIG_PATH,
    PROJECT_KEY,
    SUBMISSION_STATUS_PATH,
    get_configured_amap_config,
    get_configured_plan_editable_days,
    get_configured_plan_start_date,
    get_configured_show_date,
    get_config_list,
    get_usage_collection_date,
    load_tube_config,
    load_section_1_submission_status,
    resolve_accessible_supply_entity_ids,
    resolve_accessible_section_1_ids,
    resolve_supply_entity_allowed_section_ids,
    save_section_1_submission_status,
    save_tube_config,
    simple_decrypt,
    simple_encrypt,
)
from backend.projects.insulation_pipe_supply_2026.services.demand_management_service import (
    build_plan_dates,
    list_pending_arrivals,
    list_plan_records,
    list_usage_records,
    save_plan_records,
    save_usage_records,
)
from backend.projects.insulation_pipe_supply_2026.services.supply_management_service import (
    build_order_no,
    build_shipment_no,
    cancel_delivery_record,
    create_delivery_record,
    build_delivery_code,
    get_next_shipment_sequence,
    get_next_order_sequence,
    update_delivery_identifiers,
    get_delivery_record_basic,
    get_shipment_owner,
    list_arrival_aggregates,
    list_delivery_aggregates,
    list_delivery_records,
    list_plan_totals,
    format_delivery_elapsed,
    list_usage_totals,
    sync_shipment_vehicle_plate,
    update_delivery_arrival_record,
    update_delivery_receipt_record,
    update_delivery_warehouse_record,
    super_update_delivery_record,
    query_history_records,
)
from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
    cancel_fitting_delivery,
    confirm_fitting_delivery_arrival,
    confirm_fitting_delivery_construction,
    confirm_fitting_delivery_warehouse,
    get_fitting_deliveries_by_ids,
    list_fitting_deliveries,
    normalize_delivery_ids,
    submit_fitting_delivery,
)
from backend.projects.insulation_pipe_supply_2026.services import weather_service
from backend.projects.insulation_pipe_supply_2026.services.audit_log_service import (
    save_operation_log,
    query_operation_logs,
    query_submission_logs,
)
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal

router = APIRouter(tags=[PROJECT_KEY])
public_router = APIRouter(tags=[PROJECT_KEY])


def run_db_migration():
    session = SessionLocal()
    try:
        session.execute(text("ALTER TABLE tube.tube_daily_usage ADD COLUMN IF NOT EXISTS loss_qty NUMERIC(18, 2) NOT NULL DEFAULT 0;"))
        session.execute(text("""
            ALTER TABLE tube.tube_daily_usage 
            DROP CONSTRAINT IF EXISTS chk_tube_daily_usage_loss_qty_nonnegative;
        """))
        session.execute(text("""
            ALTER TABLE tube.tube_daily_usage 
            ADD CONSTRAINT chk_tube_daily_usage_loss_qty_nonnegative CHECK (loss_qty >= 0);
        """))
        
        # 2026-06-15 & 2026-07-30 操作审计日志表自动初始化与 logs Schema / tube_operation_logs 转移
        session.execute(text("CREATE SCHEMA IF NOT EXISTS logs;"))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS logs.tube_operation_logs (
                id SERIAL PRIMARY KEY,
                project_key VARCHAR(50) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
                operator VARCHAR(100) NOT NULL,
                operator_group VARCHAR(100),
                action_type VARCHAR(50) NOT NULL,
                action_desc TEXT NOT NULL,
                resource_id VARCHAR(100),
                before_value JSONB,
                after_value JSONB,
                client_ip VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_operator ON logs.tube_operation_logs(operator);"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_action_type ON logs.tube_operation_logs(action_type);"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_created_at ON logs.tube_operation_logs(created_at DESC);"))
        
        # 2026-06-23 新增差异审批与超时接收字段
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_by VARCHAR(128);"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_at TIMESTAMPTZ;"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_remark TEXT;"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS is_timeout_receive BOOLEAN NOT NULL DEFAULT FALSE;"))
        
        # 更新 CHECK 约束以支持 'pending_diff_approve' 状态
        session.execute(text("ALTER TABLE tube.tube_delivery DROP CONSTRAINT IF EXISTS chk_tube_delivery_status;"))
        session.execute(text("""
            ALTER TABLE tube.tube_delivery ADD CONSTRAINT chk_tube_delivery_status 
            CHECK (status IN ('pending_arrival', 'cancelled', 'pending_receive', 'pending_warehouse', 'completed', 'pending_diff_approve'));
        """))
        
        session.commit()
    except Exception as e:
        session.rollback()
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"数据库初始化迁移失败: {e}", exc_info=True)
        raise RuntimeError(f"数据库初始化迁移失败，应用无法启动: {e}") from e
    finally:
        session.close()

run_db_migration()



class DemandPlanRecordInput(BaseModel):
    plan_date: date
    pipe_model_id: str
    plan_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandPlanSavePayload(BaseModel):
    section_1_id: str
    records: List[DemandPlanRecordInput] = []


class DemandUsageRecordInput(BaseModel):
    pipe_model_id: str
    usage_qty: float = Field(default=0, ge=0)
    loss_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandUsageSavePayload(BaseModel):
    section_1_id: str
    usage_date: date
    records: List[DemandUsageRecordInput] = []


class DemandSection1SubmissionPayload(BaseModel):
    section_1_id: str
    remark: str = ""


class TubeConfigSavePayload(BaseModel):
    config: Dict[str, Any]


class TubeConfigSectionSavePayload(BaseModel):
    section: str
    data: Any


class WeatherEvalPayload(BaseModel):
    api_url: Optional[str] = None


class WeatherImportPayload(BaseModel):
    api_url: Optional[str] = None


class SupplyDeliveryCreatePayload(BaseModel):
    supply_entity_id: str
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    shipped_at: datetime
    shipment_no: str = ""
    vehicle_plate_no: str = ""
    ship_contact_name: str = ""
    ship_contact_phone: str = ""
    ship_remark: str = ""


class SupplyDeliveryBatchItemInput(BaseModel):
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    ship_remark: str = ""


class SupplyDeliveryBatchCreatePayload(BaseModel):
    supply_entity_id: str
    shipped_at: datetime
    shipment_no: str = ""
    vehicle_plate_no: str = ""
    ship_contact_name: str = ""
    ship_contact_phone: str = ""
    items: List[SupplyDeliveryBatchItemInput]


class SupplyDeliveryCancelPayload(BaseModel):
    cancel_reason: str = ""


class CustomSupplyEntityPayload(BaseModel):
    entity_name: str
    contact_name: str = ""
    contact_phone: str = ""



class SuperUpdateDeliveryPayload(BaseModel):
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    shipped_at: datetime
    vehicle_plate_no: str = ""
    ship_remark: str = ""
    status: str
    order_no: str = ""
    shipment_no: str = ""
    arrived_qty: Optional[float] = None
    received_qty: Optional[float] = None
    arrived_confirm_at: Optional[datetime] = None
    received_confirm_at: Optional[datetime] = None
    warehouse_confirm_at: Optional[datetime] = None



class WarehouseArrivalConfirmPayload(BaseModel):
    arrived_qty: float = Field(ge=0.01)
    remark: str = ""


from backend.projects.insulation_pipe_supply_2026.services import weather_service
from backend.projects.insulation_pipe_supply_2026.services.audit_log_service import (
    save_operation_log,
    query_operation_logs,
    query_submission_logs,
)
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal

router = APIRouter(tags=[PROJECT_KEY])
public_router = APIRouter(tags=[PROJECT_KEY])


def run_db_migration():
    session = SessionLocal()
    try:
        session.execute(text("ALTER TABLE tube.tube_daily_usage ADD COLUMN IF NOT EXISTS loss_qty NUMERIC(18, 2) NOT NULL DEFAULT 0;"))
        session.execute(text("""
            ALTER TABLE tube.tube_daily_usage 
            DROP CONSTRAINT IF EXISTS chk_tube_daily_usage_loss_qty_nonnegative;
        """))
        session.execute(text("""
            ALTER TABLE tube.tube_daily_usage 
            ADD CONSTRAINT chk_tube_daily_usage_loss_qty_nonnegative CHECK (loss_qty >= 0);
        """))
        
        # 2026-06-15 & 2026-07-30 操作审计日志表自动初始化与 logs Schema / tube_operation_logs 转移
        session.execute(text("CREATE SCHEMA IF NOT EXISTS logs;"))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS logs.tube_operation_logs (
                id SERIAL PRIMARY KEY,
                project_key VARCHAR(50) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
                operator VARCHAR(100) NOT NULL,
                operator_group VARCHAR(100),
                action_type VARCHAR(50) NOT NULL,
                action_desc TEXT NOT NULL,
                resource_id VARCHAR(100),
                before_value JSONB,
                after_value JSONB,
                client_ip VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_operator ON logs.tube_operation_logs(operator);"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_action_type ON logs.tube_operation_logs(action_type);"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_logs_tube_op_created_at ON logs.tube_operation_logs(created_at DESC);"))
        
        # 2026-06-23 新增差异审批与超时接收字段
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_by VARCHAR(128);"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_at TIMESTAMPTZ;"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS diff_approve_remark TEXT;"))
        session.execute(text("ALTER TABLE tube.tube_delivery ADD COLUMN IF NOT EXISTS is_timeout_receive BOOLEAN NOT NULL DEFAULT FALSE;"))
        
        # 更新 CHECK 约束以支持 'pending_diff_approve' 状态
        session.execute(text("ALTER TABLE tube.tube_delivery DROP CONSTRAINT IF EXISTS chk_tube_delivery_status;"))
        session.execute(text("""
            ALTER TABLE tube.tube_delivery ADD CONSTRAINT chk_tube_delivery_status 
            CHECK (status IN ('pending_arrival', 'cancelled', 'pending_receive', 'pending_warehouse', 'completed', 'pending_diff_approve'));
        """))
        
        session.commit()
    except Exception as e:
        session.rollback()
        import logging
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"数据库初始化迁移失败: {e}", exc_info=True)
        raise RuntimeError(f"数据库初始化迁移失败，应用无法启动: {e}") from e
    finally:
        session.close()

run_db_migration()



class DemandPlanRecordInput(BaseModel):
    plan_date: date
    pipe_model_id: str
    plan_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandPlanSavePayload(BaseModel):
    section_1_id: str
    records: List[DemandPlanRecordInput] = []


class DemandUsageRecordInput(BaseModel):
    pipe_model_id: str
    usage_qty: float = Field(default=0, ge=0)
    loss_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandUsageSavePayload(BaseModel):
    section_1_id: str
    usage_date: date
    records: List[DemandUsageRecordInput] = []


class DemandSection1SubmissionPayload(BaseModel):
    section_1_id: str
    remark: str = ""


class TubeConfigSavePayload(BaseModel):
    config: Dict[str, Any]


class TubeConfigSectionSavePayload(BaseModel):
    section: str
    data: Any


class WeatherEvalPayload(BaseModel):
    api_url: Optional[str] = None


class WeatherImportPayload(BaseModel):
    api_url: Optional[str] = None


class SupplyDeliveryCreatePayload(BaseModel):
    supply_entity_id: str
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    shipped_at: datetime
    shipment_no: str = ""
    vehicle_plate_no: str = ""
    ship_contact_name: str = ""
    ship_contact_phone: str = ""
    ship_remark: str = ""


class SupplyDeliveryBatchItemInput(BaseModel):
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    ship_remark: str = ""


class SupplyDeliveryBatchCreatePayload(BaseModel):
    supply_entity_id: str
    shipped_at: datetime
    shipment_no: str = ""
    vehicle_plate_no: str = ""
    ship_contact_name: str = ""
    ship_contact_phone: str = ""
    items: List[SupplyDeliveryBatchItemInput]


class SupplyDeliveryCancelPayload(BaseModel):
    cancel_reason: str = ""


class CustomSupplyEntityPayload(BaseModel):
    entity_name: str
    contact_name: str = ""
    contact_phone: str = ""



class SuperUpdateDeliveryPayload(BaseModel):
    section_1_id: str
    pipe_model_id: str
    shipped_qty: float = Field(ge=0.01)
    shipped_at: datetime
    vehicle_plate_no: str = ""
    ship_remark: str = ""
    status: str
    order_no: str = ""
    shipment_no: str = ""
    arrived_qty: Optional[float] = None
    received_qty: Optional[float] = None
    arrived_confirm_at: Optional[datetime] = None
    received_confirm_at: Optional[datetime] = None
    warehouse_confirm_at: Optional[datetime] = None



class WarehouseArrivalConfirmPayload(BaseModel):
    arrived_qty: float = Field(ge=0.01)
    remark: str = ""


class WarehouseReceiptConfirmPayload(BaseModel):
    received_qty: float = Field(ge=0.01)
    remark: str = ""


class WarehouseConfirmPayload(BaseModel):
    remark: str = ""


class DiffApprovePayload(BaseModel):
    approved: bool
    remark: str = ""


PositiveFittingInt = conint(gt=0)


class StrictFittingPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FittingDeliveryItemInput(BaseModel):
    fitting_type: str = Field(min_length=1)
    model_spec: str = Field(min_length=1)
    shipped_qty: PositiveFittingInt
    unit: Optional[str] = "个"
    remark: Optional[str] = ""
    model_config = ConfigDict(extra="ignore")


class FittingDeliverySubmitPayload(BaseModel):
    supply_entity_id: str = Field(min_length=1)
    vehicle_plate_no: str = Field(min_length=1)
    section_1_id: str = Field(min_length=1)
    shipped_at: datetime
    ship_contact_name: Optional[str] = ""
    ship_contact_phone: Optional[str] = ""
    ship_remark: Optional[str] = ""
    items: List[FittingDeliveryItemInput] = Field(min_length=1)
    model_config = ConfigDict(extra="ignore")


class FittingArrivalConfirmPayload(BaseModel):
    ids: List[PositiveFittingInt] = Field(min_length=1)
    arrived_qty_map: Dict[str, PositiveFittingInt] = Field(default_factory=dict)
    remark: Optional[str] = ""
    model_config = ConfigDict(extra="ignore")


class FittingConfirmPayload(BaseModel):
    ids: List[PositiveFittingInt] = Field(min_length=1)
    remark: Optional[str] = ""
    model_config = ConfigDict(extra="ignore")


class FittingCancelPayload(BaseModel):
    ids: List[PositiveFittingInt] = Field(min_length=1)
    remark: str = Field(min_length=2)
    model_config = ConfigDict(extra="ignore")


def _ensure_site_manager_access(session: AuthSession) -> None:
    group = str(session.group or "").strip()
    if group not in {"Global_admin", "tube_site_manager"}:
        raise HTTPException(status_code=403, detail="当前账号无差异审批权限，必须是 site_manager")


def _normalize_pipe_model_id(value: Any) -> str:
    return str(value or "").strip().upper()


def _build_section_1_name_map(payload: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in get_config_list(payload, "demand_entities"):
        section_1_id = str(item.get("section_1_id") or "").strip()
        code = str(item.get("code") or "").strip()
        name = str(item.get("section_1_name") or section_1_id)
        if section_1_id:
            result[section_1_id] = name
            result[section_1_id.lower()] = name
            result[section_1_id.upper()] = name
        if code:
            result[code] = name
            result[code.lower()] = name
            result[code.upper()] = name
    return result


def _build_section_1_code_map(payload: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for index, item in enumerate(get_config_list(payload, "demand_entities")):
        section_1_id = str(item.get("section_1_id") or "").strip()
        if not section_1_id:
            continue
        explicit_code = str(item.get("code") or "").strip().upper()
        result[section_1_id] = explicit_code or _index_to_letters(index)
    return result


def _build_pipe_model_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "pipe_models"):
        pipe_model_id = _normalize_pipe_model_id(item.get("pipe_model_id"))
        if not pipe_model_id:
            continue
        result[pipe_model_id] = {
            **item,
            "pipe_model_id": pipe_model_id,
            "pipe_model_name": str(item.get("pipe_model_name") or pipe_model_id).strip() or pipe_model_id,
        }
    for item in get_config_list(payload, "baseline_presets"):
        pipe_model_id = _normalize_pipe_model_id(item.get("pipe_model_id"))
        if pipe_model_id and pipe_model_id not in result:
            result[pipe_model_id] = {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model_id,
                "unit": "米",
            }
    return result


def _build_supply_entity_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "supply_entities"):
        entity_id = str(item.get("entity_id") or "").strip()
        code = str(item.get("code") or "").strip()
        if entity_id:
            result[entity_id] = item
            result[entity_id.lower()] = item
            result[entity_id.upper()] = item
        if code:
            result[code] = item
            result[code.lower()] = item
            result[code.upper()] = item
    return result


def _build_supply_entity_code_map(payload: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for index, item in enumerate(get_config_list(payload, "supply_entities")):
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id:
            continue
        explicit_code = str(item.get("code") or "").strip().upper()
        if explicit_code:
            result[entity_id] = explicit_code
            continue
        result[entity_id] = f"S{_index_to_letters(index)}"
    return result


def _index_to_letters(index: int) -> str:
    if index < 0:
        index = 0
    value = index
    letters: List[str] = []
    while True:
        value, remainder = divmod(value, 26)
        letters.append(chr(ord("A") + remainder))
        if value == 0:
            break
        value -= 1
    return "".join(reversed(letters))


def _derive_delivery_code_prefix(entity_id: str, entity_name: str, fallback_index: int) -> str:
    explicit_sources = [str(entity_id or "").strip(), str(entity_name or "").strip()]
    for source in explicit_sources:
        normalized = source.replace("-", "_").replace(" ", "_").upper()
        parts = [part for part in normalized.split("_") if part]
        if len(parts) >= 2:
            candidate = "".join(part[0] for part in parts if part[:1].isascii() and part[:1].isalnum())
            if candidate:
                return candidate[:4]
        ascii_chars = "".join(ch for ch in normalized if ch.isascii() and ch.isalnum())
        if ascii_chars:
            return ascii_chars[:4]
    return _index_to_letters(fallback_index)


def _build_supply_entity_prefix_map(payload: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for index, item in enumerate(get_config_list(payload, "supply_entities")):
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id:
            continue
        explicit_prefix = str(item.get("delivery_code_prefix") or "").strip().upper()
        if explicit_prefix:
            result[entity_id] = explicit_prefix
            continue
        result[entity_id] = _derive_delivery_code_prefix(
            entity_id,
            str(item.get("entity_name") or ""),
            index,
        )
    return result


def _ensure_global_admin(session: AuthSession) -> None:
    if str(session.group or "").strip() != "Global_admin":
        raise HTTPException(status_code=403, detail="只有 Global_admin 可以访问该页面")


def _ensure_warehouse_access(session: AuthSession) -> None:
    group = str(session.group or "").strip()
    if group not in {"Global_admin", "tube_warehouse_keeper", "tube_global_viewer"}:
        raise HTTPException(status_code=403, detail="当前账号无库管页面访问权限")


def _build_baseline_preset_map(payload: Dict[str, Any], section_1_id: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "baseline_presets"):
        normalized_section_1_id = str(item.get("section_1_id") or "").strip()
        pipe_model_id = str(item.get("pipe_model_id") or "").strip()
        if normalized_section_1_id != section_1_id or not pipe_model_id:
            continue
        result[pipe_model_id] = {
            "design_qty": item.get("design_qty"),
            "purchase_plan_qty": item.get("purchase_plan_qty"),
            "remark": item.get("remark") or "",
        }
    return result


def _parse_pipe_model_diameters(model_code: str) -> Tuple[float, float]:
    if not model_code:
        return (0.0, 0.0)
    parts = str(model_code).strip().split('/')
    left_str = parts[0] if len(parts) > 0 else ""
    right_str = parts[1] if len(parts) > 1 else ""
    left_match = re.search(r'(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)', left_str, re.I)
    right_match = re.search(r'(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)', right_str, re.I)
    main_d = float(left_match.group(1)) if left_match else 0.0
    outer_d = float(right_match.group(1)) if right_match else 0.0
    return (main_d, outer_d)


def _resolve_section_1_sorted_pipe_model_ids(payload: Dict[str, Any], section_1_id: str) -> List[str]:
    peer_section_ids = [section_1_id]
    supply_entities = get_config_list(payload, "supply_entities")
    for entity in supply_entities:
        sec_ids = entity.get("section_1_ids") or []
        if section_1_id in sec_ids:
            peer_section_ids = sec_ids
            break

    seen = set()
    model_ids: List[str] = []
    for sec_id in peer_section_ids:
        preset_map = _build_baseline_preset_map(payload, sec_id)
        for pm_id in preset_map.keys():
            if pm_id and pm_id not in seen:
                model_ids.append(pm_id)
                seen.add(pm_id)
            
    if not model_ids:
        pipe_model_map = _build_pipe_model_map(payload)
        for pm_id in pipe_model_map.keys():
            if pm_id and pm_id not in seen:
                model_ids.append(pm_id)
                seen.add(pm_id)
            
    def sort_key(pm_id: str):
        main_d, outer_d = _parse_pipe_model_diameters(pm_id)
        return (-main_d, -outer_d, pm_id)
        
    return sorted(model_ids, key=sort_key)


def _save_config_section(section: str, data: Any) -> Dict[str, Any]:
    payload = load_tube_config()
    normalized_section = str(section or "").strip()
    allowed_sections = {
        "show_date",
        "usage_collection_date",
        "plan_start_date",
        "auto_update_plan_start_date",
        "plan_editable_days",
        "strict_planning_flow_control",
        "fitting_config",
        "supply_entities",
        "demand_entities",
        "pipe_models",
        "production_capacities",
        "manager_assignments",
        "construction_units",
        "warehouse_keepers",
        "baseline_presets",
        "weather_api_url",
        "weather_provider",
        "management_mode",
        "amap_config",
    }
    if normalized_section not in allowed_sections:
        raise HTTPException(status_code=422, detail=f"不支持的配置区块：{normalized_section}")

    if normalized_section in {"show_date", "usage_collection_date", "plan_start_date"}:
        normalized_date = str(data or "").strip()
        if not normalized_date:
            raise HTTPException(status_code=422, detail=f"{normalized_section} 不能为空")
        try:
            date.fromisoformat(normalized_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{normalized_section} 非法：{normalized_date}") from exc
        payload[normalized_section] = normalized_date
    elif normalized_section == "auto_update_plan_start_date":
        if data == "all":
            payload[normalized_section] = "all"
        elif isinstance(data, bool):
            payload[normalized_section] = data
        else:
            raise HTTPException(status_code=422, detail="auto_update_plan_start_date 仅支持 false、true 或 all")
    elif normalized_section == "strict_planning_flow_control":
        payload[normalized_section] = bool(data)
    elif normalized_section == "plan_editable_days":
        try:
            normalized_editable_days = int(data)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 非法：{data}") from exc
        if normalized_editable_days < 0 or normalized_editable_days > 3:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 超出范围：{normalized_editable_days}")
        payload[normalized_section] = normalized_editable_days
    elif normalized_section == "weather_api_url":
        payload[normalized_section] = str(data or "").strip()
    elif normalized_section == "weather_provider":
        if isinstance(data, dict):
            provider_val = str(data.get("provider") or "amap").strip()
            api_key_plain = str(data.get("api_key") or "").strip()
            payload["weather_provider"] = provider_val
            if api_key_plain:
                amap_cfg = payload.setdefault("amap_config", {})
                if not isinstance(amap_cfg, dict):
                    amap_cfg = {}
                    payload["amap_config"] = amap_cfg
                amap_cfg["api_key"] = simple_encrypt(api_key_plain)
        else:
            payload["weather_provider"] = str(data or "").strip()
    elif normalized_section == "management_mode":
        val = str(data or "").strip()
        if val != "section_1":
            raise HTTPException(status_code=422, detail=f"不支持的管理模式：{val}")
        payload[normalized_section] = val
    elif normalized_section == "amap_config":
        if not isinstance(data, dict):
            raise HTTPException(status_code=422, detail="amap_config 必须为对象")
        api_key_plain = str(data.get("api_key") or "").strip()
        security_code_plain = str(data.get("security_code") or "").strip()
        payload[normalized_section] = {
            "api_key": simple_encrypt(api_key_plain),
            "security_code": simple_encrypt(security_code_plain),
        }
    elif normalized_section == "fitting_config":
        if not isinstance(data, dict):
            raise HTTPException(status_code=422, detail="fitting_config 必须为对象")
        allowed_units = [str(x).strip() for x in (data.get("allowed_units") or []) if str(x).strip()]
        standard_types = [str(x).strip() for x in (data.get("standard_types") or []) if str(x).strip()]
        if not allowed_units:
            raise HTTPException(status_code=422, detail="管件允许单位列表 (allowed_units) 不能为空")
        payload[normalized_section] = {
            "allowed_units": allowed_units,
            "standard_types": standard_types,
        }
    else:
        if not isinstance(data, list):
            raise HTTPException(status_code=422, detail=f"{normalized_section} 必须为数组")
        payload[normalized_section] = data

    save_tube_config(payload)
    return payload


def _ensure_section_1_access(section_1_id: str, accessible_section_1_ids: set[str]) -> None:
    normalized_section_1_id = str(section_1_id or "").strip()
    if not normalized_section_1_id:
        raise HTTPException(status_code=422, detail="section_1_id 不能为空")
    if normalized_section_1_id not in accessible_section_1_ids:
        raise HTTPException(status_code=403, detail=f"当前账号无需求主体 {normalized_section_1_id} 的访问权限")


def _serialize_section_1_options(payload: Dict[str, Any], accessible_section_1_ids: set[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in get_config_list(payload, "demand_entities"):
        section_1_id = str(item.get("section_1_id") or "").strip()
        if not section_1_id or section_1_id not in accessible_section_1_ids:
            continue
        rows.append(
            {
                "section_1_id": section_1_id,
                "code": str(item.get("code") or "").strip().upper(),
                "section_1_name": item.get("section_1_name") or section_1_id,
                "section_2": item.get("section_2") or "",
                "section_3": item.get("section_3") or "",
                "construction_status": item.get("construction_status") or "",
            }
        )
    return rows


def _normalize_submission_rows(rows: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    normalized_rows: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        section_1_id = str(item.get("section_1_id") or "").strip()
        if not section_1_id:
            continue
        normalized_rows.append(dict(item))
    return normalized_rows


def _serialize_pipe_options(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    supply_entities = get_config_list(payload, "supply_entities")
    pipe_model_map = _build_pipe_model_map(payload)
    
    seen = set()
    result_rows: List[Dict[str, Any]] = []
    
    for entity in supply_entities:
        entity_id = str(entity.get("entity_id") or "").strip()
        entity_name = entity.get("entity_name") or entity_id
        sec_ids = entity.get("section_1_ids") or []
        
        group_model_ids: List[str] = []
        group_seen = set()
        for sec_id in sec_ids:
            preset_map = _build_baseline_preset_map(payload, sec_id)
            for pm_id in preset_map.keys():
                if pm_id and pm_id not in group_seen:
                    group_model_ids.append(pm_id)
                    group_seen.add(pm_id)
                    
        if not group_model_ids:
            for pm_id in pipe_model_map.keys():
                if pm_id and pm_id not in group_seen:
                    group_model_ids.append(pm_id)
                    group_seen.add(pm_id)
                    
        def sort_key(pm_id: str):
            main_d, outer_d = _parse_pipe_model_diameters(pm_id)
            return (-main_d, -outer_d, pm_id)
            
        sorted_group_ids = sorted(group_model_ids, key=sort_key)
        if "low" in entity_id.lower() or any("low" in str(s).lower() for s in sec_ids) or "xinruide" in entity_id.lower():
            group_label = "低温水网"
        else:
            group_label = "高温水网"
        
        for pm_id in sorted_group_ids:
            if pm_id not in seen:
                pipe_model = pipe_model_map.get(pm_id) or {}
                result_rows.append(
                    {
                        "pipe_model_id": pm_id,
                        "pipe_model_name": pipe_model.get("pipe_model_name") or pm_id,
                        "unit": pipe_model.get("unit") or "米",
                        "category_group": group_label,
                    }
                )
                seen.add(pm_id)
                
    for pm_id, pipe_model in pipe_model_map.items():
        if pm_id not in seen:
            result_rows.append(
                {
                    "pipe_model_id": pm_id,
                    "pipe_model_name": pipe_model.get("pipe_model_name") or pm_id,
                    "unit": pipe_model.get("unit") or "米",
                    "category_group": "其他",
                }
            )
            seen.add(pm_id)
            
    return result_rows


def _is_admin_or_supplier_admin(group: str) -> bool:
    normalized_group = str(group or "").strip()
    return normalized_group in ("Global_admin", "tube_global_viewer", "tube_supplier_admin")

def _serialize_supply_entity_options(
    payload: Dict[str, Any],
    accessible_supply_entity_ids: set[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in get_config_list(payload, "supply_entities"):
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id or entity_id not in accessible_supply_entity_ids:
            continue
        rows.append(
            {
                "entity_id": entity_id,
                "code": str(item.get("code") or "").strip().upper(),
                "entity_name": item.get("entity_name") or entity_id,
                "contact_name": item.get("contact_name") or "",
                "contact_phone": item.get("contact_phone") or "",
                "section_1_ids": item.get("section_1_ids") or [],
                "is_custom": bool(item.get("is_custom")),
            }
        )
    return rows


def _serialize_all_supply_entity_options(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in get_config_list(payload, "supply_entities"):
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id:
            continue
        rows.append(
            {
                "entity_id": entity_id,
                "code": str(item.get("code") or "").strip().upper(),
                "entity_name": item.get("entity_name") or entity_id,
                "contact_name": item.get("contact_name") or "",
                "contact_phone": item.get("contact_phone") or "",
                "section_1_ids": item.get("section_1_ids") or [],
            }
        )
    return rows


def _decorate_delivery_rows(payload: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    section_1_name_map = _build_section_1_name_map(payload)
    section_1_code_map = _build_section_1_code_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    supply_entity_map = _build_supply_entity_map(payload)
    supply_entity_code_map = _build_supply_entity_code_map(payload)
    
    # 建立负责人账号映射 (manager_id -> manager_name & contact_phone)
    manager_assignments = payload.get("manager_assignments") or []
    manager_map = {}
    for item in manager_assignments:
        m_id = str(item.get("manager_id") or "").strip()
        if m_id:
            manager_map[m_id] = {
                "manager_name": item.get("manager_name") or "",
                "contact_phone": item.get("contact_phone") or ""
            }

    # 建立施工单位映射 (unit_id -> contact_name & contact_phone)
    construction_units = payload.get("construction_units") or []
    construction_map = {}
    for item in construction_units:
        u_id = str(item.get("unit_id") or "").strip()
        if u_id:
            construction_map[u_id] = {
                "contact_name": item.get("contact_name") or "",
                "contact_phone": item.get("contact_phone") or ""
            }

    # 建立库管人员映射 (keeper_id -> keeper_name & contact_phone)
    warehouse_keepers = payload.get("warehouse_keepers") or []
    keeper_map = {}
    for item in warehouse_keepers:
        k_id = str(item.get("keeper_id") or "").strip()
        if k_id:
            keeper_map[k_id] = {
                "keeper_name": item.get("keeper_name") or "",
                "contact_phone": item.get("contact_phone") or ""
            }

    for row in rows:
        shipped_at_value = datetime.fromisoformat(row["shipped_at"]) if row.get("shipped_at") else None
        arrived_confirm_at_value = datetime.fromisoformat(row["arrived_confirm_at"]) if row.get("arrived_confirm_at") else None
        supply_entity_id = row.get("supply_entity_id") or ""
        section_1_id = row.get("section_1_id") or ""
        row_id = row.get("id") or 0
        supply_code = supply_entity_code_map.get(supply_entity_id, "")
        section_1_code = section_1_code_map.get(section_1_id, "")
        row["order_no"] = row.get("order_no") or build_order_no(
            row_id,
            shipped_at=shipped_at_value,
            supply_code=supply_code,
            section_1_code=section_1_code,
        )
        row["shipment_no"] = row.get("shipment_no") or build_shipment_no(
            row_id,
            shipped_at=shipped_at_value,
            supply_code=supply_code,
        )
        row["delivery_code"] = row.get("order_no") or row.get("shipment_no") or ""
        if row.get("status") == "cancelled":
            row["delivery_elapsed_label"] = ""
        else:
            row["delivery_elapsed_label"] = format_delivery_elapsed(
                shipped_at_value,
                arrived_confirm_at=arrived_confirm_at_value,
            )
        row["section_1_name"] = section_1_name_map.get(section_1_id, section_1_id)
        pipe_model_id = row.get("pipe_model_id")
        if pipe_model_id:
            row["pipe_model_name"] = pipe_model_map.get(pipe_model_id, {}).get("pipe_model_name") or pipe_model_id
        else:
            row["pipe_model_name"] = f"{row.get('fitting_type', '')} ({row.get('model_spec', '')})".strip()
        row["supply_entity_name"] = supply_entity_map.get(supply_entity_id, {}).get("entity_name") or supply_entity_id
        
        # 填充到货确认的操作负责人姓名和电话
        arrived_by = row.get("arrived_confirm_by")
        if arrived_by and arrived_by in manager_map:
            row["arrived_confirm_name"] = manager_map[arrived_by]["manager_name"]
            row["arrived_confirm_phone"] = manager_map[arrived_by]["contact_phone"]
        else:
            row["arrived_confirm_name"] = arrived_by or ""
            row["arrived_confirm_phone"] = ""

        # 填充施工接收的操作负责人姓名和电话
        received_by = row.get("received_confirm_by")
        if received_by and received_by in construction_map:
            row["received_confirm_name"] = construction_map[received_by]["contact_name"]
            row["received_confirm_phone"] = construction_map[received_by]["contact_phone"]
        else:
            row["received_confirm_name"] = received_by or ""
            row["received_confirm_phone"] = ""

        # 填充库管确认的操作负责人姓名 and 电话
        warehouse_by = row.get("warehouse_confirm_by")
        if warehouse_by and warehouse_by in keeper_map:
            row["warehouse_confirm_name"] = keeper_map[warehouse_by]["keeper_name"]
            row["warehouse_confirm_phone"] = keeper_map[warehouse_by]["contact_phone"]
        else:
            row["warehouse_confirm_name"] = warehouse_by or ""
            row["warehouse_confirm_phone"] = ""


def _resolve_shipment_no_for_create(
    *,
    requested_shipment_no: str,
    supply_entity_id: str,
    supply_code: str,
    shipped_at: datetime,
    requested_vehicle_plate_no: str = "",
) -> tuple[str, bool, str]:
    normalized_requested = str(requested_shipment_no or "").strip().upper()
    normalized_requested_vehicle_plate_no = str(requested_vehicle_plate_no or "").strip().upper()
    if normalized_requested:
        shipment_owner = get_shipment_owner(normalized_requested)
        if not shipment_owner:
            raise HTTPException(status_code=422, detail="指定的运输车次号不存在，无法继续沿用。")
        if shipment_owner.get("supply_entity_id") != supply_entity_id:
            raise HTTPException(status_code=422, detail="运输车次号所属供给主体与当前发货主体不一致。")
        existing_vehicle_plate_no = str(shipment_owner.get("vehicle_plate_no") or "").strip().upper()
        if existing_vehicle_plate_no and normalized_requested_vehicle_plate_no and existing_vehicle_plate_no != normalized_requested_vehicle_plate_no:
            raise HTTPException(status_code=422, detail="当前运输车次号已登记其他车牌号，不能填写不一致的车牌号。")
        return normalized_requested, True, existing_vehicle_plate_no or normalized_requested_vehicle_plate_no
    next_sequence = get_next_shipment_sequence(
        supply_code=supply_code,
        shipped_at=shipped_at,
    )
    return (
        build_shipment_no(
            next_sequence,
            shipped_at=shipped_at,
            supply_code=supply_code,
        ),
        False,
        normalized_requested_vehicle_plate_no,
    )


def _create_supply_delivery_entry(
    *,
    config_payload: Dict[str, Any],
    session: AuthSession,
    supply_entity_id: str,
    section_1_id: str,
    pipe_model_id: str,
    shipped_qty: float,
    shipped_at: datetime,
    ship_contact_name: str,
    ship_contact_phone: str,
    ship_remark: str,
    vehicle_plate_no: str = "",
    requested_shipment_no: str = "",
) -> Dict[str, Any]:
    allowed_section_ids = resolve_supply_entity_allowed_section_ids(config_payload, supply_entity_id)
    if allowed_section_ids and section_1_id not in allowed_section_ids:
        section_map = _build_section_1_name_map(config_payload)
        allowed_names = [section_map.get(sid, sid) for sid in allowed_section_ids]
        supply_name_map = {item.get("entity_id"): item.get("entity_name") for item in get_config_list(config_payload, "supply_entities")}
        supply_name = supply_name_map.get(supply_entity_id, supply_entity_id)
        raise HTTPException(
            status_code=403,
            detail=f"供给主体 [{supply_name}] 无权为需求标段 [{section_map.get(section_1_id, section_1_id)}] 登记发货，该供给主体仅供货于: {', '.join(allowed_names)}"
        )

    supply_entity_code_map = _build_supply_entity_code_map(config_payload)
    section_1_code_map = _build_section_1_code_map(config_payload)
    supply_code = supply_entity_code_map.get(supply_entity_id, "")
    section_1_code = section_1_code_map.get(section_1_id, "")
    delivery_id = create_delivery_record(
        supply_entity_id=supply_entity_id,
        order_no="",
        shipment_no="",
        vehicle_plate_no="",
        section_1_id=section_1_id,
        pipe_model_id=pipe_model_id,
        shipped_qty=shipped_qty,
        shipped_at=shipped_at,
        ship_contact_name=ship_contact_name,
        ship_contact_phone=ship_contact_phone,
        ship_remark=ship_remark,
        operator=session.username,
    )
    next_order_sequence = get_next_order_sequence(
        supply_code=supply_code,
        shipped_at=shipped_at,
    )
    order_no = build_order_no(
        next_order_sequence,
        shipped_at=shipped_at,
        supply_code=supply_code,
        section_1_code=section_1_code,
    )
    shipment_no, shipment_reused, resolved_vehicle_plate_no = _resolve_shipment_no_for_create(
        requested_shipment_no=requested_shipment_no,
        supply_entity_id=supply_entity_id,
        supply_code=supply_code,
        shipped_at=shipped_at,
        requested_vehicle_plate_no=vehicle_plate_no,
    )
    update_delivery_identifiers(
        delivery_id,
        order_no=order_no,
        shipment_no=shipment_no,
        operator=session.username,
    )
    sync_shipment_vehicle_plate(
        shipment_no=shipment_no,
        vehicle_plate_no=resolved_vehicle_plate_no,
        operator=session.username,
    )
    return {
        "delivery_id": delivery_id,
        "order_no": order_no,
        "shipment_no": shipment_no,
        "vehicle_plate_no": resolved_vehicle_plate_no,
        "shipment_reused": shipment_reused,
        "delivery_code": order_no,
    }


@public_router.get("/workspace/config-summary", summary="读取 tube 配置摘要")
def get_workspace_config_summary() -> Dict[str, Any]:
    payload = load_tube_config()
    supply_entities = get_config_list(payload, "supply_entities")
    demand_entities = get_config_list(payload, "demand_entities")
    pipe_models = get_config_list(payload, "pipe_models")
    production_capacities = get_config_list(payload, "production_capacities")
    manager_assignments = get_config_list(payload, "manager_assignments")
    construction_units = get_config_list(payload, "construction_units")
    warehouse_keepers = get_config_list(payload, "warehouse_keepers")
    baseline_presets = get_config_list(payload, "baseline_presets")

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "show_date": get_configured_show_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "usage_collection_date": get_usage_collection_date(payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(payload),
        "management_mode": payload.get("management_mode", "section_1"),
        "summary": {
            "supply_entity_count": len(supply_entities),
            "demand_entity_count": len(demand_entities),
            "pipe_model_count": len(pipe_models),
            "production_capacity_count": len(production_capacities),
            "manager_assignment_count": len(manager_assignments),
            "construction_unit_count": len(construction_units),
            "warehouse_keeper_count": len(warehouse_keepers),
            "baseline_preset_count": len(baseline_presets),
        },
        "supply_entities": supply_entities,
        "demand_entities": demand_entities,
        "pipe_models": _serialize_pipe_options(payload),
        "production_capacities": production_capacities,
        "manager_assignments": manager_assignments,
        "construction_units": construction_units,
        "warehouse_keepers": warehouse_keepers,
        "baseline_presets": baseline_presets,
    }


@public_router.get("/workspace/weather", summary="大盘气象数据接口")
def get_workspace_weather_data(
    show_date: str = "",
) -> Dict[str, Any]:
    if not show_date:
        try:
            payload = load_tube_config()
            show_date = get_configured_show_date(payload).isoformat()
        except Exception:
            show_date = date.today().isoformat()
    return weather_service.get_weather_dashboard_data(show_date)


@router.get("/demand-management/options", summary="读取需求侧页面选项")
def get_demand_management_options(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    show_date = get_configured_show_date(payload)
    plan_start_date = get_configured_plan_start_date(payload)
    usage_collection_date = get_usage_collection_date(payload)
    plan_editable_days = get_configured_plan_editable_days(payload)
    supply_entities = get_config_list(payload, "supply_entities")

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "user": {
            "username": session.username,
            "group": session.group,
            "unit": session.unit,
        },
        "section_1s": _serialize_section_1_options(payload, accessible_section_1_ids),
        "supply_entities": supply_entities,
        "pipe_models": _serialize_pipe_options(payload),
        "fitting_config": payload.get("fitting_config") or {},
        "show_date": show_date.isoformat(),
        "plan_start_date": plan_start_date.isoformat(),
        "plan_editable_days": plan_editable_days,
        "default_plan_anchor_date": plan_start_date.isoformat(),
        "usage_collection_date": usage_collection_date.isoformat(),
        "default_usage_date": usage_collection_date.isoformat(),
    }
@router.get("/supply-management/options", summary="读取供给侧页面选项")
def get_supply_management_options(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_supply_entity_ids = resolve_accessible_supply_entity_ids(payload, session.username, session.group)
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "user": {
            "username": session.username,
            "group": session.group,
            "unit": session.unit,
        },
        "supply_entities": _serialize_supply_entity_options(payload, accessible_supply_entity_ids),
        "section_1s": _serialize_section_1_options(payload, accessible_section_1_ids),
        "pipe_models": _serialize_pipe_options(payload),
        "fitting_config": payload.get("fitting_config") or {},
        "show_date": get_configured_show_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "current_supply_entity_ids": sorted(accessible_supply_entity_ids),
    }


@router.post("/supply-management/custom-entities", summary="快速添加/持久化自定义供给主体")
def create_custom_supply_entity(
    payload: CustomSupplyEntityPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    if session.group not in ("Global_admin", "tube_global_viewer", "tube_supplier_admin"):
        raise HTTPException(status_code=403, detail="仅全局管理员或供给方管理员可添加自定义供给主体")

    raw_name = str(payload.entity_name or "").strip()
    if not raw_name:
        raise HTTPException(status_code=422, detail="自定义供给主体名称不能为空")

    config = load_tube_config()
    supply_entities = config.get("supply_entities") or []

    for item in supply_entities:
        e_id = str(item.get("entity_id") or "").strip()
        e_name = str(item.get("entity_name") or "").strip()
        if raw_name in (e_id, e_name):
            return {
                "ok": True,
                "created": False,
                "message": "已存在相同名称的供给主体",
                "entity": item,
            }

    existing_codes = [str(item.get("code") or "") for item in supply_entities]
    max_seq = 0
    for c in existing_codes:
        if c.startswith("CUST_"):
            try:
                max_seq = max(max_seq, int(c.split("CUST_")[-1]))
            except ValueError:
                pass
    next_code = f"CUST_{max_seq + 1:02d}"
    new_entity = {
        "entity_id": raw_name,
        "code": next_code,
        "entity_name": raw_name,
        "contact_name": str(payload.contact_name or "").strip(),
        "contact_phone": str(payload.contact_phone or "").strip(),
        "section_1_ids": [],
        "is_custom": True,
    }

    supply_entities.append(new_entity)
    config["supply_entities"] = supply_entities
    save_tube_config(config)

    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CREATE_CUSTOM_SUPPLY_ENTITY",
        action_desc=f"添加自定义供给主体: {raw_name}",
        resource_id=raw_name,
        before_value=None,
        after_value=new_entity,
        client_ip=_get_client_ip(request),
    )

    return {
        "ok": True,
        "created": True,
        "message": f"成功持久化保存自定义供给主体: {raw_name}",
        "entity": new_entity,
    }
@router.get("/supply-management/demand-summary", summary="读取供给侧需求与缺口汇总")
def get_supply_management_demand_summary(
    show_date: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    # 遵循用户指令：数据看板不受任何账号/标段隔离约束，全量呈现全盘大盘汇总数据
    all_demand_entities = get_config_list(payload, "demand_entities")
    accessible_section_1_ids = {
        str(item.get("section_1_id") or "").strip()
        for item in all_demand_entities
        if str(item.get("section_1_id") or "").strip()
    }
    section_1_name_map = _build_section_1_name_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    parsed_show_date = None
    if show_date:
        try:
            parsed_show_date = date.fromisoformat(str(show_date).strip())
        except Exception:
            parsed_show_date = None
    show_date_obj = parsed_show_date or get_configured_show_date(payload)
    plan_dates = build_plan_dates(show_date_obj + timedelta(days=1))
    plan_total_map = list_plan_totals(plan_dates)
    delivery_aggregate_map = list_delivery_aggregates()
    arrival_aggregate_map = list_arrival_aggregates(show_date_obj.isoformat())
    usage_total_map = list_usage_totals(show_date_obj.isoformat())

    rows: List[Dict[str, Any]] = []
    for section_1 in get_config_list(payload, "demand_entities"):
        section_1_id = str(section_1.get("section_1_id") or "").strip()
        if not section_1_id or section_1_id not in accessible_section_1_ids:
            continue
        section_1_baseline_preset_map = _build_baseline_preset_map(payload, section_1_id)
        
        all_model_ids_for_section = _resolve_section_1_sorted_pipe_model_ids(payload, section_1_id)
        added_set = set(all_model_ids_for_section)
        
        sec_prefix = f"{section_1_id}::"
        for map_item in (plan_total_map, delivery_aggregate_map, arrival_aggregate_map, usage_total_map):
            for k in map_item.keys():
                if k.startswith(sec_prefix):
                    pm_id = k.split("::", 1)[1]
                    if pm_id and pm_id not in added_set:
                        all_model_ids_for_section.append(pm_id)
                        added_set.add(pm_id)

        for pipe_model_id in all_model_ids_for_section:
            pipe_model = pipe_model_map.get(pipe_model_id) or {}
            key = f"{section_1_id}::{pipe_model_id}"
            baseline_row = section_1_baseline_preset_map.get(pipe_model_id) or {}
            plan_total_qty = float(plan_total_map.get(key, 0) or 0)
            delivery_aggregate = delivery_aggregate_map.get(key) or {}
            arrival_aggregate = arrival_aggregate_map.get(key) or {}
            usage_aggregate = usage_total_map.get(key) or {}
            pending_arrival_qty = float(delivery_aggregate.get("pending_arrival_qty", 0) or 0)
            pending_receive_qty = float(delivery_aggregate.get("pending_receive_qty", 0) or 0)
            pending_warehouse_qty = float(delivery_aggregate.get("pending_warehouse_qty", 0) or 0)
            completed_qty = float(delivery_aggregate.get("completed_qty", 0) or 0)
            total_shipped_qty = float(delivery_aggregate.get("total_shipped_qty", 0) or 0)
            total_arrived_qty = float(arrival_aggregate.get("total_arrived_qty", 0) or 0)
            total_usage_qty = float(usage_aggregate.get("total_usage_qty", 0) or 0)
            total_loss_qty = float(usage_aggregate.get("total_loss_qty", 0) or 0)
            section_1_inventory_qty = total_arrived_qty - total_usage_qty - total_loss_qty
            inbound_pipeline_qty = pending_arrival_qty
            net_gap_qty = max(plan_total_qty - inbound_pipeline_qty - section_1_inventory_qty, 0)
            # 统一硬缺口计算：未来三日计划 - 现场库存（由于使用量已做硬性强拦截校验，正常业务下库存永不为负；若异常负值发生，硬缺口将真实包含历史亏空补齐）
            hard_gap_qty = max(plan_total_qty - section_1_inventory_qty, 0.0)
            design_qty = float(baseline_row.get("design_qty", 0) or 0)
            purchase_plan_qty = float(baseline_row.get("purchase_plan_qty", 0) or 0)
            if (
                design_qty <= 0
                and purchase_plan_qty <= 0
                and plan_total_qty <= 0
                and inbound_pipeline_qty <= 0
                and section_1_inventory_qty <= 0
                and completed_qty <= 0
                and total_shipped_qty <= 0
            ):
                continue
            rows.append(
                {
                    "section_1_id": section_1_id,
                    "section_1_name": section_1_name_map.get(section_1_id, section_1_id),
                    "pipe_model_id": pipe_model_id,
                    "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                    "unit": pipe_model.get("unit") or "",
                    "design_qty": design_qty,
                    "purchase_plan_qty": purchase_plan_qty,
                    "future_plan_qty": plan_total_qty,
                    "pending_arrival_qty": pending_arrival_qty,
                    "pending_receive_qty": pending_receive_qty,
                    "pending_warehouse_qty": pending_warehouse_qty,
                    "completed_qty": completed_qty,
                    "total_shipped_qty": total_shipped_qty,
                    "total_arrived_qty": total_arrived_qty,
                    "total_usage_qty": total_usage_qty,
                    "total_loss_qty": total_loss_qty,
                    "section_1_inventory_qty": section_1_inventory_qty,
                    "inbound_pipeline_qty": inbound_pipeline_qty,
                    "net_gap_qty": net_gap_qty,
                    "hard_gap_qty": hard_gap_qty,
                    "remark": baseline_row.get("remark") or "",
                }
            )

    # 局部导入底层 DB 依赖，执行 KPI 指标的后端物理计算
    from sqlalchemy import text
    from backend.db.database_daily_report_25_26 import SessionLocal

    # 1. 查 OTD 的完成单与准时单数量（ status <> 'cancelled' 且 arrived_confirm_at 与 shipped_at 不为空）
    sql_otd = text(
        """
        SELECT 
            COUNT(*) AS total_completed,
            SUM(CASE WHEN arrived_confirm_at - shipped_at <= INTERVAL '24 hours' THEN 1 ELSE 0 END) AS on_time_count
        FROM tube.tube_delivery
        WHERE status <> 'cancelled'
          AND arrived_confirm_at IS NOT NULL
          AND shipped_at IS NOT NULL
        """
    )
    db_session = SessionLocal()
    completed_deliveries_count = 0
    on_time_count = 0
    try:
        otd_row = db_session.execute(sql_otd).first()
        if otd_row:
            completed_deliveries_count = int(otd_row[0]) if otd_row[0] is not None else 0
            on_time_count = int(otd_row[1]) if otd_row[1] is not None else 0
    except Exception as e:
        print(f"⚠️ 后端计算 OTD 时发生异常: {e}")
    finally:
        db_session.close()

    otd = round((on_time_count / completed_deliveries_count) * 100, 1) if completed_deliveries_count > 0 else 0.0

    # 2. 从已生成的 rows 中计算剩下的指标 (DOI, PCR, UCR, SSR)
    total_inv = sum(row["section_1_inventory_qty"] for row in rows)
    total_future_plan = sum(row["future_plan_qty"] for row in rows)
    daily_consume_plan = total_future_plan / 3.0 if total_future_plan > 0 else 0.0
    total_usage = sum(row["total_usage_qty"] for row in rows)
    total_arrived = sum(row["total_arrived_qty"] for row in rows)

    # 读取各工区的物理施工状态
    construction_status_map = {
        str(item.get("section_1_id") or "").strip(): str(item.get("construction_status") or "").strip()
        for item in get_config_list(payload, "demand_entities")
        if str(item.get("section_1_id") or "").strip()
    }

    # 在建施工工区：状态为“施工中”或未特别标注的处于真正在建状态的工区集合（自动排除“未开工”、“暂停”或“完工”等非活跃在建状态）
    under_construction_set = {
        sec_id for sec_id, status in construction_status_map.items()
        if status in ("施工中", "在建", "")
    }

    # 活跃考核工区：处于在建状态且设计量大于0的站点的唯一集合
    active_section_1s = {
        row["section_1_id"] for row in rows 
        if row["design_qty"] > 0 and (row["section_1_id"] in under_construction_set)
    }
    # 提报计划工区：未来计划大于0的站点的唯一集合
    section_1s_with_plan = {row["section_1_id"] for row in rows if row["future_plan_qty"] > 0}
    submitted_section_1_count = len(section_1s_with_plan.intersection(active_section_1s))
    
    # 物理断料工区：硬缺口大于0的站点的唯一集合
    gap_section_1s = {row["section_1_id"] for row in rows if row["hard_gap_qty"] > 0}
    safe_section_1_count = len(active_section_1s - gap_section_1s)

    # 核心指标计算
    doi = round(total_inv / daily_consume_plan, 1) if daily_consume_plan > 0 else 0.0
    if daily_consume_plan <= 0:
        doi_score = 100.0 if total_inv > 0 else 0.0
    elif doi >= 3.0:
        doi_score = 100.0
    elif 1.0 <= doi < 3.0:
        doi_score = round(60.0 + (doi - 1.0) / 2.0 * 40.0, 1)
    else:
        doi_score = round(max(0.0, doi * 60.0), 1)

    pcr = round((submitted_section_1_count / len(active_section_1s)) * 100, 1) if len(active_section_1s) > 0 else 0.0
    ucr = round((total_usage / total_arrived) * 100, 1) if total_arrived > 0 else 0.0
    ssr = round((safe_section_1_count / len(active_section_1s)) * 100, 1) if len(active_section_1s) > 0 else 0.0

    metrics = {
        "otd": otd,
        "onTimeCount": on_time_count,
        "completedDeliveriesCount": completed_deliveries_count,
        
        "doi": doi,
        "doiScore": doi_score,
        "totalInv": total_inv,
        "dailyConsumePlan": daily_consume_plan,
        "totalFuturePlan": total_future_plan,
        
        "pcr": pcr,
        "submitted_section_1_count": submitted_section_1_count,
        "active_section_1_count": len(active_section_1s),
        "unstarted_section_1_count": len({sec_id for sec_id, status in construction_status_map.items() if status == "未开工"}),
        
        "ucr": ucr,
        "totalUsage": total_usage,
        "totalArrived": total_arrived,
        
        "ssr": ssr,
        "safe_section_1_count": safe_section_1_count
    }

    rows.sort(key=lambda item: (item["section_1_id"], item["pipe_model_id"]))
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "plan_dates": [item.isoformat() for item in plan_dates],
        "rows": rows,
        "metrics": metrics,
    }


@router.get("/supply-management/deliveries", summary="读取供给侧发货记录")
def get_supply_management_deliveries(
    section_1_id: str = "",
    status: str = "",
    supply_entity_id: str = "",
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_supply_entity_ids = resolve_accessible_supply_entity_ids(payload, session.username, session.group)
    if not accessible_supply_entity_ids:
        return {"ok": True, "project_key": PROJECT_KEY, "rows": []}

    requested_supply_entity_id = str(supply_entity_id or "").strip()
    if requested_supply_entity_id:
        if requested_supply_entity_id not in accessible_supply_entity_ids and not _is_admin_or_supplier_admin(session.group):
            raise HTTPException(status_code=403, detail="当前账号无该供给主体的访问权限")
        target_supply_entity_ids = [requested_supply_entity_id]
    else:
        target_supply_entity_ids = sorted(accessible_supply_entity_ids)

    rows = list_delivery_records(
        supply_entity_ids=target_supply_entity_ids,
        section_1_id=section_1_id,
        status=status,
    )
    _decorate_delivery_rows(payload, rows)

    return {"ok": True, "project_key": PROJECT_KEY, "rows": rows}


@router.post("/supply-management/deliveries", summary="新增供给侧发货记录")
def create_supply_management_delivery(
    payload: SupplyDeliveryCreatePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_supply_entity_ids = resolve_accessible_supply_entity_ids(config_payload, session.username, session.group)
    if payload.supply_entity_id not in accessible_supply_entity_ids and not _is_admin_or_supplier_admin(session.group):
        raise HTTPException(status_code=403, detail="当前账号无该供给主体的发货权限")
    created = _create_supply_delivery_entry(
        config_payload=config_payload,
        session=session,
        supply_entity_id=payload.supply_entity_id,
        section_1_id=payload.section_1_id,
        pipe_model_id=payload.pipe_model_id,
        shipped_qty=payload.shipped_qty,
        shipped_at=payload.shipped_at,
        ship_contact_name=payload.ship_contact_name,
        ship_contact_phone=payload.ship_contact_phone,
        ship_remark=payload.ship_remark,
        vehicle_plate_no=payload.vehicle_plate_no,
        requested_shipment_no=payload.shipment_no,
    )
    
    # 记录操作审计日志
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CREATE_DELIVERY",
        action_desc=f"创建发货单: 订单号 {created['order_no']} (车次: {created['shipment_no']}, 车牌: {created['vehicle_plate_no']})，规格 {payload.pipe_model_id}，发货 {payload.shipped_qty} 米",
        resource_id=str(created["delivery_id"]),
        before_value=None,
        after_value={
            "delivery_id": created["delivery_id"],
            "order_no": created["order_no"],
            "shipment_no": created["shipment_no"],
            "vehicle_plate_no": created["vehicle_plate_no"],
            "supply_entity_id": payload.supply_entity_id,
            "section_1_id": payload.section_1_id,
            "pipe_model_id": payload.pipe_model_id,
            "shipped_qty": payload.shipped_qty,
            "shipped_at": payload.shipped_at.isoformat() if payload.shipped_at else None,
            "ship_contact_name": payload.ship_contact_name,
            "ship_contact_phone": payload.ship_contact_phone,
            "ship_remark": payload.ship_remark,
        },
        client_ip=_get_client_ip(request)
    )
    
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        **created,
    }


@router.post("/supply-management/deliveries/batch", summary="批量新增供给侧发货记录")
def create_supply_management_delivery_batch(
    payload: SupplyDeliveryBatchCreatePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_supply_entity_ids = resolve_accessible_supply_entity_ids(config_payload, session.username, session.group)
    if payload.supply_entity_id not in accessible_supply_entity_ids and not _is_admin_or_supplier_admin(session.group):
        raise HTTPException(status_code=403, detail="当前账号无该供给主体的发货权限")
    items = list(payload.items or [])
    if not items:
        raise HTTPException(status_code=422, detail="至少需要一条发货明细。")
    shared_shipment_no = str(payload.shipment_no or "").strip().upper()
    created_rows: List[Dict[str, Any]] = []
    current_shipment_no = shared_shipment_no
    for item in items:
        created = _create_supply_delivery_entry(
            config_payload=config_payload,
            session=session,
            supply_entity_id=payload.supply_entity_id,
            section_1_id=item.section_1_id,
            pipe_model_id=item.pipe_model_id,
            shipped_qty=item.shipped_qty,
            shipped_at=payload.shipped_at,
            ship_contact_name=payload.ship_contact_name,
            ship_contact_phone=payload.ship_contact_phone,
            ship_remark=item.ship_remark,
            vehicle_plate_no=payload.vehicle_plate_no,
            requested_shipment_no=current_shipment_no,
        )
        if not current_shipment_no:
            current_shipment_no = created["shipment_no"]
        created_rows.append(created)
        
        # 批量发货记录明细日志
        save_operation_log(
            operator=session.username,
            operator_group=session.group,
            action_type="CREATE_DELIVERY",
            action_desc=f"批量创建发货单: 订单号 {created['order_no']} (车次: {created['shipment_no']}, 车牌: {payload.vehicle_plate_no})，规格 {item.pipe_model_id}，发货 {item.shipped_qty} 米",
            resource_id=str(created["delivery_id"]),
            before_value=None,
            after_value={
                "delivery_id": created["delivery_id"],
                "order_no": created["order_no"],
                "shipment_no": created["shipment_no"],
                "vehicle_plate_no": payload.vehicle_plate_no,
                "supply_entity_id": payload.supply_entity_id,
                "section_1_id": item.section_1_id,
                "pipe_model_id": item.pipe_model_id,
                "shipped_qty": item.shipped_qty,
                "shipped_at": payload.shipped_at.isoformat() if payload.shipped_at else None,
                "ship_contact_name": payload.ship_contact_name,
                "ship_contact_phone": payload.ship_contact_phone,
                "ship_remark": item.ship_remark,
            },
            client_ip=_get_client_ip(request)
        )
        
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "shipment_no": current_shipment_no,
        "vehicle_plate_no": created_rows[0].get("vehicle_plate_no", "") if created_rows else "",
        "shipment_reused": bool(shared_shipment_no),
        "rows": created_rows,
    }


@router.post("/supply-management/deliveries/{delivery_id}/cancel", summary="撤销供给侧发货记录")
def cancel_supply_management_delivery(
    delivery_id: int,
    payload: SupplyDeliveryCancelPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_supply_entity_ids = resolve_accessible_supply_entity_ids(config_payload, session.username, session.group)
    
    before_val = get_delivery_record_basic(delivery_id)
    allowed_ids = set(accessible_supply_entity_ids)
    if _is_admin_or_supplier_admin(session.group) and before_val.get("supply_entity_id"):
        allowed_ids.add(before_val["supply_entity_id"])
    
    cancel_delivery_record(
        delivery_id=delivery_id,
        allowed_supply_entity_ids=sorted(allowed_ids),
        operator=session.username,
        cancel_reason=payload.cancel_reason,
    )
    
    after_val = get_delivery_record_basic(delivery_id)
    
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CANCEL_DELIVERY",
        action_desc=f"撤销发货单: 订单号 {before_val.get('order_no')}，原因: {payload.cancel_reason}",
        resource_id=str(delivery_id),
        before_value=_to_json_serializable(before_val),
        after_value=_to_json_serializable(after_val),
        client_ip=_get_client_ip(request)
    )
    
    return {"ok": True, "project_key": PROJECT_KEY, "delivery_id": delivery_id}


@router.post("/supply-management/deliveries/{delivery_id}/super-update", summary="[超级管理员] 强力覆写更新发货单任意信息")
def super_update_supply_management_delivery(
    delivery_id: int,
    payload: SuperUpdateDeliveryPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    group_lower = str(session.group or "").strip().lower()
    if group_lower != "global_admin":
        raise HTTPException(status_code=403, detail="此接口为 Global_admin 超级管理员专属数据订正通道,普通角色无权访问")
    
    before_val = get_delivery_record_basic(delivery_id)
    
    super_update_delivery_record(
        delivery_id=delivery_id,
        section_1_id=payload.section_1_id,
        pipe_model_id=payload.pipe_model_id,
        shipped_qty=payload.shipped_qty,
        shipped_at=payload.shipped_at,
        vehicle_plate_no=payload.vehicle_plate_no,
        ship_remark=payload.ship_remark,
        status=payload.status,
        order_no=payload.order_no,
        shipment_no=payload.shipment_no,
        arrived_qty=payload.arrived_qty,
        received_qty=payload.received_qty,
        arrived_confirm_at=payload.arrived_confirm_at,
        received_confirm_at=payload.received_confirm_at,
        warehouse_confirm_at=payload.warehouse_confirm_at,
        operator=session.username,
    )
    
    after_val = get_delivery_record_basic(delivery_id)
    
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="SUPER_UPDATE_DELIVERY",
        action_desc=f"超级管理员强力覆写发货单: 订单号 {before_val.get('order_no')}",
        resource_id=str(delivery_id),
        before_value=_to_json_serializable(before_val),
        after_value=_to_json_serializable(after_val),
        client_ip=_get_client_ip(request)
    )
    
    return {
        "ok": True,
        "detail": "发货记录已由超级管理员强力重写保存",
    }



@router.get("/warehouse-management/options", summary="读取库管页选项")
def get_warehouse_management_options(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_warehouse_access(session)
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    if not accessible_section_1_ids and session.group == "tube_warehouse_keeper":
        accessible_section_1_ids = set(_build_section_1_name_map(payload).keys())

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "user": {
            "username": session.username,
            "group": session.group,
            "unit": session.unit,
        },
        "section_1s": _serialize_section_1_options(payload, accessible_section_1_ids),
        "pipe_models": _serialize_pipe_options(payload),
        "supply_entities": _serialize_all_supply_entity_options(payload),
        "fitting_config": payload.get("fitting_config") or {},
        "show_date": get_configured_show_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "delivery_status_options": [
            {"value": "pending_arrival", "label": "已发货待到货"},
            {"value": "pending_receive", "label": "已到货待接收"},
            {"value": "pending_warehouse", "label": "已接收待库管"},
            {"value": "completed", "label": "已完成"},
            {"value": "cancelled", "label": "已撤销"},
        ],
    }


@router.get("/warehouse-management/deliveries", summary="读取库管页发货记录")
def get_warehouse_management_deliveries(
    section_1_id: str = "",
    status: str = "",
    supply_entity_id: str = "",
    pipe_model_id: str = "",
    shipment_no: str = "",
    order_no: str = "",
    vehicle_plate_no: str = "",
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_warehouse_access(session)
    payload = load_tube_config()
    all_supply_entity_ids = [item.get("entity_id") for item in get_config_list(payload, "supply_entities")]
    
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    if not accessible_section_1_ids and session.group == "tube_warehouse_keeper":
        accessible_section_1_ids = set(_build_section_1_name_map(payload).keys())

    # 逗号分隔解析多选值
    selected_section_1s = {s.strip() for s in section_1_id.split(",") if s.strip()} if section_1_id else set()
    selected_statuses = {s.strip() for s in status.split(",") if s.strip()} if status else set()
    selected_supply_entities = {s.strip() for s in supply_entity_id.split(",") if s.strip()} if supply_entity_id else set()
    selected_pipe_models = {_normalize_pipe_model_id(s) for s in pipe_model_id.split(",") if s.strip()} if pipe_model_id else set()

    # 在 SQL 层面，我们不传入单选 section_1_id 和 status，以便我们在 Python 内存中对大盘记录直接做高性能多选集合检索
    rows = list_delivery_records(
        supply_entity_ids=all_supply_entity_ids,
        section_1_id="",
        status="",
    )
    _decorate_delivery_rows(payload, rows)
    
    normalized_shipment_no = str(shipment_no or "").strip().upper()
    normalized_order_no = str(order_no or "").strip().upper()
    normalized_vehicle_plate_no = str(vehicle_plate_no or "").strip().upper()
    
    filtered_rows: List[Dict[str, Any]] = []
    for row in rows:
        sec_id = str(row.get("section_1_id") or "").strip()

        # 核心拦截：账号分管标段范围边界过滤
        if accessible_section_1_ids and sec_id not in accessible_section_1_ids:
            continue
        if selected_supply_entities and row["supply_entity_id"] not in selected_supply_entities:
            continue
        if selected_pipe_models and _normalize_pipe_model_id(row["pipe_model_id"]) not in selected_pipe_models:
            continue
        if selected_section_1s and sec_id not in selected_section_1s:
            continue
        if selected_statuses and row["status"] not in selected_statuses:
            continue
        if normalized_shipment_no and str(row.get("shipment_no") or "").strip().upper() != normalized_shipment_no:
            continue
        if normalized_order_no and normalized_order_no not in str(row.get("order_no") or row.get("delivery_code") or "").strip().upper():
            continue
        if normalized_vehicle_plate_no and normalized_vehicle_plate_no not in str(row.get("vehicle_plate_no") or "").strip().upper():
            continue
        filtered_rows.append(row)
    return {"ok": True, "project_key": PROJECT_KEY, "rows": filtered_rows}



@router.post("/warehouse-management/deliveries/{delivery_id}/warehouse", summary="库管确认手续闭环")
def confirm_warehouse_delivery_warehouse(
    delivery_id: int,
    payload: WarehouseConfirmPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_warehouse_access(session)
    if str(session.group or "").strip() == "tube_global_viewer":
        raise HTTPException(status_code=403, detail="只读账号无权提交数据")
    before_val = get_delivery_record_basic(delivery_id)
    update_delivery_warehouse_record(
        delivery_id=delivery_id,
        operator=session.username,
        remark=payload.remark,
    )
    after_val = get_delivery_record_basic(delivery_id)
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CONFIRM_WAREHOUSE",
        action_desc=f"库管确认订单手续闭环: 订单号 {before_val.get('order_no')}",
        resource_id=str(delivery_id),
        before_value=_to_json_serializable(before_val),
        after_value=_to_json_serializable(after_val),
        client_ip=_get_client_ip(request)
    )
    return {"ok": True, "project_key": PROJECT_KEY, "delivery_id": delivery_id}


@router.get("/demand-management/baseline", summary="读取需求侧基准数据")
def get_demand_management_baseline(
    section_1_id: str,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    _ensure_section_1_access(section_1_id, accessible_section_1_ids)

    section_1_name_map = _build_section_1_name_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    baseline_preset_map = _build_baseline_preset_map(payload, section_1_id)
    model_ids = _resolve_section_1_sorted_pipe_model_ids(payload, section_1_id)

    rows: List[Dict[str, Any]] = []
    for pipe_model_id in model_ids:
        pipe_model = pipe_model_map.get(pipe_model_id) or {}
        baseline = baseline_preset_map.get(pipe_model_id) or {}
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "unit": pipe_model.get("unit") or "米",
                "design_qty": baseline.get("design_qty"),
                "purchase_plan_qty": baseline.get("purchase_plan_qty"),
                "remark": baseline.get("remark") or "",
            }
        )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1": {
            "section_1_id": section_1_id,
            "section_1_name": section_1_name_map.get(section_1_id, section_1_id),
        },
        "rows": rows,
    }


@router.get("/demand-management/plan-matrix", summary="读取需求侧三日计划矩阵")
def get_demand_management_plan_matrix(
    section_1_id: str,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    _ensure_section_1_access(section_1_id, accessible_section_1_ids)

    plan_dates = build_plan_dates(get_configured_plan_start_date(payload))
    pipe_model_map = _build_pipe_model_map(payload)
    matrix = list_plan_records(section_1_id, plan_dates)
    
    strict_planning_flow_control = bool(payload.get("strict_planning_flow_control", True))
    usage_date = get_usage_collection_date(payload)
    usage_map = list_usage_records(section_1_id, usage_date)
    is_usage_submitted = len(usage_map) > 0
    
    show_date = get_configured_show_date(payload)
    delivery_aggregate_map = list_delivery_aggregates()
    arrival_aggregate_map = list_arrival_aggregates(show_date.isoformat())
    usage_total_map = list_usage_totals(show_date.isoformat())
    
    model_ids = _resolve_section_1_sorted_pipe_model_ids(payload, section_1_id)
    rows: List[Dict[str, Any]] = []
    for pipe_model_id in model_ids:
        pipe_model = pipe_model_map.get(pipe_model_id) or {}
        cell_values: Dict[str, Any] = {}
        cell_remarks: Dict[str, str] = {}
        for plan_date in plan_dates:
            key = plan_date.isoformat()
            record = matrix.get(f"{pipe_model_id}::{key}")
            cell_values[key] = float(record["plan_qty"]) if record and record.get("plan_qty") is not None else 0
            cell_remarks[key] = record.get("remark") if record else ""
            
        agg_key = f"{section_1_id}::{pipe_model_id}"
        delivery_aggregate = delivery_aggregate_map.get(agg_key) or {}
        arrival_aggregate = arrival_aggregate_map.get(agg_key) or {}
        usage_aggregate = usage_total_map.get(agg_key) or {}
        
        pending_arrival_qty = float(delivery_aggregate.get("pending_arrival_qty", 0) or 0)
        pending_receive_qty = float(delivery_aggregate.get("pending_receive_qty", 0) or 0)
        
        total_arrived_qty = float(arrival_aggregate.get("total_arrived_qty", 0) or 0)
        total_usage_qty = float(usage_aggregate.get("total_usage_qty", 0) or 0)
        total_loss_qty = float(usage_aggregate.get("total_loss_qty", 0) or 0)
        
        # 允许库存为负数，真实暴露管理问题，不强制锁死为 0
        section_1_inventory_qty = total_arrived_qty - total_usage_qty - total_loss_qty
        inbound_pipeline_qty = pending_arrival_qty
        
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "unit": pipe_model.get("unit") or "米",
                "section_1_inventory_qty": section_1_inventory_qty,
                "inbound_pipeline_qty": inbound_pipeline_qty,
                "values": cell_values,
                "remarks": cell_remarks,
            }
        )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1": {
            "section_1_id": section_1_id,
            "section_1_name": _build_section_1_name_map(payload).get(section_1_id, section_1_id),
        },
        "plan_dates": [item.isoformat() for item in plan_dates],
        "strict_planning_flow_control": strict_planning_flow_control,
        "is_usage_submitted": is_usage_submitted,
        "rows": rows,
    }


@router.post("/demand-management/plan-matrix", summary="保存需求侧三日计划矩阵")
def save_demand_management_plan_matrix(
    payload: DemandPlanSavePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(config_payload, session.username, session.group)
    _ensure_section_1_access(payload.section_1_id, accessible_section_1_ids)
 
    # 严格流程顺序锁后台强拦截
    strict_planning_flow_control = bool(config_payload.get("strict_planning_flow_control", True))
    if strict_planning_flow_control:
        usage_date = get_usage_collection_date(config_payload)
        usage_map = list_usage_records(payload.section_1_id, usage_date)
        if len(usage_map) == 0:
            plan_dates = build_plan_dates(get_configured_plan_start_date(config_payload))
            if len(plan_dates) >= 3:
                tail_date_str = plan_dates[2].isoformat()
                for rec in payload.records:
                    if rec.plan_date.isoformat() == tail_date_str and rec.plan_qty > 0:
                        raise HTTPException(
                            status_code=400,
                            detail="🚨 填报被顺序锁阻断：当前前日实际消耗尚未结清上报！请先返回完成消耗上报，再填写并提交第三日计划量。"
                        )
 
    # 获取修改前快照
    plan_dates_list = [item.plan_date for item in payload.records]
    before_records = list_plan_records(payload.section_1_id, plan_dates_list)
    before_serialized = {}
    for k, v in before_records.items():
        before_serialized[k] = {
            "plan_qty": float(v.get("plan_qty", 0) or 0),
            "remark": v.get("remark") or ""
        }
 
    saved_count = save_plan_records(
        section_1_id=payload.section_1_id,
        records=[item.model_dump() for item in payload.records],
        operator=session.username,
    )
 
    # 获取修改后快照
    after_records = list_plan_records(payload.section_1_id, plan_dates_list)
    after_serialized = {}
    for k, v in after_records.items():
        after_serialized[k] = {
            "plan_qty": float(v.get("plan_qty", 0) or 0),
            "remark": v.get("remark") or ""
        }
 
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="SAVE_PLAN",
        action_desc=f"更新需求主体【{payload.section_1_id}】三日计划量，共计 {saved_count} 条记录",
        resource_id=payload.section_1_id,
        before_value=before_serialized,
        after_value=after_serialized,
        client_ip=_get_client_ip(request)
    )
 
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1_id": payload.section_1_id,
        "saved_count": saved_count,
    }


@router.get("/demand-management/usage-sheet", summary="读取需求侧实际使用量表")
def get_demand_management_usage_sheet(
    section_1_id: str,
    usage_date: date,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    _ensure_section_1_access(section_1_id, accessible_section_1_ids)
 
    pipe_model_map = _build_pipe_model_map(payload)
    usage_map = list_usage_records(section_1_id, usage_date)
    model_ids = _resolve_section_1_sorted_pipe_model_ids(payload, section_1_id)
    rows: List[Dict[str, Any]] = []
    for pipe_model_id in model_ids:
        pipe_model = pipe_model_map.get(pipe_model_id) or {}
        usage = usage_map.get(pipe_model_id) or {}
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "unit": pipe_model.get("unit") or "米",
                "usage_qty": float(usage.get("usage_qty", 0) or 0),
                "loss_qty": float(usage.get("loss_qty", 0) or 0),
                "remark": usage.get("remark") or "",
            }
        )
 
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1": {
            "section_1_id": section_1_id,
            "section_1_name": _build_section_1_name_map(payload).get(section_1_id, section_1_id),
        },
        "usage_date": usage_date.isoformat(),
        "rows": rows,
    }
 
 
@router.post("/demand-management/usage-sheet", summary="保存需求侧实际使用量表")
def save_demand_management_usage_sheet(
    payload: DemandUsageSavePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(config_payload, session.username, session.group)
    _ensure_section_1_access(payload.section_1_id, accessible_section_1_ids)
 
    # 获取修改前快照
    before_usages = list_usage_records(payload.section_1_id, payload.usage_date)
    before_serialized = {}
    for k, v in before_usages.items():
        before_serialized[k] = {
            "usage_qty": float(v.get("usage_qty", 0) or 0),
            "loss_qty": float(v.get("loss_qty", 0) or 0),
            "remark": v.get("remark") or ""
        }
 
    saved_count = save_usage_records(
        section_1_id=payload.section_1_id,
        usage_date=payload.usage_date,
        records=[item.model_dump() for item in payload.records],
        operator=session.username,
    )
 
    # 获取修改后快照
    after_usages = list_usage_records(payload.section_1_id, payload.usage_date)
    after_serialized = {}
    for k, v in after_usages.items():
        after_serialized[k] = {
            "usage_qty": float(v.get("usage_qty", 0) or 0),
            "loss_qty": float(v.get("loss_qty", 0) or 0),
            "remark": v.get("remark") or ""
        }
 
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="SUBMIT_USAGE",
        action_desc=f"上报施工使用与损耗量: 需求主体【{payload.section_1_id}】，消耗日期 {payload.usage_date.isoformat()}",
        resource_id=payload.section_1_id,
        before_value=before_serialized,
        after_value=after_serialized,
        client_ip=_get_client_ip(request)
    )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1_id": payload.section_1_id,
        "usage_date": payload.usage_date.isoformat(),
        "saved_count": saved_count,
    }


@router.post("/demand-management/submission", summary="提交填报完成状态")
def submit_demand_management_section_1_status(
    payload: DemandSection1SubmissionPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(config_payload, session.username, session.group)
    _ensure_section_1_access(payload.section_1_id, accessible_section_1_ids)
 
    section_1_name_map = _build_section_1_name_map(config_payload)
    plan_start_date = get_configured_plan_start_date(config_payload)
    show_date = get_configured_show_date(config_payload)
    usage_collection_date = get_usage_collection_date(config_payload)
    current_status = load_section_1_submission_status()
    latest_submissions = _normalize_submission_rows(current_status.get("latest_submissions"))
    history_submissions = _normalize_submission_rows(current_status.get("history_submissions"))
 
    existing_latest: Optional[Dict[str, Any]] = None
    next_latest_submissions: List[Dict[str, Any]] = []
    for item in latest_submissions:
        if str(item.get("section_1_id") or "").strip() == payload.section_1_id:
            existing_latest = item
            continue
        next_latest_submissions.append(item)
 
    if existing_latest:
        history_submissions.insert(0, existing_latest)
 
    submission_record = {
        "section_1_id": payload.section_1_id,
        "section_1_name": section_1_name_map.get(payload.section_1_id, payload.section_1_id),
        "data_submit_date": plan_start_date.isoformat(),
        "plan_start_date": plan_start_date.isoformat(),
        "show_date": show_date.isoformat(),
        "usage_date": usage_collection_date.isoformat(),
        "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "submitted_by": session.username,
        "submitted_group": session.group,
        "remark": payload.remark or "",
    }
    next_latest_submissions.append(submission_record)
    next_latest_submissions.sort(key=lambda item: str(item.get("section_1_id") or ""))
 
    save_section_1_submission_status(
        {
            "latest_submissions": next_latest_submissions,
            "history_submissions": history_submissions,
        }
    )
 
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="SUBMIT_STATUS",
        action_desc=f"确认提交填报完成状态: 需求主体【{payload.section_1_id}】，计划启用日期 {plan_start_date.isoformat()}，实际消耗日期 {usage_collection_date.isoformat()}",
        resource_id=payload.section_1_id,
        before_value=existing_latest,
        after_value=submission_record,
        client_ip=_get_client_ip(request)
    )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1_id": payload.section_1_id,
        "submission": submission_record,
        "latest_submission_count": len(next_latest_submissions),
        "history_submission_count": len(history_submissions),
    }


@router.get("/demand-management/pending-arrivals", summary="读取待确认到货记录")
def get_demand_management_pending_arrivals(
    section_1_id: str,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    _ensure_section_1_access(section_1_id, accessible_section_1_ids)

    rows = list_pending_arrivals(section_1_id)
    _decorate_delivery_rows(payload, rows)
    section_1_name_map = _build_section_1_name_map(payload)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1": {
            "section_1_id": section_1_id,
            "section_1_name": section_1_name_map.get(section_1_id, section_1_id),
        },
        "rows": rows,
    }


@router.get("/demand-management/logistics-records", summary="读取需求侧物流确认记录")
def get_demand_management_logistics_records(
    section_1_id: str,
    order_no: str = "",
    shipment_no: str = "",
    pipe_model_id: str = "",
    shipped_date: str = "",
    arrived_date: str = "",
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    _ensure_section_1_access(section_1_id, accessible_section_1_ids)

    all_supply_entity_ids = [item.get("entity_id") for item in get_config_list(payload, "supply_entities")]
    rows = list_delivery_records(
        supply_entity_ids=all_supply_entity_ids,
        section_1_id=section_1_id,
        status="",
    )
    _decorate_delivery_rows(payload, rows)
    filtered_rows = [
        row
        for row in rows
        if row.get("section_1_id") == section_1_id and row.get("status") in {"pending_arrival", "pending_receive", "pending_warehouse", "pending_diff_approve", "completed"}
    ]
    normalized_order_no = str(order_no or "").strip().upper()
    normalized_shipment_no = str(shipment_no or "").strip().upper()
    normalized_pipe_model_id = _normalize_pipe_model_id(pipe_model_id)
    normalized_shipped_date = str(shipped_date or "").strip()
    normalized_arrived_date = str(arrived_date or "").strip()
    if normalized_order_no:
        filtered_rows = [
            row
            for row in filtered_rows
            if normalized_order_no in str(row.get("order_no") or row.get("delivery_code") or "").strip().upper()
        ]
    if normalized_shipment_no:
        filtered_rows = [
            row for row in filtered_rows if str(row.get("shipment_no") or "").strip().upper() == normalized_shipment_no
        ]
    if normalized_pipe_model_id:
        filtered_rows = [
            row for row in filtered_rows if _normalize_pipe_model_id(row.get("pipe_model_id")) == normalized_pipe_model_id
        ]
    if normalized_shipped_date:
        filtered_rows = [
            row for row in filtered_rows if str(row.get("shipped_at") or "").strip()[:10] == normalized_shipped_date
        ]
    if normalized_arrived_date:
        filtered_rows = [
            row for row in filtered_rows if str(row.get("arrived_confirm_at") or "").strip()[:10] == normalized_arrived_date
        ]
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section_1": {
            "section_1_id": section_1_id,
            "section_1_name": _build_section_1_name_map(payload).get(section_1_id, section_1_id),
        },
        "rows": filtered_rows,
    }


def _ensure_demand_arrival_access(session: AuthSession) -> None:
    group = str(session.group or "").strip()
    if group not in {"Global_admin", "tube_site_manager"}:
        raise HTTPException(status_code=403, detail="当前账号无到货确认权限")


def _ensure_demand_receipt_access(session: AuthSession) -> None:
    group = str(session.group or "").strip()
    if group not in {"Global_admin", "tube_construction_unit"}:
        raise HTTPException(status_code=403, detail="当前账号无施工接收权限")


@router.post("/demand-management/deliveries/{delivery_id}/arrival", summary="需求侧确认到货")
def confirm_demand_management_delivery_arrival(
    delivery_id: int,
    payload: WarehouseArrivalConfirmPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_demand_arrival_access(session)
    delivery = get_delivery_record_basic(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail=f"发货记录不存在：{delivery_id}")
    accessible_section_1_ids = resolve_accessible_section_1_ids(load_tube_config(), session.username, session.group)
    _ensure_section_1_access(delivery["section_1_id"], accessible_section_1_ids)
    
    before_val = _to_json_serializable(delivery)
    
    update_delivery_arrival_record(
        delivery_id=delivery_id,
        operator=session.username,
        arrived_qty=payload.arrived_qty,
        remark=payload.remark,
    )
    
    after_val = _to_json_serializable(get_delivery_record_basic(delivery_id))
    
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CONFIRM_ARRIVAL",
        action_desc=f"确认到货: 订单号 {delivery.get('order_no')} (到货 {payload.arrived_qty} 米)",
        resource_id=str(delivery_id),
        before_value=before_val,
        after_value=after_val,
        client_ip=_get_client_ip(request)
    )
    
    return {"ok": True, "project_key": PROJECT_KEY, "delivery_id": delivery_id}


@router.post("/demand-management/deliveries/{delivery_id}/receipt", summary="需求侧确认施工接收")
def confirm_demand_management_delivery_receipt(
    delivery_id: int,
    payload: WarehouseReceiptConfirmPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_demand_receipt_access(session)
    delivery = get_delivery_record_basic(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail=f"发货记录不存在：{delivery_id}")
    accessible_section_1_ids = resolve_accessible_section_1_ids(load_tube_config(), session.username, session.group)
    _ensure_section_1_access(delivery["section_1_id"], accessible_section_1_ids)
    
    before_val = _to_json_serializable(delivery)
    
    new_status = update_delivery_receipt_record(
        delivery_id=delivery_id,
        operator=session.username,
        received_qty=payload.received_qty,
        remark=payload.remark,
    )
    
    after_val = _to_json_serializable(get_delivery_record_basic(delivery_id))
    
    action_desc = (
        f"提交施工接收 (待差异审批): 订单号 {delivery.get('order_no')} (实收 {payload.received_qty} 米, 理由: {payload.remark})"
        if new_status == 'pending_diff_approve' else
        f"施工确认接收: 订单号 {delivery.get('order_no')} (实收 {payload.received_qty} 米)"
    )
    
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="CONFIRM_CONSTRUCTION",
        action_desc=action_desc,
        resource_id=str(delivery_id),
        before_value=before_val,
        after_value=after_val,
        client_ip=_get_client_ip(request)
    )
    
    return {"ok": True, "project_key": PROJECT_KEY, "delivery_id": delivery_id, "status": new_status}


@router.post("/demand-management/deliveries/{delivery_id}/diff-approve", summary="Site Manager差异审批")
def approve_delivery_difference(
    delivery_id: int,
    payload: DiffApprovePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_site_manager_access(session)
    delivery = get_delivery_record_basic(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail=f"发货记录不存在：{delivery_id}")
        
    accessible_section_1_ids = resolve_accessible_section_1_ids(load_tube_config(), session.username, session.group)
    _ensure_section_1_access(delivery["section_1_id"], accessible_section_1_ids)
    
    if delivery["status"] != 'pending_diff_approve':
        raise HTTPException(status_code=422, detail="该发货单不需要进行差异审批或已被审批")
        
    before_val = _to_json_serializable(delivery)
    
    arrived_qty = float(delivery["arrived_qty"] if delivery["arrived_qty"] is not None else delivery["shipped_qty"] or 0)
    final_received_qty = float(delivery["received_qty"]) if payload.approved else arrived_qty
    new_status = 'pending_warehouse'
    
    approve_remark = str(payload.remark or "").strip()
    if not payload.approved:
        approve_remark = f"[Site Manager驳回少接收，更正为确认到货量] {approve_remark}"
        
    sql_update = text(
        """
        UPDATE tube.tube_delivery
        SET
            received_qty = :received_qty,
            status = :new_status,
            diff_approve_by = :diff_approve_by,
            diff_approve_at = NOW(),
            diff_approve_remark = :diff_approve_remark,
            updated_by = :updated_by,
            updated_at = NOW()
        WHERE id = :delivery_id
        """
    )
    db_session = SessionLocal()
    try:
        db_session.execute(
            sql_update,
            {
                "delivery_id": int(delivery_id),
                "received_qty": final_received_qty,
                "new_status": new_status,
                "diff_approve_by": session.username,
                "diff_approve_remark": approve_remark,
                "updated_by": session.username,
            }
        )
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()
        
    after_val = _to_json_serializable(get_delivery_record_basic(delivery_id))
    
    action_desc = (
        f"Site Manager同意差异接收: 订单号 {delivery.get('order_no')} (实收确认 {final_received_qty} 米)"
        if payload.approved else
        f"Site Manager驳回差异接收: 订单号 {delivery.get('order_no')} (强制按到货量 {final_received_qty} 米接收)"
    )
    
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="APPROVE_DIFFERENCE",
        action_desc=action_desc,
        resource_id=str(delivery_id),
        before_value=before_val,
        after_value=after_val,
        client_ip=_get_client_ip(request)
    )
    
    return {
        "ok": True, 
        "project_key": PROJECT_KEY, 
        "delivery_id": delivery_id,
        "approved": payload.approved,
        "final_received_qty": final_received_qty
    }


@router.get("/global-management/config", summary="读取全局管理配置")
def get_global_management_config(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    payload = load_tube_config()
    submission_status = load_section_1_submission_status()
    amap_config_decrypted = get_configured_amap_config(payload)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "config": payload,
        "amap_config_decrypted": amap_config_decrypted,
        "show_date": get_configured_show_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "usage_collection_date": get_usage_collection_date(payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(payload),
        "submission_status_path": str(SUBMISSION_STATUS_PATH),
        "submission_status": submission_status,
    }


@router.post("/global-management/config", summary="保存全局管理配置")
def save_global_management_config(
    payload: TubeConfigSavePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    before_config = load_tube_config()
    save_tube_config(payload.config)
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="UPDATE_CONFIG",
        action_desc="保存全局管理配置（完整覆盖）",
        resource_id="global_config",
        before_value=before_config,
        after_value=payload.config,
        client_ip=_get_client_ip(request)
    )
    return {"ok": True, "project_key": PROJECT_KEY}


@router.post("/global-management/config-section", summary="保存全局管理配置区块")
def save_global_management_config_section(
    payload: TubeConfigSectionSavePayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    before_config = load_tube_config()
    before_section = before_config.get(payload.section)
    updated = _save_config_section(payload.section, payload.data)
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="UPDATE_CONFIG",
        action_desc=f"保存全局配置区块: {payload.section}",
        resource_id=payload.section,
        before_value={payload.section: before_section} if before_section is not None else None,
        after_value={payload.section: payload.data},
        client_ip=_get_client_ip(request)
    )
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "section": payload.section,
        "config": updated,
        "show_date": get_configured_show_date(updated).isoformat(),
        "plan_start_date": get_configured_plan_start_date(updated).isoformat(),
        "usage_collection_date": get_usage_collection_date(updated).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(updated),
    }


@router.get("/global-management/weather/config", summary="读取天气配置与统计行数")
def get_global_management_weather_config(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    stats = weather_service.get_weather_db_stats()
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        **stats
    }


@router.post("/global-management/weather/eval", summary="评估天气数据导入")
def evaluate_global_management_weather_import(
    payload: WeatherEvalPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    result = weather_service.evaluate_weather_import(payload.api_url)
    return result


@router.post("/global-management/weather/import", summary="物理导入天气数据")
def import_global_management_weather_data(
    payload: WeatherImportPayload,
    request: Request,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    stats_before = weather_service.get_weather_db_stats()
    result = weather_service.import_weather_data(payload.api_url)
    
    # 物理导入天气数据写审计日志
    save_operation_log(
        operator=session.username,
        operator_group=session.group,
        action_type="UPDATE_CONFIG",
        action_desc=f"物理拉取并覆盖导入天气数据，API 网址: {payload.api_url}",
        resource_id="weather_data",
        before_value={"daily_count": stats_before.get("daily_count"), "hourly_count": stats_before.get("hourly_count")},
        after_value=result,
        client_ip=_get_client_ip(request)
    )
    return result


def _to_json_serializable(snap: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not snap:
        return None
    res = {}
    for k, v in snap.items():
        if isinstance(v, (datetime, date)):
            res[k] = v.isoformat()
        else:
            res[k] = v
    return res


@router.get("/global-management/submission-logs", summary="读取主体数据提交记录")
def get_global_management_submission_logs(
    entity_type: Optional[str] = None,
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    group_lower = str(session.group or "").strip().lower()
    if group_lower not in {"global_admin", "tube_warehouse_admin", "tube_supplier_admin", "tube_demand_admin"}:
        raise HTTPException(status_code=403, detail="无权查看主体提交行为记录")
        
    offset = (page - 1) * limit
    result = query_submission_logs(
        entity_type=entity_type,
        action_type=action_type,
        operator=operator,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "total": result["total"],
        "page": page,
        "limit": limit,
        "latest_submitted_at": result.get("latest_submitted_at"),
        "recent_24h_count": result.get("recent_24h_count", 0),
        "demand_24h_count": result.get("demand_24h_count", 0),
        "supply_24h_count": result.get("supply_24h_count", 0),
        "rows": result["logs"]
    }


@router.get("/global-management/operation-logs", summary="读取操作审计日志")
def get_global_management_operation_logs(
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    group_lower = str(session.group or "").strip().lower()
    if group_lower not in {"global_admin", "tube_warehouse_admin"}:
        raise HTTPException(status_code=403, detail="无权查看系统操作审计日志")
        
    offset = (page - 1) * limit
    result = query_operation_logs(
        action_type=action_type,
        operator=operator,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "total": result["total"],
        "page": page,
        "limit": limit,
        "rows": result["logs"]
    }


import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/global-management/operation-logs/export", summary="导出操作审计日志")
def export_global_management_operation_logs(
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    session: AuthSession = Depends(get_current_session),
):
    group_lower = str(session.group or "").strip().lower()
    if group_lower not in {"global_admin", "tube_warehouse_admin"}:
        raise HTTPException(status_code=403, detail="无权导出系统操作审计日志")
        
    result = query_operation_logs(
        action_type=action_type,
        operator=operator,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0
    )
    
    logs = result["logs"]
    
    output = io.StringIO()
    # 写入 UTF-8 BOM 防止 Excel 乱码
    output.write('\ufeff')
    writer = csv.writer(output)
    
    writer.writerow(["时间", "操作人", "操作角色", "操作类型", "操作详情", "关联资源ID", "IP地址"])
    
    action_type_map = {
        "CREATE_DELIVERY": "新增发货单",
        "CANCEL_DELIVERY": "撤销发货",
        "CONFIRM_ARRIVAL": "确认到货",
        "CONFIRM_CONSTRUCTION": "施工接收",
        "CONFIRM_WAREHOUSE": "库管确认",
        "SAVE_PLAN": "更新三日计划",
        "SUBMIT_USAGE": "上报消耗损耗",
        "SUBMIT_STATUS": "提交填报状态",
        "UPDATE_CONFIG": "配置修改",
        "SUPER_UPDATE_DELIVERY": "超管强改",
        "SUBMIT_FITTING_DELIVERY": "提交管件发货",
        "CONFIRM_FITTING_ARRIVAL": "管件现场确认到货",
        "CONFIRM_FITTING_CONSTRUCTION": "管件施工确认接收",
        "CONFIRM_FITTING_WAREHOUSE": "管件库管确认入库",
        "CANCEL_FITTING_DELIVERY": "撤销管件发货",
        "DELETE_FITTING_DELIVERY": "撤销管件发货",
    }
    
    for log in logs:
        created_at_str = log["created_at"]
        if created_at_str:
            try:
                dt = datetime.fromisoformat(created_at_str)
                created_at_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
                
        action_name = action_type_map.get(log["action_type"], log["action_type"])
        writer.writerow([
            created_at_str,
            log["operator"],
            log["operator_group"] or "",
            action_name,
            log["action_desc"],
            log["resource_id"] or "",
            log["client_ip"] or "",
        ])
        
    output.seek(0)
    
    response = StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv"
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    response.headers["Content-Disposition"] = f"attachment; filename=operation_logs_{timestamp}.csv"
    return response


@router.get("/global-management/history", summary="读取历史填报与到货聚合数据")
def get_global_management_history(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    section_1_id: Optional[str] = Query(None, description="需求主体ID (支持逗号分隔多选)"),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    group_lower = str(session.group or "").strip().lower()
    allowed_groups = {
        "global_admin",
        "tube_warehouse_admin",
        "tube_supplier_admin",
        "tube_supplier",
        "tube_site_manager",
        "tube_construction_unit",
        "tube_warehouse_keeper",
        "tube_global_viewer",
    }
    if group_lower not in allowed_groups:
        raise HTTPException(status_code=403, detail="无权查看历史数据")
        
    try:
        dt_start = date.fromisoformat(start_date)
        dt_end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期格式不正确，应为 YYYY-MM-DD") from exc

    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    if not accessible_section_1_ids and session.group == "tube_warehouse_keeper":
        accessible_section_1_ids = set(_build_section_1_name_map(payload).keys())

    selected_section_1s = {s.strip() for s in section_1_id.split(",") if s.strip()} if section_1_id else set()

    # 获取原始合并历史数据
    rows = query_history_records(start_date=dt_start, end_date=dt_end, section_1_id=None)
    
    # 建立映射字典
    section_1_map = {
        item.get("section_1_id"): item.get("section_1_name")
        for item in payload.get("demand_entities", [])
        if item.get("section_1_id")
    }
    pipe_map = {
        item.get("pipe_model_id"): item.get("pipe_model_name")
        for item in payload.get("pipe_models", [])
        if item.get("pipe_model_id")
    }
    
    filtered_rows = []
    for row in rows:
        sec_id = str(row.get("section_1_id") or "").strip()
        if accessible_section_1_ids and sec_id not in accessible_section_1_ids:
            continue
        if selected_section_1s and sec_id not in selected_section_1s:
            continue
        row["section_1_name"] = section_1_map.get(sec_id) or sec_id
        row["pipe_model_name"] = pipe_map.get(row.get("pipe_model_id")) or row.get("pipe_model_id")
        filtered_rows.append(row)
        
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "rows": filtered_rows
    }


@router.get("/global-management/history/export", summary="导出历史填报与到货数据")
def export_global_management_history(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    section_1_id: Optional[str] = Query(None, description="需求主体ID (支持逗号分隔多选)"),
    session: AuthSession = Depends(get_current_session),
):
    group_lower = str(session.group or "").strip().lower()
    allowed_groups = {
        "global_admin",
        "tube_warehouse_admin",
        "tube_supplier_admin",
        "tube_supplier",
        "tube_site_manager",
        "tube_construction_unit",
        "tube_warehouse_keeper",
        "tube_global_viewer",
    }
    if group_lower not in allowed_groups:
        raise HTTPException(status_code=403, detail="无权导出历史数据")
        
    try:
        dt_start = date.fromisoformat(start_date)
        dt_end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期格式不正确，应为 YYYY-MM-DD") from exc

    payload = load_tube_config()
    accessible_section_1_ids = resolve_accessible_section_1_ids(payload, session.username, session.group)
    if not accessible_section_1_ids and session.group == "tube_warehouse_keeper":
        accessible_section_1_ids = set(_build_section_1_name_map(payload).keys())

    selected_section_1s = {s.strip() for s in section_1_id.split(",") if s.strip()} if section_1_id else set()

    rows = query_history_records(start_date=dt_start, end_date=dt_end, section_1_id=None)

    filtered_rows = []
    for row in rows:
        sec_id = str(row.get("section_1_id") or "").strip()
        if accessible_section_1_ids and sec_id not in accessible_section_1_ids:
            continue
        if selected_section_1s and sec_id not in selected_section_1s:
            continue
        filtered_rows.append(row)
    rows = filtered_rows
    
    section_1_map = {
        item.get("section_1_id"): item.get("section_1_name")
        for item in payload.get("demand_entities", [])
        if item.get("section_1_id")
    }
    pipe_map = {
        item.get("pipe_model_id"): item.get("pipe_model_name")
        for item in payload.get("pipe_models", [])
        if item.get("pipe_model_id")
    }
    
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM
    writer = csv.writer(output)
    
    # 按需求主体进行分组与排序
    from collections import defaultdict
    section_1_groups = defaultdict(list)
    for row in rows:
        section_1_groups[row["section_1_id"]].append(row)
        
    sorted_section_1_ids = sorted(section_1_groups.keys())
    
    for st_id in sorted_section_1_ids:
        # 1. 每个需求主体块的头部写入相同的表头
        writer.writerow([
            "日期", "需求主体ID", "需求主体名称", "管材型号ID", "管材型号名称", 
            "当日计划量 (米)", "当日使用量 (米)", "当日损耗量 (米)", 
            "确认到货量 (米)", "运输在途时间", "时间单位"
        ])
        
        group_rows = section_1_groups[st_id]
        # 按日期降序排序
        group_rows.sort(key=lambda x: x["biz_date"], reverse=True)
        st_name = section_1_map.get(st_id) or st_id
        
        # 2. 写入该站明细行
        for row in group_rows:
            pm_name = pipe_map.get(row["pipe_model_id"]) or row["pipe_model_id"]
            
            # 计算在途时间（分钟）
            transit_val = ""
            unit_val = ""
            if row["arrived_batch_count"] > 0:
                avg_seconds = row["total_transit_seconds"] / row["arrived_batch_count"]
                transit_val = round(avg_seconds / 60, 1)
                unit_val = "分钟"
                
            writer.writerow([
                row["biz_date"],
                row["section_1_id"],
                st_name,
                row["pipe_model_id"],
                pm_name,
                row["plan_qty"],
                row["usage_qty"],
                row["loss_qty"],
                row["arrived_qty"],
                transit_val,
                unit_val
            ])
            
        # 3. 计算并写入该站历史小计行（对应表头列填写）
        sub_plan = sum(r["plan_qty"] for r in group_rows)
        sub_usage = sum(r["usage_qty"] for r in group_rows)
        sub_loss = sum(r["loss_qty"] for r in group_rows)
        sub_arrived = sum(r["arrived_qty"] for r in group_rows)
        sub_transit = sum(r["total_transit_seconds"] for r in group_rows)
        sub_batches = sum(r["arrived_batch_count"] for r in group_rows)
        
        sub_transit_val = round(sub_transit / 60 / sub_batches, 1) if sub_batches > 0 else ""
        sub_unit_val = "分钟" if sub_batches > 0 else ""
        
        writer.writerow([
            f"[{st_name}] 历史小计",
            st_id,
            st_name,
            "-",
            "-",
            sub_plan,
            sub_usage,
            sub_loss,
            sub_arrived,
            sub_transit_val,
            sub_unit_val
        ])
        
        # 4. 计算并写入该站专属的决策辅助透视（两列纯文本形式）
        sub_active_dates = {r["biz_date"] for r in group_rows if r["usage_qty"] > 0 and r["biz_date"]}
        sub_active_days_count = len(sub_active_dates)
        
        sub_valid_mins = [r["min_transit_seconds"] for r in group_rows if r.get("min_transit_seconds") is not None]
        sub_valid_maxs = [r["max_transit_seconds"] for r in group_rows if r.get("max_transit_seconds") is not None]
        sub_min_transit_val = min(sub_valid_mins) if sub_valid_mins else None
        sub_max_transit_val = max(sub_valid_maxs) if sub_valid_maxs else None
        
        sub_fulfillment_rate_str = f"{(sub_arrived / sub_plan * 100):.1f}%" if sub_plan > 0 else "-"
        sub_plan_usage_alignment_str = f"{(sub_usage / sub_plan * 100):.1f}%" if sub_plan > 0 else "-"
        sub_loss_rate_str = f"{(sub_loss / (sub_usage + sub_loss) * 100):.1f}%" if (sub_usage + sub_loss) > 0 else "-"
        sub_daily_consumption_str = f"{(sub_usage / sub_active_days_count):.1f} 米/天" if sub_active_days_count > 0 else "-"
        
        sub_min_transit_str = format_delivery_elapsed_seconds(sub_min_transit_val) if sub_min_transit_val is not None else "-"
        sub_max_transit_str = format_delivery_elapsed_seconds(sub_max_transit_val) if sub_max_transit_val is not None else "-"
        sub_avg_transit_str = format_delivery_elapsed_seconds(sub_transit / sub_batches) if sub_batches > 0 else "-"
        sub_overall_transit_str = f"最快 {sub_min_transit_str} / 最慢 {sub_max_transit_str} (平均 {sub_avg_transit_str}, 共 {sub_batches} 批)"
        
        writer.writerow([f"--- [{st_name}] 决策辅助透视 ---"])
        writer.writerow(["物资综合保障率", f"{sub_fulfillment_rate_str} (计划 {sub_plan:.1f} 米 / 到货 {sub_arrived:.1f} 米)"])
        writer.writerow(["计划消耗契合度", f"{sub_plan_usage_alignment_str} (实际消耗 {sub_usage:.1f} 米 / 计划 {sub_plan:.1f} 米)"])
        writer.writerow(["施工综合损耗率", f"{sub_loss_rate_str} (消耗 {sub_usage:.1f} 米 / 损耗 {sub_loss:.1f} 米)"])
        writer.writerow(["施工消耗强度", f"{sub_daily_consumption_str} (施工 {sub_active_days_count} 天)"])
        writer.writerow(["物流配送效率区间", sub_overall_transit_str])
        
        # 需求主体之间空出 2 行
        writer.writerow([])
        writer.writerow([])

class GisMarkerCreatePayload(BaseModel):
    type: str = Field(..., alias="type", description="点位类型: weld, meter, tee, compensator, elbow, valve")
    section_name: Optional[str] = Field(default="", alias="sectionName", description="施工标段名称")
    pipeline_name: str = Field(..., alias="pipelineName", description="管线名称/编号")
    code: str = Field(..., description="点位唯一编号")
    name: str = Field(..., description="名称描述")
    lng: float = Field(..., description="经度 Lng")
    lat: float = Field(..., description="纬度 Lat")
    status: str = Field(default="passed")
    spec: Optional[str] = None
    remarks: Optional[str] = None
    sort_order: int = Field(default=0, alias="sortOrder")
    parent_code: Optional[str] = Field(default="", alias="parentCode", description="父级三通/节点编号")

    class Config:
        allow_population_by_field_name = True


@public_router.get("/gis/config", summary="获取 GIS 高德地图 SDK API Key 配置")
def get_gis_map_config() -> Dict[str, Any]:
    """
    提供解密后的高德地图 API Key 与安全 Key 供前端 SDK 动态加载
    """
    payload = load_tube_config()
    amap_cfg = get_configured_amap_config(payload)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "api_key": amap_cfg["api_key"],
        "security_code": amap_cfg["security_code"]
    }


@public_router.get("/gis/markers")
def list_gis_markers():
    """
    拉取 PostgreSQL tube.tube_gis 数据库表中持久化的所有焊口、三通、表计等标注
    同时动态读取 tube_config.json 设定的官方系统标段列表 (demand_entities.section_1_name)
    """
    from sqlalchemy import text
    from backend.db.database_daily_report_25_26 import SessionLocal
    from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config

    db_session = SessionLocal()
    try:
        # 动态读取系统权威配置文件 tube_config.json
        config = load_tube_config() or {}
        system_sections = []
        for item in config.get("demand_entities", []):
            sec_name = str(item.get("section_1_name") or "").strip()
            if sec_name and sec_name not in system_sections:
                system_sections.append(sec_name)

        query_sql = text("""
            SELECT id, project_key, marker_type, section_name, pipeline_name, code, name, lng, lat, status, spec, remarks, sort_order, parent_code, created_at
            FROM tube.tube_gis
            WHERE project_key = :project_key
            ORDER BY sort_order ASC, id ASC
        """)
        rows = db_session.execute(query_sql, {"project_key": PROJECT_KEY}).fetchall()

        markers = []
        for r in rows:
            mtype = r.marker_type or 'weld'
            status_text = '运行正常'
            status_class = 'tag-success'
            if mtype == 'weld':
                if r.status == 'pending':
                    status_text = '待探伤'
                    status_class = 'tag-warning'
                elif r.status == 'failed':
                    status_text = '待复焊'
                    status_class = 'tag-danger'
                else:
                    status_text = '探伤合格'
                    status_class = 'tag-success'
            elif mtype == 'meter':
                if r.status == 'warning':
                    status_text = '压差预警'
                    status_class = 'tag-warning'
                else:
                    status_text = '运行正常'
                    status_class = 'tag-info'
            elif mtype == 'tee':
                status_text = '三通分叉点'
                status_class = 'tag-warning'
            elif mtype == 'compensator':
                status_text = '吸收变形中'
                status_class = 'tag-info'
            elif mtype == 'elbow':
                status_text = '转向弯头'
                status_class = 'tag-purple'
            elif mtype == 'valve':
                if r.status == 'closed':
                    status_text = '阀门常闭'
                    status_class = 'tag-warning'
                else:
                    status_text = '开启状态'
                    status_class = 'tag-success'

            created_at_str = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(r, 'created_at', None) else ""

            markers.append({
                "id": r.id,
                "type": mtype,
                "sectionName": r.section_name or "",
                "pipelineName": r.pipeline_name,
                "code": r.code,
                "name": r.name,
                "lng": float(r.lng),
                "lat": float(r.lat),
                "status": r.status,
                "statusText": status_text,
                "statusClass": status_class,
                "spec": r.spec or "",
                "remarks": r.remarks or "",
                "sortOrder": r.sort_order,
                "parentCode": r.parent_code or "",
                "createdAt": created_at_str
            })

        return {"ok": True, "data": markers, "systemSections": system_sections}
    finally:
        db_session.close()


@public_router.post("/gis/markers")
def create_gis_marker(
    payload: GisMarkerCreatePayload,
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    """
    新增标注点位并持久化到 PostgreSQL tube.tube_gis 数据库表中
    """
    from sqlalchemy import text
    from backend.db.database_daily_report_25_26 import SessionLocal

    db_session = SessionLocal()
    user_name = session.username if session and hasattr(session, 'username') else 'Global_admin'
    try:
        insert_sql = text("""
            INSERT INTO tube.tube_gis 
            (project_key, marker_type, section_name, pipeline_name, code, name, lng, lat, status, spec, remarks, sort_order, parent_code, created_by, updated_by)
            VALUES
            (:project_key, :marker_type, :section_name, :pipeline_name, :code, :name, :lng, :lat, :status, :spec, :remarks, :sort_order, :parent_code, :user, :user)
            RETURNING id;
        """)

        res = db_session.execute(insert_sql, {
            "project_key": PROJECT_KEY,
            "marker_type": payload.type,
            "section_name": payload.section_name or "",
            "pipeline_name": payload.pipeline_name,
            "code": payload.code,
            "name": payload.name,
            "lng": payload.lng,
            "lat": payload.lat,
            "status": payload.status,
            "spec": payload.spec,
            "remarks": payload.remarks,
            "sort_order": payload.sort_order,
            "parent_code": payload.parent_code or None,
            "user": user_name
        })
        new_id = res.fetchone()[0]
        db_session.commit()
        return {"ok": True, "id": new_id, "message": "保存点位到数据库成功"}
    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=400, detail=f"保存到数据库失败: {str(e)}")
    finally:
        db_session.close()


@public_router.put("/gis/markers/{marker_id}")
def update_gis_marker(
    marker_id: int,
    payload: GisMarkerCreatePayload,
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    """
    更新 PostgreSQL tube.tube_gis 数据库表中的点位标注信息
    """
    from sqlalchemy import text
    from backend.db.database_daily_report_25_26 import SessionLocal

    db_session = SessionLocal()
    user_name = session.username if session and hasattr(session, 'username') else 'Global_admin'
    try:
        update_sql = text("""
            UPDATE tube.tube_gis
            SET marker_type = :marker_type,
                section_name = :section_name,
                pipeline_name = :pipeline_name,
                code = :code,
                name = :name,
                lng = :lng,
                lat = :lat,
                status = :status,
                spec = :spec,
                remarks = :remarks,
                sort_order = :sort_order,
                parent_code = :parent_code,
                updated_by = :user,
                updated_at = NOW()
            WHERE id = :id AND project_key = :project_key;
        """)

        db_session.execute(update_sql, {
            "id": marker_id,
            "project_key": PROJECT_KEY,
            "marker_type": payload.type,
            "section_name": payload.section_name or "",
            "pipeline_name": payload.pipeline_name,
            "code": payload.code,
            "name": payload.name,
            "lng": payload.lng,
            "lat": payload.lat,
            "status": payload.status,
            "spec": payload.spec,
            "remarks": payload.remarks or "",
            "sort_order": payload.sort_order,
            "parent_code": payload.parent_code or None,
            "user": user_name,
        })
        db_session.commit()
        return {"ok": True, "message": "更新点位成功"}
    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=400, detail=f"更新点位失败: {str(e)}")
    finally:
        db_session.close()


@public_router.delete("/gis/markers/{marker_id}")
def delete_gis_marker(
    marker_id: int,
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    """
    从 PostgreSQL tube.tube_gis 数据库表中删除指定点位
    """
    from sqlalchemy import text
    from backend.db.database_daily_report_25_26 import SessionLocal

    db_session = SessionLocal()
    try:
        delete_sql = text("""
            DELETE FROM tube.tube_gis
            WHERE id = :id AND project_key = :project_key;
        """)
        db_session.execute(delete_sql, {
            "id": marker_id,
            "project_key": PROJECT_KEY
        })
        db_session.commit()
        return {"ok": True, "message": "点位已从数据库彻底删除"}
    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=400, detail=f"数据库删除失败: {str(e)}")
    finally:
        db_session.close()


# ==================== 在线用户心跳与 Presence 模块 ====================

@public_router.post("/presence/heartbeat", summary="用户静默心跳上报")
def handle_presence_heartbeat(
    payload: Dict[str, Any] = Body(default={}),
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    from backend.projects.insulation_pipe_supply_2026.services.presence_service import record_user_heartbeat
    is_valid_session = session and hasattr(session, "username") and isinstance(session.username, str)
    username = session.username if is_valid_session else payload.get("username", "guest")
    display_name = session.unit if is_valid_session else payload.get("display_name", "")
    unit = session.unit if is_valid_session else payload.get("unit", "")
    group = session.group if is_valid_session else payload.get("group", "")
    current_page = payload.get("current_page", "")

    return record_user_heartbeat(
        username=username,
        display_name=display_name,
        unit=unit,
        group=group,
        current_page=current_page,
    )


@public_router.get("/presence/online-users", summary="获取当前在线用户数量与列表")
def get_online_users_presence(
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    from backend.projects.insulation_pipe_supply_2026.services.presence_service import get_online_users_list
    users = get_online_users_list()
    return {
        "ok": True,
        "online_count": len(users),
        "users": users,
    }


@public_router.post("/presence/logout", summary="主动显式标记下线")
def handle_presence_logout(
    payload: Dict[str, Any] = Body(default={}),
    session: Optional[AuthSession] = Depends(get_current_session_optional)
):
    from backend.projects.insulation_pipe_supply_2026.services.presence_service import record_user_logout
    is_valid_session = session and hasattr(session, "username") and isinstance(session.username, str)
    username = session.username if is_valid_session else payload.get("username", "")
    record_user_logout(username)
    return {"ok": True}


def _ensure_fitting_role(session: AuthSession, allowed_groups: Set[str], action_name: str) -> None:
    group = str(session.group or "").strip().lower()
    if group not in allowed_groups:
        raise HTTPException(status_code=403, detail=f"当前账号无{action_name}权限")


def _normalized_access_ids(values: Set[str]) -> Set[str]:
    return {str(value or "").strip().lower() for value in values if str(value or "").strip()}


def _ensure_fitting_section_access(rows: List[Dict[str, Any]], session: AuthSession) -> None:
    config = load_tube_config()
    allowed_ids = _normalized_access_ids(resolve_accessible_section_1_ids(config, session.username, session.group))
    denied = sorted({str(row.get("section_1_id") or "").strip() for row in rows if str(row.get("section_1_id") or "").strip().lower() not in allowed_ids})
    if denied:
        raise HTTPException(status_code=403, detail=f"当前账号无以下标段的管件操作权限：{', '.join(denied)}")


def _ensure_fitting_supply_access(rows: List[Dict[str, Any]], session: AuthSession) -> None:
    config = load_tube_config()
    allowed_ids = _normalized_access_ids(resolve_accessible_supply_entity_ids(config, session.username, session.group))
    denied = sorted({str(row.get("supply_entity_id") or "").strip() for row in rows if str(row.get("supply_entity_id") or "").strip().lower() not in allowed_ids})
    if denied:
        raise HTTPException(status_code=403, detail=f"当前账号无以下供给主体的管件操作权限：{', '.join(denied)}")


@router.post("/workspace/fitting_deliveries/submit", summary="提交管件发货记录表")
def handle_submit_fitting_delivery(
    payload: FittingDeliverySubmitPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_fitting_role(session, {"global_admin", "tube_supplier_admin", "tube_supplier"}, "管件发货")
    config = load_tube_config()
    accessible_supply_ids = resolve_accessible_supply_entity_ids(config, session.username, session.group)
    if payload.supply_entity_id.strip().lower() not in _normalized_access_ids(accessible_supply_ids):
        raise HTTPException(status_code=403, detail="当前账号无该供给主体的管件发货权限")
    allowed_section_ids = resolve_supply_entity_allowed_section_ids(config, payload.supply_entity_id)
    if allowed_section_ids and payload.section_1_id.strip().lower() not in _normalized_access_ids(allowed_section_ids):
        raise HTTPException(status_code=403, detail="当前供给主体无该标段的管件发货权限")
    return submit_fitting_delivery(payload.model_dump(), operator=session.username, operator_group=session.group)


@router.post("/workspace/fitting_deliveries/confirm_arrival", summary="确认管件现场到货")
def handle_confirm_fitting_delivery_arrival(
    payload: FittingArrivalConfirmPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_fitting_role(session, {"global_admin", "tube_site_manager"}, "管件到货确认")
    rows = get_fitting_deliveries_by_ids(payload.ids)
    found_ids = {int(row["id"]) for row in rows}
    if not set(payload.ids).issubset(found_ids):
        raise HTTPException(status_code=404, detail="部分管件记录不存在")
    _ensure_fitting_section_access(rows, session)
    return confirm_fitting_delivery_arrival(payload.model_dump(), operator=session.username, operator_group=session.group)


@router.post("/workspace/fitting_deliveries/confirm_construction", summary="施工单位确认接收管件")
def handle_confirm_fitting_delivery_construction(
    payload: FittingConfirmPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_fitting_role(session, {"global_admin", "tube_construction_unit"}, "管件施工接收确认")
    rows = get_fitting_deliveries_by_ids(payload.ids)
    found_ids = {int(row["id"]) for row in rows}
    if not set(payload.ids).issubset(found_ids):
        raise HTTPException(status_code=404, detail="部分管件记录不存在")
    _ensure_fitting_section_access(rows, session)
    return confirm_fitting_delivery_construction(payload.model_dump(), operator=session.username, operator_group=session.group)


@router.post("/workspace/fitting_deliveries/confirm_warehouse", summary="库管确认管件入库")
def handle_confirm_fitting_delivery_warehouse(
    payload: FittingConfirmPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_fitting_role(session, {"global_admin", "tube_warehouse_admin", "tube_warehouse_keeper"}, "管件库管入库确认")
    rows = get_fitting_deliveries_by_ids(payload.ids)
    found_ids = {int(row["id"]) for row in rows}
    if not set(payload.ids).issubset(found_ids):
        raise HTTPException(status_code=404, detail="部分管件记录不存在")
    _ensure_fitting_section_access(rows, session)
    return confirm_fitting_delivery_warehouse(payload.model_dump(), operator=session.username, operator_group=session.group)


@router.post("/workspace/fitting_deliveries/cancel", summary="撤销管件发货单")
def handle_cancel_fitting_delivery(
    payload: FittingCancelPayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_fitting_role(session, {"global_admin", "tube_supplier_admin", "tube_supplier"}, "管件发货撤销")
    rows = get_fitting_deliveries_by_ids(payload.ids)
    found_ids = {int(row["id"]) for row in rows}
    if not set(payload.ids).issubset(found_ids):
        raise HTTPException(status_code=404, detail="部分管件记录不存在")
    _ensure_fitting_supply_access(rows, session)
    return cancel_fitting_delivery(payload.model_dump(), operator=session.username, operator_group=session.group)


@router.get("/workspace/fitting_deliveries/list", summary="分页查询管件发货记录")
def handle_list_fitting_deliveries(
    section_1_id: str = Query("", description="接收标段/工程ID，多个值以逗号分隔"),
    supply_entity_id: str = Query("", description="供给主体ID"),
    start_date: str = Query("", description="开始时间/日期"),
    end_date: str = Query("", description="结束时间/日期"),
    search_keyword: str = Query("", description="搜索关键字"),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500),
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config = load_tube_config()
    group = str(session.group or "").strip().lower()
    _ensure_fitting_role(
        session,
        {
            "global_admin", "tube_supplier_admin", "tube_supplier",
            "tube_site_manager", "tube_construction_unit",
            "tube_warehouse_admin", "tube_warehouse_keeper", "tube_global_viewer",
        },
        "管件发货记录查询",
    )
    accessible_section_ids = resolve_accessible_section_1_ids(config, session.username, session.group)
    accessible_supply_ids = resolve_accessible_supply_entity_ids(config, session.username, session.group)
    section_scoped_groups = {"tube_supplier", "tube_site_manager", "tube_construction_unit", "tube_warehouse_keeper"}
    supply_scoped_groups = {"tube_supplier"}
    result = list_fitting_deliveries(
        section_1_id=section_1_id,
        supply_entity_id=supply_entity_id,
        start_date=start_date,
        end_date=end_date,
        search_keyword=search_keyword,
        page=page,
        page_size=limit,
        allowed_section_ids=sorted(accessible_section_ids) if group in section_scoped_groups else None,
        allowed_supply_ids=sorted(accessible_supply_ids) if group in supply_scoped_groups else None,
    )
    _decorate_delivery_rows(config, result["items"])
    return {"ok": True, **result}





