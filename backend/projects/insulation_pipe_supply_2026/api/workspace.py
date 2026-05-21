# -*- coding: utf-8 -*-
"""
insulation_pipe_supply_2026 工作台基础接口。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    CONFIG_PATH,
    PROJECT_KEY,
    get_configured_biz_date,
    get_configured_plan_editable_days,
    get_configured_plan_start_date,
    get_config_list,
    load_tube_config,
    resolve_accessible_station_ids,
    save_tube_config,
)
from backend.projects.insulation_pipe_supply_2026.services.demand_management_service import (
    build_plan_dates,
    list_baseline_rows,
    list_pending_arrivals,
    list_plan_records,
    list_usage_records,
    save_plan_records,
    save_usage_records,
)

router = APIRouter(tags=[PROJECT_KEY])
public_router = APIRouter(tags=[PROJECT_KEY])


class DemandPlanRecordInput(BaseModel):
    plan_date: date
    pipe_model_id: str
    plan_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandPlanSavePayload(BaseModel):
    station_id: str
    records: List[DemandPlanRecordInput] = []


class DemandUsageRecordInput(BaseModel):
    pipe_model_id: str
    usage_qty: float = Field(default=0, ge=0)
    remark: str = ""


class DemandUsageSavePayload(BaseModel):
    station_id: str
    usage_date: date
    records: List[DemandUsageRecordInput] = []


class TubeConfigSavePayload(BaseModel):
    config: Dict[str, Any]


class TubeConfigSectionSavePayload(BaseModel):
    section: str
    data: Any


def _build_station_name_map(payload: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in get_config_list(payload, "demand_entities"):
        station_id = str(item.get("station_id") or "").strip()
        if not station_id:
            continue
        result[station_id] = str(item.get("station_name") or station_id)
    return result


def _build_pipe_model_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "pipe_models"):
        pipe_model_id = str(item.get("pipe_model_id") or "").strip()
        if not pipe_model_id:
            continue
        result[pipe_model_id] = item
    return result


def _build_supply_entity_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "supply_entities"):
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id:
            continue
        result[entity_id] = item
    return result


def _ensure_global_admin(session: AuthSession) -> None:
    if str(session.group or "").strip() != "Global_admin":
        raise HTTPException(status_code=403, detail="只有 Global_admin 可以访问该页面")


def _build_baseline_preset_map(payload: Dict[str, Any], station_id: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for item in get_config_list(payload, "baseline_presets"):
        normalized_station_id = str(item.get("station_id") or "").strip()
        pipe_model_id = str(item.get("pipe_model_id") or "").strip()
        if normalized_station_id != station_id or not pipe_model_id:
            continue
        result[pipe_model_id] = {
            "design_qty": item.get("design_qty"),
            "purchase_plan_qty": item.get("purchase_plan_qty"),
            "remark": item.get("remark") or "",
        }
    return result


def _save_config_section(section: str, data: Any) -> Dict[str, Any]:
    payload = load_tube_config()
    normalized_section = str(section or "").strip()
    allowed_sections = {
        "biz_date",
        "plan_start_date",
        "plan_editable_days",
        "supply_entities",
        "demand_entities",
        "pipe_models",
        "manager_assignments",
        "construction_units",
        "construction_assignments",
        "baseline_presets",
    }
    if normalized_section not in allowed_sections:
        raise HTTPException(status_code=422, detail=f"不支持的配置区块：{normalized_section}")

    if normalized_section in {"biz_date", "plan_start_date"}:
        normalized_date = str(data or "").strip()
        if not normalized_date:
            raise HTTPException(status_code=422, detail=f"{normalized_section} 不能为空")
        try:
            date.fromisoformat(normalized_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{normalized_section} 非法：{normalized_date}") from exc
        payload[normalized_section] = normalized_date
    elif normalized_section == "plan_editable_days":
        try:
            normalized_editable_days = int(data)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 非法：{data}") from exc
        if normalized_editable_days < 0 or normalized_editable_days > 3:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 超出范围：{normalized_editable_days}")
        payload[normalized_section] = normalized_editable_days
    else:
        if not isinstance(data, list):
            raise HTTPException(status_code=422, detail=f"{normalized_section} 必须为数组")
        payload[normalized_section] = data

    save_tube_config(payload)
    return payload


def _ensure_station_access(station_id: str, accessible_station_ids: set[str]) -> None:
    normalized_station_id = str(station_id or "").strip()
    if not normalized_station_id:
        raise HTTPException(status_code=422, detail="station_id 不能为空")
    if normalized_station_id not in accessible_station_ids:
        raise HTTPException(status_code=403, detail=f"当前账号无换热站 {normalized_station_id} 的访问权限")


def _serialize_station_options(payload: Dict[str, Any], accessible_station_ids: set[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in get_config_list(payload, "demand_entities"):
        station_id = str(item.get("station_id") or "").strip()
        if not station_id or station_id not in accessible_station_ids:
            continue
        rows.append(
            {
                "station_id": station_id,
                "station_name": item.get("station_name") or station_id,
                "region": item.get("region") or "",
                "section": item.get("section") or "",
                "construction_status": item.get("construction_status") or "",
            }
        )
    return rows


def _serialize_pipe_options(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in get_config_list(payload, "pipe_models"):
        pipe_model_id = str(item.get("pipe_model_id") or "").strip()
        if not pipe_model_id:
            continue
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": item.get("pipe_model_name") or pipe_model_id,
                "diameter_label": item.get("diameter_label") or "",
                "unit": item.get("unit") or "",
                "category": item.get("category") or "",
            }
        )
    return rows


@public_router.get("/workspace/config-summary", summary="读取 tube 配置摘要")
def get_workspace_config_summary() -> Dict[str, Any]:
    payload = load_tube_config()
    supply_entities = get_config_list(payload, "supply_entities")
    demand_entities = get_config_list(payload, "demand_entities")
    pipe_models = get_config_list(payload, "pipe_models")
    manager_assignments = get_config_list(payload, "manager_assignments")
    construction_units = get_config_list(payload, "construction_units")
    construction_assignments = get_config_list(payload, "construction_assignments")
    baseline_presets = get_config_list(payload, "baseline_presets")

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "config_path": str(CONFIG_PATH),
        "biz_date": get_configured_biz_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(payload),
        "summary": {
            "supply_entity_count": len(supply_entities),
            "demand_entity_count": len(demand_entities),
            "pipe_model_count": len(pipe_models),
            "manager_assignment_count": len(manager_assignments),
            "construction_unit_count": len(construction_units),
            "construction_assignment_count": len(construction_assignments),
            "baseline_preset_count": len(baseline_presets),
        },
        "supply_entities": supply_entities,
        "demand_entities": demand_entities,
        "pipe_models": pipe_models,
        "manager_assignments": manager_assignments,
        "construction_units": construction_units,
        "construction_assignments": construction_assignments,
        "baseline_presets": baseline_presets,
    }


@router.get("/demand-management/options", summary="读取需求侧页面选项")
def get_demand_management_options(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(payload, session.username, session.group)
    biz_date = get_configured_biz_date(payload)
    plan_start_date = get_configured_plan_start_date(payload)
    plan_editable_days = get_configured_plan_editable_days(payload)

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "user": {
            "username": session.username,
            "group": session.group,
            "unit": session.unit,
        },
        "stations": _serialize_station_options(payload, accessible_station_ids),
        "pipe_models": _serialize_pipe_options(payload),
        "biz_date": biz_date.isoformat(),
        "plan_start_date": plan_start_date.isoformat(),
        "plan_editable_days": plan_editable_days,
        "default_plan_anchor_date": plan_start_date.isoformat(),
        "default_usage_date": biz_date.isoformat(),
    }


@router.get("/demand-management/baseline", summary="读取需求侧基准数据")
def get_demand_management_baseline(
    station_id: str,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(payload, session.username, session.group)
    _ensure_station_access(station_id, accessible_station_ids)

    station_name_map = _build_station_name_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    baseline_map = list_baseline_rows(station_id)
    baseline_preset_map = _build_baseline_preset_map(payload, station_id)

    rows: List[Dict[str, Any]] = []
    for pipe_model_id, pipe_model in pipe_model_map.items():
        baseline = baseline_map.get(pipe_model_id) or baseline_preset_map.get(pipe_model_id) or {}
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "diameter_label": pipe_model.get("diameter_label") or "",
                "unit": pipe_model.get("unit") or "",
                "category": pipe_model.get("category") or "",
                "design_qty": baseline.get("design_qty"),
                "purchase_plan_qty": baseline.get("purchase_plan_qty"),
                "remark": baseline.get("remark") or "",
            }
        )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": station_id,
        "station_name": station_name_map.get(station_id, station_id),
        "rows": rows,
    }


@router.get("/global-management/config", summary="读取全局管理配置")
def get_global_management_config(
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    payload = load_tube_config()
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "config_path": str(CONFIG_PATH),
        "biz_date": get_configured_biz_date(payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(payload),
        "config": payload,
    }


@router.post("/global-management/config", summary="保存全局管理配置")
def save_global_management_config(
    payload: TubeConfigSavePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    config_payload = dict(payload.config or {})
    normalized_biz_date = str(config_payload.get("biz_date") or "").strip()
    if normalized_biz_date:
        try:
            date.fromisoformat(normalized_biz_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"biz_date 非法：{normalized_biz_date}") from exc
    normalized_plan_start_date = str(config_payload.get("plan_start_date") or "").strip()
    if normalized_plan_start_date:
        try:
            date.fromisoformat(normalized_plan_start_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"plan_start_date 非法：{normalized_plan_start_date}") from exc
    plan_editable_days = config_payload.get("plan_editable_days")
    if plan_editable_days not in (None, ""):
        try:
            normalized_editable_days = int(plan_editable_days)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 非法：{plan_editable_days}") from exc
        if normalized_editable_days < 0 or normalized_editable_days > 3:
            raise HTTPException(status_code=422, detail=f"plan_editable_days 超出范围：{normalized_editable_days}")
    save_tube_config(config_payload)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "config_path": str(CONFIG_PATH),
        "biz_date": get_configured_biz_date(config_payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(config_payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(config_payload),
        "config": config_payload,
    }


@router.post("/global-management/config-section", summary="保存全局管理单个配置区块")
def save_global_management_config_section(
    payload: TubeConfigSectionSavePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    _ensure_global_admin(session)
    config_payload = _save_config_section(payload.section, payload.data)
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "config_path": str(CONFIG_PATH),
        "biz_date": get_configured_biz_date(config_payload).isoformat(),
        "plan_start_date": get_configured_plan_start_date(config_payload).isoformat(),
        "plan_editable_days": get_configured_plan_editable_days(config_payload),
        "config": config_payload,
        "saved_section": str(payload.section or "").strip(),
    }


@router.get("/demand-management/plan-matrix", summary="读取需求侧三日计划矩阵")
def get_demand_management_plan_matrix(
    station_id: str,
    anchor_date: date,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(payload, session.username, session.group)
    _ensure_station_access(station_id, accessible_station_ids)

    station_name_map = _build_station_name_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    plan_dates = build_plan_dates(anchor_date)
    plan_record_map = list_plan_records(station_id, plan_dates)

    rows: List[Dict[str, Any]] = []
    for pipe_model_id, pipe_model in pipe_model_map.items():
        values: Dict[str, Optional[float]] = {}
        remarks: Dict[str, str] = {}
        for plan_date in plan_dates:
            date_key = plan_date.isoformat()
            record = plan_record_map.get(f"{pipe_model_id}::{date_key}", {})
            values[date_key] = record.get("plan_qty")
            remarks[date_key] = record.get("remark") or ""
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "unit": pipe_model.get("unit") or "",
                "values": values,
                "remarks": remarks,
            }
        )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": station_id,
        "station_name": station_name_map.get(station_id, station_id),
        "anchor_date": anchor_date.isoformat(),
        "plan_dates": [item.isoformat() for item in plan_dates],
        "rows": rows,
    }


@router.post("/demand-management/plan-matrix", summary="保存需求侧三日计划矩阵")
def save_demand_management_plan_matrix(
    payload: DemandPlanSavePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(config_payload, session.username, session.group)
    _ensure_station_access(payload.station_id, accessible_station_ids)

    saved_count = save_plan_records(
        station_id=payload.station_id,
        records=[item.model_dump() for item in payload.records],
        operator=session.username,
    )
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": payload.station_id,
        "saved_count": saved_count,
    }


@router.get("/demand-management/usage-sheet", summary="读取需求侧实际使用表单")
def get_demand_management_usage_sheet(
    station_id: str,
    usage_date: date,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(payload, session.username, session.group)
    _ensure_station_access(station_id, accessible_station_ids)

    station_name_map = _build_station_name_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    usage_record_map = list_usage_records(station_id, usage_date)

    rows: List[Dict[str, Any]] = []
    for pipe_model_id, pipe_model in pipe_model_map.items():
        usage_record = usage_record_map.get(pipe_model_id, {})
        rows.append(
            {
                "pipe_model_id": pipe_model_id,
                "pipe_model_name": pipe_model.get("pipe_model_name") or pipe_model_id,
                "unit": pipe_model.get("unit") or "",
                "usage_qty": usage_record.get("usage_qty"),
                "remark": usage_record.get("remark") or "",
            }
        )

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": station_id,
        "station_name": station_name_map.get(station_id, station_id),
        "usage_date": usage_date.isoformat(),
        "rows": rows,
    }


@router.post("/demand-management/usage-sheet", summary="保存需求侧实际使用表单")
def save_demand_management_usage_sheet(
    payload: DemandUsageSavePayload,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    config_payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(config_payload, session.username, session.group)
    _ensure_station_access(payload.station_id, accessible_station_ids)

    saved_count = save_usage_records(
        station_id=payload.station_id,
        usage_date=payload.usage_date,
        records=[item.model_dump() for item in payload.records],
        operator=session.username,
    )
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": payload.station_id,
        "usage_date": payload.usage_date.isoformat(),
        "saved_count": saved_count,
    }


@router.get("/demand-management/pending-arrivals", summary="读取需求侧待确认到货记录")
def get_demand_management_pending_arrivals(
    station_id: str,
    session: AuthSession = Depends(get_current_session),
) -> Dict[str, Any]:
    payload = load_tube_config()
    accessible_station_ids = resolve_accessible_station_ids(payload, session.username, session.group)
    _ensure_station_access(station_id, accessible_station_ids)

    station_name_map = _build_station_name_map(payload)
    supply_entity_map = _build_supply_entity_map(payload)
    pipe_model_map = _build_pipe_model_map(payload)
    rows = list_pending_arrivals(station_id)
    for row in rows:
        supply_entity = supply_entity_map.get(row["supply_entity_id"], {})
        pipe_model = pipe_model_map.get(row["pipe_model_id"], {})
        row["supply_entity_name"] = supply_entity.get("entity_name") or row["supply_entity_id"]
        row["pipe_model_name"] = pipe_model.get("pipe_model_name") or row["pipe_model_id"]

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "station_id": station_id,
        "station_name": station_name_map.get(station_id, station_id),
        "rows": rows,
    }
