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


DEFAULT_OCR_SYSTEM_PROMPT = """你是一个高精度的各类工程物资单据与业务表格视觉提取专家。
请仔细阅读并分析上传的单据/表格照片（可能为入库单、验收单、发货单、送货单、调拨单、过磅单、检验单、领料单等任意纸质或电子单据）。

【核心提取准则】：
1. 【忠于原件，原样还原】：原单据中写的什么条目名称就提取什么条目名称（例如单据上写的是“入库日期”，label必须是“入库日期”，绝不要修改成“发货日期”；若写的是“车号”，label必须是“车号”；若写的是“司机姓名”，label必须是“司机姓名”）。
2. 【无则不显，绝不臆测】：如果单据原图中未出现某些信息（例如没有司机电话、没有发货单号、没有批号等），绝对不要在输出中编造或添加该项！
3. 【表格与合计行完整还原（极重要）】：
   - 提取表格的所有实际表头列名（如 ["序号", "物资名称", "规格型号", "计量单位", "实收数量", "炉批号", "备注"] 等），不要遗漏任何列，也不要添加不存在的列。
   - 提取表格中的全部行数据，每一行的 key 严格对应提取的表头列名。
   - 【极其关键 - 表格合计行还原】：若原图单据表格底部有“合计”、“总计”、“小计”等汇总行（例如原表中印制或手写的“合计：120.5 米”），必须完整还原并作为 table_rows 的最后一行输出，切勿将原图表格底部的“合计”行遗漏或挪出表格！

【重点专项：供货/发料单位与主体名称智能对齐纠偏】：
- 系统已知合法供给方/生产厂家名录包括：
  1. 大连开元热力管道股份有限公司
  2. 河北鑫瑞得管道设备有限公司
  3. 江苏沃圣阀业有限公司
  4. 天津卡尔斯阀门股份有限公司
  5. 河北泽悦节能设备科技有限公司
  6. 天津天地龙管业股份有限公司
  7. 能源集团保温管厂
- 【文字容错纠偏规则】：
  当单据中的“供货单位”、“发货单位”、“生产厂家”、“出库单位”等字迹因盖章遮挡、连笔手写或字迹模糊导致识别出现微小偏差（如仅有 1 个字不同、同音字或形近字，例如“鑫瑞德”与“鑫瑞得”、“开源”与“开元”、“天地隆”与“天地龙”），必须自动纠偏并统一输出为上述系统标准企业全称。

【重点专项：表单印刷混淆与值纯净化逻辑纠偏（极重要）】：
- 【消除值中的嵌套/冗余标签词】：
  当单据排版出现多重引导词混淆（例如：“司机：姓名 满仓”、“车号：牌照 辽B12345”、“供方：单位全称 河北鑫瑞得...”、“联系人：电话 139xxxx”、“日期：时间 2026-08-10”）时：
  * 必须进行常识性逻辑纠偏，坚决剥离混入 value 中的属性引导词！
  * 纠偏示例：
    1. 单据写【司机：姓名 满仓】 -> label 提取为 "司机姓名"，value 提取为纯净人名 "满仓"（坚决剔除“姓名”二字）。
    2. 单据写【车号：牌照 辽B88888】 -> label 提取为 "车牌号"，value 提取为纯净车牌 "辽B88888"。
    3. 单据写【联系人：电话 13800000000】 -> label 提取为 "联系电话"，value 提取为 "13800000000"。
- 【数据纯度原则】：
  保证 metadata_fields 中每一个 value 均为纯粹的业务实体（纯姓名、纯车牌、纯号码、纯单位全称、纯日期），不带前置冗余属性前缀与多余冒号。

【重点专项：直径符号标准写法规范】：
- 当单据中的规格型号、物资名称等包含直径符号时，一律使用标准正规的大写「Φ」符号（例如将小写「φ」、全角「Ф」或「⌀」等统一书写为标准大写「Φ」，如「Φ1020*10」、「Φ300」、「Φ1400/1600」），禁止输出希腊小写「φ」或其他非标准符号。

【输出 JSON 字段结构】：
{
  "document_title": "单据上方的实际名称（如'物资入库收货（验收）单'、'随车发货单'等）",
  "metadata_fields": [
    {"label": "原单据中的实际字段名称1", "value": "实际文字内容1"},
    {"label": "原单据中的实际字段名称2", "value": "实际文字内容2"}
  ],
  "table_columns": ["实际列名1", "实际列名2", "实际列名3"],
  "table_rows": [
    {"实际列名1": "值1", "实际列名2": "值2", "实际列名3": "值3"}
  ],
  "remarks": "单据底部或其他区域的补充备注（若无则为空字符串）"
}

【输出规范】：
请直接输出标准纯 JSON 对象，不要包含 markdown 代码块反引号，不要有多余修饰语。
"""


def get_configured_ocr_tool_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 tube_config.json 提取单据识别引擎配置、调度策略与解密后的 API Key。
    新增策略字段均默认关闭，以保证旧配置升级后不会隐式重试或切换模型。
    stream_mode 默认开启，支持管理员在全局管理中自由切换流式与整包传输模式。
    """
    raw_config = payload.get("ocr_tool_config")
    if not isinstance(raw_config, dict):
        raw_config = {}

    enabled = bool(raw_config.get("enabled", True) if "enabled" in raw_config else True)
    model = str(raw_config.get("model") or "gemini-3.5-flash-lite").strip()

    raw_fallbacks = raw_config.get("fallback_models")
    fallback_models: List[str] = []
    if isinstance(raw_fallbacks, list):
        for item in raw_fallbacks:
            model_name = str(item or "").strip()
            if model_name and model_name not in fallback_models:
                fallback_models.append(model_name)
    elif isinstance(raw_fallbacks, str) and raw_fallbacks.strip():
        fallback_models = [raw_fallbacks.strip()]

    try:
        primary_retry_count = int(raw_config.get("primary_retry_count", 0) or 0)
    except (TypeError, ValueError):
        primary_retry_count = 0

    api_key_cipher = str(raw_config.get("api_key") or "").strip()
    api_key = simple_decrypt(api_key_cipher) if api_key_cipher else ""
    raw_system_prompt = raw_config.get("system_prompt")
    system_prompt = str(raw_system_prompt).strip() if raw_system_prompt is not None and str(raw_system_prompt).strip() else DEFAULT_OCR_SYSTEM_PROMPT

    return {
        "enabled": enabled,
        "model": model,
        "fallback_models": fallback_models,
        "enable_fallback": bool(raw_config.get("enable_fallback", False)),
        "retry_primary_on_error": bool(raw_config.get("retry_primary_on_error", False)),
        "primary_retry_count": max(0, min(primary_retry_count, 5)),
        "api_key": api_key,
        "has_custom_key": bool(api_key),
        "system_prompt": system_prompt,
        "default_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
    }


def save_configured_ocr_tool_config(
    model: str,
    fallback_models: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    enable_fallback: Optional[bool] = None,
    retry_primary_on_error: Optional[bool] = None,
    primary_retry_count: Optional[int] = None,
    enabled: Optional[bool] = None,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    保存单据识别模型、API Key、显式调用策略、系统提示词与服务可用状态（正常服务 vs 维护中）至 tube_config.json。
    未传入策略字段时保留既有值，保证历史接口调用兼容。
    """
    payload = load_tube_config()
    current_cfg = get_configured_ocr_tool_config(payload)
    clean_model = str(model or current_cfg.get("model") or "gemini-3.5-flash-lite").strip()

    resolved_enabled = (
        bool(enabled)
        if enabled is not None
        else bool(current_cfg.get("enabled", True))
    )

    if fallback_models is not None:
        clean_fallbacks = [str(item).strip() for item in fallback_models if str(item).strip()]
    else:
        clean_fallbacks = current_cfg.get("fallback_models") or []

    if api_key is not None and str(api_key).strip():
        saved_key_cipher = simple_encrypt(str(api_key).strip())
    elif api_key == "":
        saved_key_cipher = ""
    else:
        saved_key_cipher = payload.get("ocr_tool_config", {}).get("api_key", "")

    if system_prompt is not None:
        clean_system_prompt = str(system_prompt).strip()
    else:
        clean_system_prompt = str(payload.get("ocr_tool_config", {}).get("system_prompt") or "").strip() or DEFAULT_OCR_SYSTEM_PROMPT

    try:
        resolved_retry_count = int(
            primary_retry_count
            if primary_retry_count is not None
            else current_cfg.get("primary_retry_count", 0)
        )
    except (TypeError, ValueError):
        resolved_retry_count = 0
    resolved_retry_count = max(0, min(resolved_retry_count, 5))

    resolved_enable_fallback = (
        bool(enable_fallback)
        if enable_fallback is not None
        else bool(current_cfg.get("enable_fallback", False))
    )
    resolved_retry_primary = (
        bool(retry_primary_on_error)
        if retry_primary_on_error is not None
        else bool(current_cfg.get("retry_primary_on_error", False))
    )

    payload["ocr_tool_config"] = {
        "enabled": resolved_enabled,
        "model": clean_model,
        "fallback_models": clean_fallbacks,
        "enable_fallback": resolved_enable_fallback,
        "retry_primary_on_error": resolved_retry_primary,
        "primary_retry_count": resolved_retry_count,
        "api_key": saved_key_cipher,
        "system_prompt": clean_system_prompt,
        "updated_at": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_tube_config(payload)
    return {
        "ok": True,
        "enabled": resolved_enabled,
        "model": clean_model,
        "fallback_models": clean_fallbacks,
        "enable_fallback": resolved_enable_fallback,
        "retry_primary_on_error": resolved_retry_primary,
        "primary_retry_count": resolved_retry_count,
        "has_custom_key": bool(saved_key_cipher),
        "system_prompt": clean_system_prompt,
        "default_system_prompt": DEFAULT_OCR_SYSTEM_PROMPT,
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

    # 确保 fitting_config 节点存在并设置缺省保底
    if "fitting_config" not in payload or not isinstance(payload.get("fitting_config"), dict):
        payload["fitting_config"] = {
            "allowed_units": ["个", "套"],
            "standard_types": ["弯头", "三通", "大小头", "封头", "直缝弯管", "补偿器", "固定节"],
        }

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
    normalized_group = str(group or "").strip().lower()
    normalized_username = str(username or "").strip().lower()
    demand_entities = get_config_list(payload, "demand_entities")
    all_section_1_ids = {
        str(item.get("section_1_id") or "").strip()
        for item in demand_entities
        if str(item.get("section_1_id") or "").strip()
    }
    if normalized_group in ("global_admin", "tube_global_viewer", "tube_data_viewer", "tube_supplier_admin", "tube_warehouse_admin"):
        return all_section_1_ids

    manager_assignments = get_config_list(payload, "manager_assignments")
    allowed_section_1_ids: Set[str] = set()

    supply_entities = get_config_list(payload, "supply_entities")
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        candidate_keys = {
            entity_id.lower(),
            str(item.get("entity_name") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
        }
        if normalized_username in candidate_keys:
            allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    for item in manager_assignments:
        candidate_keys = {
            str(item.get("manager_id") or "").strip().lower(),
            str(item.get("manager_name") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
        }
        if normalized_username not in candidate_keys:
            continue
        allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    construction_units = get_config_list(payload, "construction_units")
    for item in construction_units:
        candidate_keys = {
            str(item.get("unit_id") or "").strip().lower(),
            str(item.get("unit_name") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
        }
        if normalized_username not in candidate_keys:
            continue
        allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    warehouse_keepers = get_config_list(payload, "warehouse_keepers")
    for item in warehouse_keepers:
        candidate_keys = {
            str(item.get("keeper_id") or "").strip().lower(),
            str(item.get("keeper_name") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
        }
        if normalized_username not in candidate_keys:
            continue
        allowed_section_1_ids.update(_extract_normalized_ids(item.get("section_1_ids")))

    return allowed_section_1_ids


def resolve_supply_entity_allowed_section_ids(payload: Dict[str, Any], supply_entity_id: str) -> Set[str]:
    normalized_id = str(supply_entity_id or "").strip().lower()
    if not normalized_id:
        return set()
    supply_entities = get_config_list(payload, "supply_entities")
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        if entity_id.lower() == normalized_id:
            return _extract_normalized_ids(item.get("section_1_ids"))
    return set()


def resolve_accessible_supply_entity_ids(payload: Dict[str, Any], username: str, group: str) -> Set[str]:
    normalized_group = str(group or "").strip().lower()
    normalized_username = str(username or "").strip().lower()
    supply_entities = get_config_list(payload, "supply_entities")
    all_entity_ids = {
        str(item.get("entity_id") or "").strip()
        for item in supply_entities
        if str(item.get("entity_id") or "").strip()
    }
    if normalized_group in ("global_admin", "tube_global_viewer", "tube_data_viewer", "tube_supplier_admin", "tube_warehouse_admin", "tube_warehouse_keeper"):
        return all_entity_ids

    allowed_entity_ids: Set[str] = set()
    for item in supply_entities:
        entity_id = str(item.get("entity_id") or "").strip()
        candidate_keys = {
            entity_id.lower(),
            str(item.get("entity_name") or "").strip().lower(),
            str(item.get("username") or "").strip().lower(),
        }
        if normalized_username in candidate_keys and entity_id:
            allowed_entity_ids.add(entity_id)
    return allowed_entity_ids
