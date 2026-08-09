# -*- coding: utf-8 -*-
"""
tube 项目配置读取服务。
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Set

from fastapi import HTTPException
from backend.services.project_data_paths import get_project_root


PROJECT_KEY = "insulation_pipe_supply_2026"
PROJECT_DATA_DIR = get_project_root(PROJECT_KEY)
CONFIG_PATH = PROJECT_DATA_DIR / "tube_config.json"
SUBMISSION_STATUS_PATH = PROJECT_DATA_DIR / "section_1_submission_status.json"

BEIJING_TZ = timezone(timedelta(hours=8))
BUSINESS_DATE_SWITCH_HOUR = 6
BUSINESS_DATE_SWITCH_MINUTE = 30
AUTO_UPDATE_MODE_MANUAL = "manual"
AUTO_UPDATE_MODE_PLAN_USAGE = "plan_usage"
AUTO_UPDATE_MODE_ALL = "all"


def _get_beijing_business_date(now: datetime | None = None) -> date:
    """返回以北京时间 06:30 为换日点的业务当天。"""
    current = now or datetime.now(BEIJING_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=BEIJING_TZ)
    else:
        current = current.astimezone(BEIJING_TZ)
    switch_time = current.replace(
        hour=BUSINESS_DATE_SWITCH_HOUR,
        minute=BUSINESS_DATE_SWITCH_MINUTE,
        second=0,
        microsecond=0,
    )
    if current < switch_time:
        return current.date() - timedelta(days=1)
    return current.date()


def get_date_auto_update_mode(payload: Dict[str, Any]) -> str:
    """兼容旧布尔值，并识别新增的“全部是”模式。"""
    raw_value = payload.get("auto_update_plan_start_date")
    if isinstance(raw_value, str):
        normalized_value = raw_value.strip().lower()
        if normalized_value == AUTO_UPDATE_MODE_ALL:
            return AUTO_UPDATE_MODE_ALL
        if normalized_value in {"true", "1", "yes", AUTO_UPDATE_MODE_PLAN_USAGE}:
            return AUTO_UPDATE_MODE_PLAN_USAGE
        return AUTO_UPDATE_MODE_MANUAL
    if bool(raw_value):
        return AUTO_UPDATE_MODE_PLAN_USAGE
    return AUTO_UPDATE_MODE_MANUAL

ENCRYPT_PREFIX = "enc_v1:"
AMAP_SECRET_KEY = "phoenix_amap_key_2026"

DEFAULT_AMAP_KEY = "7939c670de3699077dc6b498cd95346f"
DEFAULT_AMAP_SECURITY_CODE = "7573fa30e86735d98bafb40466822b3a"


def simple_encrypt(plain_text: str) -> str:
    """
    简单 XOR + Base64 加密算法，返回以 enc_v1: 为前缀的加密字符串
    """
    if not plain_text:
        return ""
    str_val = str(plain_text).strip()
    if str_val.startswith(ENCRYPT_PREFIX):
        return str_val
    
    key_bytes = AMAP_SECRET_KEY.encode('utf-8')
    text_bytes = str_val.encode('utf-8')
    xored = bytearray()
    for i, b in enumerate(text_bytes):
        xored.append(b ^ key_bytes[i % len(key_bytes)])
    
    encoded = base64.b64encode(xored).decode('utf-8')
    return f"{ENCRYPT_PREFIX}{encoded}"


def simple_decrypt(cipher_text: str) -> str:
    """
    简单 XOR + Base64 解密算法，将以 enc_v1: 为前缀的加密字符串还原为明文
    """
    if not cipher_text:
        return ""
    raw_str = str(cipher_text).strip()
    if not raw_str.startswith(ENCRYPT_PREFIX):
        return raw_str
    
    encoded = raw_str[len(ENCRYPT_PREFIX):]
    try:
        xored = base64.b64decode(encoded.encode('utf-8'))
        key_bytes = AMAP_SECRET_KEY.encode('utf-8')
        text_bytes = bytearray()
        for i, b in enumerate(xored):
            text_bytes.append(b ^ key_bytes[i % len(key_bytes)])
        return text_bytes.decode('utf-8')
    except Exception:
        return raw_str


def get_configured_amap_config(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    从 tube_config.json 提取解密后的高德地图 API 配置
    若未配置则使用默认值并可进行初始化加密存储
    """
    raw_config = payload.get("amap_config")
    if not isinstance(raw_config, dict):
        raw_config = {}
    
    api_key_cipher = str(raw_config.get("api_key") or "").strip()
    security_code_cipher = str(raw_config.get("security_code") or "").strip()
    
    api_key = simple_decrypt(api_key_cipher) if api_key_cipher else DEFAULT_AMAP_KEY
    security_code = simple_decrypt(security_code_cipher) if security_code_cipher else DEFAULT_AMAP_SECURITY_CODE
    
    return {
        "api_key": api_key,
        "security_code": security_code,
    }


def load_tube_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="tube_config.json 不存在")
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"tube_config.json 格式错误：{exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="tube_config.json 顶层必须为对象")
    
    # 确保 amap_config 节点存在并密文存储
    if "amap_config" not in payload:
        payload["amap_config"] = {
            "api_key": simple_encrypt(DEFAULT_AMAP_KEY),
            "security_code": simple_encrypt(DEFAULT_AMAP_SECURITY_CODE),
        }
        try:
            save_tube_config(payload)
        except Exception:
            pass

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


def load_section_1_submission_status() -> Dict[str, Any]:
    if not SUBMISSION_STATUS_PATH.exists():
        return {
            "latest_submissions": [],
            "history_submissions": [],
        }
    try:
        payload = json.loads(SUBMISSION_STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"section_1_submission_status.json 格式错误：{exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="section_1_submission_status.json 顶层必须为对象")
    latest_submissions = payload.get("latest_submissions")
    history_submissions = payload.get("history_submissions")
    return {
        "latest_submissions": latest_submissions if isinstance(latest_submissions, list) else [],
        "history_submissions": history_submissions if isinstance(history_submissions, list) else [],
    }


def save_section_1_submission_status(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="section_1_submission_status.json 顶层必须为对象")
    temp_path = SUBMISSION_STATUS_PATH.with_name(SUBMISSION_STATUS_PATH.name + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(SUBMISSION_STATUS_PATH)


def get_configured_show_date(payload: Dict[str, Any]) -> date:
    if get_date_auto_update_mode(payload) == AUTO_UPDATE_MODE_ALL:
        return _get_beijing_business_date() - timedelta(days=1)
    raw_value = str(payload.get("show_date") or payload.get("biz_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 show_date 非法：{raw_value}") from exc
    return get_configured_plan_start_date(payload) - timedelta(days=1)


def get_configured_plan_start_date(payload: Dict[str, Any]) -> date:
    if get_date_auto_update_mode(payload) != AUTO_UPDATE_MODE_MANUAL:
        return _get_beijing_business_date()
    raw_value = str(payload.get("plan_start_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 plan_start_date 非法：{raw_value}") from exc
    return _get_beijing_business_date()


def get_usage_collection_date(payload: Dict[str, Any]) -> date:
    if get_date_auto_update_mode(payload) != AUTO_UPDATE_MODE_MANUAL:
        return get_configured_plan_start_date(payload) - timedelta(days=1)
    raw_value = str(payload.get("usage_collection_date") or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"tube_config.json 中 usage_collection_date 非法：{raw_value}") from exc
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


def _extract_normalized_ids(raw_value: Any) -> Set[str]:
    result: Set[str] = set()
    if not raw_value:
        return result
    if isinstance(raw_value, str):
        parts = raw_value.split(",")
    elif isinstance(raw_value, (list, tuple, set)):
        parts = []
        for sub in raw_value:
            if isinstance(sub, str):
                parts.extend(sub.split(","))
            else:
                parts.append(str(sub))
    else:
        parts = [str(raw_value)]

    for part in parts:
        cleaned = str(part or "").strip()
        if cleaned:
            result.add(cleaned)
    return result


def resolve_accessible_section_1_ids(payload: Dict[str, Any], username: str, group: str) -> Set[str]:
    normalized_group = str(group or "").strip()
    normalized_username = str(username or "").strip()
    demand_entities = get_config_list(payload, "demand_entities")
    all_section_1_ids = {
        str(item.get("section_1_id") or "").strip()
        for item in demand_entities
        if str(item.get("section_1_id") or "").strip()
    }
    if normalized_group in ("Global_admin", "tube_global_viewer", "tube_supplier_admin"):
        return all_section_1_ids

    manager_assignments = get_config_list(payload, "manager_assignments")
    allowed_section_1_ids: Set[str] = set()

    supply_entities = get_config_list(payload, "supply_entities")
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        candidate_keys = {
            entity_id,
            str(item.get("entity_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username in candidate_keys:
            allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    for item in manager_assignments:
        candidate_keys = {
            str(item.get("manager_id") or "").strip(),
            str(item.get("manager_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username not in candidate_keys:
            continue
        allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    construction_units = get_config_list(payload, "construction_units")
    for item in construction_units:
        candidate_keys = {
            str(item.get("unit_id") or "").strip(),
            str(item.get("unit_name") or "").strip(),
            str(item.get("username") or "").strip(),
        }
        if normalized_username not in candidate_keys:
            continue
        allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))
    return allowed_section_1_ids


def resolve_supply_entity_allowed_section_ids(payload: Dict[str, Any], supply_entity_id: str) -> Set[str]:
    normalized_id = str(supply_entity_id or "").strip()
    if not normalized_id:
        return set()
    supply_entities = get_config_list(payload, "supply_entities")
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        if entity_id == normalized_id:
            return _extract_normalized_ids(item.get("section_1_ids"))
    return set()


def resolve_accessible_supply_entity_ids(payload: Dict[str, Any], username: str, group: str) -> Set[str]:
    normalized_group = str(group or "").strip()
    normalized_username = str(username or "").strip()
    supply_entities = get_config_list(payload, "supply_entities")
    all_entity_ids = {
        str(item.get("entity_id") or "").strip()
        for item in supply_entities
        if str(item.get("entity_id") or "").strip()
    }
    if normalized_group in ("Global_admin", "tube_global_viewer", "tube_supplier_admin"):
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
