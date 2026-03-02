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
from urllib.parse import quote
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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

PROJECT_KEY = "monthly_data_show"
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
