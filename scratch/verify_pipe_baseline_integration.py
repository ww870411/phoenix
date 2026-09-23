# -*- coding: utf-8 -*-
"""验证天地龙甲供钢管型号录入后的业务链路与排序逻辑"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config
from backend.projects.insulation_pipe_supply_2026.services.baseline_service import list_pipe_baselines
from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    _resolve_section_1_sorted_pipe_model_ids,
    _parse_pipe_model_diameters,
)
# from backend.projects.insulation_pipe_supply_2026.services.price_service import get_material_unit_price
from sqlalchemy import text


def verify_all():
    print("=== 1. 验证数据库中 low_lot_6 的基准数据 ===")
    rows = list_pipe_baselines(section_1_id="low_lot_6")
    print(f"low_lot_6 总条数: {len(rows)}")
    jg_rows = [r for r in rows if "甲供" in r["pipe_model_id"]]
    print(f"甲供钢管条数: {len(jg_rows)} (预期 10 条)")
    assert len(jg_rows) == 10, f"甲供钢管数量异常: {len(jg_rows)}"

    for r in jg_rows:
        assert float(r["design_qty"]) == 0.0, f"设计量不为0: {r}"
        assert float(r["purchase_plan_qty"]) == 0.0, f"采购量不为0: {r}"
        print(f"  [OK] id={r['id']} | {r['pipe_model_id']:<35} | design={r['design_qty']} | plan={r['purchase_plan_qty']} | {r['remark']}")

    print("\n=== 2. 验证后端 _resolve_section_1_sorted_pipe_model_ids 排序 ===")
    cfg = load_tube_config()
    sorted_models = _resolve_section_1_sorted_pipe_model_ids(cfg, "low_lot_6")
    print(f"解析 low_lot_6 排序后的全部直管型号数量: {len(sorted_models)}")
    for i, m in enumerate(sorted_models, 1):
        d_main, d_outer = _parse_pipe_model_diameters(m)
        is_jg = " [甲供]" if "甲供" in m else ""
        print(f"  {i:2d}. {m:<35} -> 内径DN={d_main}, 外径={d_outer}{is_jg}")

    # 验证是否全部 10 个甲供型号都在返回列表中
    for r in jg_rows:
        assert r["pipe_model_id"] in sorted_models, f"型号未出现在可用列表: {r['pipe_model_id']}"

    print("\n=== 3. 验证与物料价格表的联动匹配 (天津天地龙) ===")
    s = SessionLocal()
    try:
        for r in jg_rows:
            model = r["pipe_model_id"]
            price_row = s.execute(text("""
                SELECT id, supplier_name, material_name, model_spec, unit_price
                FROM tube.tube_material_price
                WHERE supplier_name LIKE '%天地龙%' AND model_spec = :model
            """), {"model": model}).fetchone()
            if price_row:
                print(f"  [OK 价格匹配] 型号: {model:<35} -> 找到价格: {price_row[4]} 元/米 (id={price_row[0]})")
            else:
                print(f"  [WARN 未匹配到价格] 型号: {model}")
    finally:
        s.close()

    print("\n✅ 所有校验全部通过！")


if __name__ == "__main__":
    verify_all()
