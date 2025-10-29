#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从「最新模板」自动生成 daily_basic_data 示例数据（本期+同期）。

输出文件：
- backend/sql/sample_daily_basic_data.csv
- backend/sql/sample_daily_basic_data.sql

日期范围（含首尾）：
- 2025-10-20 ~ 2025-10-27，共 8 天

关键适配点：
- 读取模板：configs/数据结构_基本指标表.json
- 扁平化分中心交叉表（GongRe_branches_detail_sheet）：按“中心列”展开为 company/company_cn
- 文本型单元（单位为 '-' 或特定项目）写入到 note，value 置为 NULL
- 插入表名修正：daily_basic_data（小写）
- 命名修正：中心英文码统一 *_Center；sheet 名统一 *_Sheet（S 大写）
- 数值关系：本期值 = 同期值 × 1.25（较同期提高 25%）
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, DefaultDict
from collections import defaultdict

# 路径与常量
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
# 唯一权威模板来源：backend_data/数据结构_基本指标表.json
TEMPLATE_FILE = ROOT_DIR / "backend_data" / "数据结构_基本指标表.json"
# 单位字典（权威来源）：英文码→中文名（含公司与中心）
UNITS_DICT_FILE = ROOT_DIR / "configs" / "单位字典.json"
# 项目字典（权威来源，用于 item 英文键）：按 sheet 维度定义（与 TEMPLATE_FILE 同源）
BACKEND_DATA_TEMPLATE_FILE = TEMPLATE_FILE
OUTPUT_CSV = BACKEND_DIR / "sql" / "sample_daily_basic_data.csv"
OUTPUT_SQL = BACKEND_DIR / "sql" / "sample_daily_basic_data.sql"
TABLE_NAME = "daily_basic_data"

# 目标日期：2025-10-20 ~ 2025-10-27（含首尾）
TARGET_DATES: List[date] = [date(2025, 10, 20) + timedelta(days=i) for i in range(8)]


@dataclass
class TemplateRow:
    """模板扁平后的单行描述（用于生成 daily_basic_data 记录）"""

    company: str
    company_cn: str
    sheet_key: str
    item_key: str
    item_cn: str
    unit: str
    sequence: int
    is_child: bool = False
    group_id: int = 0


def load_templates() -> Dict[str, dict]:
    """读取基础指标模板（JSON）。"""
    raw = TEMPLATE_FILE.read_text(encoding="utf-8")
    return json.loads(raw)


def load_units_dict() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    读取单位字典（权威）：configs/单位字典.json
    结构示例：
    {
      "单位字典": {
        "BeiHai": "北海热电厂",
        "DongGang_Center": "东港中心",
        ...
      }
    }
    返回：
      company_en_to_cn, center_en_to_cn, company_cn_to_en, center_cn_to_en
    判定规则：以键名是否以 '_Center' 结尾区分中心；其余视为公司。
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
    # 反向映射（中文→英文）
    company_cn_to_en = {v: k for k, v in company_en_to_cn.items()}
    center_cn_to_en = {v: k for k, v in center_en_to_cn.items()}
    return company_en_to_cn, center_en_to_cn, company_cn_to_en, center_cn_to_en


def load_item_dict_index() -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """
    从 backend_data/数据结构_基本指标表.json 读取每个表的“项目字典”，
    返回两个映射：
      - cn2en_index：sheet_key_lower -> { 项目中文 -> 项目英文key }
      - en2cn_index：sheet_key_lower -> { 项目英文key -> 项目中文 }
    """
    cn2en_index: Dict[str, Dict[str, str]] = {}
    en2cn_index: Dict[str, Dict[str, str]] = {}
    if not BACKEND_DATA_TEMPLATE_FILE.exists():
        return cn2en_index, en2cn_index
    data = json.loads(BACKEND_DATA_TEMPLATE_FILE.read_text(encoding="utf-8"))
    for sheet_key, sheet in data.items():
        item_dict = sheet.get("项目字典") or {}
        if isinstance(item_dict, dict):
            # en->cn 原字典，反转出 中文->英文
            en_to_cn = {str(k).strip(): str(v).strip() for k, v in item_dict.items()}
            cn_to_en = {v: k for k, v in en_to_cn.items()}
            key = str(sheet_key).lower()
            cn2en_index[key] = cn_to_en
            en2cn_index[key] = en_to_cn
    return cn2en_index, en2cn_index


def slugify(text: str) -> str:
    """将任意文本转为下划线 key。"""
    cleaned = []
    for ch in text.strip():
        if ch.isalnum():
            cleaned.append(ch.lower())
        elif ch in ("-", "_", " "):
            cleaned.append("_")
        else:
            cleaned.append("_")
    slug = "_".join(filter(bool, "".join(cleaned).split("_")))
    return slug or "item"


def _normalize_center_code(code: str) -> str:
    """
    规范化中心英文标识为 *_Center（末尾 Center 大写；修复历史 *_center 大小写问题）：
    - DongGang_Center -> DongGang_Center
    - DongGang_center -> DongGang_Center
    - 若不含下划线 center/Center，则追加 _Center
    """
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


def _derive_company_code_from_sheet(sheet_key: str) -> str:
    """
    从 sheet_key 前缀推导单位英文码（示例：
    - BeiHai_co_generation_sheet -> BeiHai
    - XiangHai_sheet -> XiangHai
    - GongRe_sheet -> GongRe
    - BeiFang_sheet -> BeiFang
    - JinZhou_sheet -> JinZhou
    ）若未命中，则回退整体 slug。
    """
    if not sheet_key:
        return "company"
    prefix = sheet_key.split("_", 1)[0]
    return prefix if prefix else slugify(sheet_key)


def _normalize_sheet_name(name: str) -> str:
    """将 xxx_sheet 统一为 xxx_Sheet（仅尾缀大小写修正）。"""
    if not isinstance(name, str):
        return name
    if name.endswith("_Sheet"):
        return name
    if name.endswith("_sheet"):
        return name[:-6] + "_Sheet"
    return name


def _is_text_cell(item_cn: str, unit: str) -> bool:
    """判断该项目属于文本型（写入 note）。"""
    if (unit or "").strip() in {"-", "—", "–"}:
        return True
    return item_cn in {"主设备启停情况", "突发情况说明"}


def _resolve_item_key(sheet_key: str, item_label: str, cn2en_index: Dict[str, Dict[str, str]], en2cn_index: Dict[str, Dict[str, str]]) -> Tuple[str, str]:
    """
    严格按照 backend_data 的“项目字典”生成 item_key 与 item_cn（权威，不做猜测）。
    返回：item_key(英文小写), item_cn(权威中文)
    """
    raw_cn = str(item_label).strip() or "未命名项目"
    sheet_lower = str(sheet_key).lower()
    dict_cn_map = cn2en_index.get(sheet_lower) or {}
    dict_en_map = en2cn_index.get(sheet_lower) or {}
    # 严格匹配：只允许“完全相等”的中文在项目字典中找到英文键
    if raw_cn not in dict_cn_map:
        available = ", ".join(list(dict_cn_map.keys())[:30])
        raise ValueError(
            f"项目字典缺少中文项: sheet={sheet_key}, label={raw_cn}; 可用中文项前30个: [{available}]"
        )
    base_key = dict_cn_map[raw_cn]
    official_cn = dict_en_map.get(base_key, raw_cn)
    return base_key.lower(), official_cn or raw_cn


def iterate_template_rows(templates: Dict[str, dict]) -> Iterable[TemplateRow]:
    """
    遍历模板，输出标准化行：
    - 标准表：company=单位标识(或 sheet_key)、company_cn=单位名
    - 分中心交叉表（GongRe_branches_detail_sheet）：按列头中心拆分 company/company_cn
    """
    sequence = 0
    company_en_to_cn, center_en_to_cn, company_cn_to_en, center_cn_to_en = load_units_dict()
    cn2en_index, en2cn_index = load_item_dict_index()

    for sheet_key, sheet in templates.items():
        # 统一字段提取
        unit_name = sheet.get("单位名") or sheet.get("单位名称") or ""
        company_en = sheet.get("单位标识") or sheet_key
        columns = list(sheet.get("列名") or [])
        data_rows = list(sheet.get("数据") or [])

        # 跳过“煤炭库存”交叉表（该表属于 coal_inventory_data，不在 daily_basic_data 范畴）
        if str(sheet_key) == "Coal_inventory_Sheet" or str(sheet.get("类型") or "").lower() == "crosstab":
            continue

        # 取计量单位列索引
        try:
            unit_idx = columns.index("计量单位")
        except ValueError:
            unit_idx = None

        # 分中心交叉表：按 sheet_key 精确识别并展开
        if str(sheet_key).lower() == "gongre_branches_detail_sheet":
            # 中心列从第 3 列（索引 2）开始
            center_names = [str(x).strip() for x in columns[2:]]
            current_group = 0
            for row in data_rows:
                if not row:
                    continue
                item_label = str(row[0]).strip() or "未命名项目"
                unit_label = str(row[1]).strip() if unit_idx is not None and unit_idx < len(row) else ""
                item_key, item_cn = _resolve_item_key(sheet_key, item_label, cn2en_index, en2cn_index)
                is_child = item_label.startswith("其中")
                if not is_child:
                    current_group += 1

                for center_cn in center_names:
                    if not center_cn:
                        continue
                    # 中文中心名 → 英文码（来自单位字典），再规范 *_center
                    company_cn = center_cn
                    mapped_en = center_cn_to_en.get(center_cn) or ""
                    company = _normalize_center_code(mapped_en) if mapped_en else _normalize_center_code(slugify(center_cn))
                    sequence += 1
                    yield TemplateRow(
                        company=company,
                        company_cn=company_cn,
                        sheet_key=sheet_key,
                        item_key=item_key,
                        item_cn=item_cn,
                        unit=unit_label,
                        sequence=sequence,
                        is_child=is_child,
                        group_id=current_group,
                    )
            continue

        # 标准表：逐行输出
        current_group = 0
        for row in data_rows:
            if not row:
                continue
            item_label = str(row[0]).strip() or "未命名项目"
            unit_label = str(row[unit_idx]).strip() if unit_idx is not None and unit_idx < len(row) else ""
            item_key, item_cn = _resolve_item_key(sheet_key, item_label, cn2en_index, en2cn_index)
            is_child = item_label.startswith("其中")
            if not is_child:
                current_group += 1

            # 公司英文码优先来自“中文名匹配单位字典”，否则退化到 sheet 前缀
            derived_code = _derive_company_code_from_sheet(sheet_key)
            company_code = company_cn_to_en.get(unit_name) or derived_code
            company_cn_effective = company_en_to_cn.get(company_code, unit_name or company_en)

            sequence += 1
            yield TemplateRow(
                company=company_code,
                company_cn=company_cn_effective,
                sheet_key=sheet_key,
                item_key=item_key,
                item_cn=item_cn,
                unit=unit_label,
                sequence=sequence,
                is_child=is_child,
                group_id=current_group,
            )


def _gen_numeric_value(sequence: int, day_offset: int, scale: Decimal = Decimal("1.00")) -> Decimal:
    """生成示例用的数值（可重复）。"""
    base = Decimal(sequence * 7)  # 相比旧版略小，便于可视化
    increment = Decimal(day_offset * 2)
    value = (base + increment) * scale
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_records(rows: Iterable[TemplateRow]) -> List[Dict[str, object]]:
    """
    依据模板行构造 CSV/SQL 记录。
    - 同期：2024-10-20 ~ 2024-10-27（与本期日期一一对应）
    - 文本型单元写入 note，value=NULL；
    - 其余写入 value（Numeric），status='sample'/'sample_peer'；
    - “其中：”分组：连续“其中：xxx”之和严格等于最近一个非“其中”的父项（按每个日期分别约束）
    """
    records: List[Dict[str, object]] = []

    # 先按 (company, company_cn, sheet_key) 分桶，保持行顺序用于分组求和
    buckets: DefaultDict[Tuple[str, str, str], List[TemplateRow]] = defaultdict(list)
    for r in rows:
        buckets[(r.company, r.company_cn, r.sheet_key)].append(r)

    peer_dates: List[date] = [date(2024, 10, 20) + timedelta(days=i) for i in range(8)]

    for (company, company_cn, sheet_key), row_list in buckets.items():
        # 针对每个日期单独生成
        for idx, biz_date in enumerate(TARGET_DATES):
            peer_date = peer_dates[idx]

            # 先为所有行准备“基础值”（父项值或非分组值）
            base_values_peer: Dict[int, Optional[Decimal]] = {}
            base_values_biz: Dict[int, Optional[Decimal]] = {}

            for i, row in enumerate(row_list):
                if _is_text_cell(row.item_cn, row.unit):
                    base_values_peer[i] = None
                    base_values_biz[i] = None
                else:
                    peer_val = _gen_numeric_value(row.sequence, idx)
                    base_values_peer[i] = peer_val
                    base_values_biz[i] = (peer_val * Decimal("1.25")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

            # 对“其中”分组进行约束调整：孩子求和 = 父项
            i = 0
            n = len(row_list)
            while i < n:
                row = row_list[i]
                if not row.is_child and i + 1 < n and row_list[i + 1].is_child:
                    # 找到一个父项 + 若干子项的分组
                    parent_idx = i
                    child_start = i + 1
                    j = child_start
                    while j < n and row_list[j].is_child:
                        j += 1
                    child_end = j  # 不含 j
                    child_count = child_end - child_start

                    # 仅在父/子均为数值型时处理；否则跳过
                    if (
                        base_values_biz[parent_idx] is not None
                        and all(base_values_biz[k] is not None for k in range(child_start, child_end))
                    ):
                        def _distribute(total: Decimal) -> List[Decimal]:
                            # 确定性权重（与 parent sequence、子序号相关）
                            weights = [
                                Decimal((row_list[parent_idx].sequence % 3) + (c + 1))
                                for c in range(child_count)
                            ]
                            sum_w = sum(weights)
                            parts_raw = [(total * w / sum_w) for w in weights]
                            parts = [p.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for p in parts_raw[:-1]]
                            last = (total - sum(parts)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                            # 防止出现负数（极端四舍五入导致），最低归零
                            if last < Decimal("0.00"):
                                last = Decimal("0.00")
                            return parts + [last]

                        # 本期
                        parts_biz = _distribute(base_values_biz[parent_idx])
                        for off, k in enumerate(range(child_start, child_end)):
                            base_values_biz[k] = parts_biz[off]
                        # 同期
                        parts_peer = _distribute(base_values_peer[parent_idx])
                        for off, k in enumerate(range(child_start, child_end)):
                            base_values_peer[k] = parts_peer[off]

                    i = child_end
                else:
                    i += 1

            # 写出本期 + 同期记录
            for i, row in enumerate(row_list):
                sheet_name_norm = _normalize_sheet_name(sheet_key)
                # 本期
                if base_values_biz[i] is None:
                    records.append(
                        {
                            "company": company,
                            "company_cn": company_cn,
                            "sheet_name": sheet_name_norm,
                            "item": row.item_key,
                            "item_cn": row.item_cn,
                            "unit": row.unit,
                            "value": None,
                            "note": f"示例：{row.item_cn}（本期 第{idx + 1}天）",
                            "status": "sample_text",
                            "date": biz_date.isoformat(),
                        }
                    )
                else:
                    records.append(
                        {
                            "company": company,
                            "company_cn": company_cn,
                            "sheet_name": sheet_name_norm,
                            "item": row.item_key,
                            "item_cn": row.item_cn,
                            "unit": row.unit,
                            "value": base_values_biz[i],
                            "note": "",
                            "status": "sample",
                            "date": biz_date.isoformat(),
                        }
                    )

                # 同期
                if base_values_peer[i] is None:
                    records.append(
                        {
                            "company": company,
                            "company_cn": company_cn,
                            "sheet_name": sheet_name_norm,
                            "item": row.item_key,
                            "item_cn": row.item_cn,
                            "unit": row.unit,
                            "value": None,
                            "note": f"示例：{row.item_cn}（同期 第{idx + 1}天）",
                            "status": "sample_text_peer",
                            "date": peer_date.isoformat(),
                        }
                    )
                else:
                    records.append(
                        {
                            "company": company,
                            "company_cn": company_cn,
                            "sheet_name": sheet_name_norm,
                            "item": row.item_key,
                            "item_cn": row.item_cn,
                            "unit": row.unit,
                            "value": base_values_peer[i],
                            "note": "",
                            "status": "sample_peer",
                            "date": peer_date.isoformat(),
                        }
                    )

    return records


def write_csv(records: List[Dict[str, object]]) -> None:
    """输出 CSV 文件。"""
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
    """输出 SQL 插入脚本（可重复执行）。"""
    OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    header = """-- 自动生成的示例数据（本期+同期 2025-10-20 ~ 2025-10-27，规则：本期=同期×1.25）
-- 导入方式（容器内）：
--   psql -U postgres -d phoenix -f /app/sql/sample_daily_basic_data.sql

"""
    with OUTPUT_SQL.open("w", encoding="utf-8") as fp:
        fp.write(header)
        for record in records:
            note_literal = "NULL" if not record["note"] else f"'{sql_literal(record['note'])}'"
            value_literal = "NULL" if record["value"] is None else str(record["value"])
            fp.write(
                f"INSERT INTO {TABLE_NAME} "
                "(company, company_cn, sheet_name, item, item_cn, unit, value, note, status, date)\n"
                f"VALUES ('{sql_literal(record['company'])}', "
                f"'{sql_literal(record['company_cn'])}', "
                f"'{sql_literal(record['sheet_name'])}', "
                f"'{sql_literal(record['item'])}', "
                f"'{sql_literal(record['item_cn'])}', "
                f"'{sql_literal(record['unit'])}', "
                f"{value_literal}, "
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
