# -*- coding: utf-8 -*-
"""
monthly_data_show 月报入库提取服务。

第一阶段目标：
- 从上传的月报 Excel 中提取基础入库字段：
  company,item,unit,value,date,period,type,report_month
- 支持按口径（子工作表）与字段复选导出 CSV。
"""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from openpyxl import load_workbook

BLOCKED_COMPANIES = {"恒流", "天然气炉", "中水"}
ALLOWED_FIELDS = ("company", "item", "unit", "value", "date", "period", "type", "report_month")
DEFAULT_SOURCE_COLUMNS = ("本年计划", "本月计划", "本月实际", "上年同期")

ITEM_EXCLUDE_SET = {
    "本期平均供暖面积",
    "实际平均供热面积",
    "高压电量",
    "管网循环水总量",
    "管网失水量",
    "管网失水率",
    "本月内最高气温",
    "本月内最低气温",
    "本月平均气温",
    "实际检测户数（室温）",
    "检测合格户数",
    "用户室温合格率",
    "用户报修次数",
    "24小时处理次数",
    "用户报修处理及时率",
    "本月供暖小时数",
    "应按期结案总数",
    "按期结案总数",
    "信访处结率",
}

ITEM_RENAME_MAP = {
    "主城区一次网电厂补水量": "一次网电厂补水量",
    "一次网电厂补水量": "一次网电厂补水量",
    "高温水网电厂补水量": "一次网电厂补水量",
    "高温水低真空电厂补水量": "一次网电厂补水量",
    "耗外购电量": "外购电量",
    "外购电量": "外购电量",
    "期末供热面积": "期末供暖收费面积",
    "单位面积耗电量": "供暖电耗率",
    "单位面积耗水量": "供暖水耗率",
    "单位面积耗标准煤量": "供暖标准煤耗率",
    "锅炉设备利用率": "供热设备利用率",
    "锅炉热效率": "全厂热效率",
    "总热效率": "全厂热效率",
    "炉耗油量": "耗油量",
    "装机总容量": "锅炉设备容量",
    "发电煤耗率": "发电标准煤耗率",
    "供电煤耗率": "供电标准煤耗率",
    "供热煤耗率": "供热标准煤耗率",
    "供热标准煤耗量": "供热耗标煤量",
    "发电标准煤耗量": "发电耗标煤量",
}

CALCULATED_ITEM_SET = {
    "综合厂用电率",
    "发电标准煤耗率",
    "供电标准煤耗率",
    "供热标准煤耗率",
    "发电水耗率",
    "供热水耗率",
    "供暖热耗率",
    "供暖水耗率",
    "供暖电耗率",
    "发电设备利用率",
    "供热设备利用率",
    "入炉煤低位发热量",
    "发电厂用电率",
    "供热厂用电率",
    "全厂热效率",
    "热电比",
    "热分摊比",
    "供热用电率",
    "供暖标准煤耗率",
}

DEFAULT_CONSTANT_RULES = [
    {"company": "北海", "item": "发电设备容量", "unit": "万千瓦", "value": 10.0, "source_columns": ["本月实际"]},
    {"company": "香海", "item": "发电设备容量", "unit": "万千瓦", "value": 10.0, "source_columns": ["本月实际"]},
    {"company": "金州", "item": "发电设备容量", "unit": "万千瓦", "value": 3.6, "source_columns": ["本月实际"]},
    {"company": "北方", "item": "发电设备容量", "unit": "万千瓦", "value": 3.96, "source_columns": ["本月实际"]},
    {"company": "北海", "item": "锅炉设备容量", "unit": "兆瓦", "value": 577.0, "source_columns": ["本月实际"]},
    {"company": "香海", "item": "锅炉设备容量", "unit": "兆瓦", "value": 528.0, "source_columns": ["本月实际"]},
    {"company": "金州", "item": "锅炉设备容量", "unit": "兆瓦", "value": 414.0, "source_columns": ["本月实际"]},
    {"company": "北方", "item": "锅炉设备容量", "unit": "兆瓦", "value": 130.0, "source_columns": ["本月实际"]},
]


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", "", text)


def _normalize_item(value: object) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    normalized = raw.replace("其中：", "")
    normalized = ITEM_RENAME_MAP.get(normalized, normalized)
    if normalized == raw:
        token = (
            normalized.replace("、", "")
            .replace("，", "")
            .replace(",", "")
            .replace("/", "")
        )
        normalized = ITEM_RENAME_MAP.get(token, normalized)
    return normalized


def _normalize_unit(value: object) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""
    normalized = raw.replace("米2", "平方米").replace("米²", "平方米")
    normalized = re.sub(r"/平方米$", "/平方米", normalized)
    normalized = normalized.replace("/米2", "/平方米").replace("/米²", "/平方米")
    return normalized


def _coerce_number(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_value(unit: str, value: object) -> object:
    number = _coerce_number(value)
    if number is None:
        return str(value).strip()
    if unit == "万千瓦时":
        return round(number, 8)
    if unit == "千瓦时":
        return round(number / 10000.0, 8)
    return round(number, 8)


def _build_period_meta(report_year: int, report_month: int, src_col: str) -> Dict[str, str]:
    if src_col == "本年计划":
        return {
            "date": f"{report_year}-01-01",
            "period": "year",
            "type": "plan",
        }
    if src_col == "本月计划":
        return {
            "date": f"{report_year}-{report_month:02d}-01",
            "period": "month",
            "type": "plan",
        }
    if src_col == "本月实际":
        return {
            "date": f"{report_year}-{report_month:02d}-01",
            "period": "month",
            "type": "real",
        }
    return {
        "date": f"{report_year - 1}-{report_month:02d}-01",
        "period": "month",
        "type": "real",
    }


def _build_report_month_text(report_year: int, report_month: int) -> str:
    return f"{report_year}-{report_month:02d}-01"


def parse_report_period_from_filename(filename: str) -> Tuple[int, int]:
    text = str(filename or "")
    matched = re.search(r"(\d{2})\.(\d{1,2})", text)
    if matched:
        year = 2000 + int(matched.group(1))
        month = int(matched.group(2))
        month = max(1, min(12, month))
        return year, month
    now = datetime.now()
    return now.year, now.month


def get_default_constant_rules() -> List[Dict[str, object]]:
    return [dict(item) for item in DEFAULT_CONSTANT_RULES]


def normalize_constant_rules(raw_rules: Optional[Sequence[Dict[str, object]]]) -> List[Dict[str, object]]:
    rules: List[Dict[str, object]] = []
    for raw in raw_rules or []:
        if not isinstance(raw, dict):
            continue
        company = str(raw.get("company") or "").strip()
        item = _normalize_item(raw.get("item"))
        unit = _normalize_unit(raw.get("unit"))
        if not company or not item:
            continue
        value = _coerce_number(raw.get("value"))
        if value is None:
            continue
        src_cols_raw = raw.get("source_columns")
        source_columns: List[str] = []
        if isinstance(src_cols_raw, list):
            for col in src_cols_raw:
                col_name = str(col or "").strip()
                if col_name in DEFAULT_SOURCE_COLUMNS and col_name not in source_columns:
                    source_columns.append(col_name)
        if not source_columns:
            fallback_col = str(raw.get("source_column") or "本月实际").strip()
            if fallback_col in DEFAULT_SOURCE_COLUMNS:
                source_columns = [fallback_col]
            else:
                source_columns = ["本月实际"]
        rules.append(
            {
                "company": company,
                "item": item,
                "unit": unit,
                "value": round(float(value), 8),
                "source_columns": source_columns,
            }
        )
    return rules


def _find_header_row_and_columns(sheet) -> Tuple[int, Dict[str, int]]:
    required = {"项目", "计量单位", "本年计划", "本月计划", "上年同期", "本月实际"}
    for row_index in range(1, min(8, sheet.max_row + 1)):
        mapping: Dict[str, int] = {}
        for col_index in range(1, sheet.max_column + 1):
            label = _clean_text(sheet.cell(row=row_index, column=col_index).value)
            if not label:
                continue
            for target in required:
                if label == target:
                    mapping[target] = col_index
        if required.issubset(set(mapping.keys())):
            return row_index, mapping
    raise ValueError(f"子表 {sheet.title} 未找到标准表头（项目/计量单位/计划/实际）")


def _iter_valid_sheets(workbook, selected_companies: Optional[Sequence[str]] = None):
    selected = {str(x).strip() for x in (selected_companies or []) if str(x).strip()}
    for name in workbook.sheetnames:
        company = str(name).strip()
        if not company or company in BLOCKED_COMPANIES:
            continue
        if selected and company not in selected:
            continue
        yield workbook[company]


def get_company_options(file_bytes: bytes) -> List[str]:
    workbook = load_workbook(filename=BytesIO(file_bytes), data_only=True, read_only=True)
    companies = [name for name in workbook.sheetnames if str(name).strip() and str(name).strip() not in BLOCKED_COMPANIES]
    workbook.close()
    return companies


def extract_rows(
    file_bytes: bytes,
    filename: str,
    selected_companies: Optional[Sequence[str]] = None,
    selected_source_columns: Optional[Sequence[str]] = None,
    constants_enabled: bool = False,
    constant_rules: Optional[Sequence[Dict[str, object]]] = None,
    report_year: Optional[int] = None,
    report_month: Optional[int] = None,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    parsed_year, parsed_month = parse_report_period_from_filename(filename)
    if report_year is None:
        report_year = parsed_year
    if report_month is None:
        report_month = parsed_month
    report_month = max(1, min(12, int(report_month)))
    report_year = int(report_year)
    report_month_text = _build_report_month_text(report_year, report_month)
    workbook = load_workbook(filename=BytesIO(file_bytes), data_only=True, read_only=True)
    rows: List[Dict[str, object]] = []
    per_company_count: Dict[str, int] = {}

    source_columns = tuple(DEFAULT_SOURCE_COLUMNS)
    selected_col_set = {str(x).strip() for x in (selected_source_columns or []) if str(x).strip()}
    if selected_col_set:
        source_columns = tuple(col for col in source_columns if col in selected_col_set)
    try:
        for sheet in _iter_valid_sheets(workbook, selected_companies=selected_companies):
            company = str(sheet.title).strip()
            header_row, col_map = _find_header_row_and_columns(sheet)
            count_before = len(rows)
            for row_idx in range(header_row + 1, sheet.max_row + 1):
                item_raw = sheet.cell(row=row_idx, column=col_map["项目"]).value
                unit_raw = sheet.cell(row=row_idx, column=col_map["计量单位"]).value
                item = _normalize_item(item_raw)
                unit = _normalize_unit(unit_raw)
                if not item:
                    continue
                if item in ITEM_EXCLUDE_SET:
                    continue
                if item in CALCULATED_ITEM_SET:
                    continue
                for src_col in source_columns:
                    value_cell = sheet.cell(row=row_idx, column=col_map[src_col]).value
                    value = _normalize_value(unit, value_cell)
                    meta = _build_period_meta(report_year, report_month, src_col)
                    rows.append(
                        {
                            "company": company,
                            "item": item,
                            "unit": "万千瓦时" if unit == "千瓦时" else unit,
                            "value": value,
                            "date": meta["date"],
                            "period": meta["period"],
                            "type": meta["type"],
                            "report_month": report_month_text,
                        }
                    )
            per_company_count[company] = len(rows) - count_before
    finally:
        workbook.close()

    stats = {
        "report_year": report_year,
        "report_month": report_month,
        "total_rows": len(rows),
        "company_rows": per_company_count,
    }

    if constants_enabled:
        normalized_rules = normalize_constant_rules(constant_rules)
        selected_company_set = {str(x).strip() for x in (selected_companies or []) if str(x).strip()}
        selected_source_set = set(source_columns)
        row_index_by_key: Dict[Tuple[str, str, str, str, str], int] = {}
        for idx, row in enumerate(rows):
            key = (
                str(row.get("company") or "").strip(),
                str(row.get("item") or "").strip(),
                str(row.get("date") or "").strip(),
                str(row.get("period") or "").strip(),
                str(row.get("type") or "").strip(),
            )
            row_index_by_key[key] = idx

        injected_count = 0
        for rule in normalized_rules:
            company = str(rule["company"])
            if company in BLOCKED_COMPANIES:
                continue
            if selected_company_set and company not in selected_company_set:
                continue
            for source_column in rule.get("source_columns", []):
                source_column = str(source_column)
                if selected_source_set and source_column not in selected_source_set:
                    continue
                meta = _build_period_meta(report_year, report_month, source_column)
                new_row = {
                    "company": company,
                    "item": str(rule["item"]),
                    "unit": str(rule["unit"]),
                    "value": round(float(rule["value"]), 8),
                    "date": meta["date"],
                    "period": meta["period"],
                    "type": meta["type"],
                    "report_month": report_month_text,
                }
                key = (new_row["company"], new_row["item"], new_row["date"], new_row["period"], new_row["type"])
                old_idx = row_index_by_key.get(key)
                if old_idx is None:
                    row_index_by_key[key] = len(rows)
                    rows.append(new_row)
                    injected_count += 1
                else:
                    rows[old_idx] = new_row
                    injected_count += 1

        stats["constants_injected"] = injected_count
        stats["total_rows"] = len(rows)
    return rows, stats


def filter_fields(rows: Iterable[Dict[str, object]], selected_fields: Sequence[str]) -> List[Dict[str, object]]:
    field_set = [field for field in ALLOWED_FIELDS if field in set(selected_fields)]
    if not field_set:
        field_set = list(ALLOWED_FIELDS)
    return [{field: row.get(field, "") for field in field_set} for row in rows]
