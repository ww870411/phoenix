"""
daily_report_25_26 项目 v1 路由

说明：
- 所有接口挂载在 `/api/v1/daily_report_25_26` 前缀下。
- 当前实现模板读取功能，提交与查询仍保留占位实现，后续可逐步替换。
- 模板文件来源于容器内数据目录（默认 `/app/data`）中的 JSON 配置。
"""

from datetime import datetime, timedelta, timezone

from pathlib import Path as SysPath

from typing import Any, Dict, Iterable, List, Optional, Tuple


from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Path, Request

from fastapi.responses import JSONResponse

from sqlalchemy import delete

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import CoalInventoryData, DailyBasicData, SessionLocal

import json





# Use统一的数据目录常量，默认指向容器内 /app/data
DATA_ROOT = SysPath(DATA_DIRECTORY)
COAL_INVENTORY_DEBUG_FILE = DATA_ROOT / "test.md"
BASIC_TEMPLATE_PATH = DATA_ROOT / "数据结构_基本指标表.json"
COAL_STORAGE_NAME_MAP = {
    "在途煤炭": ("coal_in_transit", "在途煤炭"),
    "港口存煤": ("coal_at_port", "港口存煤"),
    "厂内存煤": ("coal_at_plant", "厂内存煤"),
}
DATA_FILE_CANDIDATES = [str(BASIC_TEMPLATE_PATH)]

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
COMPANY_DICT_KEYS = ("company_dict", "单位字典")


def _iter_data_files() -> Iterable[SysPath]:
    """返回所有存在的候选数据文件路径。"""
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
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if value == "":
                value = "0"
        elif raw_value is None:
            value = "0"
        else:
            value = str(raw_value).strip()
            if value == "":
                value = "0"

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
        unit = row[2] if len(row) > 2 else ""
        
        company_id = rev_company_map.get(company_cn)
        item_id = rev_item_map.get(item_cn)

        if not company_id or not item_id:
            continue # 如果单位或煤种无法映射，则跳过此行

        # 遍历该行中的每个数据列
        for col_info in data_columns:
            col_idx = col_info["index"]
            storage_type_cn = col_info["name_cn"]
            
            raw_value = row[col_idx]
            # 如果值为空或无效，则跳过
            if raw_value is None or str(raw_value).strip() == "":
                continue

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
                "note": "", # 备注字段暂时为空
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

    rows = [list(row) for row in rows_raw if isinstance(row, list)]
    item_dict = _extract_mapping(payload, ITEM_DICT_KEYS)
    company_dict = _extract_mapping(payload, COMPANY_DICT_KEYS)
    
    response_content = {
        "ok": True,
        "sheet_key": sheet_key,
        "sheet_name": names["sheet_name"] or sheet_key,
        "unit_id": names["unit_id"],
        "unit_name": names["unit_name"],
        "rows": rows,
        "item_dict": item_dict,
        "company_dict": company_dict,
    }

    # 根据 sheet_key 判断模板类型并选择不同的列处理方式
    if sheet_key == "Coal_inventory_Sheet":
        response_content["template_type"] = "crosstab"
        response_content["columns"] = list(columns_raw)  # 直接使用原始列
        
        # 为交叉表单独生成业务日期
        tz = timezone(timedelta(hours=8))
        yesterday = (datetime.now(tz) - timedelta(days=1)).date()
        response_content["biz_date"] = yesterday.isoformat()
    else:
        response_content["template_type"] = "standard"
        response_content["columns"] = _decorate_columns(columns_raw)  # 对标准报表加注日期

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
    if sheet_key == "Coal_inventory_Sheet":
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
                "message": f"未在 {DATA_ROOT} 目录中找到任何模板文件",
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

        unit_value = ""
        if unit_idx is not None and unit_idx < len(row):
            unit_value = str(row[unit_idx] or "").strip()

        note_value = ""
        if note_idx is not None and note_idx < len(row):
            note_value = str(row[note_idx] or "").strip()

        company_code = company_lookup.get(company_cn, company_cn)
        coal_type_code = coal_lookup.get(coal_type_cn, coal_type_cn)

        for col_idx, storage_code, storage_cn in storage_columns:
            if col_idx >= len(row):
                value_str = "0"
            else:
                raw_value = row[col_idx]
                value_raw = str(raw_value).strip() if raw_value is not None else ""
                value_str = value_raw if value_raw != "" else "0"

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
