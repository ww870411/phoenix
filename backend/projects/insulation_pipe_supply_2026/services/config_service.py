# -*- coding: utf-8 -*-
"""
tube 项目配置读取服务。
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Set

from fastapi import HTTPException
from backend.services.project_data_paths import get_project_root


PROJECT_KEY = "insulation_pipe_supply_2026"
PROJECT_DATA_DIR = get_project_root(PROJECT_KEY)
CONFIG_PATH = PROJECT_DATA_DIR / "tube_config.json"
SUBMISSION_STATUS_PATH = PROJECT_DATA_DIR / "station_submission_status.json"


def load_tube_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="tube_config.json 不存在")
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"tube_config.json 格式错误：{exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="tube_config.json 顶层必须为对象")
    return payload


def save_tube_config(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="tube_config.json 顶层必须为对象")
    temp_path = CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(CONFIG_PATH)


def load_station_submission_status() -> Dict[str, Any]:
    if not SUBMISSION_STATUS_PATH.exists():
        return {
            "latest_submissions": [],
            "history_submissions": [],
        }
    try:
        payload = json.loads(SUBMISSION_STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"station_submission_status.json 格式错误：{exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="station_submission_status.json 顶层必须为对象")
    latest_submissions = payload.get("latest_submissions")
    history_submissions = payload.get("history_submissions")
    return {
        "latest_submissions": latest_submissions if isinstance(latest_submissions, list) else [],
        "history_submissions": history_submissions if isinstance(history_submissions, list) else [],
    }


def save_station_submission_status(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="station_submission_status.json 顶层必须为对象")
    temp_path = SUBMISSION_STATUS_PATH.with_name(SUBMISSION_STATUS_PATH.name + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(SUBMISSION_STATUS_PATH)


def get_configured_show_date(payload: Dict[str, Any]) -> date:
    raw_value = str(payload.get("show_date") or payload.get("biz_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 show_date 非法：{raw_value}") from exc
    return get_configured_plan_start_date(payload) - timedelta(days=1)


def get_configured_plan_start_date(payload: Dict[str, Any]) -> date:
    auto_update = bool(payload.get("auto_update_plan_start_date"))
    if auto_update:
        return date.today()
    raw_value = str(payload.get("plan_start_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 plan_start_date 非法：{raw_value}") from exc
    return date.today()


def get_usage_collection_date(payload: Dict[str, Any]) -> date:
    return get_configured_plan_start_date(payload) - timedelta(days=1)


def get_configured_plan_editable_days(payload: Dict[str, Any]) -> int:
    raw_value = payload.get("plan_editable_days")
    if raw_value in (None, ""):
        return 3
    try:
        normalized_value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"tube_config.json 中 plan_editable_days 非法：{raw_value}") from exc
    if normalized_value < 0 or normalized_value > 3:
        raise HTTPException(status_code=500, detail=f"tube_config.json 中 plan_editable_days 超出范围：{normalized_value}")
    return normalized_value


def get_config_list(payload: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def resolve_accessible_station_ids(payload: Dict[str, Any], username: str, group: str) -> Set[str]:
    normalized_group = str(group or "").strip()
    normalized_username = str(username or "").strip()
    demand_entities = get_config_list(payload, "demand_entities")
    all_station_ids = {
        str(item.get("station_id") or "").strip()
        for item in demand_entities
        if str(item.get("station_id") or "").strip()
    }
    if normalized_group == "Global_admin":
        return all_station_ids

    manager_assignments = get_config_list(payload, "manager_assignments")
    allowed_station_ids: Set[str] = set()
    for item in manager_assignments:
        candidate_keys = {
            str(item.get("manager_id") or "").strip(),
            str(item.get("manager_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username not in candidate_keys:
            continue
        for station_id in item.get("station_ids") or []:
            normalized_station_id = str(station_id or "").strip()
            if normalized_station_id:
                allowed_station_ids.add(normalized_station_id)

    construction_units = get_config_list(payload, "construction_units")
    for item in construction_units:
        candidate_keys = {
            str(item.get("unit_id") or "").strip(),
            str(item.get("unit_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username not in candidate_keys:
            continue
        for station_id in item.get("station_ids") or []:
            normalized_station_id = str(station_id or "").strip()
            if normalized_station_id:
                allowed_station_ids.add(normalized_station_id)
    return allowed_station_ids


def resolve_accessible_supply_entity_ids(payload: Dict[str, Any], username: str, group: str) -> Set[str]:
    normalized_group = str(group or "").strip()
    normalized_username = str(username or "").strip()
    supply_entities = get_config_list(payload, "supply_entities")
    all_entity_ids = {
        str(item.get("entity_id") or "").strip()
        for item in supply_entities
        if str(item.get("entity_id") or "").strip()
    }
    if normalized_group == "Global_admin":
        return all_entity_ids

    allowed_entity_ids: Set[str] = set()
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        candidate_keys = {
            entity_id,
            str(item.get("entity_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username in candidate_keys and entity_id:
            allowed_entity_ids.add(entity_id)
    return allowed_entity_ids
