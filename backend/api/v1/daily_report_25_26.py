"""
daily_report_25_26 项目 v1 路由

说明：
- 所有接口挂载在 `/api/v1/daily_report_25_26` 前缀下。
- 当前实现模板读取功能，提交与查询仍保留占位实现，后续可逐步替换。
- 模板文件来源于项目根目录下 `backend_data` 目录内的 JSON 配置。
"""

from datetime import datetime, timedelta, timezone

from pathlib import Path as SysPath

from typing import Any, Dict, Iterable, List, Optional, Tuple

import os

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Path, Request

from fastapi.responses import JSONResponse

from sqlalchemy import delete

from backend.db.database_daily_report_25_26 import DailyBasicData, SessionLocal

import json





# Use DATA_DIRECTORY from env var if available (for Docker),

# otherwise, fall back to a path relative to the project root (for local dev).

DATA_PATH_STR = os.environ.get("DATA_DIRECTORY")

if DATA_PATH_STR:

    # Path inside container, e.g., /app/data

    DATA_ROOT = SysPath(DATA_PATH_STR)

else:

    # Path for local development

    PROJECT_ROOT = SysPath(__file__).resolve().parents[3]

    DATA_ROOT = PROJECT_ROOT / "backend_data"

EAST_8_TZ = timezone(timedelta(hours=8))

# The only data file we need to read, as requested by the user.

BASIC_DATA_FILE = DATA_ROOT / "数据结构_基本指标表.json"
UNIT_KEYS = ("unit_id", "单位标识", "单位中文名", "单位名", "unit_name")
SHEET_NAME_KEYS = ("表名", "表中文名", "表类别", "sheet_name")
COLUMN_KEYS = ("列名", "columns", "表头")
ROW_KEYS = ("数据", "rows", "records", "lines")
ITEM_DICT_KEYS = ("item_dict", "项目字典")
COMPANY_DICT_KEYS = ("company_dict", "单位字典")


def _iter_data_files() -> Iterable[SysPath]:
    """返回唯一的数据文件路径。"""
    if BASIC_DATA_FILE.exists():
        yield BASIC_DATA_FILE


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


def _locate_sheet_payload(sheet_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[SysPath]]:
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

    for data_path in _iter_data_files():
        raw = _read_json(data_path)

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

def _extract_mapping(payload: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
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
        operation_time = submit_time_raw.strip()
    elif submit_time_raw is None:
        operation_time = ""
    else:
        operation_time = str(submit_time_raw)

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

    records = normalized.get("records")
    if not isinstance(records, list):
        return []

    flattened: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        col_index = record.get("column_index")
        if not isinstance(col_index, int) or col_index < 2:
            continue
        if col_index >= len(columns):
            continue

        raw_value = record.get("value_raw")
        if raw_value is None:
            continue
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if value == "":
                continue
        else:
            value = str(raw_value)
            if value == "":
                continue

        row_label = record.get("row_label") or ""
        row_label_str = str(row_label).strip()
        unit = record.get("unit") or ""
        unit_str = str(unit).strip()
        date_value = columns[col_index] if col_index < len(columns) else ""
        date_value = date_value.strip() if isinstance(date_value, str) else str(date_value)

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
                "note": "",
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


def _decorate_columns(columns: Iterable[Any]) -> Iterable[str]:
    base = list(columns) if isinstance(columns, list) else list(columns)
    head = base[:2]
    while len(head) < 2:
        head.append("")

    tz = timezone(timedelta(hours=8))
    yesterday = (datetime.now(tz) - timedelta(days=1)).date()
    current = yesterday.isoformat()
    try:
        last_year = yesterday.replace(year=yesterday.year - 1)
    except ValueError:
        # 处理闰年的 2 月 29 日，向前回退到 2 月 28 日
        last_year = yesterday.replace(year=yesterday.year - 1, month=2, day=28)
    previous = last_year.isoformat()

    return head + [current, previous]


def _collect_catalog() -> Dict[str, Dict[str, str]]:
    catalog_path = BASIC_DATA_FILE
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
):
    payload, data_path = _locate_sheet_payload(sheet_key)
    if payload is None:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "message": f"sheet_key={sheet_key} 未在 {', '.join(DATA_FILE_CANDIDATES)} 中找到",
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

    columns = _decorate_columns(columns_raw)
    rows = [list(row) for row in rows_raw if isinstance(row, list)]
    item_dict = _extract_mapping(payload, ITEM_DICT_KEYS)
    company_dict = _extract_mapping(payload, COMPANY_DICT_KEYS)

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "sheet_key": sheet_key,
            "sheet_name": names["sheet_name"] or sheet_key,
            "unit_id": names["unit_id"],
            "unit_name": names["unit_name"],
            "columns": columns,
            "rows": rows,
            "item_dict": item_dict,
            "company_dict": company_dict,
        },
    )


@router.post("/data_entry/sheets/{sheet_key}/submit", summary="提交数据填报（调试）")
async def submit_debug(
    request: Request,
    sheet_key: str = Path(..., description="目标 sheet_key"),
):
    payload = await request.json()
    normalized = _normalize_submission(payload)
    flattened = _flatten_records(payload, normalized)
    try:
        inserted_rows = _persist_daily_basic(payload, normalized, flattened)
        db_error = ""
    except Exception as exc:
        inserted_rows = 0
        db_error = str(exc)

    if db_error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "写入数据库失败", "error": db_error},
        )

        fh.write("\n\n---\n\n")

    if db_error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": "写入数据库失败", "error": db_error},
        )

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": f"payload received for {sheet_key}",
            "records": len(normalized.get("records", [])),
            "flattened_records": len(flattened),
            "inserted": inserted_rows,
        },
    )





@router.post("/data_entry/sheets/{sheet_key}/query", summary="查询数据填报（占位）")
def query_placeholder(
    sheet_key: str = Path(..., description="目标 sheet_key"),
):
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "query endpoint placeholder",
            "sheet_key": sheet_key,
        },
    )


@router.get("/data_entry/sheets", summary="获取数据填报模板清单")
def list_sheets():
    catalog = _collect_catalog()
    if not catalog:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "message": "未在 backend_data 目录中找到任何模板文件",
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
