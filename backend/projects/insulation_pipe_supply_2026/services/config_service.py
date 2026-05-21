# -*- coding: utf-8 -*-
"""
tube 项目配置读取服务。
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Set

from fastapi import HTTPException


PROJECT_KEY = "insulation_pipe_supply_2026"
PROJECT_DATA_DIR = Path(__file__).resolve().parents[4] / "backend_data" / "projects" / PROJECT_KEY
CONFIG_PATH = PROJECT_DATA_DIR / "tube_config.json"


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


def get_configured_biz_date(payload: Dict[str, Any]) -> date:
    raw_value = str(payload.get("biz_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 biz_date 非法：{raw_value}") from exc
    return date.today() - timedelta(days=1)


def get_configured_plan_start_date(payload: Dict[str, Any]) -> date:
    raw_value = str(payload.get("plan_start_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 plan_start_date 非法：{raw_value}") from exc
    return get_configured_biz_date(payload)


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
    return allowed_station_ids
