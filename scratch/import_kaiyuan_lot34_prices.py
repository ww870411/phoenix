# -*- coding: utf-8 -*-
"""
执行开元新增高温水3、4标段保温管与管件单价数据导入与核验。
"""
import os
import sys
from decimal import Decimal
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.price_service import (
    ensure_price_table,
    import_kaiyuan_lot34_prices,
    list_material_prices,
)

EXCEL_PATH = os.path.join(project_root, "configs", "9.22 导入_开元新增高温水3、4标段保温管、管件.xlsx")


def main():
    print(f"🚀 开始执行开元高温水3、4标段单价导入...")
    ensure_price_table()

    session = SessionLocal()
    try:
        # 1. 导入前统计
        cnt_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        kaiyuan_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'kaiyuan';")).scalar() or 0
        print(f"📊 [导入前统计]")
        print(f"   tube_material_price 全表总行数: {cnt_before}")
        print(f"   开元已有记录数 (高温水1、2标段): {kaiyuan_before}")

        # 2. 执行导入
        res = import_kaiyuan_lot34_prices(EXCEL_PATH, operator="user_import_20260922")
        print(f"\n✅ [导入结果]")
        print(f"   成功导入: {res['total_inserted']} 条记录")
        print(f"   其中保温管: {res['pipe_count']} 条, 管件: {res['fitting_count']} 条")

        # 3. 导入后统计
        cnt_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        kaiyuan_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'kaiyuan';")).scalar() or 0
        print(f"\n🎉 [导入后统计]")
        print(f"   tube_material_price 全表总行数: {cnt_after} (净增 {cnt_after - cnt_before})")
        print(f"   开元总记录数: {kaiyuan_after}")

        # 4. 分组核验
        groups = session.execute(text("""
            SELECT supplier_name, applicable_sections, section_name_scope, material_kind, COUNT(*),
                   MIN(unit_price) as min_p, MAX(unit_price) as max_p, ROUND(AVG(unit_price), 2) as avg_p
            FROM tube.tube_material_price
            GROUP BY supplier_name, applicable_sections, section_name_scope, material_kind
            ORDER BY supplier_name, applicable_sections, material_kind DESC;
        """)).fetchall()

        print("\n📋 各厂家与标段单价分组总览:")
        for g in groups:
            print(f"   - 【{g[0]}】标段: {g[1]} ({g[2]}) | 大类: {g[3]} | 条数: {g[4]} | 单价区间: {g[5]} ~ {g[6]} 元 (均价: {g[7]} 元)")

        # 5. 验证开元1、2标段 vs 3、4标段同型号价格差异
        diff_specs = session.execute(text("""
            SELECT p1.model_spec, p1.unit_price as price_12, p2.unit_price as price_34, (p2.unit_price - p1.unit_price) as diff
            FROM tube.tube_material_price p1
            JOIN tube.tube_material_price p2 
              ON p1.supply_entity_id = p2.supply_entity_id 
             AND p1.model_spec = p2.model_spec
            WHERE p1.supply_entity_id = 'kaiyuan'
              AND p1.applicable_sections = 'high_lot_1,high_lot_2'
              AND p2.applicable_sections = 'high_lot_3,high_lot_4'
            ORDER BY p1.material_kind DESC, p1.category, p1.model_spec;
        """)).fetchall()

        print(f"\n🔍 开元同规格型号在【1、2标段】与【3、4标段】价格对比（共 {len(diff_specs)} 项交集规格）:")
        for ds in diff_specs[:10]:
            diff_sign = f"+{ds[3]}" if ds[3] > 0 else f"{ds[3]}"
            print(f"   - 规格: {ds[0]} | 1、2标段: ¥{ds[1]} | 3、4标段: ¥{ds[2]} (差额: {diff_sign} 元)")

    finally:
        session.close()


if __name__ == "__main__":
    main()
