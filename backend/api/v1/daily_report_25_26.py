"""
daily_report_25_26 项目 v1 路由

说明：
- 所有接口挂载在 `/api/v1/daily_report_25_26` 前缀下。
- 当前实现模板读取功能，提交与查询仍保留占位实现，后续可逐步替换。
- 模板文件来源于容器内数据目录（默认 `/app/data`）中的 JSON 配置。
"""

import copy
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path as SysPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy import bindparam, delete, text

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import (
    CoalInventoryData,
    ConstantData,
    DailyBasicData,
    SessionLocal,
)
from backend.schemas.auth import (
    WorkflowApproveRequest,
    WorkflowRevokeRequest,
    WorkflowPublishRequest,
    WorkflowPublishStatus,
    WorkflowStatusResponse,
    WorkflowUnitStatus,
)
from backend.services import dashboard_cache
from backend.services.auth_manager import EAST_8, AuthSession, auth_manager, get_current_session
from backend.services.dashboard_expression import evaluate_dashboard, load_default_push_date
from backend.services.dashboard_cache_job import cache_publish_job_manager
from backend.services.runtime_expression import render_spec
from backend.services.workflow_status import workflow_status_manager
from backend.services.weather_importer import (
    WeatherImporterError,
    fetch_hourly_temperatures,
    compare_with_existing,
    persist_hourly_temperatures,
)





# Use统一的数据目录常量，默认指向容器内 /app/data
from backend.services import data_analysis as data_analysis_service
from backend.services import data_analysis_ai_report

DATA_ROOT = SysPath(DATA_DIRECTORY)
PROJECT_KEY = "daily_report_25_26"
COAL_INVENTORY_DEBUG_FILE = DATA_ROOT / "test.md"
GONGRE_DEBUG_FILE = SysPath(__file__).resolve().parents[3] / "configs" / "111.md"
GONGRE_SHEET_KEYS = {"gongre_branches_detail_sheet"}
BASIC_TEMPLATE_PATH = DATA_ROOT / "数据结构_基本指标表.json"
DATA_ANALYSIS_SCHEMA_PATH = DATA_ROOT / "数据结构_数据分析表.json"
APPROVAL_STRUCTURE_PATH = DATA_ROOT / "数据结构_审批用表.json"
CONSTANT_STRUCTURE_PATH = DATA_ROOT / "数据结构_常量指标表.json"
COAL_STORAGE_NAME_MAP = {
    "在途煤炭": ("coal_in_transit", "在途煤炭"),
    "港口存煤": ("coal_at_port", "港口存煤"),
    "厂内存煤": ("coal_at_plant", "厂内存煤"),
}
TEMPERATURE_COLUMN_MAP = data_analysis_service.TEMPERATURE_COLUMN_MAP
TEMPERATURE_UNIT = data_analysis_service.TEMPERATURE_UNIT
MAX_TIMELINE_DAYS = data_analysis_service.MAX_TIMELINE_DAYS
BEIHAI_SUB_SCOPES = {"BeiHai_co_generation_Sheet", "BeiHai_water_boiler_Sheet"}

logger = logging.getLogger(__name__)

def _is_coal_inventory_sheet(name: Optional[str], tpl_payload: Optional[Dict[str, Any]] = None) -> bool:
    """
    识别煤炭库存类报表：
    - 名称启发：包含 "coal_inventory" 或 "Coal_inventory"（不区分大小写）。
    - 结构启发：模板列头中包含 COAL_STORAGE_NAME_MAP 的任一中文列名（如“在途煤炭/港口存煤/厂内存煤”）。
    """
    if isinstance(name, str) and name:
        lowered = name.lower()
        if "coal_inventory" in lowered:
            return True
    if isinstance(tpl_payload, dict):
        columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
        if isinstance(columns_raw, list):
            col_set = {str(c).strip() for c in columns_raw if c is not None}
            for cn in COAL_STORAGE_NAME_MAP.keys():
                if cn in col_set:
                    return True
    return False


def _resolve_data_file(path_expression: Optional[str]) -> Optional[SysPath]:
    """将相对路径解析为 DATA_ROOT 下的实际文件路径。"""
    if not path_expression:
        return None
    normalized = path_expression.strip()
    if not normalized:
        return None
    candidate = SysPath(normalized)
    if not candidate.is_absolute():
        candidate = (DATA_ROOT / normalized).resolve()
    else:
        candidate = candidate.resolve()
    try:
        candidate.relative_to(DATA_ROOT.resolve())
    except ValueError:
        return None
    if not candidate.exists():
        return None
    return candidate

def _load_data_file_candidates() -> List[str]:
    candidates: Set[SysPath] = {BASIC_TEMPLATE_PATH.resolve()}
    project_config_path = DATA_ROOT / "项目列表.json"
    if project_config_path.exists():
        try:
            raw = json.loads(project_config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = None
        if isinstance(raw, dict):
            for _project_id, project in raw.items():
                if not isinstance(project, dict):
                    continue
                pages = project.get("pages")
                if isinstance(pages, dict):
                    for _page_key, meta in pages.items():
                        if not isinstance(meta, dict):
                            continue
                        ds = meta.get("数据源") or meta.get("data_source")
                        if isinstance(ds, str) and ds.strip():
                            candidate = _resolve_data_file(ds.strip())
                            if candidate:
                                candidates.add(candidate)
                elif isinstance(pages, list):
                    for entry in pages:
                        if not isinstance(entry, dict):
                            continue
                        for _, relative_path in entry.items():
                            if not isinstance(relative_path, str):
                                continue
                            normalized = relative_path.strip()
                            if not normalized:
                                continue
                            candidate = _resolve_data_file(normalized)
                            if candidate:
                                candidates.add(candidate)
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                pages = item.get("pages")
                if isinstance(pages, list):
                    for entry in pages:
                        if not isinstance(entry, dict):
                            continue
                        for _, relative_path in entry.items():
                            if not isinstance(relative_path, str):
                                continue
                            normalized = relative_path.strip()
                            if not normalized:
                                continue
                            candidate = _resolve_data_file(normalized)
                            if candidate:
                                candidates.add(candidate)
    return [str(path) for path in candidates]


DATA_FILE_CANDIDATES = _load_data_file_candidates()
# otherwise, fall back to a path relative to the project root (for local dev).


    # Path inside container, e.g., /app/data



    # Path for local development



EAST_8_TZ = timezone(timedelta(hours=8))

# The only data file we need to read, as requested by the user.

BASIC_DATA_FILE = BASIC_TEMPLATE_PATH
UNIT_KEYS = ("unit_id", "单位标识", "单位中文名", "单位名", "unit_name")
SHEET_NAME_KEYS = ("表名", "表中文名", "表类别", "sheet_name")
COLUMN_KEYS = ("列名", "columns", "表头", "列名1", "列名2")
ROW_KEYS = ("数据", "rows", "records", "lines")
ITEM_DICT_KEYS = ("item_dict", "项目字典")
COMPANY_DICT_KEYS = ("company_dict", "单位字典", "unit_dict")
CENTER_DICT_KEYS = ("center_dict", "中心字典")
STATUS_DICT_KEYS = ("status_dict", "状态字典")
LINKAGE_DICT_KEYS = ("linkage_dict", "指标联动")
VALIDATION_RULE_KEYS = ("validation_rules", "校验规则", "数据校验")
DICT_KEY_GROUPS = {
    "item_dict": ITEM_DICT_KEYS,
    "company_dict": COMPANY_DICT_KEYS,
    "center_dict": CENTER_DICT_KEYS,
    "status_dict": STATUS_DICT_KEYS,
    "linkage_dict": LINKAGE_DICT_KEYS,
    "validation_rules": VALIDATION_RULE_KEYS,
}


def _iter_data_files() -> Iterable[SysPath]:
    """返回所有存在的候选数据文件路径。"""
    seen: Set[SysPath] = set()
    for candidate in DATA_FILE_CANDIDATES:
        path = SysPath(candidate)
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield resolved


def _read_json(path: SysPath) -> Any:
    """尝试多种常见编码读取 JSON。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
        try:
            with path.open("r", encoding=enc) as fh:
                return json.load(fh)
        except Exception:
            continue
    raise FileNotFoundError(f"无法读取 JSON：{path}")


def _extract_names(payload: Dict[str, Any]) -> Dict[str, str]:
    unit_id = ""
    unit_name = ""
    sheet_name = ""

    for key in ("unit_id", "单位标识"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            unit_id = value.strip()
            break

    for key in ("单位中文名", "单位名称", "单位名", "unit_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            unit_name = value.strip()
            break

    for key in ("表名", "表中文名", "表类别", "sheet_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            sheet_name = value.strip()
            break

    return {
        "unit_id": unit_id,
        "unit_name": unit_name,
        "sheet_name": sheet_name or "",
    }


def _locate_sheet_payload(
    sheet_key: str,
    preferred_path: Optional[SysPath] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[SysPath], bool]:
    """在候选模板文件中按 sheet_key 查找配置，并返回对应的全局校验开关。"""

    def _consider(
        payload: Dict[str, Any],
        path: SysPath,
        global_validation_enabled: bool,
    ) -> Optional[Tuple[Dict[str, Any], SysPath, bool]]:
        if not isinstance(payload, dict):
            return None
        names = _extract_names(payload)
        if names["unit_id"]:
            return payload, path, global_validation_enabled
        return None

    best_payload: Optional[Dict[str, Any]] = None
    best_path: Optional[SysPath] = None
    best_global_flag: bool = True
    target_key_lower = sheet_key.lower()

    candidate_paths: List[SysPath] = []
    preferred_resolved: Optional[SysPath] = None
    if preferred_path is not None and preferred_path.exists():
        preferred_resolved = preferred_path.resolve()
        candidate_paths.append(preferred_resolved)

    for data_path in _iter_data_files():
        resolved = data_path.resolve()
        if preferred_resolved is not None and resolved == preferred_resolved:
            continue
        candidate_paths.append(resolved)

    for data_path in candidate_paths:
        try:
            raw = _read_json(data_path)
        except Exception:
            # 跳过不可读取/非 JSON 的候选文件，避免整体查询失败
            continue
        global_flag = _extract_global_validation_setting(raw)

        if isinstance(raw, dict):
            direct = raw.get(sheet_key)
            if isinstance(direct, dict):
                hit = _consider(direct, data_path, global_flag)
                if hit:
                    return hit
                if best_payload is None:
                    best_payload, best_path, best_global_flag = direct, data_path, global_flag

            for key, payload in raw.items():
                if not isinstance(payload, dict):
                    continue
                if key in {"__global_settings__", "__meta__", "全局配置"}:
                    continue
                if key.lower() == target_key_lower:
                    hit = _consider(payload, data_path, global_flag)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path, best_global_flag = payload, data_path, global_flag
                        continue
                names = _extract_names(payload)
                if names["sheet_name"] == sheet_key:
                    hit = _consider(payload, data_path, global_flag)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path, best_global_flag = payload, data_path, global_flag

        elif isinstance(raw, list):
            for payload in raw:
                if not isinstance(payload, dict):
                    continue
                candidate = payload.get("sheet_key")
                names = _extract_names(payload)
                if candidate == sheet_key or names["sheet_name"] == sheet_key:
                    hit = _consider(payload, data_path, global_flag)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path, best_global_flag = payload, data_path, global_flag

    return best_payload, best_path, best_global_flag


def _extract_list(payload: Dict[str, Any], keys: Iterable[str]) -> Optional[Iterable[Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return None

def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    if isinstance(value, list):
        converted: Dict[str, Any] = {}
        for item in value:
            if isinstance(item, dict):
                for item_key, item_value in item.items():
                    converted[str(item_key)] = item_value
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                converted[str(item[0])] = item[1]
        if converted:
            return converted
    return {}


def _extract_global_validation_setting(raw: Any) -> bool:
    def _try_from_mapping(mapping: Dict[str, Any]) -> Optional[bool]:
        for key in ("校验总开关", "validation_master_switch", "validation_master_toggle", "validation_enabled", "校验开关"):
            if key in mapping:
                return _coerce_bool(mapping.get(key), default=True)
        return None

    if isinstance(raw, dict):
        for key in ("__global_settings__", "__meta__", "全局配置"):
            settings = raw.get(key)
            if isinstance(settings, dict):
                result = _try_from_mapping(settings)
                if result is not None:
                    return result
        # 兼容直接在根上声明的场景
        root_result = _try_from_mapping(raw)
        if root_result is not None:
            return root_result
    return True


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return default


def _extract_validation_enabled(payload: Dict[str, Any], global_enabled: bool = True) -> bool:
    local_enabled = True
    for key in ("validation_enabled", "enable_validation", "校验开关", "validation_switch"):
        if key in payload:
            local_enabled = _coerce_bool(payload.get(key), default=True)
            break
    return global_enabled and local_enabled


def _extract_local_validation_switch(payload: Dict[str, Any]) -> bool:
    local_enabled = True
    for key in ("validation_enabled", "enable_validation", "校验开关", "validation_switch"):
        if key in payload:
            local_enabled = _coerce_bool(payload.get(key), default=True)
            break
    return local_enabled


def _load_master_validation_config() -> Tuple[bool, Dict[str, Any]]:
    path = BASIC_TEMPLATE_PATH
    if not path.exists():
        raise HTTPException(status_code=500, detail="基准模板文件不存在，无法读取校验开关。")
    try:
        raw = _read_json(path)
    except Exception as exc:  # pragma: no cover - 读取失败直接抛 500
        raise HTTPException(status_code=500, detail=f"读取模板文件失败：{path}") from exc
    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="模板文件不是 JSON 对象，无法解析全局校验开关。")
    flag = _extract_global_validation_setting(raw)
    return flag, raw


def _persist_master_validation_switch(enabled: bool) -> bool:
    _, raw = _load_master_validation_config()
    normalized = bool(enabled)
    global_settings = raw.get("__global_settings__")
    if not isinstance(global_settings, dict):
        global_settings = {}
    for key in ("校验总开关", "validation_master_switch", "validation_master_toggle", "validation_enabled"):
        global_settings[key] = normalized
    raw["__global_settings__"] = global_settings
    serialized = json.dumps(raw, ensure_ascii=False, indent=2)
    temp_path = BASIC_TEMPLATE_PATH.with_name(BASIC_TEMPLATE_PATH.name + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.write("\n")
        temp_path.replace(BASIC_TEMPLATE_PATH)
    except Exception as exc:  # pragma: no cover
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="写入模板文件失败，校验总开关未更新。") from exc
    return normalized


def _find_sheet_entry_key(raw: Dict[str, Any], sheet_key: str) -> Optional[str]:
    target_lower = sheet_key.lower()
    for key, payload in raw.items():
        if key in {"__global_settings__", "__meta__", "全局配置"}:
            continue
        if key == sheet_key or key.lower() == target_lower:
            return key
        if isinstance(payload, dict):
            names = _extract_names(payload)
            if names["sheet_name"] == sheet_key:
                return key
    return None


def _persist_sheet_validation_switch(
    sheet_key: str,
    enabled: bool,
    preferred_path: Optional[SysPath] = None,
) -> bool:
    payload, data_path, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
    if payload is None or data_path is None:
        raise HTTPException(status_code=404, detail=f"未找到 sheet_key={sheet_key} 的模板配置。")
    try:
        raw = _read_json(data_path)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"读取模板文件失败：{data_path}") from exc
    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="模板文件结构错误，无法更新校验开关。")
    entry_key = _find_sheet_entry_key(raw, sheet_key)
    if entry_key is None:
        raise HTTPException(status_code=404, detail=f"模板中未找到 {sheet_key} 对应的配置。")
    entry = raw.get(entry_key)
    if not isinstance(entry, dict):
        raise HTTPException(status_code=500, detail=f"{sheet_key} 配置格式异常，无法更新校验开关。")
    normalized = bool(enabled)
    for key in ("validation_enabled", "enable_validation", "校验开关", "validation_switch"):
        entry[key] = normalized
    raw[entry_key] = entry
    serialized = json.dumps(raw, ensure_ascii=False, indent=2)
    temp_path = data_path.with_name(data_path.name + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.write("\n")
        temp_path.replace(data_path)
    except Exception as exc:  # pragma: no cover
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail="写入模板文件失败，表级校验开关未更新。") from exc
    return normalized


def _extract_mapping(payload: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    for key in keys:
        mapping = _coerce_mapping(payload.get(key))
        if mapping:
            return mapping
    return {}


def _collect_all_dicts(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for canonical_key, aliases in DICT_KEY_GROUPS.items():
        for alias in aliases:
            mapping = _coerce_mapping(payload.get(alias))
            if mapping:
                result[canonical_key] = mapping
                break
    return result


def _is_gongre_sheet(name: Optional[str]) -> bool:
    if not name:
        return False
    return name.strip().lower() in GONGRE_SHEET_KEYS


def _write_gongre_branches_debug(payload: Dict[str, Any], records: List[Dict[str, Any]]) -> None:
    """将供热分中心调试信息写入 configs/111.md。"""
    GONGRE_DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(EAST_8_TZ).strftime("%Y-%m-%d %H:%M:%S")
    raw_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    parsed = json.dumps(records, ensure_ascii=False, indent=2)
    with GONGRE_DEBUG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"## GongRe Branches Detail Debug {timestamp}\n\n")
        fh.write("### Raw Payload\n```json\n")
        fh.write(raw_payload)
        fh.write("\n```\n\n### Parsed Records\n```json\n")
        fh.write(parsed)
        fh.write("\n```\n\n")


def _parse_gongre_branches_detail_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    将供热分中心表的 payload 拆解为结构化记录。
    修改：无论单元格是否为空，都生成记录，以便写入 NULL 或覆盖旧值。
    """
    columns = payload.get("columns") or []
    rows = payload.get("rows") or []
    if not columns or not rows:
        return []

    center_mapping = _extract_mapping(payload, CENTER_DICT_KEYS)
    if not center_mapping:
        # 兼容模板仅提供“单位字典”的场景
        center_mapping = _extract_mapping(payload, COMPANY_DICT_KEYS)
    center_lookup = _invert_mapping(center_mapping)

    item_mapping = _extract_mapping(payload, ITEM_DICT_KEYS)
    item_lookup = _invert_mapping(item_mapping)

    date_columns: List[Tuple[int, Any]] = []
    note_column: Optional[int] = None
    for idx, header in enumerate(columns):
        if idx < 3:
            continue
        header_text = str(header).strip() if header is not None else ""
        if not header_text:
            continue
        parsed_date = _parse_date_value(header_text)
        if parsed_date:
            date_columns.append((idx, parsed_date))
            continue
        if note_column is None and ("说明" in header_text or "备注" in header_text or "note" in header_text.lower()):
            note_column = idx

    if not date_columns:
        return []

    primary_measure_index = date_columns[0][0]
    status_value = str(payload.get("status") or "submit").strip() or "submit"
    submit_time = payload.get("submit_time")
    sheet_identifier = str(payload.get("sheet_key") or payload.get("sheet_name") or "").strip()

    parsed_records: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 3:
            continue

        item_cn = str(row[0]).strip() if row[0] is not None else ""
        center_cn = str(row[1]).strip() if row[1] is not None else ""
        unit_value = str(row[2]).strip() if row[2] is not None else ""

        if not item_cn or not center_cn:
            continue

        item_code = item_lookup.get(item_cn, item_cn)
        center_code = center_lookup.get(center_cn, center_cn)
        note_value = None
        if note_column is not None and note_column < len(row):
            candidate = str(row[note_column]).strip() if row[note_column] is not None else ""
            note_value = candidate or None

        for col_index, col_date in date_columns:
            cell_value = None  # 默认值为 None
            if col_index < len(row):
                raw_cell = row[col_index]
                if raw_cell is not None:
                    text = str(raw_cell).strip()
                    if text:
                        cell_value = text
            
            # 不再检查 cell_value is None 并 continue，而是始终生成记录
            parsed_records.append(
                {
                    "center": center_code,
                    "center_cn": center_cn,
                    "sheet_name": sheet_identifier,
                    "item": item_code,
                    "item_cn": item_cn,
                    "unit": unit_value or None,
                    "date": col_date.isoformat(),
                    "value": cell_value,  # 此处可能为 None
                    "note": note_value if col_index == primary_measure_index else None,
                    "status": status_value,
                    "operation_time": submit_time,
                }
            )

    return parsed_records


async def handle_gongre_branches_detail_submission(payload: Dict[str, Any]) -> JSONResponse:
    # 解析原始 payload → 分中心记录
    records = _parse_gongre_branches_detail_records(payload)
    _write_gongre_branches_debug(payload, records)

    # 将 center/center_cn 映射为 company/company_cn，统一写 daily_basic_data
    sheet_key = str(payload.get("sheet_key") or "GongRe_branches_detail_Sheet").strip() or "GongRe_branches_detail_Sheet"
    default_operation_time = _parse_operation_time(payload.get("submit_time"))
    default_status = (payload.get("status") or "submit").strip() or "submit"

    flattened: List[Dict[str, Any]] = []
    for r in records:
        row_date = _parse_date_value(r.get("date"))
        if row_date is None:
            continue
        flattened.append(
            {
                "company": str(r.get("center") or "").strip(),
                "company_cn": (str(r.get("center_cn") or "").strip() or None),
                "sheet_name": sheet_key,
                "item": str(r.get("item") or "").strip(),
                "item_cn": (str(r.get("item_cn") or "").strip() or None),
                "value": r.get("value"),
                "unit": (str(r.get("unit") or "").strip() or None),
                "note": (str(r.get("note") or "").strip() or None),
                "date": row_date.isoformat(),
                "status": str(r.get("status") or default_status).strip() or default_status,
                "operation_time": r.get("operation_time") or default_operation_time.isoformat(),
            }
        )

    normalized_hint = {
        "submit_time": payload.get("submit_time"),
        "unit_name": payload.get("unit_name"),
        "sheet_key": sheet_key,
    }
    inserted = _persist_daily_basic(payload, normalized_hint, flattened)
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "供热分中心数据已处理（统一写入 daily_basic_data）",
            "records": len(records),
            "inserted": inserted,
        },
    )


def _resolve_company_name(unit_id: str, normalized: Dict[str, Any], payload: Dict[str, Any]) -> str:
    def _lookup(mapping: Any) -> Optional[str]:
        if isinstance(mapping, dict):
            value = mapping.get(unit_id)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    candidates = [
        normalized.get("company_dict"),
        payload.get("company_dict"),
        payload.get("unit_dict"),
        payload.get("单位字典"),
    ]
    for mapping in candidates:
        result = _lookup(mapping)
        if result:
            return result

    fallback_candidates = [
        payload.get("company_name"),
        payload.get("unit_name"),
        normalized.get("unit_name"),
        payload.get("单位名称"),
        normalized.get("sheet_name"),
        payload.get("sheet_name"),
    ]
    for value in fallback_candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return unit_id


def _flatten_records(payload: Dict[str, Any], normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    columns_raw = payload.get("columns")
    if isinstance(columns_raw, list):
        columns = [col.strip() if isinstance(col, str) else str(col) for col in columns_raw]
    else:
        columns = []

    status_raw = payload.get("status")
    if isinstance(status_raw, str):
        status = status_raw.strip() or "submit"
    else:
        status = "submit"

    submit_time_raw = payload.get("submit_time")
    if isinstance(submit_time_raw, str):
        operation_time = submit_time_raw.strip() or None
    elif submit_time_raw is None:
        operation_time = None
    else:
        operation_time = str(submit_time_raw).strip() or None

    unit_id = normalized.get("unit_id") or payload.get("unit_id") or ""
    company_cn = _resolve_company_name(unit_id, normalized, payload)
    sheet_key = normalized.get("sheet_key") or payload.get("sheet_key") or ""
    sheet_name_cn = normalized.get("sheet_name") or payload.get("sheet_name") or sheet_key

    item_dict = normalized.get("item_dict")
    if not isinstance(item_dict, dict):
        item_dict = {}
    reverse_item_map: Dict[str, str] = {}
    for item_key, item_cn in item_dict.items():
        if isinstance(item_cn, str):
            reverse_item_map[item_cn.strip()] = item_key

    note_column_index: Optional[int] = None
    note_labels = {"解释说明", "说明", "备注", "note", "Note"}
    for idx, name in enumerate(columns):
        if isinstance(name, str) and name.strip() in note_labels:
            note_column_index = idx
            break
    if note_column_index is None and len(columns) >= 5:
        note_column_index = len(columns) - 1

    records = normalized.get("records")
    if not isinstance(records, list):
        return []

    notes_by_row: Dict[int, str] = {}
    if note_column_index is not None:
        for record in records:
            if not isinstance(record, dict):
                continue
            col_index = record.get("column_index")
            row_index = record.get("row_index")
            if (
                isinstance(col_index, int)
                and col_index == note_column_index
                and isinstance(row_index, int)
            ):
                raw_note = record.get("value_raw")
                if isinstance(raw_note, str):
                    value_note = raw_note.strip()
                    notes_by_row[row_index] = value_note or None
                elif raw_note is None:
                    notes_by_row[row_index] = None
                else:
                    value_note = str(raw_note).strip()
                    notes_by_row[row_index] = value_note or None

    current_column_index: Optional[int] = 2 if len(columns) > 2 else None

    flattened: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        col_index = record.get("column_index")
        if not isinstance(col_index, int) or col_index < 2:
            continue
        if col_index >= len(columns):
            continue
        if note_column_index is not None and col_index == note_column_index:
            continue

        raw_value = record.get("value_raw")
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if value == "":
                value = None
        elif raw_value is None:
            value = None
        else:
            value = str(raw_value).strip()
            if value == "":
                value = None

        row_label = record.get("row_label") or ""
        row_label_str = str(row_label).strip()
        unit = record.get("unit") or ""
        unit_str = str(unit).strip()
        date_value_raw = columns[col_index] if col_index < len(columns) else ""
        if isinstance(date_value_raw, str):
            date_value = date_value_raw.strip() or None
        elif date_value_raw is None:
            date_value = None
        else:
            date_value = str(date_value_raw).strip() or None

        note_value = None
        if (
            current_column_index is not None
            and col_index == current_column_index
            and isinstance(record.get("row_index"), int)
        ):
            note_value = notes_by_row.get(record["row_index"], None)

        item_key = reverse_item_map.get(row_label_str)
        if not item_key:
            for candidate_key, candidate_cn in item_dict.items():
                if isinstance(candidate_cn, str) and candidate_cn.strip() == row_label_str:
                    item_key = candidate_key
                    break

        flattened.append(
            {
                "company": unit_id,
                "company_cn": company_cn,
                "sheet_name": sheet_key,
                "sheet_name_cn": sheet_name_cn,
                "item": item_key or "",
                "item_cn": row_label_str,
                "value": value,
                "unit": unit_str,
                "note": note_value,
                "date": date_value,
                "status": status,
                "operation_time": operation_time,
            }
        )

    return flattened


def _parse_decimal_value(raw: Any) -> Optional[Decimal]:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return None
        # 兼容常见的千位分隔符与空格
        sanitized = value.replace(",", "").replace("，", "").replace(" ", "")
        # 过滤掉常见的“无数据”占位符
        if sanitized in {"--", "-", "N/A", "n/a", "NA", "na", "None"}:
            return None
        try:
            return Decimal(sanitized)
        except InvalidOperation:
            return None
    return None


def _parse_date_value(raw: Any) -> Optional["date"]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    from datetime import date as date_type

    if isinstance(raw, date_type):
        return raw
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _parse_operation_time(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=EAST_8_TZ)
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return datetime.now(EAST_8_TZ)
        try:
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=EAST_8_TZ)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.replace(tzinfo=EAST_8_TZ)
                except ValueError:
                    continue
    return datetime.now(EAST_8_TZ)


def _persist_daily_basic(
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    flattened: List[Dict[str, Any]],
) -> int:
    """
    将标准/每日数据写入 daily_basic_data，幂等键为 (company, sheet_name, item, date)。

    旧实现为“先删后插”，在高并发下可能出现删除在前、两次插入都成功，导致同键重复的情况。
    现改为 PostgreSQL ON CONFLICT UPSERT，保证并发安全与幂等。
    """
    if not flattened:
        return 0

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    default_operation_time = _parse_operation_time(
        normalized.get("submit_time") or payload.get("submit_time")
    )
    default_status = (payload.get("status") or "submit").strip() or "submit"

    session = SessionLocal()
    try:
        upserts: List[Dict[str, Any]] = []

        for record in flattened:
            company = str(record.get("company") or payload.get("unit_id") or "").strip()
            if not company:
                continue

            company_cn = (
                str(record.get("company_cn") or normalized.get("unit_name") or payload.get("unit_name") or "")
                .strip()
                or None
            )
            sheet_name_key = str(
                record.get("sheet_name")
                or normalized.get("sheet_key")
                or payload.get("sheet_key")
                or ""
            ).strip()
            if not sheet_name_key:
                continue

            item_key = str(record.get("item") or "").strip()
            if not item_key:
                continue

            row_date = _parse_date_value(record.get("date"))
            if row_date is None:
                continue

            value_decimal = _parse_decimal_value(record.get("value"))
            operation_time = _parse_operation_time(
                record.get("operation_time") or default_operation_time
            )
            status_value = str(record.get("status") or default_status).strip() or default_status

            upserts.append(
                dict(
                    company=company,
                    company_cn=company_cn,
                    sheet_name=sheet_name_key,
                    item=item_key,
                    item_cn=str(record.get("item_cn") or "").strip() or None,
                    value=value_decimal,
                    unit=str(record.get("unit") or "").strip() or None,
                    note=str(record.get("note") or "").strip() or None,
                    date=row_date,
                    status=status_value,
                    operation_time=operation_time,
                )
            )

        if not upserts:
            return 0

        stmt = pg_insert(DailyBasicData.__table__).values(upserts)
        # 冲突时覆盖可变字段，并以最新提交的 operation_time 为准
        stmt = stmt.on_conflict_do_update(
            index_elements=["company", "sheet_name", "item", "date"],
            set_={
                "company_cn": stmt.excluded.company_cn,
                "item_cn": stmt.excluded.item_cn,
                "value": stmt.excluded.value,
                "unit": stmt.excluded.unit,
                "note": stmt.excluded.note,
                "status": stmt.excluded.status,
                "operation_time": stmt.excluded.operation_time,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(upserts)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _persist_constant_data_from_flattened(
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    flattened: List[Dict[str, Any]],
) -> int:
    """将扁平记录转换为 constant_data 所需结构并调用记录级持久化函数。

    注意：跳过列头为“计量单位”的列；当 item 为空时回落为 item_cn；
    period 使用列头文本；允许 value 为空（写入 NULL）。
    """
    if not flattened:
        return 0

    default_operation_time = _parse_operation_time(
        normalized.get("submit_time") or payload.get("submit_time")
    )
    records: List[Dict[str, Any]] = []
    for rec in flattened:
        period_raw = rec.get("date")
        period = (str(period_raw).strip() if period_raw is not None else "")
        if not period:
            continue
        if period == "计量单位":
            continue

        item_key = (str(rec.get("item") or "").strip())
        if not item_key:
            item_key = (str(rec.get("item_cn") or "").strip())
        if not item_key:
            continue

        company_value = str(rec.get("company") or payload.get("unit_id") or "").strip()
        if not company_value:
            continue

        sheet_value = str(rec.get("sheet_name") or normalized.get("sheet_key") or payload.get("sheet_key") or "").strip()
        if not sheet_value:
            continue

        records.append(
            {
                "company": company_value,
                "company_cn": (str(rec.get("company_cn") or normalized.get("unit_name") or payload.get("unit_name") or "").strip() or None),
                "sheet_name": sheet_value,
                "item": item_key,
                "item_cn": (str(rec.get("item_cn") or "").strip() or None),
                "value": _parse_decimal_value(rec.get("value")),
                "unit": (str(rec.get("unit") or "").strip() or None),
                "period": period,
                "operation_time": _parse_operation_time(rec.get("operation_time") or default_operation_time),
            }
        )

    if not records:
        return 0

    return _persist_constant_data(records)


def _persist_constant_data(
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    flattened: List[Dict[str, Any]],
) -> int:
    """将常量指标数据写入 constant_data 表，以 (company, sheet_name, item, period) 幂等覆盖。"""
    if not flattened:
        return 0

    default_operation_time = _parse_operation_time(
        normalized.get("submit_time") or payload.get("submit_time")
    )

    # 解析列信息与字典映射（供热分中心常量表需要 center 映射以及行内计量单位）
    columns = payload.get("columns") or payload.get("列名") or []
    if isinstance(columns, list):
        col_names = [str(c).strip() if c is not None else "" for c in columns]
    else:
        col_names = []
    try:
        unit_col_index = col_names.index("计量单位") if "计量单位" in col_names else -1
    except ValueError:
        unit_col_index = -1

    # 行映射：item_cn -> row 数组（用于取本行的计量单位）
    row_map: Dict[str, List[Any]] = {}
    for r in (payload.get("rows") or payload.get("数据") or []):
        if isinstance(r, list) and r:
            key = str(r[0]).strip() if r[0] is not None else ""
            if key and key not in row_map:
                row_map[key] = r

    # 反转中心字典（存在则表示该常量表为“中心”维度）
    center_dict = payload.get("center_dict") or payload.get("中心字典") or {}
    center_lookup = {}
    if isinstance(center_dict, dict):
        for k, v in center_dict.items():
            if isinstance(v, str):
                center_lookup[v.strip()] = str(k)
    has_center_dimension = isinstance(center_dict, dict) and len(center_dict) > 0

    session = SessionLocal()
    try:
        models: List[ConstantData] = []
        delete_keys = set()

        for record in flattened:
            company = str(record.get("company") or payload.get("unit_id") or "").strip()
            if not company:
                continue

            company_cn = (
                str(record.get("company_cn") or normalized.get("unit_name") or payload.get("unit_name") or "")
                .strip()
                or None
            )
            sheet_name_key = str(
                record.get("sheet_name")
                or normalized.get("sheet_key")
                or payload.get("sheet_key")
                or ""
            ).strip()
            if not sheet_name_key:
                continue

            item_key = str(record.get("item") or "").strip()
            if not item_key:
                continue

            # 常量数据的 period 使用列名（原 record['date']）的原始文本
            period_value = record.get("date")
            if period_value is None:
                continue
            period = str(period_value).strip()
            if not period:
                continue
            if period == "计量单位":
                # 跳过“计量单位”列产生的伪记录
                continue

            value_decimal = _parse_decimal_value(record.get("value"))
            operation_time = _parse_operation_time(
                record.get("operation_time") or default_operation_time
            )

            # 含中心维度的常量表的 center 与 unit 处理
            is_center_sheet = has_center_dimension or (
                sheet_name_key.strip().lower() == "gongre_branches_detail_constant_sheet"
            )
            center_code = None
            center_cn = None
            unit_value = (str(record.get("unit") or "").strip() or None)
            if is_center_sheet:
                # 若 record.unit 恰为中心中文名，则作为 center_cn
                if isinstance(unit_value, str) and unit_value.strip():
                    if unit_value.strip() in center_lookup:
                        center_cn = unit_value.strip()
                        center_code = center_lookup.get(center_cn)
                    else:
                        # 无 center_dict 时，以中文名作为编码回落
                        center_cn = unit_value.strip()
                        center_code = center_cn
                # 真实计量单位来自本行的“计量单位”列
                if unit_col_index >= 0:
                    row = row_map.get(str(record.get("item_cn") or "").strip())
                    if isinstance(row, list) and unit_col_index < len(row):
                        unit_candidate = row[unit_col_index]
                        unit_value = (str(unit_candidate).strip() or None) if unit_candidate is not None else None

            obj_kwargs = dict(
                company=company,
                company_cn=company_cn,
                sheet_name=sheet_name_key,
                item=item_key,
                item_cn=str(record.get("item_cn") or "").strip() or None,
                value=value_decimal,
                unit=unit_value,
                period=period,
                operation_time=operation_time,
            )
            if hasattr(ConstantData, "center"):
                obj_kwargs["center"] = center_code
            if hasattr(ConstantData, "center_cn"):
                obj_kwargs["center_cn"] = center_cn

            models.append(ConstantData(**obj_kwargs))
            # 删除键：若模型包含 center 且有中心维度，则加入 center 提升幂等粒度
            if hasattr(ConstantData, "center") and is_center_sheet:
                delete_keys.add((company, sheet_name_key, item_key, period, center_code))
            else:
                delete_keys.add((company, sheet_name_key, item_key, period))

        if not models:
            return 0

        for key in delete_keys:
            if hasattr(ConstantData, "center") and (len(key) == 5):
                company, sheet_name_key, item_key, period, center_code = key
                session.execute(
                    delete(ConstantData).where(
                        ConstantData.company == company,
                        ConstantData.sheet_name == sheet_name_key,
                        ConstantData.item == item_key,
                        ConstantData.period == period,
                        ConstantData.center == center_code,
                    )
                )
            else:
                company, sheet_name_key, item_key, period = key
                session.execute(
                    delete(ConstantData).where(
                        ConstantData.company == company,
                        ConstantData.sheet_name == sheet_name_key,
                        ConstantData.item == item_key,
                        ConstantData.period == period,
                    )
                )

        session.bulk_save_objects(models)
        session.commit()
        return len(models)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _flatten_records_for_coal(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    将煤炭库存表的宽表 payload 拆解为扁平化的数据库记录列表。
    """
    # 提取关键字典和日期
    company_dict = payload.get("company_dict", {})
    item_dict = payload.get("item_dict", {})  # 煤种字典
    status_dict = payload.get("status_dict", {}) # 状态/库存类型字典
    biz_date = payload.get("biz_date")
    
    # 创建反向查找字典，用于从中文名映射回 ID
    rev_company_map = {v: k for k, v in company_dict.items()}
    rev_item_map = {v: k for k, v in item_dict.items()}
    rev_status_map = {v: k for k, v in status_dict.items()}

    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    
    # 定位数据列的索引和中文名
    data_columns = []
    for i, col_name in enumerate(columns):
        # 数据列通常从第2列之后开始（第0列是单位，第1列是煤种）
        if i > 1 and col_name in rev_status_map:
            data_columns.append({"index": i, "name_cn": col_name})

    flattened_records = []
    operation_time = datetime.now(EAST_8_TZ)

    # 遍历每一行数据
    for row in rows:
        if not isinstance(row, list) or len(row) < len(columns):
            continue

        company_cn = row[0]
        item_cn = row[1] # 煤种中文名
        unit_raw = row[2] if len(row) > 2 else ""
        unit = str(unit_raw).strip() or None
        
        company_id = rev_company_map.get(company_cn)
        item_id = rev_item_map.get(item_cn)

        if not company_id or not item_id:
            continue # 如果单位或煤种无法映射，则跳过此行

        # 遍历该行中的每个数据列
        for col_info in data_columns:
            col_idx = col_info["index"]
            storage_type_cn = col_info["name_cn"]
            
            raw_value = row[col_idx]
            value_decimal = None
            if raw_value is not None and str(raw_value).strip() != "":
                value_decimal = _parse_decimal_value(raw_value)
            storage_type_id = rev_status_map.get(storage_type_cn)

            record = {
                "company": company_id,
                "company_cn": company_cn,
                "coal_type": item_id,
                "coal_type_cn": item_cn,
                "storage_type": storage_type_id,
                "storage_type_cn": storage_type_cn,
                "value": value_decimal,
                "unit": unit,
                "note": None, # 备注字段暂时为空
                "status": "submit",
                "date": _parse_date_value(biz_date),
                "operation_time": operation_time,
            }
            flattened_records.append(record)
            
    return flattened_records

def _persist_coal_inventory(records: List[Dict[str, Any]]) -> int:
    """
    将拆解后的煤炭库存记录持久化到数据库。
    """
    if not records:
        return 0

    session = SessionLocal()
    try:
        # 幂等写入：删除当天所有数据
        # 从第一条记录获取业务日期，并假设所有记录都是同一天
        biz_date = records[0].get("date")
        if biz_date:
            session.execute(
                delete(CoalInventoryData).where(CoalInventoryData.date == biz_date)
            )

        # 批量插入新数据
        session.bulk_insert_mappings(CoalInventoryData, records)
        session.commit()
        return len(records)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

async def handle_coal_inventory_submission(payload: Dict[str, Any]) -> JSONResponse:
    """
    处理煤炭库存表的专用提交逻辑。
    """
    try:
        flattened_records = _flatten_records_for_coal(payload)
        inserted_count = _persist_coal_inventory(flattened_records)
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "message": "煤炭库存数据处理成功",
                "flattened_records": len(flattened_records),
                "inserted": inserted_count,
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "处理煤炭库存数据时发生错误", "error": str(exc)},
        )


def _is_constant_sheet(name: Optional[str]) -> bool:
    if not name:
        return False
    return name.strip().lower().endswith("_constant_sheet")


HEATING_SEASON_ALIASES = {
    "本供暖期": "25-26",
    "同供暖期": "24-25",
    "25-26": "25-26",
    "24-25": "24-25",
}


def _strip_period_wrappers(label: str) -> str:
    if not label:
        return ""
    return re.sub(r"[()（）\s]", "", label)


def _normalize_constant_period_key(label: str) -> str:
    raw = (label or "").strip()
    if not raw:
        return ""
    simplified = _strip_period_wrappers(raw)
    if simplified:
        simplified_key = HEATING_SEASON_ALIASES.get(simplified, simplified)
    else:
        simplified_key = ""
    return HEATING_SEASON_ALIASES.get(raw, simplified_key or raw)


def _display_constant_period_label(label: str) -> str:
    normalized = _normalize_constant_period_key(label)
    if normalized:
        return normalized
    return (label or "").strip()


def _resolve_period_index(period_keys: List[str], period_label: str) -> Optional[int]:
    if not period_keys:
        return None
    normalized = _normalize_constant_period_key(period_label)
    if normalized:
        for idx, candidate in enumerate(period_keys):
            if normalized == candidate:
                return idx
    if not normalized:
        return 0
    return None


def _parse_constant_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    将常量表的宽表 payload 拆解为扁平化的数据库记录列表。

    兼容两类结构：
    1) 含中心维度（存在 center_dict）：列通常为 [项目, 中心, 计量单位, 期次1, 期次2, ...]
       此时 company 采用 center_id（由 center_dict 反向映射），company_cn 为中心中文名。
    2) 无中心维度：列通常为 [项目, 计量单位, 期次1, 期次2, ...]
       此时 company 采用 unit_id（payload.unit_id），company_cn 为 unit_name。
    """
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])

    # 字典与反向映射
    item_dict = payload.get("item_dict", {})
    center_dict = payload.get("center_dict", {})
    rev_item_map = {v: k for k, v in item_dict.items()} if isinstance(item_dict, dict) else {}
    rev_center_map = {v: k for k, v in center_dict.items()} if isinstance(center_dict, dict) else {}
    has_center = isinstance(center_dict, dict) and len(center_dict) > 0

    # 列头作为默认 period，若 payload 显式提供 periods 列表，则以其为准
    # 对于含中心维度，数据列从第 4 列（索引 3）开始；无中心维度，从第 3 列（索引 2）开始
    start_idx = 3 if has_center else 2
    header_periods = [str(c).strip() if c is not None else "" for c in columns[start_idx:]]
    periods_payload = payload.get("periods")
    if isinstance(periods_payload, list) and len(periods_payload) == len(header_periods):
        periods = [str(p).strip() for p in periods_payload]
    else:
        periods = header_periods

    op_time = _parse_operation_time(payload.get("submit_time"))
    sheet_key = payload.get("sheet_key", "")
    unit_id = str(payload.get("unit_id") or "").strip()
    unit_name = str(payload.get("unit_name") or "").strip() or None

    result: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) <= start_idx:
            continue
        item_cn = str(row[0]).strip() if row[0] is not None else ""
        if not item_cn:
            continue
        item_id = rev_item_map.get(item_cn, item_cn)

        if has_center:
            center_cn = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            unit = str(row[2]).strip() or None if len(row) > 2 else None
            # 不再持久化 center/center_cn 字段，仅用于解析 company/company_cn
            company_id = rev_center_map.get(center_cn, center_cn) if center_cn else ""
            company_cn = center_cn or None
        else:
            center_cn = None
            unit = str(row[1]).strip() or None if len(row) > 1 else None
            company_id = unit_id
            company_cn = unit_name

        if not company_id:
            continue

        # 遍历数据列
        for idx, period in enumerate(periods):
            if not period or period == "计量单位":
                continue
            col_index = start_idx + idx
            if col_index >= len(row):
                value = None
            else:
                value = _parse_decimal_value(row[col_index])

            period_key = _normalize_constant_period_key(period)
            if not period_key:
                continue

            rec = {
                "company": company_id,
                "company_cn": company_cn,
                "sheet_name": sheet_key,
                "item": item_id or item_cn,
                "item_cn": item_cn,
                "value": value,
                "unit": unit,
                "period": period_key,
                "operation_time": op_time,
            }
            result.append(rec)

    return result


def _persist_constant_data(records: List[Dict[str, Any]]) -> int:
    """将拆解后的常量记录持久化到数据库，使用 ON CONFLICT DO UPDATE 保证幂等。"""
    if not records:
        return 0

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    session = SessionLocal()
    try:
        # 准备要插入或更新的数据（移除对 center/center_cn 的依赖）
        upsert_values = []
        for r in records:
            r.pop('id', None)  # 移除 id，让数据库自增
            # 不再使用 center/center_cn 字段，确保不存在残留键
            r.pop('center', None)
            r.pop('center_cn', None)
            upsert_values.append(r)

        if not upsert_values:
            return 0

        # 构建 ON CONFLICT DO UPDATE 语句
        stmt = pg_insert(ConstantData.__table__).values(upsert_values)
        
        # 定义冲突时的更新策略
        # 唯一索引调整为 (company, item, period)
        stmt = stmt.on_conflict_do_update(
            index_elements=["company", "item", "period"],
            # 当冲突发生时，更新以下字段为新提交的值
            set_={
                "company_cn": stmt.excluded.company_cn,
                "item_cn": stmt.excluded.item_cn,
                "value": stmt.excluded.value,
                "unit": stmt.excluded.unit,
                "operation_time": stmt.excluded.operation_time,
            }
        )

        session.execute(stmt)
        session.commit()
        return len(upsert_values)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def handle_constant_submission(payload: Dict[str, Any]) -> JSONResponse:
    """处理常量表的专用提交逻辑。"""
    try:
        records = _parse_constant_records(payload)
        inserted_count = _persist_constant_data(records)
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "message": "常量表数据处理成功",
                "records_parsed": len(records),
                "inserted": inserted_count,
            },
        )
    except Exception as exc:
        # Provide more detailed error logging if possible
        print(f"Error processing constant submission: {exc}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "处理常量表数据时发生错误", "error": str(exc)},
        )


def _decorate_columns(columns: Iterable[Any]) -> List[str]:
    """将列定义转为列表，不再在服务端注入日期。"""
    return list(columns) if isinstance(columns, list) else list(columns)


def _collect_catalog(data_file: Optional[SysPath] = None) -> Dict[str, Dict[str, str]]:
    catalog_path = data_file or BASIC_DATA_FILE
    if not catalog_path.exists():
        return {}
    raw = _read_json(catalog_path)
    if isinstance(raw, dict):
        iterator = raw.items()
    elif isinstance(raw, list):
        iterator = ((payload.get("sheet_key") or "", payload) for payload in raw)
    else:
        iterator = []

    catalog: Dict[str, Dict[str, str]] = {}
    for sheet_key, payload in iterator:
        normalized_key = str(sheet_key or "").strip()
        if normalized_key in {"__global_settings__", "__meta__", "__config__", "全局配置"}:
            continue
        if not isinstance(payload, dict):
            continue
        names = _extract_names(payload)
        key = normalized_key or names["sheet_name"]
        if not key or key in catalog:
            continue
        sheet_name = names["sheet_name"] or key
        unit_name = names["unit_name"]
        catalog[key] = {
            "unit_id": names.get("unit_id", ""),
            "unit_name": names.get("unit_name", unit_name or ""),
            "sheet_name": sheet_name,
        }
    return catalog


router = APIRouter(dependencies=[Depends(get_current_session)])
public_router = APIRouter()


class ValidationMasterSwitchPayload(BaseModel):
    validation_enabled: bool


class DataAnalysisQueryPayload(BaseModel):
    unit_key: str
    metrics: List[str]
    analysis_mode: Optional[str] = "daily"
    start_date: date
    end_date: Optional[date] = None
    scope_key: Optional[str] = None
    schema_unit_key: Optional[str] = None
    request_ai_report: bool = False


def _ensure_system_admin(session: AuthSession) -> None:
    group = (session.group or "").strip()
    allowed = {"系统管理员", "Global_admin"}
    if group not in allowed:
        raise HTTPException(status_code=403, detail="仅系统管理员可修改校验总开关。")


def _ensure_cache_operator(session: AuthSession) -> None:
    """
    数据看板缓存仅开放给具有发布权限的账号。
    """
    can_publish = getattr(session.permissions.actions, "can_publish", False)
    if not can_publish:
        raise HTTPException(status_code=403, detail="当前账号无权操作数据看板缓存。")


def _collect_seed_units() -> List[str]:
    known = auth_manager.list_known_units()
    ordered: List[str] = list(known)
    if "Group" not in ordered:
        ordered.append("Group")
    return ordered


def _current_biz_datetime() -> datetime:
    biz_date = auth_manager.current_biz_date()
    naive = datetime.combine(biz_date, datetime.min.time())
    return naive.replace(tzinfo=EAST_8)


def _build_workflow_response(session: AuthSession) -> WorkflowStatusResponse:
    project_key = "daily_report_25_26"
    biz_date = auth_manager.current_biz_date()
    biz_datetime = _current_biz_datetime()
    display_date = auth_manager.current_display_date()
    seed_units = _collect_seed_units()
    visible_units = session.allowed_units or set(seed_units)
    snapshot = workflow_status_manager.get_snapshot(
        project_key=project_key,
        biz_date=biz_datetime,
        visible_units=visible_units,
        seed_units=seed_units,
    )
    units_payload = [
        WorkflowUnitStatus(
            unit=state.unit,
            status=state.status,
            approved_by=state.approved_by,
            approved_at=state.approved_at,
        )
        for state in sorted(snapshot.units.values(), key=lambda item: item.unit)
    ]
    publish_payload = WorkflowPublishStatus(
        status=snapshot.publish.status,
        published_by=snapshot.publish.published_by,
        published_at=snapshot.publish.published_at,
    )
    return WorkflowStatusResponse(
        project_key=project_key,
        biz_date=biz_date,
        display_date=display_date,
        units=units_payload,
        publish=publish_payload,
    )


@router.get(
    "/workflow/status",
    response_model=WorkflowStatusResponse,
    summary="获取审批与发布状态",
)
def get_workflow_status_endpoint(
    session: AuthSession = Depends(get_current_session),
) -> WorkflowStatusResponse:
    return _build_workflow_response(session)


@router.post(
    "/workflow/approve",
    response_model=WorkflowStatusResponse,
    summary="标记单位审批完成",
)
def approve_unit_workflow(
    payload: WorkflowApproveRequest,
    session: AuthSession = Depends(get_current_session),
) -> WorkflowStatusResponse:
    if not session.permissions.actions.can_approve:
        raise HTTPException(status_code=403, detail="当前账号无审批权限")
    target_unit = payload.unit
    allowed_units = session.allowed_units or set(_collect_seed_units())
    if target_unit not in allowed_units:
        raise HTTPException(status_code=403, detail="无权审批该单位")
    workflow_status_manager.mark_approved(
        "daily_report_25_26",
        _current_biz_datetime(),
        target_unit,
        session,
    )
    return _build_workflow_response(session)


@router.post(
    "/workflow/revoke",
    response_model=WorkflowStatusResponse,
    summary="撤销单位审批",
)
def revoke_unit_workflow(
    payload: WorkflowRevokeRequest,
    session: AuthSession = Depends(get_current_session),
) -> WorkflowStatusResponse:
    if not session.permissions.actions.can_revoke:
        raise HTTPException(status_code=403, detail="当前账号无取消批准权限")
    target_unit = payload.unit
    allowed_units = session.allowed_units or set(_collect_seed_units())
    if target_unit not in allowed_units:
        raise HTTPException(status_code=403, detail="无权取消该单位审批")
    workflow_status_manager.mark_pending(
        "daily_report_25_26",
        _current_biz_datetime(),
        target_unit,
        session,
    )
    return _build_workflow_response(session)


@router.post(
    "/workflow/publish",
    response_model=WorkflowStatusResponse,
    summary="发布当日数据",
)
def publish_daily_report(
    payload: WorkflowPublishRequest,
    session: AuthSession = Depends(get_current_session),
) -> WorkflowStatusResponse:
    if not session.permissions.actions.can_publish:
        raise HTTPException(status_code=403, detail="当前账号无发布权限")
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="请确认后再发布")
    biz_date = auth_manager.current_biz_date()
    biz_datetime = datetime.combine(biz_date, datetime.min.time()).replace(tzinfo=EAST_8)
    workflow_status_manager.mark_published(
        "daily_report_25_26",
        biz_datetime,
        session,
    )
    auth_manager.set_display_date(biz_date)
    return _build_workflow_response(session)


@router.get("/ping", summary="daily_report_25_26 心跳", tags=["daily_report_25_26"])
def ping_daily_report():
    return {"ok": True, "project": "daily_report_25_26", "message": "pong"}


from backend.services.dashboard_expression import evaluate_dashboard


def _build_dashboard_payload(result) -> Dict[str, Any]:
    base = result.to_dict()
    payload = {"ok": True}
    payload.update(base)
    return payload


def _attach_cache_metadata(
    payload: Dict[str, Any],
    cache_status: Dict[str, Any],
    cache_hit: bool,
    cache_key: str,
) -> Dict[str, Any]:
    enriched = copy.deepcopy(payload)
    enriched["cache_hit"] = cache_hit
    enriched["cache_disabled"] = cache_status.get("disabled", False)
    enriched["cache_dates"] = cache_status.get("available_dates", [])
    enriched["cache_updated_at"] = cache_status.get("updated_at")
    enriched["cache_key"] = cache_key
    return enriched


@public_router.get(
    "/dashboard",
    summary="获取数据看板配置数据",
    tags=["daily_report_25_26"],
)
def get_dashboard_data(
    show_date: str = Query(
        default="",
        description="展示日期，格式为 YYYY-MM-DD；留空时返回默认配置",
    ),
):
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    cached_payload, cache_status = dashboard_cache.get_cached_payload(PROJECT_KEY, cache_key)
    if cached_payload is not None:
        return _attach_cache_metadata(cached_payload, cache_status, cache_hit=True, cache_key=cache_key)

    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = _build_dashboard_payload(result)
    if cache_status.get("disabled"):
        return _attach_cache_metadata(payload, cache_status, cache_hit=False, cache_key=cache_key)
    cache_status = dashboard_cache.update_cache_entry(PROJECT_KEY, cache_key, payload)
    return _attach_cache_metadata(payload, cache_status, cache_hit=False, cache_key=cache_key)


@public_router.get(
    "/dashboard/date",
    summary="获取当前 set_biz_date",
    tags=["daily_report_25_26"],
)
def get_dashboard_date():
    return {
        "ok": True,
        "set_biz_date": load_default_push_date(),
    }


@router.post(
    "/dashboard/cache/publish",
    summary="批量发布数据看板缓存（set_biz_date 及前六日）",
    tags=["daily_report_25_26"],
)
def publish_dashboard_cache(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    target_dates = list(reversed(dashboard_cache.default_publish_dates()))
    schedule = target_dates
    snapshot, started = cache_publish_job_manager.start(PROJECT_KEY, schedule)
    return {
        "ok": True,
        "started": started,
        "job": snapshot,
    }


@router.delete(
    "/dashboard/cache",
    summary="禁用并清空数据看板缓存",
    tags=["daily_report_25_26"],
)
def disable_dashboard_cache_endpoint(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    status = dashboard_cache.disable_cache(PROJECT_KEY)
    return {
        "ok": True,
        "cache_disabled": status.get("disabled", True),
        "cache_updated_at": status.get("updated_at"),
    }


@router.post(
    "/dashboard/temperature/import",
    summary="获取 Open-Meteo 气温数据（仅预览，不写库）",
    tags=["daily_report_25_26"],
)
def import_dashboard_temperature(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    db_session = SessionLocal()
    try:
        result = fetch_hourly_temperatures()
        tz_name = (result.get("source") or {}).get("timezone")
        compare_result = compare_with_existing(db_session, result.get("hourly", []), tz_name)
    except WeatherImporterError as exc:
        db_session.close()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        db_session.close()
    fetched_at = datetime.now(tz=EAST_8).isoformat()
    return {
        "ok": True,
        "fetched_at": fetched_at,
        "source": result.get("source"),
        "summary": result.get("summary"),
        "dates": result.get("dates", []),
        "hourly": result.get("hourly", []),
        "overlap": compare_result.get("overlap"),
        "differences": compare_result.get("differences", []),
        "overlap_records": compare_result.get("overlap_records", []),
    }


@router.post(
    "/dashboard/temperature/import/commit",
    summary="获取 Open-Meteo 气温数据并写入 temperature_data（覆盖同一时间段）",
    tags=["daily_report_25_26"],
)
def commit_dashboard_temperature(
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    db_session = SessionLocal()
    try:
        result = fetch_hourly_temperatures()
        tz_name = (result.get("source") or {}).get("timezone")
        persist_result = persist_hourly_temperatures(db_session, result.get("hourly", []), tz_name)
    except WeatherImporterError as exc:
        db_session.close()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db_session.rollback()
        db_session.close()
        raise
    fetched_at = datetime.now(tz=EAST_8).isoformat()
    db_session.close()
    return {
        "ok": True,
        "fetched_at": fetched_at,
        "source": result.get("source"),
        "summary": result.get("summary"),
        "dates": result.get("dates", []),
        "write_result": persist_result,
    }


@router.get(
    "/data_entry/validation/master-switch",
    summary="查看全局数据填报校验总开关状态",
)
def get_validation_master_switch_state():
    flag, _ = _load_master_validation_config()
    return {"ok": True, "validation_enabled": flag}


@router.post(
    "/data_entry/validation/master-switch",
    summary="更新全局数据填报校验总开关",
)
def update_validation_master_switch(
    payload: ValidationMasterSwitchPayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_system_admin(session)
    updated = _persist_master_validation_switch(payload.validation_enabled)
    return {"ok": True, "validation_enabled": updated}


@router.get(
    "/data_entry/sheets/{sheet_key}/validation-switch",
    summary="查看指定表的校验开关",
)
def get_sheet_validation_switch(
    sheet_key: str = Path(..., description="目标 sheet_key"),
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="优先查找的模板配置文件",
    ),
):
    preferred_path = None
    if config:
        preferred_path = _resolve_data_file(config)
        if preferred_path is None:
            raise HTTPException(status_code=404, detail=f"未找到页面配置文件: {config}")
    payload, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"未找到 sheet_key={sheet_key} 的模板配置。")
    local_flag = _extract_local_validation_switch(payload)
    return {"ok": True, "validation_enabled": local_flag}


@router.post(
    "/data_entry/sheets/{sheet_key}/validation-switch",
    summary="更新指定表的校验开关",
)
def update_sheet_validation_switch(
    sheet_key: str = Path(..., description="目标 sheet_key"),
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="优先查找的模板配置文件",
    ),
    payload: ValidationMasterSwitchPayload = ...,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_system_admin(session)
    preferred_path = None
    if config:
        preferred_path = _resolve_data_file(config)
        if preferred_path is None:
            raise HTTPException(status_code=404, detail=f"未找到页面配置文件: {config}")
    updated = _persist_sheet_validation_switch(sheet_key, payload.validation_enabled, preferred_path=preferred_path)
    return {"ok": True, "validation_enabled": updated}


@router.get("/data_entry/sheets/{sheet_key}/template", summary="获取数据填报模板")
def get_sheet_template(
    sheet_key: str = Path(..., description="目标 sheet_key"),
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="优先查找的模板配置文件",
    ),
):
    preferred_path = None
    if config:
        preferred_path = _resolve_data_file(config)
        if preferred_path is None:
            return JSONResponse(
                status_code=404,
                content={
                    "ok": False,
                    "message": f"未找到页面配置文件: {config}",
                },
            )

    payload, data_path, global_validation_enabled = _locate_sheet_payload(
        sheet_key,
        preferred_path=preferred_path,
    )
    if payload is None:
        message = f"sheet_key={sheet_key} 未在 {', '.join(DATA_FILE_CANDIDATES)} 中找到"
        if preferred_path is not None:
            message = f"sheet_key={sheet_key} 未在 {preferred_path} 中找到"
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "message": message,
            },
        )

    names = _extract_names(payload)
    columns_raw = _extract_list(payload, COLUMN_KEYS)
    rows_raw = _extract_list(payload, ROW_KEYS)

    if columns_raw is None or rows_raw is None:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "message": f"sheet_key={sheet_key} 的模板缺少列名或数据",
                "source": str(data_path) if data_path else "",
            },
        )

    rows = [list(row) for row in rows_raw if isinstance(row, list)]
    dict_bundle = _collect_all_dicts(payload)
    item_dict = dict_bundle.get("item_dict", {})
    company_dict = dict_bundle.get("company_dict", {})

    columns_standard = _decorate_columns(columns_raw)

    response_content = {
        "ok": True,
        "sheet_key": sheet_key,
        "sheet_name": names["sheet_name"] or sheet_key,
        "unit_id": names["unit_id"],
        "unit_name": names["unit_name"],
        "rows": rows,
        "item_dict": item_dict,
        "company_dict": company_dict,
        "columns": columns_standard,
    }

    for dict_key, dict_value in dict_bundle.items():
        response_content[dict_key] = dict_value

    validation_enabled_flag = _extract_validation_enabled(payload, global_validation_enabled)
    response_content["validation_enabled"] = validation_enabled_flag
    payload_map = payload.get("validation_explanation_map") or payload.get("校验说明映射")
    if isinstance(payload_map, dict) and payload_map:
        response_content["validation_explanation_map"] = payload_map

    if _is_coal_inventory_sheet(sheet_key, payload):
        response_content["template_type"] = "crosstab"
        response_content["columns"] = list(columns_raw) if isinstance(columns_raw, list) else list(columns_raw)
    elif _is_constant_sheet(sheet_key):
        response_content["template_type"] = "constant"
    else:
        response_content["template_type"] = "standard"

    return JSONResponse(
        status_code=200,
        content=response_content,
    )


@router.post("/data_entry/sheets/{sheet_key}/submit", summary="提交数据填报（调试）")
async def submit_debug(
    request: Request,
    sheet_key: str = Path(..., description="目标 sheet_key"),
):
    """
    数据提交总调度入口。
    根据 sheet_key 将请求分发到不同的处理器。
    """
    payload = await request.json()

    # 根据 sheet_key 进行路由分发
    if _is_gongre_sheet(sheet_key):
        return await handle_gongre_branches_detail_submission(payload)

    if _is_constant_sheet(sheet_key):
        return await handle_constant_submission(payload)

    if _is_coal_inventory_sheet(sheet_key, payload):
        # 调用煤炭库存表的专用处理器
        return await handle_coal_inventory_submission(payload)
    else:
        # 调用处理标准基础报表的旧逻辑
        try:
            payload_aligned = _apply_linkage_constraints(payload)
            normalized = _normalize_submission(payload_aligned)
            flattened = _flatten_records(payload_aligned, normalized)
            inserted_rows = _persist_daily_basic(payload_aligned, normalized, flattened)
            return JSONResponse(
                status_code=200,
                content={
                    "ok": True,
                    "message": f"标准报表 '{sheet_key}' 数据处理成功",
                    "records": len(normalized.get("records", [])),
                    "flattened_records": len(flattened),
                    "inserted": inserted_rows,
                },
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={"ok": False, "message": "处理标准报表时发生错误", "error": str(exc)},
            )





@router.post("/data_entry/sheets/{sheet_key}/query", summary="镜像查询（逆 submit）：按表读取已入库数据")
async def query_sheet(
    request: Request,
    sheet_key: str = Path(..., description="目标 sheet_key"),
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="优先查找的模板配置文件（用于常量/煤炭库存推断列头/期别）",
    ),
):
    """
    统一镜像查询：与 submit 落库“互逆”。
    - 标准/每日：按 date=biz_date 查询 daily_basic_data，返回与模板一致的 `columns` + `rows` 结构。
    - 常量指标：按 period 查询 constant_data，返回与模板一致的 `columns` + `rows` 结构。
    - 煤炭库存：按 date=biz_date 查询 coal_inventory_data，返回 rows+columns 宽表矩阵。

    说明：
    - `unit` 字段一律表示“计量单位”（如 万kWh、GJ、吨），不是公司/组织。
    - 组织维度过滤使用 `company` 或 `company_id`（可选）。
    """

    payload = await request.json()
    # 解析公共参数
    biz_date = payload.get("biz_date") if isinstance(payload, dict) else None
    period = payload.get("period") if isinstance(payload, dict) else None
    company = None
    if isinstance(payload, dict):
        company = (
            payload.get("company")
            or payload.get("company_id")
            or payload.get("unit_id")  # 历史命名兼容：内部仍使用 company 语义
        )
        if company is not None:
            company = str(company).strip() or None

    # 如需读取模板（计算列/期别），解析首选配置文件路径 —— 必须在模板类型判定之前
    preferred_path = None
    if config:
        preferred_path = _resolve_data_file(config)

    # 推断模板类型
    template_type = "standard"
    if _is_constant_sheet(sheet_key):
        template_type = "constant"
    else:
        # 通过模板或名称启发式识别 crosstab
        tpl_payload_detect, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
        if _is_coal_inventory_sheet(sheet_key, tpl_payload_detect):
            template_type = "crosstab"

    # 执行不同模板类型的镜像查询
    try:
        if _is_gongre_sheet(sheet_key):
            if not biz_date:
                return JSONResponse(
                    status_code=422,
                    content={"ok": False, "message": "供热分中心查询需提供 biz_date"},
                )

            tpl_payload, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )

            names = _extract_names(tpl_payload)
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            rows_raw = _extract_list(tpl_payload, ROW_KEYS) or []
            dict_bundle = _collect_all_dicts(tpl_payload)

            cols_norm = [str(c).strip() if c is not None else "" for c in columns_raw]
            note_labels = {"解释说明", "说明", "备注", "note", "Note"}
            note_column_index: Optional[int] = None
            for idx, name in enumerate(cols_norm):
                if name in note_labels:
                    note_column_index = idx
                    break
            
            rows: List[List[Any]] = [list(r) if isinstance(r, list) else [] for r in rows_raw]
            row_index_map: Dict[Tuple[str, str], int] = {}
            for i, r in enumerate(rows):
                if len(r) > 1:
                    item_label = str(r[0]).strip() if r[0] is not None else ""
                    center_label = str(r[1]).strip() if r[1] is not None else ""
                    if item_label and center_label:
                        row_index_map[(item_label, center_label)] = i

            columns_standard = _decorate_columns(columns_raw)

            session = SessionLocal()
            try:
                biz_date_obj = _parse_date_value(biz_date)
                for col_idx in range(len(columns_raw)):
                    if col_idx < 3:
                        continue
                    if note_column_index is not None and col_idx == note_column_index:
                        continue
                    
                    if col_idx == 3:
                        date_obj = biz_date_obj
                    else:
                        label = columns_raw[col_idx]
                        s = str(label).strip() if label is not None else ""
                        if s and ("同期" in s):
                            try:
                                date_obj = biz_date_obj.replace(year=biz_date_obj.year - 1) if biz_date_obj else None
                            except Exception:
                                if biz_date_obj and biz_date_obj.month == 2 and biz_date_obj.day == 29:
                                    date_obj = biz_date_obj.replace(year=biz_date_obj.year - 1, day=28)
                                else:
                                    date_obj = None
                        elif s and ("本期" in s or "当日" in s or "本日" in s):
                            date_obj = biz_date_obj
                        else:
                            date_obj = _parse_date_value(s)
                    
                    if date_obj is None:
                        continue

                    q = session.query(DailyBasicData).filter(
                        DailyBasicData.sheet_name == sheet_key,
                        DailyBasicData.date == date_obj,
                    )
                    rows_db: List[DailyBasicData] = q.all()

                    for rec in rows_db:
                        value = float(rec.value) if rec.value is not None else None
                        key_candidates = [
                            (str(rec.item_cn or "").strip(), str(rec.company_cn or "").strip()),
                            (str(rec.item or "").strip(), str(rec.company or "").strip()),
                        ]
                        row_idx: Optional[int] = None
                        for k in key_candidates:
                            row_idx = row_index_map.get(k)
                            if row_idx is not None:
                                break
                        
                        if row_idx is not None:
                            if col_idx >= len(rows[row_idx]):
                                rows[row_idx].extend([None] * (col_idx - len(rows[row_idx]) + 1))
                            rows[row_idx][col_idx] = value

                            if col_idx == 3 and note_column_index is not None and isinstance(rec.note, (str,)):
                                note_text = rec.note.strip()
                                if note_text:
                                    if note_column_index >= len(rows[row_idx]):
                                        rows[row_idx].extend([None] * (note_column_index - len(rows[row_idx]) + 1))
                                    rows[row_idx][note_column_index] = note_text
                
                from datetime import datetime, timezone, timedelta
                _ts = datetime.now(timezone(timedelta(hours=8)))
                _attatch_time = _ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                content = {
                    "ok": True,
                    "template_type": "standard",
                    "mode": "gongre_detail",
                    "sheet_key": sheet_key,
                    "biz_date": biz_date,
                    "sheet_name": names["sheet_name"] or sheet_key,
                    "unit_id": names["unit_id"],
                    "unit_name": names["unit_name"],
                    "columns": columns_standard,
                    "rows": rows,
                    "attatch_time": _attatch_time,
                    "request_id": (payload.get("request_id") if isinstance(payload, dict) else None),
                }
                for dict_key, dict_value in dict_bundle.items():
                    content[dict_key] = dict_value

                return JSONResponse(status_code=200, content=content)
            finally:
                session.close()
        elif template_type == "crosstab":
            # 煤炭库存：返回与模板一致的结构（columns + rows），并补全模板元信息
            if not biz_date:
                return JSONResponse(
                    status_code=422,
                    content={"ok": False, "message": "煤炭库存查询需提供 biz_date"},
                )

            # 读取模板元信息与列头
            tpl_payload, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )
            names = _extract_names(tpl_payload)
            dict_bundle = _collect_all_dicts(tpl_payload)
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            columns: List[str] = [str(c) for c in (columns_raw or [])]

            # 反查存量列中文名在模板中的索引
            storage_index: Dict[str, int] = {}
            if isinstance(columns, list):
                for idx, name in enumerate(columns):
                    if isinstance(name, str):
                        storage_index[name.strip()] = idx

            # DB 查询
            session = SessionLocal()
            try:
                q = session.query(CoalInventoryData).filter(
                    CoalInventoryData.date == _parse_date_value(biz_date)
                )
                if company:
                    q = q.filter(CoalInventoryData.company == company)
                rows_db: List[CoalInventoryData] = q.all()

                # 组装 (公司, 煤种) → 行缓冲
                row_map: Dict[Tuple[str, str], List[Any]] = {}
                # 备注列索引（若模板中存在“备注”等列）
                note_idx = None
                if isinstance(columns, list):
                    for i, n in enumerate(columns):
                        if str(n).strip() in {"备注", "说明", "解释说明", "note", "Note"}:
                            note_idx = i
                            break

                for rec in rows_db:
                    key = (rec.company_cn or rec.company, rec.coal_type_cn or rec.coal_type)
                    if key not in row_map:
                        # 初始化为全空的行
                        base = [""] * len(columns)
                        if len(base) >= 1:
                            base[0] = rec.company_cn or rec.company or ""
                        if len(base) >= 2:
                            base[1] = rec.coal_type_cn or rec.coal_type or ""
                        if len(base) >= 3:
                            base[2] = rec.unit or ""
                        row_map[key] = base

                    # 定位存量列索引：优先使用记录中的中文列名；否则用映射表匹配
                    col_idx = None
                    if isinstance(rec.storage_type_cn, str):
                        cname = rec.storage_type_cn.strip()
                        col_idx = storage_index.get(cname)
                    if col_idx is None and isinstance(rec.storage_type, str):
                        # 由 code 映射中文，再找索引
                        for cn_name, (code, label_cn) in COAL_STORAGE_NAME_MAP.items():
                            if code == rec.storage_type:
                                col_idx = storage_index.get(cn_name) or storage_index.get(label_cn)
                                if col_idx is None:
                                    # 兜底查找：模板列名中出现 label_cn
                                    col_idx = next(
                                        (i for i, n in enumerate(columns) if str(n).strip() == label_cn),
                                        None,
                                    )
                                break

                    if isinstance(col_idx, int) and 0 <= col_idx < len(row_map[key]):
                        val = rec.value
                        row_map[key][col_idx] = float(val) if val is not None else None

                    # 填充备注（若存在备注列）：采用首个非空备注
                    if note_idx is not None and isinstance(rec.note, (str,)):
                        if not row_map[key][note_idx]:
                            nt = rec.note.strip()
                            if nt:
                                row_map[key][note_idx] = nt

                # 若无任何查询结果，则返回模板行而非空数组；否则严格按模板行顺序回填
                rows_raw = _extract_list(tpl_payload, ROW_KEYS) or []
                if row_map:
                    ordered_rows: List[List[Any]] = []
                    for tmpl_row in rows_raw:
                        normalized_row = list(tmpl_row) if isinstance(tmpl_row, list) else []
                        company_label = (
                            str(normalized_row[0]).strip()
                            if len(normalized_row) > 0 and normalized_row[0] is not None
                            else ""
                        )
                        coal_label = (
                            str(normalized_row[1]).strip()
                            if len(normalized_row) > 1 and normalized_row[1] is not None
                            else ""
                        )
                        key = (company_label, coal_label) if company_label and coal_label else None
                        if key and key in row_map:
                            ordered_rows.append(row_map.pop(key))
                        else:
                            ordered_rows.append(normalized_row)
                    if row_map:
                        ordered_rows.extend(row_map.values())
                    result_rows = ordered_rows
                else:
                    result_rows = [list(r) if isinstance(r, list) else [] for r in rows_raw]

                # 生成东八区毫秒时间戳（attatch_time）
                from datetime import datetime, timezone, timedelta
                _ts = datetime.now(timezone(timedelta(hours=8)))
                _attatch_time = _ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                # 生成 source 记录：函数、模板类型、请求来源与载荷摘要
                source = {
                    "handler": "query_sheet",
                    "template_type": "standard",
                    "received": {
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "payload": {
                            "biz_date": biz_date,
                            "period": period,
                            "company": company,
                        },
                    },
                }

                # 生成 source 记录：函数、模板类型、请求来源与载荷摘要
                source = {
                    "handler": "query_sheet",
                    "template_type": "constant",
                    "received": {
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "payload": {
                            "biz_date": biz_date,
                            "period": period,
                            "company": company,
                        },
                    },
                }

                # 生成 source 记录：函数、模板类型、请求来源与载荷摘要
                source = {
                    "handler": "query_sheet",
                    "template_type": "crosstab",
                    "received": {
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "payload": {
                            "biz_date": biz_date,
                            "period": period,
                            "company": company,
                        },
                    },
                }

                content = {
                    "ok": True,
                    "template_type": "crosstab",
                    "sheet_key": sheet_key,
                    "biz_date": biz_date,
                    "sheet_name": names["sheet_name"] or sheet_key,
                    "unit_id": names["unit_id"],
                    "unit_name": names["unit_name"],
                    "columns": columns,
                    "rows": result_rows,
                    "attatch_time": _attatch_time,
                    "request_id": (payload.get("request_id") if isinstance(payload, dict) else None),
                    "source": source,
                }
                for dict_key, dict_value in dict_bundle.items():
                    content[dict_key] = dict_value

                return JSONResponse(status_code=200, content=content)
            finally:
                session.close()

        elif template_type == "constant":
            # 常量指标：按模板 columns/rows 结构回填（不再返回 cells，完全 rows-only）
            tpl_payload, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )

            names = _extract_names(tpl_payload)
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            rows_raw = _extract_list(tpl_payload, ROW_KEYS) or []
            dict_bundle = _collect_all_dicts(tpl_payload)
            has_center = isinstance(dict_bundle.get("center_dict"), dict) and len(dict_bundle.get("center_dict")) > 0
            start_idx = 3 if has_center else 2
            periods = [str(c).strip() if c is not None else "" for c in columns_raw[start_idx:]]
            period_keys = [_normalize_constant_period_key(label) for label in periods]
            period_display = [_display_constant_period_label(label) for label in periods]

            columns_standard = _decorate_columns(columns_raw)
            for idx, label in enumerate(period_display):
                target_index = start_idx + idx
                if target_index < len(columns_standard):
                    columns_standard[target_index] = label

            # 初始化为模板行的深拷贝（按模板回填）
            rows: List[List[Any]] = [list(r) if isinstance(r, list) else [] for r in rows_raw]
            # 行索引映射：(项目, 单位) -> 行号
            row_index_map: Dict[Tuple[str, str], int] = {}
            for i, r in enumerate(rows):
                item_label = str(r[0]).strip() if len(r) > 0 and r[0] is not None else ""
                unit_label = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
                row_index_map[(item_label, unit_label)] = i

            session = SessionLocal()
            try:
                q = session.query(ConstantData).filter(ConstantData.sheet_name == sheet_key)
                if period:
                    normalized_period = str(period).strip()
                    period_candidates = {normalized_period}
                    simplified = _strip_period_wrappers(normalized_period)
                    if simplified and simplified != normalized_period:
                        period_candidates.add(simplified)
                    normalized_key = _normalize_constant_period_key(normalized_period)
                    if normalized_key:
                        period_candidates.add(normalized_key)
                    period_candidates = {candidate for candidate in period_candidates if candidate}
                    if period_candidates:
                        q = q.filter(ConstantData.period.in_(period_candidates))
                if company:
                    q = q.filter(ConstantData.company == company)
                rows_db: List[ConstantData] = q.all()

                for rec in rows_db:
                    value = float(rec.value) if rec.value is not None else None
                    rec_period = str(rec.period or "").strip()
                    period_index = _resolve_period_index(period_keys, rec_period)
                    if period_index is None:
                        continue
                    col_index = start_idx + period_index

                    if has_center:
                        key_candidates = [
                            (str(rec.item_cn or "").strip(), str(rec.company_cn or rec.company or "").strip()),
                            (str(rec.item or "").strip(), str(rec.company or rec.company_cn or "").strip()),
                        ]
                    else:
                        key_candidates = [
                            (str(rec.item_cn or "").strip(), str(rec.unit or "").strip()),
                            (str(rec.item or "").strip(), str(rec.unit or "").strip()),
                        ]
                    row_idx: Optional[int] = None
                    for k in key_candidates:
                        row_idx = row_index_map.get(k)
                        if row_idx is not None:
                            break

                    if row_idx is not None:
                        # 确保行长度足够
                        if col_index >= len(rows[row_idx]):
                            rows[row_idx].extend([None] * (col_index - len(rows[row_idx]) + 1))
                        rows[row_idx][col_index] = value


                # 生成东八区毫秒时间戳（attatch_time）
                from datetime import datetime, timezone, timedelta
                _ts = datetime.now(timezone(timedelta(hours=8)))
                _attatch_time = _ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                source = {
                    "handler": "query_sheet",
                    "template_type": "constant",
                    "received": {
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "payload": {
                            "biz_date": biz_date,
                            "period": period,
                            "company": company,
                        },
                    },
                }

                content = {
                    "ok": True,
                    "template_type": "constant",
                    "mode": "constant",
                    "sheet_key": sheet_key,
                    "period": period,
                    "sheet_name": names["sheet_name"] or sheet_key,
                    "unit_id": names["unit_id"],
                    "unit_name": names["unit_name"],
                    "columns": columns_standard,
                    "rows": rows,
                    "attatch_time": _attatch_time,
                    "request_id": (payload.get("request_id") if isinstance(payload, dict) else None),
                    "source": source,
                }
                for dict_key, dict_value in dict_bundle.items():
                    content[dict_key] = dict_value

                return JSONResponse(status_code=200, content=content)
            finally:
                session.close()

        else:
            # 标准/每日：按 biz_date 查询 daily_basic_data，返回与模板一致的 columns+rows 结构（rows-only）
            if not biz_date:
                return JSONResponse(
                    status_code=422,
                    content={"ok": False, "message": "标准表查询需提供 biz_date"},
                )

            tpl_payload, _, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )

            names = _extract_names(tpl_payload)
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            rows_raw = _extract_list(tpl_payload, ROW_KEYS) or []
            dict_bundle = _collect_all_dicts(tpl_payload)

            # 定位备注列索引（若存在）
            cols_norm = [str(c).strip() if c is not None else "" for c in columns_raw]
            note_labels = {"解释说明", "说明", "备注", "note", "Note"}
            note_column_index: Optional[int] = None
            for idx, name in enumerate(cols_norm):
                if name in note_labels:
                    note_column_index = idx
                    break
            if note_column_index is None and len(cols_norm) >= 5:
                note_column_index = len(cols_norm) - 1

            # 深拷贝模板行 & 行映射
            rows: List[List[Any]] = [list(r) if isinstance(r, list) else [] for r in rows_raw]
            row_index_map: Dict[Tuple[str, str], int] = {}
            for i, r in enumerate(rows):
                item_label = str(r[0]).strip() if len(r) > 0 and r[0] is not None else ""
                unit_label = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
                row_index_map[(item_label, unit_label)] = i

            columns_standard = _decorate_columns(columns_raw)

            session = SessionLocal()
            try:
                # 遍历所有数据列（跳过前两列和备注列）
                # 预解析 biz_date 对象，供关键字列头（如“同期日”）推算使用
                biz_date_obj = _parse_date_value(biz_date)
                for col_idx in range(len(columns_raw)):
                    if col_idx < 2:
                        continue
                    if note_column_index is not None and col_idx == note_column_index:
                        continue
                    # 列日期解析：第一个数据列强制采用 biz_date，其余尝试从列头解析
                    if col_idx == 2:
                        date_obj = biz_date_obj
                    else:
                        label = columns_raw[col_idx]
                        s = str(label).strip() if label is not None else ""
                        if s and ("同期" in s):
                            # 同期日：按 biz_date 的去年同日推算（闰日回退到 2/28）
                            try:
                                date_obj = biz_date_obj.replace(year=biz_date_obj.year - 1) if biz_date_obj else None
                            except Exception:
                                if biz_date_obj and biz_date_obj.month == 2 and biz_date_obj.day == 29:
                                    date_obj = biz_date_obj.replace(year=biz_date_obj.year - 1, day=28)
                                else:
                                    date_obj = None
                        elif s and ("本期" in s or "当日" in s or "本日" in s):
                            date_obj = biz_date_obj
                        else:
                            date_obj = _parse_date_value(s)
                    if date_obj is None:
                        continue

                    q = session.query(DailyBasicData).filter(
                        DailyBasicData.sheet_name == sheet_key,
                        DailyBasicData.date == date_obj,
                    )
                    if company:
                        q = q.filter(DailyBasicData.company == company)
                    rows_db: List[DailyBasicData] = q.all()

                    for rec in rows_db:
                        value = float(rec.value) if rec.value is not None else None
                        key_candidates = [
                            (str(rec.item_cn or "").strip(), str(rec.unit or "").strip()),
                            (str(rec.item or "").strip(), str(rec.unit or "").strip()),
                        ]
                        row_idx: Optional[int] = None
                        for k in key_candidates:
                            row_idx = row_index_map.get(k)
                            if row_idx is not None:
                                break
                        if row_idx is None:
                            continue

                        if col_idx >= len(rows[row_idx]):
                            rows[row_idx].extend([None] * (col_idx - len(rows[row_idx]) + 1))
                        rows[row_idx][col_idx] = value

                        # 仅当当前列是第一个数据列时，填充备注列（与提交一致）。
                        # 说明：某些模板“解释说明”列头在模板中为空或不稳定，为保证稳定性，这里额外做一次兜底填充：
                        # 若遍历结束后仍无备注回填，将在循环外再次按 biz_date 做一次专门的备注回填。
                        if col_idx == 2 and note_column_index is not None and isinstance(rec.note, (str,)):
                            note_text = rec.note.strip()
                            if note_text:
                                if note_column_index >= len(rows[row_idx]):
                                    rows[row_idx].extend([None] * (note_column_index - len(rows[row_idx]) + 1))
                                rows[row_idx][note_column_index] = note_text

                # 兜底：如首列遍历没有带出备注，则按 biz_date 再做一次备注仅回填
                if note_column_index is not None and biz_date_obj is not None:
                    q_note = session.query(DailyBasicData).filter(
                        DailyBasicData.sheet_name == sheet_key,
                        DailyBasicData.date == biz_date_obj,
                    )
                    if company:
                        q_note = q_note.filter(DailyBasicData.company == company)
                    note_rows: List[DailyBasicData] = q_note.all()
                    for rec in note_rows:
                        if not isinstance(rec.note, (str,)):
                            continue
                        note_text = rec.note.strip()
                        if not note_text:
                            continue
                        key_candidates = [
                            (str(rec.item_cn or "").strip(), str(rec.unit or "").strip()),
                            (str(rec.item or "").strip(), str(rec.unit or "").strip()),
                        ]
                        row_idx: Optional[int] = None
                        for k in key_candidates:
                            row_idx = row_index_map.get(k)
                            if row_idx is not None:
                                break
                        if row_idx is None:
                            continue
                        if note_column_index >= len(rows[row_idx]):
                            rows[row_idx].extend([None] * (note_column_index - len(rows[row_idx]) + 1))
                        if not rows[row_idx][note_column_index]:
                            rows[row_idx][note_column_index] = note_text

                # 生成东八区毫秒时间戳（attatch_time）
                from datetime import datetime, timezone, timedelta
                _ts = datetime.now(timezone(timedelta(hours=8)))
                _attatch_time = _ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                source = {
                    "handler": "query_sheet",
                    "template_type": "standard",
                    "received": {
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "payload": {
                            "biz_date": biz_date,
                            "period": period,
                            "company": company,
                        },
                    },
                }

                content = {
                    "ok": True,
                    "template_type": "standard",
                    "sheet_key": sheet_key,
                    "biz_date": biz_date,
                    "sheet_name": names["sheet_name"] or sheet_key,
                    "unit_id": names["unit_id"],
                    "unit_name": names["unit_name"],
                    "columns": columns_standard,
                    "rows": rows,
                    "attatch_time": _attatch_time,
                    "request_id": (payload.get("request_id") if isinstance(payload, dict) else None),
                    "source": source,
                }
                for dict_key, dict_value in dict_bundle.items():
                    content[dict_key] = dict_value

                return JSONResponse(status_code=200, content=content)
            finally:
                session.close()

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "查询处理发生错误", "error": str(exc)},
        )


@router.get("/data_entry/sheets", summary="获取数据填报模板清单")
def list_sheets(
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="页面模板配置文件（相对 DATA_DIRECTORY 的路径）",
    ),
):
    data_file: Optional[SysPath] = None
    if config:
        data_file = _resolve_data_file(config)
        if data_file is None:
            return JSONResponse(
                status_code=404,
                content={
                    "ok": False,
                    "message": f"未找到页面配置文件: {config}",
            },
        )

    catalog = _collect_catalog(data_file)
    if not catalog:
        location = data_file or DATA_ROOT
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "message": f"未在 {location} 中找到任何模板文件",
            },
    )
    return JSONResponse(status_code=200, content=catalog)


def _load_json_dict(path: SysPath) -> Optional[Dict[str, Any]]:
    if not path or not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _try_inject_constant_metric(schema_payload: Dict[str, Any], metric_key: str) -> bool:
    """若数据分析 schema 中缺少某常量指标，尝试从常量配置补齐到 metric_dict 与视图映射。"""
    const_struct = _load_json_dict(CONSTANT_STRUCTURE_PATH)
    if not const_struct:
        return False
    found_label: Optional[str] = None
    for sheet in const_struct.values():
        if not isinstance(sheet, dict):
            continue
        item_dict = sheet.get("项目字典") or sheet.get("item_dict")
        if not isinstance(item_dict, dict):
            continue
        if metric_key in item_dict:
            found_label = str(item_dict[metric_key])
            break
    if not found_label:
        return False

    metric_dict = schema_payload.setdefault("metric_dict", {})
    metric_group_views = schema_payload.setdefault("metric_group_views", {})
    metric_decimals = schema_payload.setdefault("metric_decimals", {})

    metric_dict[metric_key] = found_label
    metric_group_views.setdefault("constant", [])
    if "constant_data" not in metric_group_views["constant"]:
        metric_group_views["constant"].append("constant_data")
    metric_decimals.setdefault(metric_key, 2)
    return True


def _collect_unit_metric_options(struct: Dict[str, Any], unit_key: str) -> Dict[str, str]:
    """
    从审批/常量配置中按单位汇总 项目字典 -> {key: label}
    """
    results: Dict[str, str] = {}
    if not struct or not unit_key:
        return results
    for sheet in struct.values():
        if not isinstance(sheet, dict):
            continue
        unit_id = sheet.get("单位标识") or sheet.get("unit_id") or sheet.get("unit_key")
        if not unit_id or str(unit_id).strip() != unit_key:
            continue
        item_dict = sheet.get("项目字典") or sheet.get("item_dict")
        if isinstance(item_dict, dict):
            for key, label in item_dict.items():
                if not key:
                    continue
                results[str(key)] = str(label) if label is not None else str(key)
    return results


def _build_unit_analysis_metric_payload(
    unit_key: str, config: Optional[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[JSONResponse]]:
    if not unit_key:
        return None, JSONResponse(
            status_code=400, content={"ok": False, "message": "缺少 unit_key"}
        )

    schema_payload, schema_error = _build_data_analysis_schema_payload(config)
    if schema_error is not None and schema_payload is None:
        return None, schema_error

    approval_struct = _load_json_dict(APPROVAL_STRUCTURE_PATH)
    constant_struct = _load_json_dict(CONSTANT_STRUCTURE_PATH)
    source_stats = {"approval": 0, "constant": 0, "temperature": 0}

    def _labels_from_rows(rows: Any) -> List[str]:
        labels: List[str] = []
        if not isinstance(rows, list):
            return labels
        for row in rows:
            if isinstance(row, list) and row:
                label = str(row[0]).strip()
                if label:
                    labels.append(label)
        return labels

    def _match_labels_with_dict(
        labels: Sequence[str], item_dict: Dict[str, str]
    ) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
        result: Dict[str, str] = {}
        order: List[Tuple[str, str]] = []
        if not labels:
            return result, order
        reversed_map = {str(v).strip(): str(k) for k, v in item_dict.items() if k}
        for label in labels:
            key = reversed_map.get(label)
            if not key:
                # 找不到匹配时用中文作为 key，至少可选
                key = label
            result[key] = label
            order.append((key, label))
        return result, order

    major_options: Dict[str, str] = {}
    constant_options: Dict[str, str] = {}
    major_order: List[Tuple[str, str]] = []
    constant_order: List[Tuple[str, str]] = []

    if approval_struct:
        for sheet in approval_struct.values():
            if not isinstance(sheet, dict):
                continue
            unit_id = sheet.get("单位标识") or sheet.get("unit_id") or sheet.get("unit_key")
            if not unit_id or str(unit_id).strip() != unit_key:
                continue
            labels = _labels_from_rows(sheet.get("数据"))
            item_dict = sheet.get("项目字典") or sheet.get("item_dict") or {}
            merged, order = _match_labels_with_dict(
                labels,
                item_dict if isinstance(item_dict, dict) else {},
            )
            major_options.update(merged)
            major_order.extend(order)
        source_stats["approval"] = len(major_options)

    if constant_struct:
        for sheet in constant_struct.values():
            if not isinstance(sheet, dict):
                continue
            unit_id = sheet.get("单位标识") or sheet.get("unit_id") or sheet.get("unit_key")
            if not unit_id or str(unit_id).strip() != unit_key:
                continue
            labels = _labels_from_rows(sheet.get("数据"))
            item_dict = sheet.get("项目字典") or sheet.get("item_dict") or {}
            merged, order = _match_labels_with_dict(
                labels,
                item_dict if isinstance(item_dict, dict) else {},
            )
            constant_options.update(merged)
            constant_order.extend(order)
        source_stats["constant"] = len(constant_options)

    decimals_map: Dict[str, Any] = {}
    temperature_options: Dict[str, str] = {}
    unit_dict = schema_payload.get("unit_dict") or {}
    unit_label = unit_dict.get(unit_key, unit_key)

    if schema_payload:
        temperature_dict = schema_payload.get("temperature_metric_dict") or {}
        if isinstance(temperature_dict, dict):
            source_stats["temperature"] = len(temperature_dict)
            for key, label in temperature_dict.items():
                if not key:
                    continue
                temperature_options[str(key)] = str(label) if label is not None else str(key)
        decimals = schema_payload.get("metric_decimals")
        if isinstance(decimals, dict):
            decimals_map = {str(k): v for k, v in decimals.items()}

    groups = []
    if major_order:
        groups.append(
            {
                "key": "major",
                "label": "主要指标",
                "options": [{"value": key, "label": value} for key, value in major_order],
            }
        )
    if constant_order:
        groups.append(
            {
                "key": "constant",
                "label": "常量指标",
                "options": [{"value": key, "label": value} for key, value in constant_order],
            }
        )
    if temperature_options:
        groups.append(
            {
                "key": "temperature",
                "label": "气温指标",
                "options": [{"value": k, "label": v} for k, v in sorted(temperature_options.items(), key=lambda x: x[1])],
            }
        )

    # 扁平化 options 方便前端兜底使用
    flat_options = []
    for group in groups:
        flat_options.extend(group["options"])

    payload = {
        "ok": True,
        "unit_key": unit_key,
        "unit_label": unit_label,
        "groups": groups,
        "options": flat_options,
        "decimals": decimals_map,
        "source": source_stats,
        "unit_dict": schema_payload.get("unit_dict") or {},
    }
    return payload, None


@router.get(
    "/data_entry/analysis/metrics",
    summary="获取填报页本单位可用的分析指标（审批+常量+气温）",
)
def get_unit_analysis_metrics(
    unit_key: str = Query(..., description="单位标识，例如 BeiHai"),
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="数据分析/审批/常量配置文件（相对 DATA_DIRECTORY 的路径）",
    ),
):
    payload, error = _build_unit_analysis_metric_payload(unit_key.strip(), config)
    if error is not None:
        return error
    return JSONResponse(status_code=200, content=payload)


def _build_data_analysis_schema_payload(
    config: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[JSONResponse]]:
    data_file: Optional[SysPath]
    if config:
        data_file = _resolve_data_file(config)
        if data_file is None:
            return None, JSONResponse(
                status_code=404,
                content={"ok": False, "message": f"未找到页面配置文件: {config}"},
            )
    else:
        data_file = DATA_ANALYSIS_SCHEMA_PATH if DATA_ANALYSIS_SCHEMA_PATH.exists() else None

    if data_file is None or not data_file.exists():
        return None, JSONResponse(
            status_code=404,
            content={"ok": False, "message": "未找到数据分析配置文件"},
        )

    try:
        raw_payload = json.loads(data_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"{data_file} 解析失败"},
        )

    return data_analysis_service.build_schema_payload(raw_payload, data_file)


@router.get(
    "/data_analysis/schema",
    summary="获取数据分析页面配置",
)
def get_data_analysis_schema(
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="优先加载的配置文件路径（相对 DATA_DIRECTORY）",
    ),
):
    content, error = _build_data_analysis_schema_payload(config)
    if error:
        return error
    if content is None:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "无法生成数据分析配置"},
        )
    return JSONResponse(status_code=200, content=content)


def _unique_metric_keys(metrics: Sequence[str]) -> List[str]:
    return data_analysis_service._unique_metric_keys(metrics)


def _sanitize_identifier(value: str) -> Optional[str]:
    return data_analysis_service._sanitize_identifier(value)


def _resolve_active_view_name(
    view_mapping: Dict[str, Any],
    mode_label: str,
    unit_label: str,
    analysis_mode_value: str,
) -> str:
    return data_analysis_service._resolve_active_view_name(
        view_mapping, mode_label, unit_label, analysis_mode_value
    )


def _resolve_unit_view(
    view_mapping: Dict[str, Any],
    mode_label: str,
    unit_label: str,
    fallback: Optional[str] = None,
) -> Optional[str]:
    return data_analysis_service._resolve_unit_view(
        view_mapping, mode_label, unit_label, fallback
    )


def _apply_analysis_window_settings(
    session,
    view_name: str,
    start_date: date,
    end_date: date,
) -> None:
    return data_analysis_service._apply_analysis_window_settings(
        session, view_name, start_date, end_date
    )


def _decimal_to_float(value: Any) -> Optional[float]:
    return data_analysis_service._decimal_to_float(value)


def _compute_delta(current: Optional[float], peer: Optional[float]) -> Optional[float]:
    return data_analysis_service._compute_delta(current, peer)


def _shift_year(value: date, years: int = 1) -> Optional[date]:
    return data_analysis_service._shift_year(value, years)


def _shift_period_label(label: Optional[str]) -> Optional[str]:
    return data_analysis_service._shift_period_label(label)


def _query_analysis_rows(
    view_name: str,
    unit_key: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
    sheet_name: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    return data_analysis_service._query_analysis_rows(
        view_name, unit_key, metric_keys, start_date, end_date, sheet_name=sheet_name
    )


def _query_analysis_timeline(
    view_name: str,
    unit_key: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
    sheet_name: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    return data_analysis_service._query_analysis_timeline(
        view_name, unit_key, metric_keys, start_date, end_date, sheet_name=sheet_name
    )


def _query_constant_rows(unit_key: str, metric_keys: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    return data_analysis_service._query_constant_rows(unit_key, metric_keys)


def _query_temperature_rows(
    view_name: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
    analysis_mode: str,
) -> Dict[str, Dict[str, Any]]:
    result, _ = data_analysis_service._query_temperature_rows(
        view_name, metric_keys, start_date, end_date, analysis_mode
    )
    return result


def _compute_previous_range(
    start_date: Union[date, datetime, str],
    end_date: Union[date, datetime, str],
) -> Tuple[Optional[date], Optional[date]]:
    MIN_DATE = date(2025, 11, 1)
    s = _parse_date_value(start_date)
    e = _parse_date_value(end_date)
    if not s or not e:
        return None, None

    # Check for full month
    # Calculate next day of end_date to see if it is the 1st of next month
    next_day = e + timedelta(days=1)
    is_full_month = (s.day == 1 and next_day.day == 1)

    if is_full_month:
        # Previous month range
        # last day of prev month = start_date - 1 day
        prev_end = s - timedelta(days=1)
        # first day of prev month = replace day with 1
        prev_start = prev_end.replace(day=1)
    else:
        # Fixed span shift
        span = (e - s).days + 1
        prev_end = s - timedelta(days=1)
        prev_start = s - timedelta(days=span)

    if prev_start < MIN_DATE:
        return None, None
    
    return prev_start, prev_end


def _build_metric_group_lookup(groups: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    return data_analysis_service._build_metric_group_lookup(groups)


def _execute_data_analysis_query(
    payload: DataAnalysisQueryPayload,
    schema_payload: Dict[str, Any],
) -> JSONResponse:
    # 使用 legacy 版本以兼容当前定制逻辑
    try:
        return _execute_data_analysis_query_legacy(payload, schema_payload)
    except Exception as exc:
        logger.exception("执行数据分析查询时发生未捕获异常")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"服务器内部错误: {str(exc)}"},
        )


def _execute_data_analysis_query_legacy(
    payload: Any,  # 原有签名兼容，实际为 DataAnalysisQueryPayload
    schema_payload: Dict[str, Any],
) -> JSONResponse:
    unit_dict = schema_payload.get("unit_dict") or {}
    metric_dict = schema_payload.get("metric_dict") or {}
    metric_groups = schema_payload.get("metric_groups") or []
    metric_group_views = schema_payload.get("metric_group_views") or {}
    metric_decimals = schema_payload.get("metric_decimals") or {}

    metrics_input = payload.metrics if hasattr(payload, "metrics") else payload.get("metrics", [])
    ordered_metrics = _unique_metric_keys(metrics_input)
    if not ordered_metrics:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "至少需要选择一个指标"},
        )

    scope_key = (payload.scope_key or "").strip() if hasattr(payload, "scope_key") else (payload.get("scope_key", "").strip() if isinstance(payload, dict) else "")
    schema_unit_key = (payload.schema_unit_key or "").strip() if hasattr(payload, "schema_unit_key") else (payload.get("schema_unit_key", "").strip() if isinstance(payload, dict) else "")
    unit_key = (payload.unit_key or "").strip() if hasattr(payload, "unit_key") else (payload.get("unit_key", "").strip() if isinstance(payload, dict) else "")
    if schema_unit_key and schema_unit_key in unit_dict:
        unit_key = schema_unit_key
    if not unit_key or unit_key not in unit_dict:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"未知单位: {unit_key or '未提供'}"},
        )
    unit_label = unit_dict.get(unit_key, unit_key)
    is_beihai_sub_scope = scope_key in BEIHAI_SUB_SCOPES
    sheet_name_filter: Optional[str] = scope_key if is_beihai_sub_scope else None

    unknown_metrics = [key for key in ordered_metrics if key not in metric_dict]
    if unknown_metrics:
        injected = False
        for key in list(unknown_metrics):
            if _try_inject_constant_metric(schema_payload, key):
                injected = True
        if injected:
            metric_dict = schema_payload.get("metric_dict") or metric_dict
            metric_group_views = schema_payload.get("metric_group_views") or metric_group_views
            metric_decimals = schema_payload.get("metric_decimals") or metric_decimals
            unknown_metrics = [key for key in ordered_metrics if key not in metric_dict]
    if unknown_metrics:
        labels = [metric_dict.get(key, key) for key in unknown_metrics]
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"存在未配置的指标: {', '.join(labels)}"},
        )

    analysis_mode_value = (payload.analysis_mode or "daily").strip().lower()
    if analysis_mode_value not in {"daily", "range"}:
        analysis_mode_value = "daily"

    start_date = payload.start_date
    end_date = payload.end_date if payload.end_date else payload.start_date
    if analysis_mode_value == "range":
        if payload.end_date is None:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "累计模式需同时提供结束日期"},
            )
        if start_date > end_date:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "起始日期不得晚于结束日期"},
            )
    else:
        end_date = start_date

    range_days = (end_date - start_date).days + 1
    if analysis_mode_value == "range" and range_days > MAX_TIMELINE_DAYS:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "message": f"累计模式暂只支持 {MAX_TIMELINE_DAYS} 天内的区间，请缩小日期范围。",
            },
        )

    analysis_modes = schema_payload.get("analysis_modes") or []
    mode_label = next(
        (item.get("label") for item in analysis_modes if item.get("value") == analysis_mode_value),
        None,
    )
    if not mode_label:
        mode_label = "单日数据" if analysis_mode_value == "daily" else "累计数据"

    view_mapping = schema_payload.get("view_mapping") or {}
    if is_beihai_sub_scope:
        active_view_name = (
            "analysis_beihai_sub_sum"
            if analysis_mode_value == "range"
            else "analysis_beihai_sub_daily"
        )
    else:
        active_view_name = _resolve_active_view_name(
            view_mapping,
            mode_label,
            unit_label,
            analysis_mode_value,
        )

    metric_group_lookup = _build_metric_group_lookup(metric_groups)
    analysis_metric_keys: List[str] = []
    constant_metric_keys: List[str] = []
    temperature_metric_keys: List[str] = []
    temperature_view_name: Optional[str] = None
    unsupported_metrics: List[str] = []

    for key in ordered_metrics:
        group_key = metric_group_lookup.get(key, "primary")
        if group_key == "constant":
            constant_metric_keys.append(key)
            continue
        if group_key == "temperature":
            temperature_metric_keys.append(key)
            if temperature_view_name is None:
                candidates = metric_group_views.get("temperature") or []
                temperature_view_name = candidates[0] if candidates else "calc_temperature_data"
            continue
        allowed_views = metric_group_views.get(group_key) or []
        if allowed_views and active_view_name not in allowed_views:
            # 特殊处理北海分表视图：如果对应的公司视图允许，则分表视图也允许
            allowed = False
            if "analysis_beihai_sub_" in active_view_name:
                fallback_view = active_view_name.replace("analysis_beihai_sub_", "analysis_company_")
                if fallback_view in allowed_views:
                    allowed = True
            if not allowed:
                unsupported_metrics.append(key)
                continue
        analysis_metric_keys.append(key)

    if unsupported_metrics:
        labels = [metric_dict.get(key, key) for key in unsupported_metrics]
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"当前视图不支持以下指标: {', '.join(labels)}"},
        )

    try:
        analysis_rows = _query_analysis_rows(
            active_view_name,
            unit_key,
            analysis_metric_keys,
            start_date,
            end_date,
            sheet_name=sheet_name_filter,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"查询分析视图失败: {exc}"},
        )

    try:
        constant_rows = _query_constant_rows(unit_key, constant_metric_keys)
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"查询常量指标失败: {exc}"},
        )

    # ... existing code ...
    temperature_rows: Dict[str, Dict[str, Any]] = {}
    if temperature_metric_keys:
        view_name = temperature_view_name or "calc_temperature_data"
        try:
            temperature_rows = _query_temperature_rows(
                view_name,
                temperature_metric_keys,
                start_date,
                end_date,
                analysis_mode_value,
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
        except Exception as exc:  # pylint: disable=broad-except
            return JSONResponse(
                status_code=500,
                content={"ok": False, "message": f"查询气温指标失败: {exc}"},
            )
    timeline_rows_map: Dict[str, List[Dict[str, Any]]] = {}
    if analysis_mode_value == "range" and analysis_metric_keys:
        if is_beihai_sub_scope:
            timeline_view_name = "analysis_beihai_sub_daily"
            timeline_sheet_name = sheet_name_filter
        else:
            fallback_timeline_view = (
                "analysis_groups_daily"
                if unit_key in {"Group", "ZhuChengQu"}
                else "analysis_company_daily"
            )
            timeline_view_name = _resolve_unit_view(
                view_mapping,
                "单日数据",
                unit_label,
                fallback=fallback_timeline_view,
            )
            timeline_sheet_name = None
        if timeline_view_name:
            try:
                timeline_rows_map = _query_analysis_timeline(
                    timeline_view_name,
                    unit_key,
                    analysis_metric_keys,
                    start_date,
                    end_date,
                    sheet_name=timeline_sheet_name,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("生成逐日明细失败: %s", exc)

    # Calculate Ring Growth for AI Report
    prev_rows_map: Dict[str, Dict[str, Any]] = {}
    if getattr(payload, "request_ai_report", False) and analysis_mode_value == "range":
        try:
            prev_start, prev_end = _compute_previous_range(start_date, end_date)
            if prev_start and prev_end:
                prev_rows_map = _query_analysis_rows(
                    active_view_name,
                    unit_key,
                    analysis_metric_keys,
                    prev_start,
                    prev_end,
                    sheet_name=sheet_name_filter,
                )
        except Exception as exc:
            logger.warning("计算环比数据失败: %s", exc)

    rows_payload: List[Dict[str, Any]] = []
    missing_metrics: List[Dict[str, str]] = []
    resolved_keys: List[str] = []

    for key in ordered_metrics:
        label = metric_dict.get(key, key)
        source = analysis_rows.get(key)
        value_type = "analysis"
        source_view = active_view_name if source else None
        decimals = metric_decimals.get(key, 2)
        if source is None:
            source = constant_rows.get(key)
            if source is not None:
                value_type = "constant"
                source_view = "constant_data"
        if source is None:
            source = temperature_rows.get(key)
            if source is not None:
                value_type = "temperature"
                source_view = source.get("source_view")
        if source is None:
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": None,
                    "current": None,
                    "peer": None,
                    "delta": None,
                    "value_type": metric_group_lookup.get(key, "primary"),
                    "source_view": None,
                    "missing": True,
                },
            )
            missing_metrics.append({"key": key, "label": label})
            continue

        resolved_keys.append(key)
        timeline_entries = timeline_rows_map.get(key, [])
        
        # Calculate totals based on value type
        if value_type == "temperature":
            # For temperature, use Average instead of Sum
            valid_currents = [entry["current"] for entry in timeline_entries if entry.get("current") is not None]
            valid_peers = [entry["peer"] for entry in timeline_entries if entry.get("peer") is not None]
            
            timeline_current_val = (sum(valid_currents) / len(valid_currents)) if valid_currents else None
            timeline_peer_val = (sum(valid_peers) / len(valid_peers)) if valid_peers else None
        else:
            # For others, use Sum
            timeline_current_val = (
                sum(entry["current"] for entry in timeline_entries if entry.get("current") is not None)
                if timeline_entries
                else None
            )
            timeline_peer_val = (
                sum(entry["peer"] for entry in timeline_entries if entry.get("peer") is not None)
                if timeline_entries
                else None
            )

        # Calculate Ring Ratio
        ring_ratio = None
        if prev_rows_map and key in prev_rows_map:
            prev_source = prev_rows_map[key]
            # In range mode, the query returns 'value' (aggregated), not 'value_biz_date'
            prev_val = _decimal_to_float(prev_source.get("value"))
            
            # Determine current value for ring calculation
            # Use the calculated total/average from timeline if available, otherwise fallback to source value
            if timeline_current_val is not None:
                current_val_for_ring = timeline_current_val
            else:
                current_val_for_ring = _decimal_to_float(source.get("value"))

            if current_val_for_ring is not None and prev_val is not None and abs(prev_val) > 1e-9:
                ring_ratio = (current_val_for_ring - prev_val) / abs(prev_val) * 100

        if value_type == "constant":
            current_value = _decimal_to_float(source.get("value"))
            peer_value = _decimal_to_float(source.get("peer"))
            # For constant, total is just the value itself if timeline is empty or same
            total_current = timeline_current_val if timeline_current_val is not None else current_value
            total_peer = timeline_peer_val if timeline_peer_val is not None else peer_value
            
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "period": source.get("period"),
                    "peer_period": source.get("peer_period"),
                    "missing": False,
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                    "ring_ratio": ring_ratio,
                },
            )
        elif value_type == "temperature":
            current_value = _decimal_to_float(source.get("value"))
            peer_value = _decimal_to_float(source.get("peer"))
            is_missing = source.get("missing")
            total_current = timeline_current_val if timeline_current_val is not None else current_value
            total_peer = timeline_peer_val if timeline_peer_val is not None else peer_value
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "missing": bool(is_missing),
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                    "ring_ratio": ring_ratio,
                },
            )
            if is_missing:
                missing_metrics.append({"key": key, "label": label})
        else:
            current_value = _decimal_to_float(source.get("value_biz_date"))
            peer_value = _decimal_to_float(source.get("value_peer_date"))
            total_current = timeline_current_val if timeline_current_val is not None else current_value
            total_peer = timeline_peer_val if timeline_peer_val is not None else peer_value
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "biz_date": source.get("biz_date").isoformat() if source.get("biz_date") else None,
                    "peer_date": source.get("peer_date").isoformat() if source.get("peer_date") else None,
                    "missing": False,
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                    "ring_ratio": ring_ratio,
                },
            )

    warnings: List[str] = []
    # ... existing code ...
    if missing_metrics:
        warnings.append(
            "以下指标暂无可返回数据：{}".format(", ".join(item["label"] for item in missing_metrics))
        )

    response_payload = {
        "ok": True,
        "config_path": schema_payload.get("config_path"),
        "unit_key": unit_key,
        "unit_label": unit_label,
        "analysis_mode": analysis_mode_value,
        "analysis_mode_label": mode_label,
        "view": active_view_name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows_payload,
        "requested_metrics": ordered_metrics,
        "resolved_metrics": resolved_keys,
        "missing_metrics": missing_metrics,
        "warnings": warnings,
    }
    if payload.request_ai_report:
        try:
            job_id = data_analysis_ai_report.enqueue_ai_report_job(response_payload)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("触发 AI 报告生成失败: %s", exc)
        else:
            if job_id:
                response_payload["ai_report_job_id"] = job_id
    return JSONResponse(status_code=200, content=response_payload)


@router.post(
    "/data_analysis/query",
    summary="执行数据分析组合查询",
)
async def query_data_analysis(
    request: Request,
    config: Optional[str] = Query(
        default=None,
        alias="config",
        description="可选配置文件路径（相对 DATA_DIRECTORY）",
    ),
):
    try:
        raw_payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "请求体必须为合法的 JSON"},
        )

    try:
        payload = DataAnalysisQueryPayload(**raw_payload)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "message": "参数校验失败", "errors": exc.errors()},
        )

    schema_payload, error = _build_data_analysis_schema_payload(config)
    if error:
        return error
    if not schema_payload:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "无法加载数据分析配置"},
        )
    return _execute_data_analysis_query(payload, schema_payload)


@router.get(
    "/data_analysis/ai_report/{job_id}",
    summary="查询 AI 数据分析报告状态",
)
async def get_data_analysis_ai_report(job_id: str = Path(..., description="AI 报告任务 ID")):
    job_payload = data_analysis_ai_report.get_report_job(job_id)
    if not job_payload:
        return JSONResponse(status_code=404, content={"ok": False, "message": "报告不存在或已过期"})
    response = {"ok": True}
    response.update(job_payload)
    return JSONResponse(status_code=200, content=response)


def _detect_readonly_limit_backend(columns: Sequence[Any]) -> int:
    if not isinstance(columns, Sequence):
        return 1
    for idx, col in enumerate(columns):
        if isinstance(col, str) and "计量单位" in col:
            return idx
    return 1


def _ensure_row_length(row: List[Any], target_length: int) -> None:
    if len(row) < target_length:
        row.extend([None] * (target_length - len(row)))


def _apply_linkage_constraints(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    rows_raw = payload.get("rows")
    columns = payload.get("columns")
    if not isinstance(rows_raw, list) or not isinstance(columns, list) or not columns:
        return payload

    linkage_raw = payload.get("linkage_dict")
    if not isinstance(linkage_raw, dict) or not linkage_raw:
        alias_raw = payload.get("指标联动")
        if isinstance(alias_raw, dict) and alias_raw:
            linkage_raw = alias_raw
        else:
            return payload

    normalized_rows: List[List[Any]] = []
    for row in rows_raw:
        if isinstance(row, list):
            normalized_rows.append(row)
        elif isinstance(row, tuple):
            normalized_rows.append(list(row))
        else:
            normalized_rows.append([row])

    payload["rows"] = normalized_rows

    label_to_index: Dict[str, int] = {}
    for idx, row in enumerate(normalized_rows):
        label_value = row[0] if row else ""
        if isinstance(label_value, str):
            label = label_value.strip()
        elif label_value is None:
            label = ""
        else:
            label = str(label_value).strip()
        if label:
            label_to_index[label] = idx

    if not label_to_index:
        return payload

    adjacency: Dict[int, Set[int]] = {}

    def _register_link(src_idx: int, dst_idx: int) -> None:
        if src_idx == dst_idx:
            return
        adjacency.setdefault(src_idx, set()).add(dst_idx)

    for src_label_raw, targets_raw in linkage_raw.items():
        src_label = "" if src_label_raw is None else str(src_label_raw).strip()
        if not src_label:
            continue
        src_idx = label_to_index.get(src_label)
        if src_idx is None:
            continue

        if isinstance(targets_raw, (list, tuple, set)):
            targets_iter = targets_raw
        else:
            targets_iter = [targets_raw]

        for target_label_raw in targets_iter:
            target_label = "" if target_label_raw is None else str(target_label_raw).strip()
            if not target_label:
                continue
            dst_idx = label_to_index.get(target_label)
            if dst_idx is None:
                continue
            _register_link(src_idx, dst_idx)
            _register_link(dst_idx, src_idx)

    if not adjacency:
        return payload

    readonly_limit = _detect_readonly_limit_backend(columns)
    value_start_col = max(readonly_limit + 1, 2)
    total_columns = len(columns)

    for row in normalized_rows:
        if isinstance(row, list):
            _ensure_row_length(row, total_columns)

    for src_idx, neighbors in adjacency.items():
        if src_idx >= len(normalized_rows):
            continue
        source_row = normalized_rows[src_idx]
        _ensure_row_length(source_row, total_columns)
        for dst_idx in neighbors:
            if dst_idx >= len(normalized_rows):
                continue
            target_row = normalized_rows[dst_idx]
            _ensure_row_length(target_row, total_columns)
            for col_idx in range(value_start_col, total_columns):
                target_row[col_idx] = source_row[col_idx]

    return payload


def _normalize_submission(payload: Dict[str, Any]) -> Dict[str, Any]:
    project_key = payload.get("project_key", "")
    project_name = payload.get("project_name") or project_key
    sheet_key = payload.get("sheet_key", "")
    sheet_name = payload.get("sheet_name", sheet_key)
    unit_id = payload.get("unit_id", "")
    unit_name_value = payload.get("unit_name")
    if not isinstance(unit_name_value, str) or not unit_name_value.strip():
        unit_name_value = payload.get("单位名称")
    if not isinstance(unit_name_value, str):
        unit_name_value = ""
    unit_name_value = unit_name_value.strip()
    submit_time_raw = payload.get("submit_time")
    submit_dt: Optional[datetime] = None
    if isinstance(submit_time_raw, str):
        try:
            submit_dt = datetime.fromisoformat(submit_time_raw.replace("Z", "+00:00"))
        except ValueError:
            submit_dt = None

    item_dict_raw = payload.get("item_dict")
    item_dict = item_dict_raw if isinstance(item_dict_raw, dict) else {}
    company_dict_raw = payload.get("company_dict")
    company_dict = company_dict_raw if isinstance(company_dict_raw, dict) else {}

    columns = payload.get("columns") or []
    rows = payload.get("rows") or []

    records: List[Dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            continue
        row_label = row[0] if len(row) > 0 else ""
        unit = row[1] if len(row) > 1 else ""
        for col_index in range(min(len(columns), len(row))):
            records.append(
                {
                    "project_key": project_key,
                    "project_name": project_name,
                    "sheet_key": sheet_key,
                    "sheet_name": sheet_name,
                    "unit_id": unit_id,
                    "row_index": row_index,
                    "row_label": row_label,
                    "unit": unit,
                    "column_index": col_index,
                    "column_name": columns[col_index],
                    "value_raw": row[col_index],
                }
            )

    return {
        "project_key": project_key,
        "project_name": project_name,
        "sheet_key": sheet_key,
        "sheet_name": sheet_name,
        "unit_id": unit_id,
        "unit_name": unit_name_value,
        "submit_time": submit_dt,
        "item_dict": item_dict,
        "company_dict": company_dict,
        "records": records,
    }


def _invert_mapping(mapping: Dict[str, Any]) -> Dict[str, str]:
    """将配置字典反转为中文 -> 英文 key 的映射。"""
    inverted: Dict[str, str] = {}
    if isinstance(mapping, dict):
        for key, value in mapping.items():
            if isinstance(value, str):
                inverted[value.strip()] = str(key).strip()
    return inverted


def _parse_coal_inventory_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """将煤炭库存表 payload 拆解为结构化记录。"""
    columns_raw = payload.get("columns") or []
    column_index: Dict[str, int] = {}
    for idx, col in enumerate(columns_raw):
        if isinstance(col, str):
            name = col.strip()
            if name and name not in column_index:
                column_index[name] = idx

    unit_idx = column_index.get("计量单位")
    note_idx = column_index.get("备注")
    storage_columns: List[Tuple[int, str, str]] = []
    for cn_name, (code, label_cn) in COAL_STORAGE_NAME_MAP.items():
        storage_idx = column_index.get(cn_name)
        if storage_idx is not None:
            storage_columns.append((storage_idx, code, label_cn))

    rows = payload.get("rows") or []
    company_dict = payload.get("company_dict")
    coal_dict = payload.get("item_dict")
    company_lookup = _invert_mapping(company_dict if isinstance(company_dict, dict) else {})
    coal_lookup = _invert_mapping(coal_dict if isinstance(coal_dict, dict) else {})

    biz_date = payload.get("biz_date")
    status_value = str(payload.get("status") or "submit").strip()
    submit_time = payload.get("submit_time")

    parsed: List[Dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) < 2:
            continue

        company_cn = str(row[0]).strip() if row[0] is not None else ""
        coal_type_cn = str(row[1]).strip() if row[1] is not None else ""
        if not company_cn or not coal_type_cn:
            continue

        unit_value = None
        if unit_idx is not None and unit_idx < len(row):
            candidate = str(row[unit_idx]).strip() if row[unit_idx] is not None else ""
            unit_value = candidate or None

        note_value = None
        if note_idx is not None and note_idx < len(row):
            candidate = str(row[note_idx]).strip() if row[note_idx] is not None else ""
            note_value = candidate or None

        company_code = company_lookup.get(company_cn, company_cn)
        coal_type_code = coal_lookup.get(coal_type_cn, coal_type_cn)

        for col_idx, storage_code, storage_cn in storage_columns:
            if col_idx >= len(row):
                value_str = None
            else:
                raw_value = row[col_idx]
                if raw_value is None:
                    value_str = None
                else:
                    value_raw = str(raw_value).strip()
                    value_str = value_raw or None

            parsed.append(
                {
                    "company": company_code,
                    "company_cn": company_cn,
                    "coal_type": coal_type_code,
                    "coal_type_cn": coal_type_cn,
                    "storage_type": storage_code,
                    "storage_type_cn": storage_cn,
                    "value": value_str,
                    "unit": unit_value,
                    "date": biz_date,
                    "note": note_value,
                    "status": status_value,
                    "operation_time": submit_time,
                }
            )

    return parsed


def _write_coal_inventory_debug(payload: Dict[str, Any], records: List[Dict[str, Any]]) -> None:
    """将调试信息写入 backend_data/test.md。"""
    COAL_INVENTORY_DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(EAST_8_TZ).strftime("%Y-%m-%d %H:%M:%S")
    debug_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    debug_records = json.dumps(records, ensure_ascii=False, indent=2)
    with COAL_INVENTORY_DEBUG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"## Coal Inventory Debug {timestamp}\n\n")
        fh.write("### Raw Payload\n```json\n")
        fh.write(debug_payload)
        fh.write("\n```\n\n### Parsed Records\n```json\n")
        fh.write(debug_records)
        fh.write("\n```\n\n")


def _persist_coal_inventory(records: List[Dict[str, Any]]) -> int:
    """将煤炭库存记录写入数据库，按 (company, coal_type, storage_type, date) 删除后插入。"""
    if not records:
        return 0

    session = SessionLocal()
    try:
        models: List[CoalInventoryData] = []
        delete_keys = set()

        for record in records:
            company = str(record.get("company") or "").strip()
            coal_type = str(record.get("coal_type") or "").strip()
            storage_type = str(record.get("storage_type") or "").strip()
            if not company or not coal_type or not storage_type:
                continue

            row_date = _parse_date_value(record.get("date"))
            if row_date is None:
                continue

            value_decimal = _parse_decimal_value(record.get("value"))
            operation_time = _parse_operation_time(record.get("operation_time"))

            models.append(
                CoalInventoryData(
                    company=company,
                    company_cn=str(record.get("company_cn") or "").strip() or None,
                    coal_type=coal_type,
                    coal_type_cn=str(record.get("coal_type_cn") or "").strip() or None,
                    storage_type=storage_type,
                    storage_type_cn=str(record.get("storage_type_cn") or "").strip() or None,
                    value=value_decimal,
                    unit=str(record.get("unit") or "").strip() or None,
                    note=str(record.get("note") or "").strip() or None,
                    date=row_date,
                    operation_time=operation_time or datetime.now(EAST_8_TZ),
                )
            )
            delete_keys.add((company, coal_type, storage_type, row_date))

        if not models:
            return 0

        for company, coal_type, storage_type, row_date in delete_keys:
            session.execute(
                delete(CoalInventoryData).where(
                    CoalInventoryData.company == company,
                    CoalInventoryData.coal_type == coal_type,
                    CoalInventoryData.storage_type == storage_type,
                    CoalInventoryData.date == row_date,
                )
            )

        session.bulk_save_objects(models)
        session.commit()
        return len(models)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def handle_coal_inventory_submission(payload: Dict[str, Any]) -> JSONResponse:
    """处理煤炭库存表，输出调试并写入数据库。"""
    records = _parse_coal_inventory_records(payload)
    _write_coal_inventory_debug(payload, records)
    inserted = _persist_coal_inventory(records)
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "煤炭库存数据已写入 coal_inventory_data（同时记录于 backend_data/test.md）",
            "records": len(records),
            "inserted": inserted,
        },
    )

# ============ 调试：运行时表达式求值 ============
@router.post("/runtime/spec/eval", summary="运行时表达式求值（调试）", tags=["runtime"])
async def runtime_eval(request: Request):
    """
    调试路由：根据模板（或内联 spec）与主键、可选 biz_date，对模板中的表达式进行求值替换，返回 rows-only 结构。
    请求体示例：
    {
      "sheet_key": "BeiHai_co_generation_approval_Sheet",
      "project_key": "daily_report_25_26",
      "primary_key": {"company": "BeiHai"},
      "config": "configs/字典样例.json",   // 可选，优先查找的模板文件（相对 data 目录）
      "biz_date": "regular" | "2025-10-27", // 可选
      "trace": false,                       // 可选
      "spec": { ... }                       // 可选，若提供则直接使用此对象作为 spec
    }
    返回：
    {
      "ok": true,
      "sheet_key": "...",
      "sheet_name": "...",
      "unit_id": "...",
      "unit_name": "...",
      "columns": [...],
      "rows": [...],
      "debug": {...}  // trace=true 时包含
    }
    """
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"ok": False, "message": "请求体需为 JSON 对象"})

    sheet_key = str(payload.get("sheet_key") or "").strip()
    project_key = str(payload.get("project_key") or "daily_report_25_26").strip()
    primary_key = payload.get("primary_key") or {}
    if not isinstance(primary_key, dict):
        return JSONResponse(status_code=422, content={"ok": False, "message": "primary_key 需为对象"})
    if not primary_key.get("company"):
        # 回落：若未提供，则尝试从模板 unit_id 填充
        pass

    trace = bool(payload.get("trace", False))
    biz_date_raw = str(payload.get("biz_date") or "regular").strip()
    resolved_biz_date: Optional[str]
    biz_date_mode = "regular"
    if not biz_date_raw or biz_date_raw.lower() == "regular":
        display_date = auth_manager.current_display_date()
        resolved_biz_date = display_date.isoformat()
    else:
        try:
            resolved_biz_date = date.fromisoformat(biz_date_raw).isoformat()
            biz_date_mode = "custom"
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "biz_date 需为空、'regular' 或符合 YYYY-MM-DD"},
            )
    config = payload.get("config")
    spec_override = payload.get("spec")

    # 准备 spec（支持三种来源优先级：spec 覆盖 > sheet_key+config 定位 > 仅 config 自动推断）
    if isinstance(spec_override, dict):
        spec = dict(spec_override)
        names = _extract_names(spec)
        columns_raw = _extract_list(spec, COLUMN_KEYS)
        rows_raw = _extract_list(spec, ROW_KEYS)
    else:
        preferred_path = _resolve_data_file(config) if isinstance(config, str) and config.strip() else None
        # 若未提供 sheet_key，且提供了 config，则尝试从文件自动推断唯一的表
        if not sheet_key and preferred_path is not None and preferred_path.exists():
            try:
                raw = _read_json(preferred_path)
                if isinstance(raw, dict) and len(raw) == 1:
                    sheet_key = next(iter(raw.keys()))
            except Exception:
                pass
        spec, data_path, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
        if spec is None:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "message": f"未找到模板：{sheet_key or '(未提供)'}"},
            )
        names = _extract_names(spec)
        columns_raw = _extract_list(spec, COLUMN_KEYS)
        rows_raw = _extract_list(spec, ROW_KEYS)

    if columns_raw is None or rows_raw is None:
        return JSONResponse(status_code=422, content={"ok": False, "message": "模板缺少列名或数据"})

    # 兼容：若模板未提供“项目字典”，尝试从 item_dict 补齐
    dict_bundle = _collect_all_dicts(spec)
    if "项目字典" not in spec and dict_bundle.get("item_dict"):
        spec = dict(spec)  # 浅拷贝
        spec["项目字典"] = dict_bundle.get("item_dict")

    # 兼容：若模板未提供“查询数据源”，填入默认值
    if "查询数据源" not in spec or not isinstance(spec.get("查询数据源"), dict):
        spec = dict(spec)
        spec["查询数据源"] = {
            "主键": {"company": names.get("unit_id") or primary_key.get("company")},
            "主表": "sum_basic_data",
            "缩写": {"c": "constant_data"},
        }

    # 路由主表：支持按公司动态选择 sum_basic_data / groups
    # 支持两种写法：
    # A) 顶层："主表路由": {"groups": ["Group","ZhuChengQu"], "default": "sum_basic_data"}
    # B) 查询数据源内："查询数据源": {"主表": {"groups": [...], "default": "sum_basic_data"}, ...}
    try:
        qds_in = spec.get("查询数据源") if isinstance(spec, dict) else None
        route_cfg = spec.get("主表路由") if isinstance(spec, dict) else None
        if not isinstance(route_cfg, dict) and isinstance(qds_in, dict):
            mb = qds_in.get("主表")
            if isinstance(mb, dict) and ("groups" in mb or "default" in mb):
                route_cfg = mb
        if isinstance(route_cfg, dict):
            groups_list = route_cfg.get("groups") or []
            default_table = route_cfg.get("default") or "sum_basic_data"
            # 确定 company：primary_key 覆盖模板 unit_id
            company_value = (primary_key.get("company") if isinstance(primary_key, dict) else None) or names.get("unit_id")
            company_value = str(company_value or '').strip()
            # 对于复合 unit_id（如 A/B/C），由行内 discriminator 覆盖；此处仅用于选默认主表
            # 选择默认表：若 company 正好在 groups 列表，则用 groups；否则 default
            target_table = "groups" if company_value in set(groups_list) else default_table
            qds = spec.get("查询数据源")
            if isinstance(qds, dict):
                # 仅当“主表”不是路由对象时才覆盖，避免破坏按公司路由
                is_route_obj = isinstance(qds.get("主表"), dict)
                if not is_route_obj:
                    qds = dict(qds)
                    qds["主表"] = target_table
                    # 回写覆盖
                    spec = dict(spec)
                    spec["查询数据源"] = qds
    except Exception:
        # 路由失败不应影响主流程
        pass

    # 若 primary_key 未提供 company，则由模板 unit_id 回填
    if not primary_key.get("company"):
        unit_id = names.get("unit_id")
        if unit_id:
            primary_key = dict(primary_key)
            primary_key["company"] = unit_id

    try:
        result = render_spec(
            spec=spec,
            project_key=project_key,
            primary_key=primary_key,
            trace=trace,
            context={"biz_date": resolved_biz_date},
        )
    except Exception as exc:
        return JSONResponse(status_code=500, content={"ok": False, "message": "求值失败", "error": str(exc)})

    # 输出 rows-only（优先使用 render_spec 返回的列头，已做占位替换；否则回落模板原列头）
    columns_from_result = result.get("columns") or result.get("列名")
    if isinstance(columns_from_result, list) and columns_from_result:
        columns = [str(c) for c in columns_from_result]
    else:
        columns = list(columns_raw) if isinstance(columns_raw, list) else list(columns_raw)
    rows = result.get("数据") or []
    # 统一解析 accuracy：支持数字或对象 {default: N}，默认 2；允许 number_format.default 覆盖
    def _resolve_acc(v):
        try:
            if isinstance(v, dict):
                v = v.get("default")
            return int(v)
        except Exception:
            return None
    acc = _resolve_acc(result.get("accuracy") if isinstance(result, dict) else None)
    if acc is None:
        acc = _resolve_acc(spec.get("accuracy") if isinstance(spec, dict) else None)
    # number_format.default 优先于 accuracy
    nf_spec = spec.get("number_format") if isinstance(spec, dict) else None
    if isinstance(nf_spec, dict):
        nf_acc = _resolve_acc(nf_spec.get("default"))
        if nf_acc is not None:
            acc = nf_acc
    if acc is None:
        acc = 2

    accuracy_map = {}
    try:
        raw_map = result.get("accuracy_map") if isinstance(result, dict) else None
        if isinstance(raw_map, dict):
            for key, val in raw_map.items():
                if key is None:
                    continue
                parsed = _resolve_acc(val)
                if parsed is None:
                    try:
                        parsed = int(val)
                    except Exception:
                        continue
                if parsed < 0:
                    parsed = 0
                if parsed > 8:
                    parsed = 8
                accuracy_map[str(key)] = parsed
    except Exception:
        accuracy_map = {}

    content = {
        "ok": True,
        "sheet_key": sheet_key or names.get("sheet_name") or "",
        "sheet_name": names.get("sheet_name") or sheet_key,
        "unit_id": names.get("unit_id", ""),
        "unit_name": names.get("unit_name", ""),
        "columns": columns,
        "rows": rows,
        "accuracy": acc,
        # 透传前端格式化用的 number_format（如 grouping/locale/default/percent）
        "number_format": (nf_spec if isinstance(nf_spec, dict) else None),
        "biz_date": resolved_biz_date,
        "biz_date_mode": biz_date_mode,
        "requested_biz_date": biz_date_raw,
    }
    if accuracy_map:
        content["accuracy_overrides"] = accuracy_map
    column_headers = result.get("column_headers")
    if isinstance(column_headers, list) and column_headers:
        content["column_headers"] = column_headers
    column_groups = result.get("column_groups")
    if isinstance(column_groups, list) and column_groups:
        content["column_groups"] = column_groups
    if trace and "_trace" in result:
        content["debug"] = {"_trace": result["_trace"]}
    return JSONResponse(status_code=200, content=content)


# 临时调试：查看指定 company 的指标与常量缓存（不依赖 render_spec）
@router.get("/runtime/spec/debug-cache", summary="调试：查看 company 的指标与常量缓存")
def debug_cache(company: str):
    """
    返回 sum_basic_data 中该 company 的 6 个口径指标，以及 constant_data 的 period 值，便于诊断为何计算为 0。
    """
    session = SessionLocal()
    try:
        m_rows = session.execute(text("""
            SELECT item, item_cn, value_biz_date, value_peer_date,
                   sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer
            FROM sum_basic_data WHERE company = :company
        """), {"company": company}).mappings().all()
        c_rows = session.execute(text("""
            SELECT item, item_cn, period, value
            FROM constant_data WHERE company = :company
            ORDER BY item, period
        """), {"company": company}).mappings().all()
        return JSONResponse(status_code=200, content={
            "ok": True,
            "company": company,
            "metrics_count": len(m_rows),
            "constants_count": len(c_rows),
            "metrics_sample": [dict(r) for r in m_rows[:50]],
            "constants_sample": [dict(r) for r in c_rows[:200]],
        })
    finally:
        session.close()
@router.get(
    "/dashboard/cache/publish/status",
    summary="查询缓存发布任务状态",
    tags=["daily_report_25_26"],
)
def get_cache_publish_status():
    snapshot = cache_publish_job_manager.snapshot()
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/publish/cancel",
    summary="停止正在运行的缓存发布任务",
    tags=["daily_report_25_26"],
)
def cancel_cache_publish(session: AuthSession = Depends(get_current_session)):
    _ensure_cache_operator(session)
    snapshot = cache_publish_job_manager.request_cancel()
    return {"ok": True, "job": snapshot}


@router.post(
    "/dashboard/cache/refresh",
    summary="刷新指定日期的数据看板缓存",
    tags=["daily_report_25_26"],
)
def refresh_dashboard_cache(
    show_date: str = Query(
        default="",
        description="目标展示日期，格式 YYYY-MM-DD；留空刷新默认缓存",
    ),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_cache_operator(session)
    cache_key = dashboard_cache.resolve_cache_key(show_date)
    result = evaluate_dashboard(PROJECT_KEY, show_date=show_date)
    payload = _build_dashboard_payload(result)
    status = dashboard_cache.update_cache_entry(PROJECT_KEY, cache_key, payload)
    return {
        "ok": True,
        "cached_key": cache_key,
        "cache_disabled": status.get("disabled", False),
        "cache_updated_at": status.get("updated_at"),
    }
