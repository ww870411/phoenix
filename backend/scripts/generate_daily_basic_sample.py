#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据模板数据自动生成 daily_basic_data 示例数据。

生成内容：
1. backend/sql/sample_daily_basic_data.csv
2. backend/sql/sample_daily_basic_data.sql

日期范围：
- 本期：2025-10-21 ～ 2025-10-25
- 同期：对应上一年同日（2024-10-21 ～ 2024-10-25）

用法：
    python backend/scripts/generate_daily_basic_sample.py
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
DATA_FILE = ROOT_DIR / "backend_data" / "数据结构_基本指标表.json"
OUTPUT_CSV = BACKEND_DIR / "sql" / "sample_daily_basic_data.csv"
OUTPUT_SQL = BACKEND_DIR / "sql" / "sample_daily_basic_data.sql"

TARGET_DATES = [date(2025, 10, 21) + timedelta(days=i) for i in range(5)]


@dataclass
class SheetRow:
    company: str
    company_cn: str
    sheet_name: str
    item: str
    item_cn: str
    unit: str
    sequence: int  # 用于生成基准数值


def load_templates() -> Dict[str, dict]:
    raw = DATA_FILE.read_text(encoding="utf-8")
    data = json.loads(raw)
    return data


def slugify(text: str) -> str:
    cleaned = []
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch.lower())
        elif ch in ("-", "_"):
            cleaned.append("_")
        else:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    return slug or "item"


def iterate_sheet_rows(templates: Dict[str, dict]) -> Iterable[SheetRow]:
    sequence = 0
    for sheet_key, sheet in templates.items():
        if sheet.get("类型") == "crosstab":
            continue  # 跳过煤炭库存等交叉表

        company = sheet.get("单位标识") or sheet.get("单位ID") or sheet_key
        company_cn = sheet.get("单位名") or sheet.get("单位名称") or company
        sheet_name = sheet.get("表名") or sheet_key
        columns = sheet.get("列名") or []
        data_rows = sheet.get("数据") or []

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
            unit_label = str(row[unit_idx]).strip() if unit_idx is not None and unit_idx < len(row) else ""

            item_cn = item_label
            item_key = slugify(item_label)

            if center_idx is not None and center_idx < len(row):
                center_name = str(row[center_idx]).strip()
                item_cn = f"{item_label}（{center_name}）"
                item_key = slugify(f"{item_label}_{center_name}")

            sequence += 1
            yield SheetRow(
                company=company,
                company_cn=company_cn,
                sheet_name=sheet_name,
                item=item_key,
                item_cn=item_cn,
                unit=unit_label,
                sequence=sequence,
            )


def generate_value(base_sequence: int, day_offset: int, scale: Decimal = Decimal("1.0")) -> Decimal:
    base = Decimal(base_sequence * 10)
    increment = Decimal(day_offset * 3)
    value = (base + increment) * scale
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def peer_of(target: date) -> date:
    try:
        return target.replace(year=target.year - 1)
    except ValueError:
        # 处理闰年 2 月 29 日
        return target.replace(month=2, day=28, year=target.year - 1)


def build_records(rows: Iterable[SheetRow]) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []

    for row in rows:
        for idx, biz_dt in enumerate(TARGET_DATES):
            value = generate_value(row.sequence, idx, Decimal("1.00"))
            records.append(
                {
                    "company": row.company,
                    "company_cn": row.company_cn,
                    "sheet_name": row.sheet_name,
                    "item": row.item,
                    "item_cn": row.item_cn,
                    "unit": row.unit,
                    "value": value,
                    "note": "",
                    "status": "sample",
                    "date": biz_dt.isoformat(),
                }
            )

            peer_dt = peer_of(biz_dt)
            peer_value = generate_value(row.sequence, idx, Decimal("0.92"))
            records.append(
                {
                    "company": row.company,
                    "company_cn": row.company_cn,
                    "sheet_name": row.sheet_name,
                    "item": f"{row.item}_peer",
                    "item_cn": f"{row.item_cn}（同期）",
                    "unit": row.unit,
                    "value": peer_value,
                    "note": "",
                    "status": "sample_peer",
                    "date": peer_dt.isoformat(),
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
            fp.write(
                "INSERT INTO daily_basic_data "
                "(company, company_cn, sheet_name, item, item_cn, unit, value, note, status, date)\n"
                f"VALUES ('{sql_literal(record['company'])}', "
                f"'{sql_literal(record['company_cn'])}', "
                f"'{sql_literal(record['sheet_name'])}', "
                f"'{sql_literal(record['item'])}', "
                f"'{sql_literal(record['item_cn'])}', "
                f"'{sql_literal(record['unit'])}', "
                f"{record['value']}, "
                f"{'NULL' if not record['note'] else "'" + sql_literal(record['note']) + "'"}, "
                f"'{sql_literal(record['status'])}', "
                f"'{record['date']}');\n\n"
            )


def main() -> None:
    templates = load_templates()
    rows = list(iterate_sheet_rows(templates))
    records = build_records(rows)
    write_csv(records)
    write_sql(records)
    print(f"生成记录 {len(records)} 条")
    print(f"- CSV: {OUTPUT_CSV}")
    print(f"- SQL: {OUTPUT_SQL}")


if __name__ == "__main__":
    main()
