#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从「常量模板」自动生成 constant_data 示例数据（本供暖期+同供暖期）。

输出文件：
- backend/sql/sample_constant_data.csv
- backend/sql/sample_constant_data.sql

口径与规则：
- period 使用供暖期编码：本供暖期='25-26'，同供暖期='24-25'
- 数值关系：本期值 = 同期值 × 0.8（较同期下降 20%）
- 命名修正：中心英文码统一 *_Center；sheet 名统一 *_Sheet（S 大写）

模板来源：
- backend_data/数据结构_常量指标表.json
- configs/单位字典.json（映射单位/中心中英文字典）
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# 路径
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
TEMPLATE_FILE = ROOT_DIR / "backend_data" / "数据结构_常量指标表.json"
UNITS_DICT_FILE = ROOT_DIR / "configs" / "单位字典.json"
OUTPUT_CSV = BACKEND_DIR / "sql" / "sample_constant_data.csv"
OUTPUT_SQL = BACKEND_DIR / "sql" / "sample_constant_data.sql"
TABLE_NAME = "constant_data"

PERIOD_BIZ = "25-26"
PERIOD_PEER = "24-25"

def ascii_slugify(text: str) -> str:
    s = []
    for ch in text.strip():
        o = ord(ch)
        if 48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122:
            s.append(ch.lower())
        elif ch in ("-", "_", " "):
            s.append("_")
        else:
            s.append("_")
    slug = "_".join(filter(bool, "".join(s).split("_")))
    return slug or "item"


def sql_literal(text: str) -> str:
    return text.replace("'", "''")


def _normalize_center_code(code: str) -> str:
    """统一中心英文码为 *_Center。"""
    if not code:
        return code
    if code.endswith("_Center"):
        return code
    if code.endswith("_center"):
        return code[:-7] + "_Center"
    if code.endswith("Center"):
        return code
    if code.endswith("center"):
        return code[:-6] + "Center"
    return code + "_Center"


def _normalize_sheet_name(name: str) -> str:
    """将 xxx_sheet 统一为 xxx_Sheet（仅尾缀大小写修正）。"""
    if not isinstance(name, str):
        return name
    if name.endswith("_Sheet"):
        return name
    if name.endswith("_sheet"):
        return name[:-6] + "_Sheet"
    return name


def _gen_numeric_value(seed: int, scale: Decimal = Decimal("1.00")) -> Decimal:
    """确定性示例数值生成（常量不需要按日期波动）。"""
    base = Decimal(seed * 9 + 13)
    value = (base * scale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value


def load_units_dict() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    返回：company_en_to_cn, center_en_to_cn
    """
    company_en_to_cn: Dict[str, str] = {}
    center_en_to_cn: Dict[str, str] = {}
    if UNITS_DICT_FILE.exists():
        data = json.loads(UNITS_DICT_FILE.read_text(encoding="utf-8"))
        mapping = data.get("单位字典") or {}
        for en, cn in mapping.items():
            if isinstance(en, str) and isinstance(cn, str):
                if en.endswith("_Center"):
                    center_en_to_cn[en] = cn
                else:
                    company_en_to_cn[en] = cn
    return company_en_to_cn, center_en_to_cn


def load_constant_template() -> Dict[str, dict]:
    raw = TEMPLATE_FILE.read_text(encoding="utf-8")
    return json.loads(raw)


@dataclass
class ConstRow:
    company: str
    company_cn: str
    center: Optional[str]
    center_cn: Optional[str]
    sheet_key: str
    item_key: str
    item_cn: str
    unit: str
    seq: int


def iterate_rows() -> Iterable[ConstRow]:
    tpls = load_constant_template()
    company_en_to_cn, center_en_to_cn = load_units_dict()
    seq = 0

    for sheet_key, sheet in tpls.items():
        unit_name = sheet.get("单位名") or sheet.get("单位名称") or ""
        company_en = sheet.get("单位标识") or ""
        columns = list(sheet.get("列名") or [])
        data_rows = list(sheet.get("数据") or [])

        # 项目字典：英文→中文，便于反查
        item_dict_raw = sheet.get("项目字典") or {}
        item_cn_by_en = {k.strip(): str(v).strip() for k, v in item_dict_raw.items()}
        # 反向：中文→英文，支撑根据行中文名找英文 key
        item_en_by_cn = {v: k for k, v in item_cn_by_en.items()}

        # 是否为“分中心明细常量表”
        is_branch_detail = str(sheet_key).lower().endswith("branches_detail_constant_sheet")

        # 列索引
        unit_idx = None
        center_idx = None
        try:
            unit_idx = columns.index("计量单位")
        except ValueError:
            unit_idx = None
        if is_branch_detail:
            try:
                center_idx = columns.index("中心")
            except ValueError:
                center_idx = 1  # 保底

        # 公司中文
        company_cn = company_en_to_cn.get(company_en, unit_name or company_en or "未命名单位")

        for row in data_rows:
            if not row:
                continue
            raw_cn = str(row[0]).strip()
            item_cn = raw_cn
            unit_label = str(row[unit_idx]).strip() if (unit_idx is not None and unit_idx < len(row)) else ""
            # 严格按项目字典：必须存在中文→英文映射，否则报错（不猜测）
            if raw_cn not in item_en_by_cn:
                available = ", ".join(list(item_en_by_cn.keys())[:30])
                raise ValueError(
                    f"常量项目字典缺少中文项: sheet={sheet_key}, label={raw_cn}; 可用中文项前30个: [{available}]"
                )
            item_key = item_en_by_cn[raw_cn].strip()

            center_en = None
            center_cn = None
            if is_branch_detail:
                center_cn = str(row[center_idx]).strip() if (center_idx is not None and center_idx < len(row)) else ""
                # 先用模板“中心字典”，再回落到全局单位字典
                center_dict = sheet.get("中心字典") or {}
                # 模板中心字典：英→中
                center_en_by_cn_local = {v: k for k, v in center_dict.items()}
                mapped = center_en_by_cn_local.get(center_cn) or next(
                    (en for en, cn2 in center_en_to_cn.items() if cn2 == center_cn), None
                )
                center_en = _normalize_center_code(mapped or center_cn.replace(" ", "_"))

            # 分支：分中心明细常量表 → “中心”作为 company/company_cn；center/center_cn 置空
            if is_branch_detail and center_en:
                eff_company = center_en
                eff_company_cn = center_cn or company_cn
                out_center = None
                out_center_cn = None
            else:
                eff_company = company_en or "company"
                eff_company_cn = company_cn
                out_center = None
                out_center_cn = None

            seq += 1
            yield ConstRow(
                company=eff_company,
                company_cn=eff_company_cn,
                center=out_center,
                center_cn=out_center_cn,
                sheet_key=sheet_key,
                item_key=item_key,
                item_cn=item_cn,
                unit=unit_label,
                seq=seq,
            )


def build_records(rows: Iterable[ConstRow]) -> List[Dict[str, object]]:
    """
    输出两期记录：
    - 同期（period='24-25'）：作为基准值
    - 本期（period='25-26'）：= 同期 × 0.8
    """
    recs: List[Dict[str, object]] = []
    for r in rows:
        # 文本类常量极少，若单位为 '-' 则仅写一条注记并跳过数值
        if (r.unit or "").strip() in {"-", "—", "–"}:
            continue

        peer_val = _gen_numeric_value(r.seq)
        biz_val = (peer_val * Decimal("0.8")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sheet_name = _normalize_sheet_name(r.sheet_key)

        # 同期
        recs.append(
            {
                "company": r.company,
                "company_cn": r.company_cn,
                "center": r.center,
                "center_cn": r.center_cn,
                "sheet_name": sheet_name,
                "item": r.item_key,
                "item_cn": r.item_cn,
                "unit": r.unit,
                "value": str(peer_val),
                "period": PERIOD_PEER,
            }
        )
        # 本期
        recs.append(
            {
                "company": r.company,
                "company_cn": r.company_cn,
                "center": r.center,
                "center_cn": r.center_cn,
                "sheet_name": sheet_name,
                "item": r.item_key,
                "item_cn": r.item_cn,
                "unit": r.unit,
                "value": str(biz_val),
                "period": PERIOD_BIZ,
            }
        )
    return recs


def write_csv(records: List[Dict[str, object]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company",
        "company_cn",
        "center",
        "center_cn",
        "sheet_name",
        "item",
        "item_cn",
        "unit",
        "value",
        "period",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def write_sql(records: List[Dict[str, object]]) -> None:
    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    header = """-- 自动生成的常量示例数据（period: 24-25 同期、25-26 本期；规则：本期=同期×0.8）
-- 导入方式（容器内）：
--   psql -U postgres -d phoenix -f /app/sql/sample_constant_data.sql

"""
    with OUTPUT_SQL.open("w", encoding="utf-8") as fp:
        fp.write(header)
        for r in records:
            center_literal = "NULL" if not r.get("center") else f"'{sql_literal(r['center'])}'"
            center_cn_literal = "NULL" if not r.get("center_cn") else f"'{sql_literal(str(r['center_cn']))}'"
            fp.write(
                f"INSERT INTO {TABLE_NAME} "
                "(company, company_cn, center, center_cn, sheet_name, item, item_cn, unit, value, period)\n"
                f"VALUES ('{sql_literal(r['company'])}', "
                f"'{sql_literal(r['company_cn'])}', "
                f"{center_literal}, "
                f"{center_cn_literal}, "
                f"'{sql_literal(r['sheet_name'])}', "
                f"'{sql_literal(r['item'])}', "
                f"'{sql_literal(r['item_cn'])}', "
                f"'{sql_literal(r['unit'])}', "
                f"{r['value']}, "
                f"'{sql_literal(r['period'])}');\n\n"
            )


def main() -> None:
    rows = list(iterate_rows())
    records = build_records(rows)
    write_csv(records)
    write_sql(records)
    print(f"生成常量记录 {len(records)} 条")
    print(f"- CSV: {OUTPUT_CSV}")
    print(f"- SQL: {OUTPUT_SQL}")


if __name__ == "__main__":
    main()
