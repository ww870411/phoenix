"""
daily_report_25_26 项目 v1 路由

说明：
- 所有接口挂载在 `/api/v1/daily_report_25_26` 前缀下。
- 当前实现模板读取功能，提交与查询仍保留占位实现，后续可逐步替换。
- 模板文件来源于容器内数据目录（默认 `/app/data`）中的 JSON 配置。
"""

from datetime import datetime, timedelta, timezone

from pathlib import Path as SysPath

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Path, Query, Request

from fastapi.responses import JSONResponse

from sqlalchemy import delete

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import ConstantData
from backend.db.database_daily_report_25_26 import (
    CoalInventoryData,
    ConstantData,
    DailyBasicData,
    GongreBranchesDetailData,
    SessionLocal,
)

import json





# Use统一的数据目录常量，默认指向容器内 /app/data
DATA_ROOT = SysPath(DATA_DIRECTORY)
COAL_INVENTORY_DEBUG_FILE = DATA_ROOT / "test.md"
GONGRE_DEBUG_FILE = SysPath(__file__).resolve().parents[3] / "configs" / "111.md"
GONGRE_SHEET_KEYS = {"gongre_branches_detail_sheet"}
BASIC_TEMPLATE_PATH = DATA_ROOT / "数据结构_基本指标表.json"
COAL_STORAGE_NAME_MAP = {
    "在途煤炭": ("coal_in_transit", "在途煤炭"),
    "港口存煤": ("coal_at_port", "港口存煤"),
    "厂内存煤": ("coal_at_plant", "厂内存煤"),
}

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
COLUMN_KEYS = ("列名", "columns", "表头")
ROW_KEYS = ("数据", "rows", "records", "lines")
ITEM_DICT_KEYS = ("item_dict", "项目字典")
COMPANY_DICT_KEYS = ("company_dict", "单位字典", "unit_dict")
CENTER_DICT_KEYS = ("center_dict", "中心字典")
STATUS_DICT_KEYS = ("status_dict", "状态字典")
DICT_KEY_GROUPS = {
    "item_dict": ITEM_DICT_KEYS,
    "company_dict": COMPANY_DICT_KEYS,
    "center_dict": CENTER_DICT_KEYS,
    "status_dict": STATUS_DICT_KEYS,
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
) -> Tuple[Optional[Dict[str, Any]], Optional[SysPath]]:
    """在候选模板文件中按 sheet_key 查找配置。"""

    def _consider(payload: Dict[str, Any], path: SysPath) -> Optional[Tuple[Dict[str, Any], SysPath]]:
        if not isinstance(payload, dict):
            return None
        names = _extract_names(payload)
        if names["unit_id"]:
            return payload, path
        return None

    best_payload: Optional[Dict[str, Any]] = None
    best_path: Optional[SysPath] = None
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

        if isinstance(raw, dict):
            direct = raw.get(sheet_key)
            if isinstance(direct, dict):
                hit = _consider(direct, data_path)
                if hit:
                    return hit
                if best_payload is None:
                    best_payload, best_path = direct, data_path

            for key, payload in raw.items():
                if not isinstance(payload, dict):
                    continue
                if key.lower() == target_key_lower:
                    hit = _consider(payload, data_path)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path = payload, data_path
                        continue
                names = _extract_names(payload)
                if names["sheet_name"] == sheet_key:
                    hit = _consider(payload, data_path)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path = payload, data_path

        elif isinstance(raw, list):
            for payload in raw:
                if not isinstance(payload, dict):
                    continue
                candidate = payload.get("sheet_key")
                names = _extract_names(payload)
                if candidate == sheet_key or names["sheet_name"] == sheet_key:
                    hit = _consider(payload, data_path)
                    if hit:
                        return hit
                    if best_payload is None:
                        best_payload, best_path = payload, data_path

    return best_payload, best_path


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

    center_lookup = _invert_mapping(payload.get("center_dict") if isinstance(payload.get("center_dict"), dict) else {})
    item_lookup = _invert_mapping(payload.get("item_dict") if isinstance(payload.get("item_dict"), dict) else {})

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


def _persist_gongre_branches_detail(payload: Dict[str, Any], records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0

    session = SessionLocal()
    try:
        models: List[GongreBranchesDetailData] = []
        delete_keys = set()
        fallback_status = str(payload.get("status") or "submit").strip() or "submit"
        fallback_operation_time = payload.get("submit_time")

        for record in records:
            center = str(record.get("center") or "").strip()
            center_cn = str(record.get("center_cn") or "").strip() or None
            sheet_name = str(record.get("sheet_name") or payload.get("sheet_key") or "").strip()
            item = str(record.get("item") or "").strip()
            item_cn = str(record.get("item_cn") or "").strip() or None

            if not center or not sheet_name or not item:
                continue

            row_date = _parse_date_value(record.get("date"))
            if row_date is None:
                continue

            value_decimal = _parse_decimal_value(record.get("value"))
            unit_value = str(record.get("unit") or "").strip() or None
            note_value = str(record.get("note") or "").strip() or None
            status_value = str(record.get("status") or fallback_status).strip() or fallback_status
            operation_time = _parse_operation_time(record.get("operation_time") or fallback_operation_time)

            models.append(
                GongreBranchesDetailData(
                    center=center,
                    center_cn=center_cn,
                    sheet_name=sheet_name,
                    item=item,
                    item_cn=item_cn,
                    value=value_decimal,
                    unit=unit_value,
                    note=note_value,
                    date=row_date,
                    status=status_value,
                    operation_time=operation_time,
                )
            )
            delete_keys.add((center, sheet_name, item, row_date))

        if not models:
            return 0

        for center, sheet_name, item, row_date in delete_keys:
            session.execute(
                delete(GongreBranchesDetailData).where(
                    GongreBranchesDetailData.center == center,
                    GongreBranchesDetailData.sheet_name == sheet_name,
                    GongreBranchesDetailData.item == item,
                    GongreBranchesDetailData.date == row_date,
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


async def handle_gongre_branches_detail_submission(payload: Dict[str, Any]) -> JSONResponse:
    records = _parse_gongre_branches_detail_records(payload)
    _write_gongre_branches_debug(payload, records)
    inserted = _persist_gongre_branches_detail(payload, records)
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "供热分中心数据已处理",
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
        try:
            return Decimal(value)
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
    if not flattened:
        return 0

    default_operation_time = _parse_operation_time(
        normalized.get("submit_time") or payload.get("submit_time")
    )
    default_status = (payload.get("status") or "submit").strip() or "submit"

    session = SessionLocal()
    try:
        models: List[DailyBasicData] = []
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

            row_date = _parse_date_value(record.get("date"))
            if row_date is None:
                continue

            value_decimal = _parse_decimal_value(record.get("value"))
            operation_time = _parse_operation_time(
                record.get("operation_time") or default_operation_time
            )
            status_value = str(record.get("status") or default_status).strip() or default_status

            model = DailyBasicData(
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
            models.append(model)
            delete_keys.add((company, sheet_name_key, item_key, row_date))

        if not models:
            return 0

        for company, sheet_name_key, item_key, row_date in delete_keys:
            session.execute(
                delete(DailyBasicData).where(
                    DailyBasicData.company == company,
                    DailyBasicData.sheet_name == sheet_name_key,
                    DailyBasicData.item == item_key,
                    DailyBasicData.date == row_date,
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

            rec = {
                "company": company_id,
                "company_cn": company_cn,
                "sheet_name": sheet_key,
                "item": item_id or item_cn,
                "item_cn": item_cn,
                "value": value,
                "unit": unit,
                "period": period,
                "operation_time": op_time,
            }
            # 如果模型包含 center 字段并且这是中心维度表，可在后续持久化中附加
            if has_center:
                rec["center_cn"] = center_cn or None
            result.append(rec)

    return result


def _persist_constant_data(records: List[Dict[str, Any]]) -> int:
    """将拆解后的常量记录持久化到数据库。"""
    if not records:
        return 0

    session = SessionLocal()
    try:
        # Use a set to track unique keys for deletion
        delete_keys = set()
        for record in records:
            key = (
                record["company"],
                record["sheet_name"],
                record["item"],
                record["period"],
            )
            delete_keys.add(key)
        
        # Idempotent write: delete existing records first
        if delete_keys:
            for company, sheet_name, item, period in delete_keys:
                session.execute(
                    delete(ConstantData).where(
                        ConstantData.company == company,
                        ConstantData.sheet_name == sheet_name,
                        ConstantData.item == item,
                        ConstantData.period == period,
                    )
                )

        # Bulk insert new records
        session.bulk_insert_mappings(ConstantData, records)
        session.commit()
        return len(records)
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
        if not isinstance(payload, dict):
            continue
        names = _extract_names(payload)
        key = str(sheet_key or names["sheet_name"])
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


router = APIRouter()


@router.get("/ping", summary="daily_report_25_26 心跳", tags=["daily_report_25_26"])
def ping_daily_report():
    return {"ok": True, "project": "daily_report_25_26", "message": "pong"}


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

    payload, data_path = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
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

    if _is_coal_inventory_sheet(sheet_key, payload):
        response_content["template_type"] = "crosstab"
        response_content["columns"] = list(columns_raw) if isinstance(columns_raw, list) else list(columns_raw)
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
            normalized = _normalize_submission(payload)
            flattened = _flatten_records(payload, normalized)
            inserted_rows = _persist_daily_basic(payload, normalized, flattened)
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
    - 标准/每日：按 date=biz_date 查询 daily_basic_data，返回 cells（回填到第一个数据列 col_index=2）。
    - 常量指标：按 period 查询 constant_data，返回 cells，col_index 为模板中对应期别的列索引。
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
        tpl_payload_detect, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
        if _is_coal_inventory_sheet(sheet_key, tpl_payload_detect):
            template_type = "crosstab"

    # 执行不同模板类型的镜像查询
    try:
        if template_type == "crosstab":
            # 煤炭库存：返回 rows/columns 宽表
            if not biz_date:
                return JSONResponse(
                    status_code=422,
                    content={"ok": False, "message": "煤炭库存查询需提供 biz_date"},
                )

            # 读取模板列头，构建列名→索引映射
            tpl_payload, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            # 确保前三列为 [单位, 煤种, 计量单位]（若模板中已有则保持原样）
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

                result_rows = list(row_map.values())

                return JSONResponse(
                    status_code=200,
                    content={
                        "ok": True,
                        "template_type": "crosstab",
                        "sheet_key": sheet_key,
                        "biz_date": biz_date,
                        "columns": columns,
                        "rows": result_rows,
                    },
                )
            finally:
                session.close()

        elif template_type == "constant":
            # 常量指标：如提供 period 则定向查询该期；否则返回所有已入库期别对应的 cells
            tpl_payload, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
            if tpl_payload is None:
                return JSONResponse(
                    status_code=404,
                    content={"ok": False, "message": f"未找到模板：{sheet_key}"},
                )
            columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
            dict_bundle = _collect_all_dicts(tpl_payload)
            has_center = isinstance(dict_bundle.get("center_dict"), dict) and len(dict_bundle.get("center_dict")) > 0
            start_idx = 3 if has_center else 2
            periods = [str(c).strip() if c is not None else "" for c in columns_raw[start_idx:]]
            session = SessionLocal()
            try:
                q = session.query(ConstantData).filter(ConstantData.sheet_name == sheet_key)
                if period:
                    q = q.filter(ConstantData.period == str(period).strip())
                if company:
                    q = q.filter(ConstantData.company == company)
                rows_db: List[ConstantData] = q.all()

                cells: List[Dict[str, Any]] = []
                for rec in rows_db:
                    value = float(rec.value) if rec.value is not None else None
                    # 为每条记录计算其列索引（根据其 period 定位到模板列头）
                    rec_period = str(rec.period or "").strip()
                    try:
                        p_offset = periods.index(rec_period) if rec_period else 0
                    except ValueError:
                        p_offset = 0
                    col_index = start_idx + p_offset
                    cells.append(
                        {
                            "row_label": rec.item_cn or rec.item,
                            "unit": rec.unit,
                            "col_index": col_index,
                            "value_type": "num" if value is not None else "text",
                            "value_num": value,
                        }
                    )

                return JSONResponse(
                    status_code=200,
                    content={
                        "ok": True,
                        "template_type": "standard",  # 常量沿用 standard 回填方式
                        "mode": "constant",
                        "sheet_key": sheet_key,
                        "period": period,
                        "cells": cells,
                    },
                )
            finally:
                session.close()

        else:
            # 标准/每日：按 biz_date 查询 daily_basic_data，返回 cells，默认回填第一个数据列（索引 2）
            if not biz_date:
                return JSONResponse(
                    status_code=422,
                    content={"ok": False, "message": "标准表查询需提供 biz_date"},
                )
            # 读取模板用于定位备注列索引
            note_column_index: Optional[int] = None
            try:
                tpl_payload, _ = _locate_sheet_payload(sheet_key, preferred_path=preferred_path)
                if tpl_payload is not None:
                    columns_raw = _extract_list(tpl_payload, COLUMN_KEYS) or []
                    cols = [str(c).strip() if c is not None else "" for c in columns_raw]
                    note_labels = {"解释说明", "说明", "备注", "note", "Note"}
                    for idx, name in enumerate(cols):
                        if name in note_labels:
                            note_column_index = idx
                            break
                    if note_column_index is None and len(cols) >= 5:
                        note_column_index = len(cols) - 1
            except Exception:
                note_column_index = None

            session = SessionLocal()
            try:
                q = session.query(DailyBasicData).filter(
                    DailyBasicData.sheet_name == sheet_key,
                    DailyBasicData.date == _parse_date_value(biz_date),
                )
                if company:
                    q = q.filter(DailyBasicData.company == company)
                rows_db: List[DailyBasicData] = q.all()

                cells: List[Dict[str, Any]] = []
                for rec in rows_db:
                    value = float(rec.value) if rec.value is not None else None
                    cells.append(
                        {
                            "row_label": rec.item_cn or rec.item,
                            "unit": rec.unit,
                            "col_index": 2,  # 默认按第一个数据列（本期日）回填
                            "value_type": "num" if value is not None else "text",
                            "value_num": value,
                        }
                    )
                    # 附加备注单元格（如果存在备注列且有备注值）
                    if note_column_index is not None and isinstance(rec.note, (str,)):
                        note_text = rec.note.strip()
                        if note_text:
                            cells.append(
                                {
                                    "row_label": rec.item_cn or rec.item,
                                    "unit": rec.unit,
                                    "col_index": note_column_index,
                                    "value_type": "text",
                                    "value_text": note_text,
                                }
                            )

                return JSONResponse(
                    status_code=200,
                    content={
                        "ok": True,
                        "template_type": "standard",
                        "sheet_key": sheet_key,
                        "biz_date": biz_date,
                        "cells": cells,
                    },
                )
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
