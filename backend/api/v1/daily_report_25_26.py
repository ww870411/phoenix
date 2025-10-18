"""
daily_report_25_26 项目 v1 路由

说明：
- 所有接口挂载在 `/api/v1/daily_report_25_26` 前缀下。
- 当前实现模板读取功能，提交与查询仍保留占位实现，后续可逐步替换。
- 模板文件来源于项目根目录下 `backend_data` 目录内的 JSON 配置。
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from pathlib import Path as SysPath
from typing import Any, Dict, Iterable, Optional, Tuple
import json


PROJECT_ROOT = SysPath(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "backend_data"
CATALOG_FILE = PROJECT_ROOT / "configs" / "数据结构_基本指标表.json"
DATA_FILE_CANDIDATES = (
    "数据结构_基本指标表.json",
    "数据结构_常量指标表.json",
)
UNIT_KEYS = ("单位名", "单位", "单位名称", "unit_name")
SHEET_NAME_KEYS = ("表名", "名称", "表名称", "sheet_name")
COLUMN_KEYS = ("列名", "columns", "表头")
ROW_KEYS = ("数据", "rows", "records", "lines")


def _iter_data_files() -> Iterable[SysPath]:
    """按优先级返回存在的模板文件路径。"""
    if CATALOG_FILE.exists():
        yield CATALOG_FILE
    for filename in DATA_FILE_CANDIDATES:
        path = DATA_DIR / filename
        if path.exists():
            yield path


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
    unit_name: Optional[str] = None
    sheet_name: Optional[str] = None
    for key in UNIT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            unit_name = value.strip()
            break
    for key in SHEET_NAME_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            sheet_name = value.strip()
            break
    return {
        "unit_name": unit_name or "",
        "sheet_name": sheet_name or "",
    }


def _locate_sheet_payload(sheet_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[SysPath]]:
    """在候选模板文件中按 sheet_key 查找配置。"""
    for data_path in _iter_data_files():
        raw = _read_json(data_path)
        if isinstance(raw, dict) and sheet_key in raw:
            payload = raw[sheet_key]
            if isinstance(payload, dict):
                return payload, data_path
        if isinstance(raw, list):
            for payload in raw:
                if not isinstance(payload, dict):
                    continue
                candidate = payload.get("sheet_key")
                names = _extract_names(payload)
                if candidate == sheet_key or names["sheet_name"] == sheet_key:
                    return payload, data_path
    return None, None


def _extract_list(payload: Dict[str, Any], keys: Iterable[str]) -> Optional[Iterable[Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return None


def _decorate_columns(columns: Iterable[Any]) -> Iterable[str]:
    base = list(columns) if isinstance(columns, list) else list(columns)
    head = base[:2]
    while len(head) < 2:
        head.append("")

    tz = timezone(timedelta(hours=8))
    today = datetime.now(tz).date()
    current = today.isoformat()
    try:
        last_year = today.replace(year=today.year - 1)
    except ValueError:
        # 处理闰年的 2 月 29 日，向前回退到 2 月 28 日
        last_year = today.replace(year=today.year - 1, month=2, day=28)
    previous = last_year.isoformat()

    return head + [current, previous]


def _collect_catalog() -> Dict[str, Dict[str, str]]:
    catalog_path = CATALOG_FILE
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
            "单位名": unit_name,
            "表名": sheet_name,
            "unit_name": unit_name,
            "sheet_name": sheet_name,
        }
    return catalog


router = APIRouter()


@router.get("/ping", summary="daily_report_25_26 心跳", tags=["daily_report_25_26"])
def ping_daily_report():
    return {"ok": True, "project": "daily_report_25_26", "message": "pong"}


@router.get("/sheets/{sheet_key}/template", summary="获取填报模板")
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

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "sheet_key": sheet_key,
            "sheet_name": names["sheet_name"] or sheet_key,
            "unit_name": names["unit_name"],
            "columns": columns,
            "rows": rows,
        },
    )


@router.post("/sheets/{sheet_key}/submit", summary="提交数据（占位）")
def submit_placeholder(
    sheet_key: str = Path(..., description="目标 sheet_key"),
):
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "submit endpoint placeholder",
            "sheet_key": sheet_key,
        },
    )


@router.post("/sheets/{sheet_key}/query", summary="查询数据（占位）")
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


@router.get("/sheets", summary="获取模板清单")
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
