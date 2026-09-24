# -*- coding: utf-8 -*-
"""
执行辽宁华阳散货单价数据（9.23_导入_辽宁华阳散货.xlsx）导入与核验。
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
    import_huayang_bulk_prices,
    list_material_prices,
)

EXCEL_PATH = os.path.join(project_root, "configs", "9.23_导入_辽宁华阳散货.xlsx")


def main():
    print("🚀 开始执行辽宁华阳散货单价追加导入...")
    ensure_price_table()

    session = SessionLocal()
    try:
        # 1. 导入前统计
        cnt_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        huayang_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'huayang';")).scalar() or 0
        print(f"📊 [导入前统计]")
        print(f"   tube_material_price 全表总行数: {cnt_before}")
        print(f"   辽宁华阳已有记录数: {huayang_before}")

        # 2. 执行导入
        res = import_huayang_bulk_prices(EXCEL_PATH, operator="user_import_20260923")
        print(f"\n✅ [导入结果]")
        print(f"   成功导入: {res['total_inserted']} 条记录")
        print(f"   其中保温管: {res['pipe_count']} 条, 管件与附件: {res['fitting_count']} 条")

        # 3. 导入后统计
        cnt_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        huayang_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'huayang';")).scalar() or 0
        print(f"\n🎉 [导入后统计]")
        print(f"   tube_material_price 全表总行数: {cnt_after} (净增 {cnt_after - cnt_before})")
        print(f"   辽宁华阳总记录数: {huayang_after}")

        # 4. 打印本次新增的 11 条记录
        new_rows = session.execute(text("""
            SELECT id, category, material_name, model_spec, unit, unit_price, applicable_sections, section_name_scope, remark
            FROM tube.tube_material_price
            WHERE supply_entity_id = 'huayang' AND created_by = 'user_import_20260923'
            ORDER BY id ASC;
        """)).fetchall()
        print(f"\n📋 本次新增入库的 11 条散货单价明细:")
        for r in new_rows:
            print(f"   - [ID {r[0]}] 品类: {r[1]} | 物资: {r[2]} | 规格: {r[3]} | 单位: {r[4]} | 单价: ¥{r[5]} | 标段: {r[6]} ({r[7]}) | 备注: {r[8]}")

        # 5. 校验幂等性测试
        print("\n🔄 测试幂等性：再次执行导入...")
        res2 = import_huayang_bulk_prices(EXCEL_PATH, operator="user_import_20260923")
        cnt_idempotent = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        huayang_idempotent = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price WHERE supply_entity_id = 'huayang';")).scalar() or 0
        print(f"   再次导入后全表行数: {cnt_idempotent} (保持一致: {cnt_idempotent == cnt_after})")
        print(f"   再次导入后华阳行数: {huayang_idempotent} (保持一致: {huayang_idempotent == huayang_after})")

        # 6. 使用 list_material_prices 查询接口核验
        api_results = list_material_prices(supplier_name="华阳")
        print(f"\n🔍 list_material_prices(supplier_name='华阳') 检索结果总数: {len(api_results)} 条")

    finally:
        session.close()


if __name__ == "__main__":
    main()
