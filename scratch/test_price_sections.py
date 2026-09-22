# -*- coding: utf-8 -*-
"""
测试 price_service.py 的标段筛选与返回字段。
"""
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.services.price_service import list_material_prices


def main():
    print("🧪 测试 list_material_prices...")
    # 1. 全量查询
    all_prices = list_material_prices()
    print(f"全量记录数: {len(all_prices)}")
    sample = all_prices[0]
    print(f"首条记录包含标段字段: applicable_sections={sample.get('applicable_sections')}, section_name_scope={sample.get('section_name_scope')}")

    # 2. 开元专属查询
    kaiyuan_prices = list_material_prices(supplier_name="开元")
    print(f"开元记录数: {len(kaiyuan_prices)}")
    for kp in kaiyuan_prices[:3]:
        print(f"  - 规格: {kp['model_spec']}, 标段: {kp['applicable_sections']} ({kp['section_name_scope']})")

    # 3. 按标段筛选: high_lot_1 (开元 1、2 标段 + 其他通用)
    lot1_prices = list_material_prices(section_1_id="high_lot_1")
    kaiyuan_in_lot1 = [p for p in lot1_prices if "开元" in p["supplier_name"]]
    print(f"high_lot_1 适用记录数: {len(lot1_prices)}, 其中包含开元条数: {len(kaiyuan_in_lot1)} (预期 79)")
    assert len(kaiyuan_in_lot1) == 79, f"预期 79，实际 {len(kaiyuan_in_lot1)}"

    # 4. 按标段筛选: high_lot_3 (开元 3、4 标段 + 其他通用)
    lot3_prices = list_material_prices(section_1_id="high_lot_3")
    kaiyuan_in_lot3 = [p for p in lot3_prices if "开元" in p["supplier_name"]]
    print(f"high_lot_3 适用记录数: {len(lot3_prices)}, 其中包含开元条数: {len(kaiyuan_in_lot3)} (预期 140)")
    assert len(kaiyuan_in_lot3) == 140, f"预期 140，实际 {len(kaiyuan_in_lot3)}"

    # 5. 精确按 applicable_sections 筛选
    specific_12 = list_material_prices(applicable_sections="high_lot_1,high_lot_2")
    specific_34 = list_material_prices(applicable_sections="high_lot_3,high_lot_4")
    print(f"applicable_sections='high_lot_1,high_lot_2' 记录数: {len(specific_12)} (预期 79)")
    print(f"applicable_sections='high_lot_3,high_lot_4' 记录数: {len(specific_34)} (预期 140)")
    assert len(specific_12) == 79
    assert len(specific_34) == 140

    print("🎉 所有 price_service 测试用例 100% 通过！")


if __name__ == "__main__":
    main()
