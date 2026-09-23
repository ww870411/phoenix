# -*- coding: utf-8 -*-
"""
从 configs/9.22_导入_天津天地龙管业.xlsx 提取带“（甲供钢管）”的保温管型号，
作为 low_lot_6 的基准数据录入 PostgreSQL 数据库表 tube.tube_pipe_baseline，
设计量和计划采购量均填 0。
"""

import os
import sys
import openpyxl

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.services.baseline_service import (
    save_pipe_baselines,
    list_pipe_baselines,
)


def extract_and_import():
    excel_path = os.path.abspath(os.path.join(project_root, "configs", "9.22_导入_天津天地龙管业.xlsx"))
    print(f"1. 正在读取 Excel 文件: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"找不到文件: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb["标准化价格表"]

    items_to_import = []
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if idx == 1:
            continue
        spec = str(row[3] or "").strip()
        unit = str(row[4] or "米").strip()
        remark_raw = str(row[7] or "").strip() if row[7] is not None else ""

        if "（甲供钢管）" in spec or "甲供钢管" in spec:
            items_to_import.append({
                "section_1_id": "low_lot_6",
                "pipe_model_id": spec,
                "unit": unit or "米",
                "design_qty": 0.0,
                "purchase_plan_qty": 0.0,
                "remark": remark_raw or "天津天地龙管业甲供钢管供货规格补录",
            })

    print(f"2. 提取到符合条件的甲供钢管型号记录数: {len(items_to_import)}")
    for i, it in enumerate(items_to_import, 1):
        print(f"   [{i}] 型号: {it['pipe_model_id']:<35} 设计量: {it['design_qty']} 采购量: {it['purchase_plan_qty']}")

    print("\n3. 开始执行幂等入库写入 tube.tube_pipe_baseline 表...")
    saved_count = save_pipe_baselines(
        items=items_to_import,
        operator_name="tiandilong_jiagong_import",
    )
    print(f"   成功保存/更新记录数: {saved_count} 条")

    print("\n4. 查询核验 low_lot_6 当前全部直管基准记录...")
    all_low_lot_6 = list_pipe_baselines(section_1_id="low_lot_6")
    print(f"   low_lot_6 当前总基准型号数: {len(all_low_lot_6)} 条")
    for r in all_low_lot_6:
        tag = "【本次新增甲供】" if "甲供" in r["pipe_model_id"] else "【常规直管】"
        print(f"   {tag} {r['pipe_model_id']:<35} 单位:{r['unit']} 设计量:{r['design_qty']} 采购量:{r['purchase_plan_qty']}")

    return items_to_import


if __name__ == "__main__":
    extract_and_import()
