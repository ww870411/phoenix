# -*- coding: utf-8 -*-
"""
执行河北泽越球阀采购单价数据（9.28 导入_河北泽越球阀采购价格表.xlsx）导入与全维度核验。
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
    import_zeyue_valve_prices,
    list_material_prices,
)

EXCEL_PATH = os.path.join(project_root, "configs", "9.28 导入_河北泽越球阀采购价格表.xlsx")


def main():
    print("🚀 开始执行河北泽越球阀采购价格表导入...")
    ensure_price_table()

    session = SessionLocal()
    try:
        # 1. 导入前统计
        cnt_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        zeyue_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'zeyue';")).scalar() or 0
        print(f"📊 [导入前统计]")
        print(f"   tube_material_price 全表总行数: {cnt_before}")
        print(f"   河北泽越已有记录数: {zeyue_before}")

        # 2. 执行导入
        res = import_zeyue_valve_prices(EXCEL_PATH, operator="EXCEL_IMPORT_20260928")
        print(f"\n✅ [导入结果]")
        print(f"   成功导入: {res['total_inserted']} 条记录")
        print(f"   厂家名称: {res['supplier_name']}")

        # 3. 导入后统计
        cnt_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        zeyue_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'zeyue';")).scalar() or 0
        print(f"\n🎉 [导入后统计]")
        print(f"   tube_material_price 全表总行数: {cnt_after} (净增 {cnt_after - cnt_before})")
        print(f"   河北泽越总记录数: {zeyue_after}")

        # 4. 打印本次入库的 38 条单价明细
        new_rows = session.execute(text("""
            SELECT id, category, material_name, model_spec, unit, unit_price, applicable_sections, section_name_scope, remark
            FROM tube.tube_material_price
            WHERE supply_entity_id = 'zeyue'
            ORDER BY id ASC;
        """)).fetchall()
        print(f"\n📋 本次入库的 38 条河北泽越球阀单价明细:")
        for r in new_rows:
            print(f"   - [ID {r[0]:3d}] 品类: {r[1]} | 物资: {r[2]:12s} | 规格: {r[3]:16s} | 单位: {r[4]} | 单价: ¥{r[5]:8.2f} | 标段: {r[6]} ({r[7]}) | 备注: {r[8]}")

        # 5. 校验幂等性测试
        print("\n🔄 测试幂等性：再次执行导入...")
        res2 = import_zeyue_valve_prices(EXCEL_PATH, operator="EXCEL_IMPORT_20260928")
        cnt_idempotent = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        zeyue_idempotent = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'zeyue';")).scalar() or 0
        print(f"   再次导入后全表行数: {cnt_idempotent} (保持一致: {cnt_idempotent == cnt_after})")
        print(f"   再次导入后泽越行数: {zeyue_idempotent} (保持一致: {zeyue_idempotent == zeyue_after})")

        # 6. 使用 list_material_prices 查询接口核验
        api_results = list_material_prices(supplier_name="泽悦")
        print(f"\n🔎 调用 list_material_prices 接口检索 '泽悦': 返回 {len(api_results)} 条记录")
        assert len(api_results) == 38, f"期望返回 38 条，实际返回 {len(api_results)} 条"
        print("   -> 接口检索校验通过，所有 38 种球阀单价均可被系统正常检索！")

    finally:
        session.close()


if __name__ == "__main__":
    main()
