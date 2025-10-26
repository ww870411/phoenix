#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从模板自动生成 daily_basic_data 示例数据。

输出文件：
- backend/sql/sample_daily_basic_data.csv
- backend/sql/sample_daily_basic_data.sql

包含日期：
- 本期：2025-10-21 至 2025-10-25
- 同期：对应上一年度同日
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
TEMPLATE_FILE = ROOT_DIR / "backend_data" / "数据结构_基本指标表.json"
OUTPUT_CSV = BACKEND_DIR / "sql" / "sample_daily_basic_data.csv"
OUTPUT_SQL = BACKEND_DIR / "sql" / "sample_daily_basic_data.sql"
TABLE_NAME = "Daily_basic_data"

TARGET_DATES: List[date] = [date(2025, 10, 21) + timedelta(days=i) for i in range(5)]


@dataclass
class TemplateRow:
    company: str
    company_cn: str
    sheet_key: str
    item_key: str
    item_cn: str
    unit: str
    sequence: int


def load_templates() -> Dict[str, dict]:
    raw = TEMPLATE_FILE.read_text(encoding="utf-8")
    return json.loads(raw)


def slugify(text: str) -> str:
    cleaned = []
    for ch in text.strip():
        if ch.isalnum():
            cleaned.append(ch.lower())
        elif ch in ("-", "_"):
            cleaned.append("_")
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug or "item"


def iterate_template_rows(templates: Dict[str, dict]) -> Iterable[TemplateRow]:
    sequence = 0
    for sheet_key, sheet in templates.items():
        if sheet.get("类型") == "crosstab":
            continue

        company = sheet.get("单位标识") or sheet_key
        company_cn = sheet.get("单位名") or sheet.get("单位名称") or company
        sheet_name_en = sheet_key
        columns = sheet.get("列名") or []
        data_rows = sheet.get("数据") or []

        item_dict_raw = sheet.get("项目字典") or {}
        item_dict = {str(v).strip(): str(k).strip() for k, v in item_dict_raw.items()}

        center_dict_raw = sheet.get("中心字典") or {}
        center_dict = {str(v).strip(): str(k).strip() for k, v in center_dict_raw.items()}

        try:
            unit_idx = columns.index("计量单位")
        except ValueError:
            unit_idx = None

        center_idx: Optional[int] = None
        if "中心" in columns:
            center_idx = columns.index("中心")

        for row in data_rows:
            if not row:
                continue

            item_label = str(row[0]).strip() or "未命名项目"
            unit_label = (
                str(row[unit_idx]).strip() if unit_idx is not None and unit_idx < len(row) else ""
            )

            base_key = item_dict.get(item_label) or slugify(item_label)
            item_key = base_key.lower()
            item_cn = item_label

            if center_idx is not None and center_idx < len(row):
                center_name = str(row[center_idx]).strip()
                if center_name:
                    center_key = center_dict.get(center_name) or slugify(center_name)
                    item_key = f"{item_key}_{center_key.lower()}"
                    item_cn = f"{item_label}（{center_name}）"

            sequence += 1
            yield TemplateRow(
                company=company,
                company_cn=company_cn,
                sheet_key=sheet_name_en,
                item_key=item_key,
                item_cn=item_cn,
                unit=unit_label,
                sequence=sequence,
            )


def generate_value(sequence: int, day_offset: int, scale: Decimal) -> Decimal:
    base = Decimal(sequence * 10)
    increment = Decimal(day_offset * 3)
    value = (base + increment) * scale
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def peer_of(target: date) -> date:
    try:
        return target.replace(year=target.year - 1)
    except ValueError:
        # handle leap year 2/29
        return target.replace(month=2, day=28, year=target.year - 1)


def build_records(rows: Iterable[TemplateRow]) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []

    for row in rows:
        for idx, biz_date in enumerate(TARGET_DATES):
            value_current = generate_value(row.sequence, idx, Decimal("1.00"))
            records.append(
                {
                    "company": row.company,
                    "company_cn": row.company_cn,
                    "sheet_name": row.sheet_key,
                    "item": row.item_key,
                    "item_cn": row.item_cn,
                    "unit": row.unit,
                    "value": value_current,
                    "note": "",
                    "status": "sample",
                    "date": biz_date.isoformat(),
                }
            )

            peer_date = peer_of(biz_date)
            value_peer = generate_value(row.sequence, idx, Decimal("0.92"))
            records.append(
                {
                    "company": row.company,
                    "company_cn": row.company_cn,
                    "sheet_name": row.sheet_key,
                    "item": row.item_key,
                    "item_cn": row.item_cn,
                    "unit": row.unit,
                    "value": value_peer,
                    "note": "",
                    "status": "sample_peer",
                    "date": peer_date.isoformat(),
                }
            )

    return records


def write_csv(records: List[Dict[str, object]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company",
        "company_cn",
        "sheet_name",
        "item",
        "item_cn",
        "unit",
        "value",
        "date",
        "note",
        "status",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def sql_literal(text: str) -> str:
    return text.replace("'", "''")


def write_sql(records: List[Dict[str, object]]) -> None:
    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    header = """-- 自动生成的示例数据
-- 导入方式：
--   psql -U <user> -d phoenix -f backend/sql/sample_daily_basic_data.sql

"""
    with OUTPUT_SQL.open("w", encoding="utf-8") as fp:
        fp.write(header)
        for record in records:
            note_literal = "NULL" if not record["note"] else f"'{sql_literal(record['note'])}'"
            fp.write(
                f"INSERT INTO {TABLE_NAME} "
                "(company, company_cn, sheet_name, item, item_cn, unit, value, note, status, date)\n"
                f"VALUES ('{sql_literal(record['company'])}', "
                f"'{sql_literal(record['company_cn'])}', "
                f"'{sql_literal(record['sheet_name'])}', "
                f"'{sql_literal(record['item'])}', "
                f"'{sql_literal(record['item_cn'])}', "
                f"'{sql_literal(record['unit'])}', "
                f"{record['value']}, "
                f"{note_literal}, "
                f"'{sql_literal(record['status'])}', "
                f"'{record['date']}');\n\n"
            )


def main() -> None:
    templates = load_templates()
    rows = list(iterate_template_rows(templates))
    records = build_records(rows)
    write_csv(records)
    write_sql(records)
    print(f"生成记录 {len(records)} 条")
    print(f"- CSV: {OUTPUT_CSV}")
    print(f"- SQL: {OUTPUT_SQL}")


if __name__ == "__main__":
    main()
