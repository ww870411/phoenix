# -*- coding: utf-8 -*-
"""
monthly_data_show 工作台接口。
"""

from __future__ import annotations

import csv
import json
import tempfile
import calendar
import math
import re
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import bindparam, text
from starlette.background import BackgroundTask

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.monthly_data_show.services.extractor import (
    ALLOWED_FIELDS,
    BLOCKED_COMPANIES,
    DEFAULT_SOURCE_COLUMNS,
    extract_rows,
    filter_fields,
    get_default_constant_rules,
    get_extraction_rule_options,
    get_company_options,
    normalize_constant_rules,
    parse_report_period_from_filename,
)
from backend.projects.monthly_data_show.services.indicator_config import (
    build_indicator_config_payload,
    evaluate_formula,
    load_indicator_runtime_config,
    order_items_by_config,
)
from backend.services import data_analysis_ai_report

PROJECT_KEY = "monthly_data_show"
CHAT_SESSION_TTL_SECONDS = 30 * 60
CHAT_SESSION_MAX_TURNS = 20
CHAT_WEB_SEARCH_LIMIT = 5
_CHAT_SESSION_LOCK = threading.Lock()
_CHAT_SESSION_STORE: Dict[str, Dict[str, Any]] = {}
ALLOWED_EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm"}

router = APIRouter(tags=["monthly_data_show"])
public_router = APIRouter(tags=["monthly_data_show"])


class InspectResponse(BaseModel):
    ok: bool
    project_key: str
    companies: List[str]
    blocked_companies: List[str]
    fields: List[str]
    default_selected_fields: List[str]
    source_columns: List[str]
    default_selected_source_columns: List[str]
    inferred_report_year: int
    inferred_report_month: int
    inferred_report_month_date: str
    constants_enabled_default: bool
    constant_rules: List[dict]
    extraction_rules: List[dict]

class ImportCsvResponse(BaseModel):
    ok: bool
    project_key: str
    imported_rows: int
    null_value_rows: int
    inserted_rows: int = 0
    updated_rows: int = 0


NULL_VALUE_TOKENS = {"", "none", "null", "nan", "-", "--", "无", "空", "#div/0!"}
AVERAGE_TEMPERATURE_ITEM = "平均气温"
AVERAGE_TEMPERATURE_UNIT = "℃"
AVERAGE_TEMPERATURE_COMPANY = "common"
INDICATOR_RUNTIME_CFG = load_indicator_runtime_config()
CALCULATED_ITEM_SET = set(INDICATOR_RUNTIME_CFG.get("calculated_item_set") or set())
CALCULATED_ITEM_UNITS = dict(INDICATOR_RUNTIME_CFG.get("calculated_item_units") or {})
CALCULATED_DEPENDENCY_MAP = {
    str(k): set(v or set()) for k, v in (INDICATOR_RUNTIME_CFG.get("calculated_dependency_map") or {}).items()
}
CALCULATED_ITEM_FORMULAS = dict(INDICATOR_RUNTIME_CFG.get("calculated_item_formulas") or {})
LATEST_VALUE_ITEMS = {
    "期末供暖收费面积",
    "期末库存煤量",
    "库存煤量",
    "发电设备容量",
    "锅炉设备容量",
    "供热设备容量",
}


def _refresh_indicator_runtime() -> None:
    global INDICATOR_RUNTIME_CFG
    global CALCULATED_ITEM_SET
    global CALCULATED_ITEM_UNITS
    global CALCULATED_DEPENDENCY_MAP
    global CALCULATED_ITEM_FORMULAS
    INDICATOR_RUNTIME_CFG = load_indicator_runtime_config()
    CALCULATED_ITEM_SET = set(INDICATOR_RUNTIME_CFG.get("calculated_item_set") or set())
    CALCULATED_ITEM_UNITS = dict(INDICATOR_RUNTIME_CFG.get("calculated_item_units") or {})
    CALCULATED_DEPENDENCY_MAP = {
        str(k): set(v or set()) for k, v in (INDICATOR_RUNTIME_CFG.get("calculated_dependency_map") or {}).items()
    }
    CALCULATED_ITEM_FORMULAS = dict(INDICATOR_RUNTIME_CFG.get("calculated_item_formulas") or {})


def _build_value_aggregate_sql(*, apply_latest_for_state_items: bool) -> str:
    sum_expr = "CASE WHEN COUNT(value) = 0 THEN NULL ELSE SUM(value) END"
    if not apply_latest_for_state_items:
        return sum_expr
    if not LATEST_VALUE_ITEMS:
        return sum_expr
    items_literal = ", ".join("'" + x.replace("'", "''") + "'" for x in sorted(LATEST_VALUE_ITEMS))
    latest_expr = (
        "(ARRAY_AGG(value ORDER BY COALESCE(report_month, date) DESC NULLS LAST, "
        "date DESC NULLS LAST, operation_time DESC NULLS LAST))[1]"
    )
    return f"CASE WHEN item IN ({items_literal}) THEN {latest_expr} ELSE {sum_expr} END"
METRIC_ALIAS_MAP = {
    "耗标煤总量": ["标煤耗量", "煤折标煤量"],
    "供热耗标煤量": ["供热标准煤耗量"],
    "发电耗标煤量": ["发电标准煤耗量"],
    "生产耗原煤量": ["原煤耗量"],
    "耗水量": ["电厂耗水量"],
}


class QueryRequest(BaseModel):
    report_month_from: Optional[str] = None
    report_month_to: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    companies: List[str] = []
    items: List[str] = []
    periods: List[str] = []
    types: List[str] = []
    order_mode: str = "company_first"
    order_fields: List[str] = []
    aggregate_companies: bool = False
    aggregate_months: bool = False
    limit: int = 200
    offset: int = 0


class QuerySummary(BaseModel):
    total_rows: int
    value_non_null_rows: int
    value_null_rows: int
    value_sum: float


class QueryResponse(BaseModel):
    ok: bool
    project_key: str
    total: int
    limit: int
    offset: int
    rows: List[dict]
    summary: QuerySummary


class QueryOptionsResponse(BaseModel):
    ok: bool
    project_key: str
    companies: List[str]
    items: List[str]
    periods: List[str]
    types: List[str]
    indicator_config: dict = {}


class QueryComparisonRow(BaseModel):
    company: str
    item: str
    period: str
    type: str
    unit: str
    current_value: Optional[float] = None
    yoy_value: Optional[float] = None
    yoy_rate: Optional[float] = None
    mom_value: Optional[float] = None
    mom_rate: Optional[float] = None
    plan_value: Optional[float] = None
    plan_rate: Optional[float] = None


class TemperatureDailyComparisonRow(BaseModel):
    current_date: str
    current_temp: Optional[float] = None
    yoy_date: str
    yoy_temp: Optional[float] = None
    yoy_diff: Optional[float] = None
    yoy_rate: Optional[float] = None


class TemperatureComparisonSummary(BaseModel):
    current_avg_temp: Optional[float] = None
    yoy_avg_temp: Optional[float] = None
    yoy_avg_diff: Optional[float] = None
    yoy_avg_rate: Optional[float] = None


class TemperatureComparisonPayload(BaseModel):
    rows: List[TemperatureDailyComparisonRow] = []
    summary: Optional[TemperatureComparisonSummary] = None


class QueryComparisonResponse(BaseModel):
    ok: bool
    project_key: str
    current_window_label: str
    yoy_window_label: str
    mom_window_label: str
    plan_window_label: str
    rows: List[QueryComparisonRow]
    temperature_comparison: Optional[TemperatureComparisonPayload] = None


class MonthlyAiReportStartPayload(BaseModel):
    rows: List[dict] = []
    comparison_rows: List[dict] = []
    current_window_label: str = ""
    yoy_window_label: str = ""
    mom_window_label: str = ""
    plan_window_label: str = ""
    ai_mode_id: str = "monthly_analysis_v1"
    ai_user_prompt: str = ""


class MonthlyAiReportStartResponse(BaseModel):
    ok: bool
    project_key: str
    ai_report_job_id: str
    ai_mode_id: str


class MonthlyAiChatToolCall(BaseModel):
    tool: str
    summary: str
    total_rows: int = 0
    details: Dict[str, Any] = {}


class MonthlyAiChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: List[dict] = []
    context: Optional[QueryRequest] = None
    enable_web_search: bool = True
    limit: int = 200
    top_n: int = 12


class MonthlyAiChatResponse(BaseModel):
    ok: bool
    project_key: str
    session_id: str
    answer: str
    tool_calls: List[MonthlyAiChatToolCall] = []
    preview_rows: List[dict] = []
    web_sources: List[dict] = []
    applied_query: Dict[str, Any] = {}


def _ensure_allowed_excel_file(filename: str) -> None:
    suffix = Path(str(filename or "")).suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_EXCEL_SUFFIXES))
        raise HTTPException(status_code=422, detail=f"仅支持以下文件格式：{allowed}")


def _cleanup_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass

def _parse_iso_date(value: str, field_name: str) -> date:
    text_value = str(value or "").strip()
    if not text_value:
        raise HTTPException(status_code=422, detail=f"CSV 字段 {field_name} 不能为空")
    try:
        return date.fromisoformat(text_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"CSV 字段 {field_name} 格式错误，需为 YYYY-MM-DD") from exc


def _parse_optional_date(value: Optional[str], field_name: str) -> Optional[date]:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return date.fromisoformat(text_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} 格式错误，需为 YYYY-MM-DD") from exc


def _normalize_text_list(values: List[str]) -> List[str]:
    seen = set()
    normalized: List[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _to_optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _normalize_calc_value(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(round(value, 8))


def _collect_required_base_items(calc_items: List[str]) -> List[str]:
    required: Set[str] = set()
    visited: Set[str] = set()

    def walk(item_name: str):
        if item_name in visited:
            return
        visited.add(item_name)
        for dep in CALCULATED_DEPENDENCY_MAP.get(item_name, set()):
            if dep == "天数":
                continue
            if dep in CALCULATED_ITEM_SET:
                walk(dep)
            else:
                required.add(dep)
                for alias in METRIC_ALIAS_MAP.get(dep, []):
                    required.add(alias)

    for item in calc_items:
        walk(item)
    return sorted(required)


def _resolve_day_count(request: QueryRequest) -> int:
    start_date, end_date = _pick_temperature_date_range(request)
    if start_date is None or end_date is None:
        return 30
    if start_date > end_date:
        return 0
    return (end_date - start_date).days + 1


def _resolve_group_day_count(
    request: QueryRequest,
    row_date: Optional[str],
    row_report_month: Optional[str],
    aggregate_months: bool,
) -> int:
    if aggregate_months:
        return _resolve_day_count(request)
    for raw in (row_report_month, row_date):
        if not raw:
            continue
        try:
            dt = date.fromisoformat(raw)
            return calendar.monthrange(dt.year, dt.month)[1]
        except Exception:
            continue
    return _resolve_day_count(request)


def _compute_calculated_indicator(
    indicator: str,
    metric_values: Dict[str, float],
    cache: Dict[str, float],
    day_count: int,
) -> float:
    if indicator in cache:
        return cache[indicator]

    def val(item_name: str) -> float:
        if item_name in CALCULATED_ITEM_SET:
            if item_name in cache:
                return _to_float(cache.get(item_name))
            if item_name in metric_values:
                return _to_float(metric_values.get(item_name))
            return _compute_calculated_indicator(item_name, metric_values, cache, day_count)
        direct = _to_float(metric_values.get(item_name))
        if direct != 0:
            return direct
        for alias in METRIC_ALIAS_MAP.get(item_name, []):
            alias_value = _to_float(metric_values.get(alias))
            if alias_value != 0:
                return alias_value
        return direct
    formula = str(CALCULATED_ITEM_FORMULAS.get(indicator) or "").strip()
    if not formula:
        computed = 0.0
    else:
        context: Dict[str, float] = {"天数": float(max(0, int(day_count or 0)))}
        dependencies = CALCULATED_DEPENDENCY_MAP.get(indicator, set())
        for dep in dependencies:
            context[str(dep)] = val(str(dep))
        computed = evaluate_formula(formula, context)

    cache[indicator] = _normalize_calc_value(computed)
    return cache[indicator]


def _compute_calculated_two_pass(
    metric_values: Dict[str, float],
    selected_calc_items: List[str],
    day_count: int,
) -> Dict[str, float]:
    if not selected_calc_items:
        return {}
    working_metrics: Dict[str, float] = dict(metric_values)
    result: Dict[str, float] = {}
    # 固定执行两轮，确保“计算指标依赖计算指标”场景可稳定收敛。
    for _ in range(2):
        pass_cache: Dict[str, float] = {}
        for indicator in selected_calc_items:
            result[indicator] = _compute_calculated_indicator(indicator, working_metrics, pass_cache, day_count)
        working_metrics.update(result)
    return result


def _build_calculated_rows(
    base_rows: List[dict],
    request: QueryRequest,
    selected_calc_items: List[str],
    aggregate_months: bool,
) -> List[dict]:
    if not base_rows or not selected_calc_items:
        return []

    grouped_metrics: Dict[Tuple[str, str, str, Optional[str], Optional[str]], Dict[str, float]] = {}
    grouped_meta: Dict[Tuple[str, str, str, Optional[str], Optional[str]], dict] = {}
    for row in base_rows:
        key = (
            _safe_str(row.get("company")),
            _safe_str(row.get("period")),
            _safe_str(row.get("type")),
            row.get("date"),
            row.get("report_month"),
        )
        metrics = grouped_metrics.setdefault(key, {})
        metric_name = _safe_str(row.get("item"))
        metric_value = row.get("value")
        if metric_name:
            metrics[metric_name] = _to_float(metrics.get(metric_name)) + _to_float(metric_value)
        grouped_meta.setdefault(
            key,
            {
                "company": row.get("company"),
                "period": row.get("period"),
                "type": row.get("type"),
                "date": row.get("date"),
                "report_month": row.get("report_month"),
                "operation_time": row.get("operation_time"),
            },
        )

    calculated_rows: List[dict] = []
    for key, metric_values in grouped_metrics.items():
        meta = grouped_meta.get(key, {})
        day_count = _resolve_group_day_count(
            request=request,
            row_date=meta.get("date"),
            row_report_month=meta.get("report_month"),
            aggregate_months=aggregate_months,
        )
        calc_values = _compute_calculated_two_pass(
            metric_values=metric_values,
            selected_calc_items=selected_calc_items,
            day_count=day_count,
        )
        for indicator in selected_calc_items:
            value = _to_float(calc_values.get(indicator))
            calculated_rows.append(
                {
                    "company": meta.get("company"),
                    "item": indicator,
                    "unit": CALCULATED_ITEM_UNITS.get(indicator, ""),
                    "value": value,
                    "date": meta.get("date"),
                    "period": meta.get("period"),
                    "type": meta.get("type"),
                    "report_month": meta.get("report_month"),
                    "operation_time": meta.get("operation_time"),
                }
            )
    return calculated_rows


def _parse_import_csv_rows(content: bytes) -> Tuple[List[dict], int]:
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV 编码需为 UTF-8（可带 BOM）") from exc
    reader = csv.DictReader(text_content.splitlines())
    required_fields = {"company", "item", "unit", "value", "date", "period", "type", "report_month"}
    headers = set(reader.fieldnames or [])
    missing = [field for field in required_fields if field not in headers]
    if missing:
        raise HTTPException(status_code=422, detail=f"CSV 缺少必要字段：{', '.join(missing)}")

    parsed_rows: List[dict] = []
    null_value_rows = 0
    for index, row in enumerate(reader, start=2):
        company = str(row.get("company") or "").strip()
        item = str(row.get("item") or "").strip()
        period = str(row.get("period") or "").strip()
        value_type = str(row.get("type") or "").strip()
        if not company or not item or not period or not value_type:
            raise HTTPException(status_code=422, detail=f"第 {index} 行 company/item/period/type 不能为空")
        value_raw = str(row.get("value") or "").strip()
        normalized_value = value_raw.lower()
        if normalized_value in NULL_VALUE_TOKENS:
            value = None
            null_value_rows += 1
        else:
            try:
                value = float(value_raw)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"第 {index} 行 value 不是有效数字") from exc
        parsed_rows.append(
            {
                "company": company,
                "item": item,
                "unit": str(row.get("unit") or "").strip(),
                "value": value,
                "date": _parse_iso_date(str(row.get("date") or ""), "date"),
                "period": period,
                "type": value_type,
                "report_month": _parse_iso_date(str(row.get("report_month") or ""), "report_month"),
            }
        )
    return parsed_rows, null_value_rows


def _build_query_sql_parts(request: QueryRequest):
    where_parts: List[str] = []
    params: dict = {}
    bind_params = []

    report_month_from = _parse_optional_date(request.report_month_from, "report_month_from")
    report_month_to = _parse_optional_date(request.report_month_to, "report_month_to")
    date_from = _parse_optional_date(request.date_from, "date_from")
    date_to = _parse_optional_date(request.date_to, "date_to")
    if report_month_from is not None:
        where_parts.append("report_month >= :report_month_from")
        params["report_month_from"] = report_month_from
    if report_month_to is not None:
        where_parts.append("report_month <= :report_month_to")
        params["report_month_to"] = report_month_to
    if date_from is not None:
        where_parts.append("date >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where_parts.append("date <= :date_to")
        params["date_to"] = date_to

    companies = _normalize_text_list(request.companies)
    items = _normalize_text_list(request.items)
    periods = _normalize_text_list(request.periods)
    types = _normalize_text_list(request.types)

    if companies:
        where_parts.append("company IN :companies")
        params["companies"] = companies
        bind_params.append(bindparam("companies", expanding=True))
    if items:
        where_parts.append("item IN :items")
        params["items"] = items
        bind_params.append(bindparam("items", expanding=True))
    if periods:
        where_parts.append("period IN :periods")
        params["periods"] = periods
        bind_params.append(bindparam("periods", expanding=True))
    if types:
        where_parts.append("type IN :types")
        params["types"] = types
        bind_params.append(bindparam("types", expanding=True))

    where_clause = " AND ".join(where_parts)
    return where_clause, params, bind_params


def _resolve_order_fields(order_mode: str, order_fields: List[str], aggregate_companies: bool) -> List[str]:
    allowed = {"time", "company", "item", "period", "type"}
    requested = []
    for value in order_fields or []:
        key = str(value or "").strip().lower()
        if key in allowed and key not in requested:
            requested.append(key)
    if not requested:
        requested = ["time", "item", "company"] if order_mode == "item_first" else ["time", "company", "item"]
    final_fields: List[str] = []
    for key in requested:
        if aggregate_companies and key == "company":
            continue
        if key not in final_fields:
            final_fields.append(key)
    for key in ("time", "company", "item", "period", "type"):
        if aggregate_companies and key == "company":
            continue
        if key not in final_fields:
            final_fields.append(key)
    return final_fields


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _iter_month_starts(start: date, end: date) -> List[date]:
    month_list: List[date] = []
    cursor = _month_start(start)
    end_month = _month_start(end)
    while cursor <= end_month:
        month_list.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return month_list


def _pick_temperature_date_range(request: QueryRequest) -> Tuple[Optional[date], Optional[date]]:
    date_from = _parse_optional_date(request.date_from, "date_from")
    date_to = _parse_optional_date(request.date_to, "date_to")
    if date_from and date_to:
        return date_from, date_to
    report_from = _parse_optional_date(request.report_month_from, "report_month_from")
    report_to = _parse_optional_date(request.report_month_to, "report_month_to")
    if report_from and report_to:
        return report_from, report_to
    if date_from and not date_to:
        month_start = _month_start(date_from)
        month_end = date(date_from.year, date_from.month, calendar.monthrange(date_from.year, date_from.month)[1])
        return month_start, month_end
    if date_to and not date_from:
        month_start = _month_start(date_to)
        month_end = date(date_to.year, date_to.month, calendar.monthrange(date_to.year, date_to.month)[1])
        return month_start, month_end
    if report_from and not report_to:
        month_start = _month_start(report_from)
        month_end = date(report_from.year, report_from.month, calendar.monthrange(report_from.year, report_from.month)[1])
        return month_start, month_end
    if report_to and not report_from:
        month_start = _month_start(report_to)
        month_end = date(report_to.year, report_to.month, calendar.monthrange(report_to.year, report_to.month)[1])
        return month_start, month_end
    return None, None


def _safe_str(value: object) -> str:
    return str(value or "").strip()


def _build_rank_map(values: List[str]) -> Dict[str, int]:
    rank_map: Dict[str, int] = {}
    for idx, value in enumerate(values or []):
        key = _safe_str(value)
        if key and key not in rank_map:
            rank_map[key] = idx
    return rank_map


def _merge_and_sort_rows(
    rows: List[dict],
    order_fields: List[str],
    aggregate_months: bool,
    rank_maps: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[dict]:
    rank_maps = rank_maps or {}

    def _date_desc_key(v: Optional[str]):
        if not v:
            return (1, 0)
        try:
            return (0, -date.fromisoformat(v).toordinal())
        except Exception:
            return (0, 0)

    def _date_asc_key(v: Optional[str]):
        if not v:
            return (1, 0)
        try:
            return (0, date.fromisoformat(v).toordinal())
        except Exception:
            return (0, 0)

    def _time_key(row: dict):
        # 月报主场景下以 report_month 为主，缺失时回退 date。
        raw = row.get("report_month") or row.get("date")
        return _date_asc_key(raw)

    def _rank_key(field: str, value: object):
        txt = _safe_str(value)
        rank_map = rank_maps.get(field) or {}
        if txt in rank_map:
            return (0, rank_map[txt], txt)
        return (1, 10**9, txt)

    def _row_key(row: dict):
        key_parts: List[object] = []
        is_avg_temp = 0 if _safe_str(row.get("item")) == AVERAGE_TEMPERATURE_ITEM else 1
        key_parts.append(is_avg_temp)
        for field in order_fields:
            if field == "time":
                if aggregate_months:
                    # 月份已聚合时，时间维度无实际排序意义，放固定占位保持稳定排序。
                    key_parts.append((1, 0))
                else:
                    key_parts.append(_time_key(row))
                continue
            key_parts.append(_rank_key(field, row.get(field)))
        # 若用户未显式选择 time，则保持历史行为：时间降序优先（最新月份在前）。
        if (not aggregate_months) and ("time" not in order_fields):
            key_parts.append(_date_desc_key(row.get("report_month")))
            key_parts.append(_date_desc_key(row.get("date")))
        key_parts.append(_safe_str(row.get("unit")))
        return tuple(key_parts)

    return sorted(rows, key=_row_key)


def _sort_comparison_rows(
    rows: List[QueryComparisonRow],
    order_fields: List[str],
    rank_maps: Dict[str, Dict[str, int]],
) -> List[QueryComparisonRow]:
    def _rank_key(field: str, value: object):
        txt = _safe_str(value)
        rank_map = rank_maps.get(field) or {}
        if txt in rank_map:
            return (0, rank_map[txt], txt)
        return (1, 10**9, txt)

    def _row_key(row: QueryComparisonRow):
        key_parts: List[object] = []
        is_avg_temp = 0 if _safe_str(getattr(row, "item", "")) == AVERAGE_TEMPERATURE_ITEM else 1
        key_parts.append(is_avg_temp)
        for field in order_fields:
            if field == "time":
                continue
            key_parts.append(_rank_key(field, getattr(row, field, "")))
        key_parts.append(_safe_str(row.unit))
        return tuple(key_parts)

    return sorted(rows, key=_row_key)


def _format_window_label(start_date: date, end_date: date) -> str:
    if start_date == end_date:
        return start_date.isoformat()
    return f"{start_date.isoformat()} ~ {end_date.isoformat()}"


def _shift_year_safe(src: date, years: int) -> date:
    target_year = src.year + years
    last_day = calendar.monthrange(target_year, src.month)[1]
    return date(target_year, src.month, min(src.day, last_day))


def _resolve_mom_window(current_start: date, current_end: date) -> Tuple[date, date]:
    """
    环比窗口规则：
    - 若当前窗口为“连续自然月区间”（从月初到某月月末），则环比取“紧邻向前、等月数”的自然月区间；
      例如 2026-01-01~2026-02-28 -> 2025-11-01~2025-12-31；
    - 否则按原滚动窗口（向前平移同天数）计算。
    """
    current_end_month_last = calendar.monthrange(current_end.year, current_end.month)[1]
    is_natural_month_span = (
        current_start.day == 1
        and current_end.day == current_end_month_last
    )
    if is_natural_month_span:
        month_count = (current_end.year - current_start.year) * 12 + (current_end.month - current_start.month) + 1
        prev_month_end = current_start - timedelta(days=1)
        prev_start_year = prev_month_end.year
        prev_start_month = prev_month_end.month - (month_count - 1)
        while prev_start_month <= 0:
            prev_start_month += 12
            prev_start_year -= 1
        prev_month_start = date(prev_start_year, prev_start_month, 1)
        return prev_month_start, prev_month_end
    window_days = (current_end - current_start).days + 1
    mom_end = current_start - timedelta(days=1)
    mom_start = mom_end - timedelta(days=window_days - 1)
    return mom_start, mom_end


def _resolve_compare_window(request: QueryRequest) -> Tuple[Optional[date], Optional[date]]:
    date_from = _parse_optional_date(request.date_from, "date_from")
    date_to = _parse_optional_date(request.date_to, "date_to")
    if date_from and date_to:
        return date_from, date_to
    if date_from and not date_to:
        month_end = date(date_from.year, date_from.month, calendar.monthrange(date_from.year, date_from.month)[1])
        return date_from, month_end
    if date_to and not date_from:
        month_start = date(date_to.year, date_to.month, 1)
        return month_start, date_to

    report_from = _parse_optional_date(request.report_month_from, "report_month_from")
    report_to = _parse_optional_date(request.report_month_to, "report_month_to")
    if report_from and report_to:
        return report_from, report_to
    if report_from and not report_to:
        month_end = date(report_from.year, report_from.month, calendar.monthrange(report_from.year, report_from.month)[1])
        return report_from, month_end
    if report_to and not report_from:
        month_start = date(report_to.year, report_to.month, 1)
        return month_start, report_to
    return None, None


def _calc_rate(current_value: Optional[float], base_value: Optional[float]) -> Optional[float]:
    if current_value is None or base_value is None:
        return None
    if base_value == 0:
        return None
    return (current_value - base_value) / abs(base_value)


def _parse_window_label_dates(label: str) -> Tuple[Optional[str], Optional[str]]:
    text_label = str(label or "").strip()
    if not text_label:
        return None, None
    if "~" in text_label:
        parts = [x.strip() for x in text_label.split("~", 1)]
        if len(parts) == 2:
            return parts[0], parts[1]
    return text_label, text_label


def _build_monthly_ai_payload(payload: MonthlyAiReportStartPayload) -> Dict[str, Any]:
    compare_rows = payload.comparison_rows if isinstance(payload.comparison_rows, list) else []
    rows: List[Dict[str, Any]] = []
    ring_prev_totals: Dict[str, float] = {}
    plan_entries: List[Dict[str, Any]] = []
    for row in compare_rows:
        if not isinstance(row, dict):
            continue
        company = _safe_str(row.get("company"))
        item = _safe_str(row.get("item"))
        if not company or not item:
            continue
        unit = _safe_str(row.get("unit"))
        key = f"{company}|{item}"
        label = f"{company} / {item}"
        current_value = _to_optional_float(row.get("currentValue"))
        yoy_value = _to_optional_float(row.get("yoyValue"))
        mom_value = _to_optional_float(row.get("momValue"))
        plan_value = _to_optional_float(row.get("planValue"))
        yoy_rate = _to_optional_float(row.get("yoyRate"))
        mom_rate = _to_optional_float(row.get("momRate"))
        rows.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "value_type": "analysis",
                "current": current_value,
                "peer": yoy_value,
                "total_current": current_value,
                "total_peer": yoy_value,
                "delta": yoy_rate * 100 if yoy_rate is not None else None,
                "total_delta": yoy_rate * 100 if yoy_rate is not None else None,
                "ring_ratio": mom_rate * 100 if mom_rate is not None else None,
                "decimals": 2,
                "timeline": [],
            }
        )
        if mom_value is not None:
            ring_prev_totals[key] = mom_value
        if plan_value is not None:
            completion_rate = (current_value / plan_value * 100) if (current_value is not None and plan_value != 0) else None
            plan_entries.append(
                {
                    "key": key,
                    "label": label,
                    "unit": unit,
                    "actual_value": current_value,
                    "plan_value": plan_value,
                    "completion_rate": completion_rate,
                }
            )

    start_date, end_date = _parse_window_label_dates(payload.current_window_label)
    meta = {
        "unit_label": "月报查询",
        "analysis_mode": "month",
        "analysis_mode_label": "月报分析",
        "start_date": start_date,
        "end_date": end_date,
    }
    ai_payload: Dict[str, Any] = {
        "meta": meta,
        "rows": rows,
        "warnings": [],
        "ringCompare": {
            "range": {
                "start": _parse_window_label_dates(payload.mom_window_label)[0],
                "end": _parse_window_label_dates(payload.mom_window_label)[1],
            },
            "prevTotals": ring_prev_totals,
            "note": "" if ring_prev_totals else "当前窗口缺少可用环比数据",
        },
        "plan_comparison": {
            "period_start": start_date,
            "period_end": end_date,
            "month_label": str(payload.plan_window_label or "")[:7],
            "entries": plan_entries,
        },
        "resolved_metrics": [row.get("key") for row in rows if row.get("key")],
        "ai_mode_id": str(payload.ai_mode_id or "monthly_analysis_v1"),
        "ai_user_prompt": str(payload.ai_user_prompt or "").strip(),
    }
    return ai_payload


def _chat_now_ts() -> float:
    return datetime.utcnow().timestamp()


def _chat_cleanup_sessions(now_ts: Optional[float] = None) -> None:
    now_value = float(now_ts or _chat_now_ts())
    expired: List[str] = []
    for sid, payload in list(_CHAT_SESSION_STORE.items()):
        updated_at = float(payload.get("updated_at") or 0)
        if now_value - updated_at > CHAT_SESSION_TTL_SECONDS:
            expired.append(sid)
    for sid in expired:
        _CHAT_SESSION_STORE.pop(sid, None)


def _chat_get_or_create_session(session_id: Optional[str]) -> str:
    candidate = str(session_id or "").strip()
    sid = candidate if candidate else f"mds-{uuid.uuid4().hex}"
    now_ts = _chat_now_ts()
    with _CHAT_SESSION_LOCK:
        _chat_cleanup_sessions(now_ts)
        payload = _CHAT_SESSION_STORE.get(sid)
        if not payload:
            _CHAT_SESSION_STORE[sid] = {"history": [], "updated_at": now_ts}
        else:
            payload["updated_at"] = now_ts
    return sid


def _chat_get_session_history(session_id: str, history: List[dict], max_turns: int = CHAT_SESSION_MAX_TURNS) -> List[dict]:
    safe_history = history if isinstance(history, list) else []
    with _CHAT_SESSION_LOCK:
        payload = _CHAT_SESSION_STORE.get(session_id) or {}
        session_history = payload.get("history") if isinstance(payload.get("history"), list) else []
    merged: List[dict] = []
    for row in session_history + safe_history:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip()
        content = str(row.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        merged.append({"role": role, "content": content})
    return merged[-max(1, int(max_turns or CHAT_SESSION_MAX_TURNS)) :]


def _chat_append_session_history(session_id: str, user_message: str, assistant_message: str) -> None:
    user_text = str(user_message or "").strip()
    assistant_text = str(assistant_message or "").strip()
    if not user_text and not assistant_text:
        return
    now_ts = _chat_now_ts()
    with _CHAT_SESSION_LOCK:
        payload = _CHAT_SESSION_STORE.get(session_id)
        if not payload:
            payload = {"history": [], "updated_at": now_ts}
            _CHAT_SESSION_STORE[session_id] = payload
        history = payload.get("history") if isinstance(payload.get("history"), list) else []
        if user_text:
            history.append({"role": "user", "content": user_text})
        if assistant_text:
            history.append({"role": "assistant", "content": assistant_text})
        payload["history"] = history[-CHAT_SESSION_MAX_TURNS:]
        payload["updated_at"] = now_ts


def _chat_use_web_search_tool(message: str) -> bool:
    text = str(message or "")
    keywords = ["联网", "网络", "搜索", "新闻", "政策", "标准", "最新", "外部"]
    return any(word in text for word in keywords)


def _chat_parse_top_n(message: str, default_top_n: int = 12, max_top_n: int = 30) -> int:
    default_value = max(1, min(max_top_n, int(default_top_n or 12)))
    text = str(message or "")
    matched = re.search(r"(?:top|TOP|前)\s*(\d{1,2})", text)
    if not matched:
        return default_value
    return max(1, min(max_top_n, int(matched.group(1))))


def _chat_summarize_rows(rows: List[dict], top_n: int = 8) -> Dict[str, Any]:
    safe_rows = [row for row in rows if isinstance(row, dict)]
    if not safe_rows:
        return {
            "row_count": 0,
            "numeric_metrics": {},
            "group_summary": [],
            "top_rows": [],
            "summary": "未命中可分析的数据行。",
        }

    metric_map: Dict[str, Dict[str, Any]] = {}
    for row in safe_rows:
        for key, value in row.items():
            numeric = _to_optional_float(value)
            if numeric is None:
                continue
            bucket = metric_map.setdefault(key, {"count": 0, "sum": 0.0, "min": numeric, "max": numeric})
            bucket["count"] += 1
            bucket["sum"] += numeric
            bucket["min"] = min(float(bucket["min"]), numeric)
            bucket["max"] = max(float(bucket["max"]), numeric)

    numeric_metrics: Dict[str, Dict[str, float]] = {}
    for key, agg in metric_map.items():
        count = int(agg.get("count") or 0)
        if count <= 0:
            continue
        total = float(agg.get("sum") or 0.0)
        numeric_metrics[key] = {
            "count": count,
            "avg": total / count,
            "min": float(agg.get("min") or 0.0),
            "max": float(agg.get("max") or 0.0),
        }

    value_key = "value" if "value" in numeric_metrics else None
    value_key = value_key or ("yoy_ratio" if "yoy_ratio" in numeric_metrics else None)
    value_key = value_key or ("mom_ratio" if "mom_ratio" in numeric_metrics else None)

    group_summary: List[Dict[str, Any]] = []
    if value_key and any("company" in row for row in safe_rows):
        company_map: Dict[str, Dict[str, float]] = {}
        for row in safe_rows:
            company = str(row.get("company") or "未标注公司")
            numeric = _to_optional_float(row.get(value_key))
            if numeric is None:
                continue
            slot = company_map.setdefault(company, {"sum": 0.0, "count": 0.0})
            slot["sum"] += numeric
            slot["count"] += 1.0
        for company, agg in company_map.items():
            count = float(agg.get("count") or 0.0)
            if count <= 0:
                continue
            group_summary.append(
                {
                    "company": company,
                    "metric": value_key,
                    "avg": float(agg.get("sum") or 0.0) / count,
                    "count": int(count),
                }
            )
        group_summary.sort(key=lambda row: abs(float(row.get("avg") or 0.0)), reverse=True)
        group_summary = group_summary[: max(1, min(10, top_n))]

    top_rows: List[dict] = []
    if value_key:
        sortable_rows = [row for row in safe_rows if _to_optional_float(row.get(value_key)) is not None]
        sortable_rows.sort(key=lambda row: abs(float(_to_optional_float(row.get(value_key)) or 0.0)), reverse=True)
        top_rows = sortable_rows[: max(1, min(10, top_n))]

    key_metrics = [key for key in ["value", "yoy_ratio", "mom_ratio", "plan_ratio"] if key in numeric_metrics]
    metrics_text = "，".join(key_metrics[:4]) if key_metrics else "无核心数值字段"
    summary = f"共 {len(safe_rows)} 行；识别到数值字段 {len(numeric_metrics)} 个（{metrics_text}）。"
    if top_rows and value_key:
        summary += f" 已提取 {len(top_rows)} 条 {value_key} 绝对值最高记录。"

    return {
        "row_count": len(safe_rows),
        "numeric_metrics": numeric_metrics,
        "group_summary": group_summary,
        "top_rows": top_rows,
        "summary": summary,
    }


def _chat_execute_web_search(message: str, limit: int = CHAT_WEB_SEARCH_LIMIT) -> List[dict]:
    query = str(message or "").strip()
    if not query:
        return []

    safe_limit = max(1, min(8, int(limit or CHAT_WEB_SEARCH_LIMIT)))
    params = urlencode(
        {
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "skip_disambig": 1,
        }
    )
    url = f"https://api.duckduckgo.com/?{params}"
    req = Request(url, headers={"User-Agent": "phoenix-monthly-data-show/1.0"})

    try:
        with urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []
    except Exception:
        return []

    sources: List[dict] = []
    abstract_text = str(payload.get("AbstractText") or "").strip()
    abstract_url = str(payload.get("AbstractURL") or "").strip()
    heading = str(payload.get("Heading") or "").strip() or "摘要"
    if abstract_text and abstract_url:
        sources.append({"title": heading, "url": abstract_url, "snippet": abstract_text})

    def walk_topics(rows: List[Any]) -> None:
        for row in rows:
            if not isinstance(row, dict):
                continue
            if isinstance(row.get("Topics"), list):
                walk_topics(row.get("Topics") or [])
                if len(sources) >= safe_limit:
                    return
            text_value = str(row.get("Text") or "").strip()
            url_value = str(row.get("FirstURL") or "").strip()
            if text_value and url_value:
                title = text_value.split(" - ")[0].strip() or "搜索结果"
                sources.append({"title": title, "url": url_value, "snippet": text_value})
                if len(sources) >= safe_limit:
                    return

    related_topics = payload.get("RelatedTopics") if isinstance(payload.get("RelatedTopics"), list) else []
    walk_topics(related_topics)

    dedup: List[dict] = []
    seen_urls: Set[str] = set()
    for row in sources:
        url_value = str(row.get("url") or "").strip()
        if not url_value or url_value in seen_urls:
            continue
        seen_urls.add(url_value)
        dedup.append(
            {
                "title": str(row.get("title") or "搜索结果").strip(),
                "url": url_value,
                "snippet": str(row.get("snippet") or "").strip(),
            }
        )
        if len(dedup) >= safe_limit:
            break
    return dedup

def _chat_to_month_start_iso(month_text: str) -> Optional[str]:
    matched = re.match(r"^\s*(20\d{2})[-/年](0?[1-9]|1[0-2])\s*$", str(month_text or ""))
    if not matched:
        return None
    year = int(matched.group(1))
    month = int(matched.group(2))
    return date(year, month, 1).isoformat()


def _chat_to_month_end_iso(month_text: str) -> Optional[str]:
    matched = re.match(r"^\s*(20\d{2})[-/年](0?[1-9]|1[0-2])\s*$", str(month_text or ""))
    if not matched:
        return None
    year = int(matched.group(1))
    month = int(matched.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day).isoformat()


def _chat_extract_month_tokens(message: str) -> List[str]:
    tokens: List[str] = []
    for year, month in re.findall(r"(20\d{2})\s*[-/年]\s*(0?[1-9]|1[0-2])", str(message or "")):
        token = f"{year}-{str(int(month)).zfill(2)}"
        if token not in tokens:
            tokens.append(token)
    return tokens


def _chat_pick_contains_candidates(message: str, candidates: List[str], max_count: int = 8) -> List[str]:
    text = str(message or "").strip()
    picked: List[str] = []
    for candidate in candidates or []:
        name = str(candidate or "").strip()
        if not name:
            continue
        if name in text and name not in picked:
            picked.append(name)
        if len(picked) >= max(1, max_count):
            break
    return picked


def _chat_build_query_request(payload: MonthlyAiChatRequest) -> QueryRequest:
    base = payload.context.model_copy(deep=True) if payload.context else QueryRequest()
    options_payload = get_monthly_data_show_query_options()

    base.companies = _normalize_text_list(base.companies)
    base.items = _normalize_text_list(base.items)
    base.periods = _normalize_text_list(base.periods) or ["month"]
    base.types = _normalize_text_list(base.types) or ["real"]
    base.limit = max(1, min(500, int(payload.limit or base.limit or 200)))
    base.offset = 0

    month_tokens = _chat_extract_month_tokens(payload.message)
    if month_tokens:
        start_iso = _chat_to_month_start_iso(month_tokens[0])
        end_iso = _chat_to_month_end_iso(month_tokens[1] if len(month_tokens) >= 2 else month_tokens[0])
        base.date_from = start_iso
        base.date_to = end_iso
        base.report_month_from = None
        base.report_month_to = None

    matched_companies = _chat_pick_contains_candidates(payload.message, options_payload.companies, max_count=6)
    if matched_companies:
        base.companies = matched_companies
    if not base.companies:
        base.companies = (options_payload.companies or [])[: min(3, len(options_payload.companies or []))]

    matched_items = _chat_pick_contains_candidates(payload.message, options_payload.items, max_count=10)
    if matched_items:
        base.items = matched_items
    if not base.items:
        base.items = (options_payload.items or [])[: min(8, len(options_payload.items or []))]

    return base


def _chat_build_history_text(history: List[dict], max_turns: int = 6) -> str:
    turns = history[-max(0, max_turns) :] if isinstance(history, list) else []
    lines: List[str] = []
    for row in turns:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role") or "").strip() or "user"
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _chat_use_comparison_tool(message: str) -> bool:
    text = str(message or "")
    keywords = ["同比", "环比", "计划比", "趋势", "波动", "变化率", "对比"]
    return any(word in text for word in keywords)


def _chat_build_answer_fallback(
    *,
    tool_name: str,
    total_rows: int,
    user_message: str,
    preview_rows: List[dict],
) -> str:
    if not preview_rows:
        return f"已按你的问题执行 {tool_name} 查询，但未命中数据。请尝试缩小或调整时间、口径、指标条件。"
    return (
        f"已按你的问题执行 {tool_name} 查询，共命中 {total_rows} 条。"
        f"当前返回前 {len(preview_rows)} 条预览，可继续追问“按口径汇总”或“只看 TopN 波动”。"
    )


def _chat_generate_answer_by_model(
    *,
    payload: MonthlyAiChatRequest,
    tool_name: str,
    tool_summary: str,
    total_rows: int,
    preview_rows: List[dict],
    history: List[dict],
    query_request: QueryRequest,
    extra_context: str = "",
) -> str:
    prompt = (
        "你是月报数据分析助手。请基于已执行的工具结果，用中文给出简洁、可执行的分析结论。\n"
        "要求：\n"
        "1) 先给结论，再给证据；\n"
        "2) 明确本次查询条件；\n"
        "3) 不编造数据，未命中时直接说明；\n"
        "4) 若使用联网信息，必须在结论后附“来源”清单。\n\n"
        f"用户问题：{str(payload.message or '').strip()}\n"
        f"历史对话：\n{_chat_build_history_text(history)}\n\n"
        f"已执行工具：{tool_name}\n"
        f"工具摘要：{tool_summary}\n"
        f"命中总条数：{total_rows}\n"
        f"查询条件(JSON)：{json.dumps(query_request.model_dump(mode='json'), ensure_ascii=False)}\n"
        f"结果预览(JSON)：{json.dumps(preview_rows, ensure_ascii=False)}\n"
        f"补充信息：{extra_context or '无'}\n"
    )
    return str(data_analysis_ai_report._call_model(prompt, retries=2) or "").strip()


def _fetch_compare_map(
    session,
    request: QueryRequest,
    start_date: date,
    end_date: date,
) -> dict:
    companies = _normalize_text_list(request.companies)
    items = _normalize_text_list(request.items)
    periods = _normalize_text_list(request.periods)
    types = _normalize_text_list(request.types)
    aggregate_companies = bool(request.aggregate_companies)
    include_avg_temp = AVERAGE_TEMPERATURE_ITEM in items
    selected_calc_items = [x for x in items if x in CALCULATED_ITEM_SET]
    selected_base_items = [x for x in items if x not in CALCULATED_ITEM_SET and x != AVERAGE_TEMPERATURE_ITEM]
    required_base_items = _collect_required_base_items(selected_calc_items)
    query_base_items = sorted(set(selected_base_items + required_base_items))

    result_map: dict = {}
    base_rows: List[dict] = []
    if companies and periods and types and query_base_items:
        where_parts = ["date BETWEEN :date_from AND :date_to"]
        params = {
            "date_from": start_date,
            "date_to": end_date,
            "companies": companies,
            "items": query_base_items,
            "periods": periods,
            "types": types,
        }
        where_parts.append("company IN :companies")
        where_parts.append("item IN :items")
        where_parts.append("period IN :periods")
        where_parts.append("type IN :types")
        where_sql = " AND ".join(where_parts)
        select_company_sql = "'聚合口径'::TEXT AS company" if aggregate_companies else "company"
        group_by_sql = "item, period, type, unit" if aggregate_companies else "company, item, period, type, unit"
        value_agg_sql = _build_value_aggregate_sql(apply_latest_for_state_items=True)
        stmt = text(
            f"""
            SELECT
                {select_company_sql},
                item,
                period,
                type,
                unit,
                {value_agg_sql} AS value
            FROM monthly_data_show
            WHERE {where_sql}
            GROUP BY {group_by_sql}
            """
        ).bindparams(
            bindparam("companies", expanding=True),
            bindparam("items", expanding=True),
            bindparam("periods", expanding=True),
            bindparam("types", expanding=True),
        )
        rows = session.execute(stmt, params).mappings().all()
        for row in rows:
            company = str(row.get("company") or "")
            item = str(row.get("item") or "")
            period = str(row.get("period") or "")
            type_value = str(row.get("type") or "")
            unit = str(row.get("unit") or "")
            key = f"{company}|{item}|{period}|{type_value}|{unit}"
            raw_value = row.get("value")
            value = _to_float(raw_value) if raw_value is not None else None
            base_row = {
                "company": company,
                "item": item,
                "period": period,
                "type": type_value,
                "unit": unit,
                "value": value,
            }
            base_rows.append(base_row)
            if item in selected_base_items:
                result_map[key] = dict(base_row)

    if selected_calc_items and base_rows:
        day_count = (end_date - start_date).days + 1
        if day_count <= 0:
            day_count = 0
        grouped_metrics: Dict[Tuple[str, str, str], Dict[str, float]] = {}
        for row in base_rows:
            group_key = (_safe_str(row.get("company")), _safe_str(row.get("period")), _safe_str(row.get("type")))
            metrics = grouped_metrics.setdefault(group_key, {})
            item = _safe_str(row.get("item"))
            metrics[item] = _to_float(metrics.get(item)) + _to_float(row.get("value"))
        for group_key, metrics in grouped_metrics.items():
            company, period, type_value = group_key
            calc_values = _compute_calculated_two_pass(
                metric_values=metrics,
                selected_calc_items=selected_calc_items,
                day_count=day_count,
            )
            for indicator in selected_calc_items:
                calc_value = _to_float(calc_values.get(indicator))
                key = f"{company}|{indicator}|{period}|{type_value}|{CALCULATED_ITEM_UNITS.get(indicator, '')}"
                result_map[key] = {
                    "company": company,
                    "item": indicator,
                    "period": period,
                    "type": type_value,
                    "unit": CALCULATED_ITEM_UNITS.get(indicator, ""),
                    "value": calc_value,
                }

    if include_avg_temp and companies and ("month" in {x.lower() for x in periods}) and ("real" in {x.lower() for x in types}):
        avg_stmt = text(
            """
            SELECT AVG(aver_temp) AS avg_temp
            FROM calc_temperature_data
            WHERE date BETWEEN :date_from AND :date_to
            """
        )
        raw_avg = session.execute(avg_stmt, {"date_from": start_date, "date_to": end_date}).scalar()
        avg_value = _to_float(raw_avg) if raw_avg is not None else None
        if avg_value is not None:
            key = f"{AVERAGE_TEMPERATURE_COMPANY}|{AVERAGE_TEMPERATURE_ITEM}|month|real|{AVERAGE_TEMPERATURE_UNIT}"
            result_map[key] = {
                "company": AVERAGE_TEMPERATURE_COMPANY,
                "item": AVERAGE_TEMPERATURE_ITEM,
                "period": "month",
                "type": "real",
                "unit": AVERAGE_TEMPERATURE_UNIT,
                "value": avg_value,
            }

    return result_map


def _fetch_plan_value_map(
    session,
    request: QueryRequest,
    start_date: date,
    end_date: date,
) -> Dict[Tuple[str, str, str, str], Optional[float]]:
    companies = _normalize_text_list(request.companies)
    items = _normalize_text_list(request.items)
    periods = _normalize_text_list(request.periods)
    aggregate_companies = bool(request.aggregate_companies)
    selected_calc_items = [x for x in items if x in CALCULATED_ITEM_SET]
    selected_base_items = [x for x in items if x not in CALCULATED_ITEM_SET and x != AVERAGE_TEMPERATURE_ITEM]
    required_base_items = _collect_required_base_items(selected_calc_items)
    query_base_items = sorted(set(selected_base_items + required_base_items))

    result_map: Dict[Tuple[str, str, str, str], Optional[float]] = {}
    base_rows: List[dict] = []
    if companies and periods and query_base_items:
        where_sql = "date BETWEEN :date_from AND :date_to AND company IN :companies AND item IN :items AND period IN :periods AND type = 'plan'"
        params = {
            "date_from": start_date,
            "date_to": end_date,
            "companies": companies,
            "items": query_base_items,
            "periods": periods,
        }
        select_company_sql = "'聚合口径'::TEXT AS company" if aggregate_companies else "company"
        group_by_sql = "item, period, unit" if aggregate_companies else "company, item, period, unit"
        value_agg_sql = _build_value_aggregate_sql(apply_latest_for_state_items=True)
        stmt = text(
            f"""
            SELECT
                {select_company_sql},
                item,
                period,
                unit,
                {value_agg_sql} AS value
            FROM monthly_data_show
            WHERE {where_sql}
            GROUP BY {group_by_sql}
            """
        ).bindparams(
            bindparam("companies", expanding=True),
            bindparam("items", expanding=True),
            bindparam("periods", expanding=True),
        )
        rows = session.execute(stmt, params).mappings().all()
        selected_base_set = set(selected_base_items)
        for row in rows:
            company = str(row.get("company") or "")
            item = str(row.get("item") or "")
            period = str(row.get("period") or "")
            unit = str(row.get("unit") or "")
            value_raw = row.get("value")
            value = _to_float(value_raw) if value_raw is not None else None
            base_rows.append(
                {
                    "company": company,
                    "item": item,
                    "period": period,
                    "unit": unit,
                    "value": value,
                }
            )
            if item in selected_base_set:
                result_map[(company, item, period, unit)] = value

    if selected_calc_items and base_rows:
        day_count = (end_date - start_date).days + 1
        if day_count <= 0:
            day_count = 0
        grouped_metrics: Dict[Tuple[str, str], Dict[str, float]] = {}
        for row in base_rows:
            group_key = (_safe_str(row.get("company")), _safe_str(row.get("period")))
            metrics = grouped_metrics.setdefault(group_key, {})
            item = _safe_str(row.get("item"))
            metrics[item] = _to_float(metrics.get(item)) + _to_float(row.get("value"))
        for (company, period), metrics in grouped_metrics.items():
            calc_values = _compute_calculated_two_pass(
                metric_values=metrics,
                selected_calc_items=selected_calc_items,
                day_count=day_count,
            )
            for indicator in selected_calc_items:
                unit = CALCULATED_ITEM_UNITS.get(indicator, "")
                result_map[(company, indicator, period, unit)] = _to_float(calc_values.get(indicator))
    return result_map


def _build_temperature_comparison_payload(
    session,
    current_start: date,
    current_end: date,
    yoy_start: date,
    yoy_end: date,
) -> TemperatureComparisonPayload:
    current_stmt = text(
        """
        SELECT date, aver_temp
        FROM calc_temperature_data
        WHERE date BETWEEN :date_from AND :date_to
        ORDER BY date
        """
    )
    yoy_stmt = text(
        """
        SELECT date, aver_temp
        FROM calc_temperature_data
        WHERE date BETWEEN :date_from AND :date_to
        ORDER BY date
        """
    )
    current_rows = session.execute(
        current_stmt,
        {"date_from": current_start, "date_to": current_end},
    ).mappings().all()
    yoy_rows = session.execute(
        yoy_stmt,
        {"date_from": yoy_start, "date_to": yoy_end},
    ).mappings().all()

    current_map: Dict[date, Optional[float]] = {}
    yoy_map: Dict[date, Optional[float]] = {}
    for row in current_rows:
        dt = row.get("date")
        if isinstance(dt, date):
            current_map[dt] = _to_optional_float(row.get("aver_temp"))
    for row in yoy_rows:
        dt = row.get("date")
        if isinstance(dt, date):
            yoy_map[dt] = _to_optional_float(row.get("aver_temp"))

    rows: List[TemperatureDailyComparisonRow] = []
    cursor = current_start
    current_values: List[float] = []
    yoy_values: List[float] = []
    while cursor <= current_end:
        current_temp = current_map.get(cursor)
        yoy_date = _shift_year_safe(cursor, -1)
        yoy_temp = yoy_map.get(yoy_date)
        yoy_diff = None
        if current_temp is not None and yoy_temp is not None:
            yoy_diff = current_temp - yoy_temp
        yoy_rate = _calc_rate(current_temp, yoy_temp)
        if current_temp is not None:
            current_values.append(current_temp)
        if yoy_temp is not None:
            yoy_values.append(yoy_temp)
        rows.append(
            TemperatureDailyComparisonRow(
                current_date=cursor.isoformat(),
                current_temp=current_temp,
                yoy_date=yoy_date.isoformat(),
                yoy_temp=yoy_temp,
                yoy_diff=yoy_diff,
                yoy_rate=yoy_rate,
            )
        )
        cursor += timedelta(days=1)

    current_avg = sum(current_values) / len(current_values) if current_values else None
    yoy_avg = sum(yoy_values) / len(yoy_values) if yoy_values else None
    avg_diff = None
    if current_avg is not None and yoy_avg is not None:
        avg_diff = current_avg - yoy_avg
    summary = TemperatureComparisonSummary(
        current_avg_temp=current_avg,
        yoy_avg_temp=yoy_avg,
        yoy_avg_diff=avg_diff,
        yoy_avg_rate=_calc_rate(current_avg, yoy_avg),
    )
    return TemperatureComparisonPayload(rows=rows, summary=summary)


def _build_average_temperature_rows(
    session,
    request: QueryRequest,
    companies_selected: List[str],
    aggregate_companies: bool,
    aggregate_months: bool,
) -> List[dict]:
    items_selected = _normalize_text_list(request.items)
    periods_selected = {x.lower() for x in _normalize_text_list(request.periods)}
    types_selected = {x.lower() for x in _normalize_text_list(request.types)}
    if AVERAGE_TEMPERATURE_ITEM not in items_selected:
        return []
    if "month" not in periods_selected or "real" not in types_selected:
        return []
    if not companies_selected:
        return []

    range_start, range_end = _pick_temperature_date_range(request)
    if range_start is None or range_end is None:
        return []
    if range_start > range_end:
        return []

    target_companies = [AVERAGE_TEMPERATURE_COMPANY]
    rows: List[dict] = []

    if aggregate_months:
        sql = text(
            """
            SELECT AVG(aver_temp) AS avg_temp
            FROM calc_temperature_data
            WHERE date BETWEEN :date_from AND :date_to
            """
        )
        avg_value = session.execute(
            sql,
            {"date_from": range_start, "date_to": range_end},
        ).scalar()
        if avg_value is None:
            return []
        try:
            value = float(avg_value)
        except (TypeError, ValueError):
            return []
        for company in target_companies:
            rows.append(
                {
                    "company": company,
                    "item": AVERAGE_TEMPERATURE_ITEM,
                    "unit": AVERAGE_TEMPERATURE_UNIT,
                    "value": value,
                    "date": None,
                    "period": "month",
                    "type": "real",
                    "report_month": None,
                    "operation_time": None,
                }
            )
        return rows

    month_starts = _iter_month_starts(range_start, range_end)
    for month_start in month_starts:
        month_end_date = date(
            month_start.year,
            month_start.month,
            calendar.monthrange(month_start.year, month_start.month)[1],
        )
        actual_start = max(range_start, month_start)
        actual_end = min(range_end, month_end_date)
        if actual_start > actual_end:
            continue
        sql = text(
            """
            SELECT AVG(aver_temp) AS avg_temp
            FROM calc_temperature_data
            WHERE date BETWEEN :date_from AND :date_to
            """
        )
        avg_value = session.execute(
            sql,
            {"date_from": actual_start, "date_to": actual_end},
        ).scalar()
        if avg_value is None:
            continue
        try:
            value = float(avg_value)
        except (TypeError, ValueError):
            continue
        for company in target_companies:
            rows.append(
                {
                    "company": company,
                    "item": AVERAGE_TEMPERATURE_ITEM,
                    "unit": AVERAGE_TEMPERATURE_UNIT,
                    "value": value,
                    "date": month_start.isoformat(),
                    "period": "month",
                    "type": "real",
                    "report_month": month_start.isoformat(),
                    "operation_time": None,
                }
            )
    return rows


@router.get("/monthly-data-show/ping", summary="monthly_data_show 连通性检查")
def ping_monthly_data_show():
    return {"ok": True, "project_key": PROJECT_KEY, "message": "monthly_data_show ready"}


@router.post("/monthly-data-show/inspect", response_model=InspectResponse, summary="上传文件并读取可选口径与字段")
async def inspect_monthly_data_show_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    _ensure_allowed_excel_file(file.filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")
    try:
        companies = get_company_options(content)
        inferred_year, inferred_month = parse_report_period_from_filename(file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析文件失败：{exc}") from exc
    return InspectResponse(
        ok=True,
        project_key=PROJECT_KEY,
        companies=companies,
        blocked_companies=sorted(BLOCKED_COMPANIES),
        fields=list(ALLOWED_FIELDS),
        default_selected_fields=list(ALLOWED_FIELDS),
        source_columns=list(DEFAULT_SOURCE_COLUMNS),
        default_selected_source_columns=list(DEFAULT_SOURCE_COLUMNS),
        inferred_report_year=inferred_year,
        inferred_report_month=inferred_month,
        inferred_report_month_date=f"{inferred_year}-{inferred_month:02d}-01",
        constants_enabled_default=True,
        constant_rules=get_default_constant_rules(),
        extraction_rules=get_extraction_rule_options(),
    )


@router.post("/monthly-data-show/extract-csv", summary="按口径与字段提取并下载 CSV")
async def extract_monthly_data_show_csv(
    file: UploadFile = File(...),
    companies: List[str] = Form(default=[]),
    fields: List[str] = Form(default=[]),
    source_columns: List[str] = Form(default=[]),
    extraction_rule_ids: List[str] = Form(default=[]),
    report_year: Optional[int] = Form(default=None),
    report_month: Optional[int] = Form(default=None),
    constants_enabled: bool = Form(default=False),
    constant_rules_json: str = Form(default="[]"),
):
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    _ensure_allowed_excel_file(file.filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")

    try:
        parsed_rules = json.loads(constant_rules_json or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"常量配置格式错误：{exc}") from exc

    normalized_rules = normalize_constant_rules(parsed_rules if isinstance(parsed_rules, list) else [])
    if report_year is not None and (report_year < 2000 or report_year > 2099):
        raise HTTPException(status_code=422, detail="report_year 必须在 2000-2099 之间")
    if report_month is not None and (report_month < 1 or report_month > 12):
        raise HTTPException(status_code=422, detail="report_month 必须在 1-12 之间")

    try:
        extracted_rows, stats = extract_rows(
            file_bytes=content,
            filename=file.filename,
            selected_companies=companies or None,
            selected_source_columns=source_columns or None,
            selected_rule_ids=extraction_rule_ids or None,
            constants_enabled=bool(constants_enabled),
            constant_rules=normalized_rules,
            report_year=report_year,
            report_month=report_month,
        )
        csv_rows = filter_fields(extracted_rows, fields)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"提取 CSV 失败：{exc}") from exc

    if not csv_rows:
        raise HTTPException(status_code=422, detail="未提取到数据，请检查所选口径与文件内容")

    selected_fields = [field for field in ALLOWED_FIELDS if field in set(fields)] or list(ALLOWED_FIELDS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile(prefix="monthly_data_show_", suffix=".csv", delete=False, mode="w", encoding="utf-8-sig", newline="") as tmp:
        writer = csv.DictWriter(tmp, fieldnames=selected_fields)
        writer.writeheader()
        writer.writerows(csv_rows)
        csv_path = tmp.name

    download_name = f"monthly_data_show_extract_{timestamp}.csv"
    semi_count = int((stats or {}).get("semi_calculated_completed") or 0)
    jinpu_count = int((stats or {}).get("jinpu_heating_area_adjusted") or 0)
    total_rows = int((stats or {}).get("total_rows") or len(extracted_rows))
    rule_details = {
        "semi_calculated_details": (stats or {}).get("semi_calculated_details") or {},
        "semi_calculated_completed": semi_count,
        "jinpu_heating_area_adjusted": jinpu_count,
        "item_exclude_hits": int((stats or {}).get("item_exclude_hits") or 0),
        "item_rename_hits": int((stats or {}).get("item_rename_hits") or 0),
        "selected_rule_ids": list((stats or {}).get("selected_rule_ids") or []),
        "constants_injected": int((stats or {}).get("constants_injected") or 0),
        "extracted_total_rows": total_rows,
    }
    encoded_rule_details = quote(json.dumps(rule_details, ensure_ascii=False, separators=(",", ":")))
    return FileResponse(
        path=csv_path,
        media_type="text/csv; charset=utf-8",
        filename=download_name,
        headers={
            "X-Monthly-Semi-Calculated-Completed": str(semi_count),
            "X-Monthly-Jinpu-Heating-Area-Adjusted": str(jinpu_count),
            "X-Monthly-Extracted-Total-Rows": str(total_rows),
            "X-Monthly-Rule-Details": encoded_rule_details,
            "Access-Control-Expose-Headers": (
                "Content-Disposition, "
                "X-Monthly-Semi-Calculated-Completed, "
                "X-Monthly-Jinpu-Heating-Area-Adjusted, "
                "X-Monthly-Extracted-Total-Rows, "
                "X-Monthly-Rule-Details"
            ),
        },
        background=BackgroundTask(_cleanup_file, csv_path),
    )


@router.post("/monthly-data-show/import-csv", response_model=ImportCsvResponse, summary="上传 CSV 并写入 monthly_data_show")
async def import_monthly_data_show_csv(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    suffix = Path(str(file.filename)).suffix.lower()
    if suffix != ".csv":
        raise HTTPException(status_code=422, detail="仅支持 .csv 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")

    rows, null_value_rows = _parse_import_csv_rows(content)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV 无有效数据行")

    upsert_sql = text(
        """
        INSERT INTO monthly_data_show (
            company, item, unit, value, date, period, type, report_month
        ) VALUES (
            :company, :item, :unit, :value, :date, :period, :type, :report_month
        )
        ON CONFLICT (company, item, date, period, type)
        DO UPDATE SET
            unit = EXCLUDED.unit,
            value = EXCLUDED.value,
            report_month = EXCLUDED.report_month,
            operation_time = CURRENT_TIMESTAMP
        RETURNING (xmax = 0) AS inserted
        """
    )
    inserted_rows = 0
    updated_rows = 0
    try:
        with SessionLocal() as session:
            # 注意：部分驱动/批量执行场景下，executemany + RETURNING 结果集不可直接 fetchall。
            # 这里改为逐行执行，确保入库稳定且可统计新增/更新。
            for payload in rows:
                flag = session.execute(upsert_sql, payload).scalar_one_or_none()
                if bool(flag):
                    inserted_rows += 1
                else:
                    updated_rows += 1
            session.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV 入库失败：{exc}") from exc

    return ImportCsvResponse(
        ok=True,
        project_key=PROJECT_KEY,
        imported_rows=len(rows),
        null_value_rows=null_value_rows,
        inserted_rows=inserted_rows,
        updated_rows=updated_rows,
    )


@router.get("/monthly-data-show/query-options", response_model=QueryOptionsResponse, summary="月报查询筛选项")
def get_monthly_data_show_query_options():
    _refresh_indicator_runtime()
    sql = text(
        """
        SELECT
            ARRAY(SELECT DISTINCT company FROM monthly_data_show ORDER BY company) AS companies,
            ARRAY(
                SELECT item
                FROM monthly_data_show
                GROUP BY item
                ORDER BY MIN(id)
            ) AS items,
            ARRAY(SELECT DISTINCT period FROM monthly_data_show ORDER BY period) AS periods,
            ARRAY(SELECT DISTINCT type FROM monthly_data_show ORDER BY type) AS types
        """
    )
    try:
        with SessionLocal() as session:
            row = session.execute(sql).mappings().first() or {}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取查询筛选项失败：{exc}") from exc

    items_from_db = [str(x) for x in (row.get("items") or []) if str(x).strip()]
    items = order_items_by_config(items_from_db, INDICATOR_RUNTIME_CFG)
    for calc_name in INDICATOR_RUNTIME_CFG.get("calculated_item_names") or []:
        text_name = str(calc_name or "").strip()
        if text_name and text_name not in items:
            items.append(text_name)
    if AVERAGE_TEMPERATURE_ITEM not in items:
        items.append(AVERAGE_TEMPERATURE_ITEM)

    return QueryOptionsResponse(
        ok=True,
        project_key=PROJECT_KEY,
        companies=[str(x) for x in (row.get("companies") or []) if str(x).strip()],
        items=items,
        periods=[str(x) for x in (row.get("periods") or []) if str(x).strip()],
        types=[str(x) for x in (row.get("types") or []) if str(x).strip()],
        indicator_config=build_indicator_config_payload(INDICATOR_RUNTIME_CFG),
    )


@router.post("/monthly-data-show/query", response_model=QueryResponse, summary="月报数据查询")
def query_month_data_show(request: QueryRequest):
    _refresh_indicator_runtime()
    limit = max(1, min(1000, int(request.limit or 200)))
    offset = max(0, int(request.offset or 0))
    companies_selected = _normalize_text_list(request.companies)
    items_selected = _normalize_text_list(request.items)
    periods_selected = _normalize_text_list(request.periods)
    types_selected = _normalize_text_list(request.types)
    if not companies_selected or not items_selected or not periods_selected or not types_selected:
        return QueryResponse(
            ok=True,
            project_key=PROJECT_KEY,
            total=0,
            limit=limit,
            offset=offset,
            rows=[],
            summary=QuerySummary(
                total_rows=0,
                value_non_null_rows=0,
                value_null_rows=0,
                value_sum=0.0,
            ),
        )
    include_average_temperature = AVERAGE_TEMPERATURE_ITEM in items_selected
    selected_calc_items = [x for x in items_selected if x in CALCULATED_ITEM_SET]
    selected_base_items = [x for x in items_selected if x not in CALCULATED_ITEM_SET and x != AVERAGE_TEMPERATURE_ITEM]
    required_base_items = _collect_required_base_items(selected_calc_items)
    query_base_items = sorted(set(selected_base_items + required_base_items))
    run_base_query = bool(query_base_items)
    if run_base_query:
        base_request = request.model_copy(update={"items": query_base_items})
        where_clause, params, bind_params = _build_query_sql_parts(base_request)
        where_sql = f"WHERE {where_clause}" if where_clause else ""
    else:
        where_clause, params, bind_params = "", {}, []
        where_sql = ""
    order_mode = str(request.order_mode or "company_first").strip().lower()
    if order_mode not in {"company_first", "item_first"}:
        raise HTTPException(status_code=422, detail="order_mode 仅支持 company_first 或 item_first")
    aggregate_companies = bool(request.aggregate_companies)
    aggregate_months = bool(request.aggregate_months)
    resolved_order_fields = _resolve_order_fields(order_mode, request.order_fields, aggregate_companies)

    if run_base_query and (aggregate_companies or aggregate_months):
        value_agg_sql = _build_value_aggregate_sql(apply_latest_for_state_items=aggregate_months)
        group_fields: List[str] = []
        if not aggregate_companies:
            group_fields.append("company")
        group_fields.extend(["item", "unit"])
        if not aggregate_months:
            group_fields.extend(["date", "report_month"])
        group_fields.extend(["period", "type"])
        group_by_sql = ", ".join(group_fields)
        list_sql = text(
            f"""
            SELECT
                {'\'聚合口径\'::TEXT AS company' if aggregate_companies else 'company'},
                item,
                unit,
                {value_agg_sql} AS value,
                {'NULL::DATE AS date' if aggregate_months else 'date'},
                period,
                type,
                {'NULL::DATE AS report_month' if aggregate_months else 'report_month'},
                MAX(operation_time) AS operation_time
            FROM monthly_data_show
            {where_sql}
            GROUP BY {group_by_sql}
            """
        )
    elif run_base_query:
        list_sql = text(
            f"""
            SELECT
                company, item, unit, value, date, period, type, report_month, operation_time
            FROM monthly_data_show
            {where_sql}
            """
        )
    if run_base_query and bind_params:
        list_sql = list_sql.bindparams(*bind_params)

    try:
        with SessionLocal() as session:
            row_mappings = session.execute(list_sql, params).mappings().all() if run_base_query else []
            temp_rows = (
                _build_average_temperature_rows(
                    session=session,
                    request=request,
                    companies_selected=companies_selected,
                    aggregate_companies=aggregate_companies,
                    aggregate_months=aggregate_months,
                )
                if include_average_temperature
                else []
            )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"查询月报数据失败：{exc}") from exc

    base_rows_all: List[dict] = []
    for row in row_mappings:
        base_rows_all.append(
            {
                "company": row.get("company"),
                "item": row.get("item"),
                "unit": row.get("unit"),
                "value": _to_float(row.get("value")) if row.get("value") is not None else None,
                "date": row.get("date").isoformat() if row.get("date") else None,
                "period": row.get("period"),
                "type": row.get("type"),
                "report_month": row.get("report_month").isoformat() if row.get("report_month") else None,
                "operation_time": row.get("operation_time").isoformat() if row.get("operation_time") else None,
            }
        )

    calculated_rows = _build_calculated_rows(
        base_rows=base_rows_all,
        request=request,
        selected_calc_items=selected_calc_items,
        aggregate_months=aggregate_months,
    )
    selected_base_set = set(selected_base_items)
    output_base_rows = [row for row in base_rows_all if _safe_str(row.get("item")) in selected_base_set]
    rank_maps = {
        "company": _build_rank_map(companies_selected),
        "item": _build_rank_map(items_selected),
        "period": _build_rank_map(periods_selected),
        "type": _build_rank_map(types_selected),
    }
    all_rows: List[dict] = []
    all_rows.extend(output_base_rows)
    all_rows.extend(calculated_rows)
    all_rows.extend(temp_rows)
    all_rows = _merge_and_sort_rows(all_rows, resolved_order_fields, aggregate_months, rank_maps=rank_maps)
    total_count = len(all_rows)
    page_rows = all_rows[offset : offset + limit]
    value_non_null_rows = sum(1 for row in all_rows if row.get("value") is not None)
    value_sum = sum(_to_float(row.get("value")) for row in all_rows if row.get("value") is not None)

    summary = QuerySummary(
        total_rows=total_count,
        value_non_null_rows=value_non_null_rows,
        value_null_rows=total_count - value_non_null_rows,
        value_sum=value_sum,
    )

    return QueryResponse(
        ok=True,
        project_key=PROJECT_KEY,
        total=total_count,
        limit=limit,
        offset=offset,
        rows=page_rows,
        summary=summary,
    )


@router.post("/monthly-data-show/query-comparison", response_model=QueryComparisonResponse, summary="月报数据同比/环比查询")
def query_month_data_show_comparison(request: QueryRequest):
    _refresh_indicator_runtime()
    companies_selected = _normalize_text_list(request.companies)
    items_selected = _normalize_text_list(request.items)
    periods_selected = _normalize_text_list(request.periods)
    types_selected = _normalize_text_list(request.types)
    order_mode = str(request.order_mode or "company_first").strip().lower()
    if order_mode not in {"company_first", "item_first"}:
        raise HTTPException(status_code=422, detail="order_mode 仅支持 company_first 或 item_first")
    aggregate_companies = bool(request.aggregate_companies)
    resolved_order_fields = _resolve_order_fields(order_mode, request.order_fields, aggregate_companies)
    rank_maps = {
        "company": _build_rank_map(companies_selected),
        "item": _build_rank_map(items_selected),
        "period": _build_rank_map(periods_selected),
        "type": _build_rank_map(types_selected),
    }
    include_temperature_comparison = AVERAGE_TEMPERATURE_ITEM in set(items_selected)
    if not companies_selected or not items_selected or not periods_selected or not types_selected:
        return QueryComparisonResponse(
            ok=True,
            project_key=PROJECT_KEY,
            current_window_label="",
            yoy_window_label="",
            mom_window_label="",
            plan_window_label="",
            rows=[],
            temperature_comparison=None,
        )

    current_start, current_end = _resolve_compare_window(request)
    if current_start is None or current_end is None:
        return QueryComparisonResponse(
            ok=True,
            project_key=PROJECT_KEY,
            current_window_label="",
            yoy_window_label="",
            mom_window_label="",
            plan_window_label="",
            rows=[],
            temperature_comparison=None,
        )
    if current_start > current_end:
        raise HTTPException(status_code=422, detail="对比窗口无效：开始日期晚于结束日期")

    yoy_start = _shift_year_safe(current_start, -1)
    yoy_end = _shift_year_safe(current_end, -1)
    mom_start, mom_end = _resolve_mom_window(current_start, current_end)

    try:
        with SessionLocal() as session:
            current_map = _fetch_compare_map(session, request, current_start, current_end)
            yoy_map = _fetch_compare_map(session, request, yoy_start, yoy_end)
            mom_map = _fetch_compare_map(session, request, mom_start, mom_end)
            plan_map = _fetch_plan_value_map(session, request, current_start, current_end)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"查询同比环比失败：{exc}") from exc

    rows: List[QueryComparisonRow] = []
    for key in current_map.keys():
        base = current_map.get(key) or {}
        current_value = base.get("value")
        yoy_value = (yoy_map.get(key) or {}).get("value")
        mom_value = (mom_map.get(key) or {}).get("value")
        plan_value = plan_map.get(
            (
                str(base.get("company") or ""),
                str(base.get("item") or ""),
                str(base.get("period") or ""),
                str(base.get("unit") or ""),
            )
        )
        rows.append(
            QueryComparisonRow(
                company=str(base.get("company") or ""),
                item=str(base.get("item") or ""),
                period=str(base.get("period") or ""),
                type=str(base.get("type") or ""),
                unit=str(base.get("unit") or ""),
                current_value=current_value,
                yoy_value=yoy_value,
                yoy_rate=_calc_rate(current_value, yoy_value),
                mom_value=mom_value,
                mom_rate=_calc_rate(current_value, mom_value),
                plan_value=plan_value,
                plan_rate=_calc_rate(current_value, plan_value),
            )
        )
    rows = _sort_comparison_rows(rows, resolved_order_fields, rank_maps)
    temperature_comparison: Optional[TemperatureComparisonPayload] = None
    if include_temperature_comparison:
        try:
            with SessionLocal() as session:
                temperature_comparison = _build_temperature_comparison_payload(
                    session=session,
                    current_start=current_start,
                    current_end=current_end,
                    yoy_start=yoy_start,
                    yoy_end=yoy_end,
                )
        except Exception:
            temperature_comparison = TemperatureComparisonPayload(rows=[], summary=None)

    return QueryComparisonResponse(
        ok=True,
        project_key=PROJECT_KEY,
        current_window_label=_format_window_label(current_start, current_end),
        yoy_window_label=_format_window_label(yoy_start, yoy_end),
        mom_window_label=_format_window_label(mom_start, mom_end),
        plan_window_label=_format_window_label(current_start, current_end),
        rows=rows,
        temperature_comparison=temperature_comparison,
    )


@router.post(
    "/monthly-data-show/ai-report/start",
    response_model=MonthlyAiReportStartResponse,
    summary="启动月报智能分析报告任务",
)
def start_monthly_ai_report(payload: MonthlyAiReportStartPayload):
    ai_payload = _build_monthly_ai_payload(payload)
    try:
        job_id = data_analysis_ai_report.enqueue_ai_report_job(ai_payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"启动月报 AI 报告失败：{exc}") from exc
    return MonthlyAiReportStartResponse(
        ok=True,
        project_key=PROJECT_KEY,
        ai_report_job_id=job_id,
        ai_mode_id=str(ai_payload.get("ai_mode_id") or "monthly_analysis_v1"),
    )


@router.get(
    "/monthly-data-show/ai-report/{job_id}",
    summary="查询月报智能分析报告任务状态",
)
def get_monthly_ai_report(job_id: str):
    job_payload = data_analysis_ai_report.get_report_job(job_id)
    if not job_payload:
        raise HTTPException(status_code=404, detail="报告不存在或已过期")
    response = {"ok": True, "project_key": PROJECT_KEY}
    response.update(job_payload)
    return response


@router.post(
    "/monthly-data-show/ai-chat/query",
    response_model=MonthlyAiChatResponse,
    summary="月报查询对话助手（受控工具调用）",
)
def chat_monthly_data_show_query(payload: MonthlyAiChatRequest):
    user_message = str(payload.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="message 不能为空")

    session_id = _chat_get_or_create_session(payload.session_id)
    merged_history = _chat_get_session_history(session_id, payload.history)
    query_request = _chat_build_query_request(payload)
    preview_limit = max(1, min(50, _chat_parse_top_n(user_message, payload.top_n or 12, 50)))

    tool_calls: List[MonthlyAiChatToolCall] = []
    web_sources: List[dict] = []
    preview_rows: List[dict] = []
    total_rows = 0
    tool_name = "query_month_data_show"
    tool_summary = ""
    extra_context = ""

    use_web_search = bool(payload.enable_web_search) and _chat_use_web_search_tool(user_message)
    if use_web_search:
        tool_name = "search_web_public"
        web_sources = _chat_execute_web_search(user_message, CHAT_WEB_SEARCH_LIMIT)
        total_rows = len(web_sources)
        preview_rows = web_sources[:preview_limit]
        if web_sources:
            tool_summary = f"联网检索命中 {total_rows} 条公开结果。"
            extra_context = f"联网来源：{json.dumps(web_sources, ensure_ascii=False)}"
        else:
            tool_summary = "已尝试联网检索，但未命中可用公开结果。"

        tool_calls.append(
            MonthlyAiChatToolCall(
                tool=tool_name,
                summary=tool_summary,
                total_rows=total_rows,
                details={"limit": CHAT_WEB_SEARCH_LIMIT},
            )
        )
    else:
        use_comparison = _chat_use_comparison_tool(user_message)

        if use_comparison:
            tool_name = "query_month_data_show_comparison"
            compare_payload = query_month_data_show_comparison(query_request)
            compare_rows = [row.model_dump(mode="json") for row in compare_payload.rows]
            total_rows = len(compare_rows)
            preview_rows = compare_rows[:preview_limit]
            tool_summary = (
                f"对比窗口={compare_payload.current_window_label or '未识别'}，"
                f"同比窗口={compare_payload.yoy_window_label or '未识别'}，"
                f"环比窗口={compare_payload.mom_window_label or '未识别'}，"
                f"计划窗口={compare_payload.plan_window_label or '未识别'}。"
            )
            data_summary = _chat_summarize_rows(compare_rows, top_n=preview_limit)
        else:
            tool_name = "query_month_data_show"
            query_payload = query_month_data_show(query_request)
            all_rows = list(query_payload.rows or [])
            total_rows = int(query_payload.total or 0)
            preview_rows = all_rows[:preview_limit]
            tool_summary = f"分页={query_payload.offset}-{query_payload.offset + len(all_rows)}，总条数={query_payload.total}。"
            data_summary = _chat_summarize_rows(all_rows, top_n=preview_limit)

        tool_calls.append(
            MonthlyAiChatToolCall(
                tool=tool_name,
                summary=tool_summary,
                total_rows=total_rows,
                details={
                    "aggregate_months": bool(query_request.aggregate_months),
                    "aggregate_companies": bool(query_request.aggregate_companies),
                },
            )
        )

        if int(data_summary.get("row_count") or 0) > 0:
            tool_calls.append(
                MonthlyAiChatToolCall(
                    tool="aggregate_rows",
                    summary=str(data_summary.get("summary") or "已完成结果聚合。"),
                    total_rows=int(data_summary.get("row_count") or 0),
                    details={
                        "group_summary": list(data_summary.get("group_summary") or []),
                        "top_rows": list(data_summary.get("top_rows") or []),
                    },
                )
            )
            extra_context = json.dumps(data_summary, ensure_ascii=False)

    try:
        answer = _chat_generate_answer_by_model(
            payload=payload,
            tool_name=tool_name,
            tool_summary=tool_summary,
            total_rows=total_rows,
            preview_rows=preview_rows,
            history=merged_history,
            query_request=query_request,
            extra_context=extra_context,
        )
    except Exception:
        answer = _chat_build_answer_fallback(
            tool_name=tool_name,
            total_rows=total_rows,
            user_message=user_message,
            preview_rows=preview_rows,
        )

    final_answer = answer or "已执行查询，但暂未生成可用分析结论。"
    _chat_append_session_history(session_id, user_message, final_answer)

    return MonthlyAiChatResponse(
        ok=True,
        project_key=PROJECT_KEY,
        session_id=session_id,
        answer=final_answer,
        tool_calls=tool_calls,
        preview_rows=preview_rows,
        web_sources=web_sources,
        applied_query=query_request.model_dump(mode="json"),
    )
