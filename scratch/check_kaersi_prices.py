# -*- coding: utf-8 -*-
"""
查看天津卡尔斯和江苏沃圣在 tube.tube_material_price 中的球阀记录格式。
"""
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def main():
    session = SessionLocal()
    try:
        rows = session.execute(text("""
            SELECT supplier_name, category, material_name, model_spec, raw_model_spec, unit, unit_price, remark
            FROM tube.tube_material_price
            WHERE supply_entity_id IN ('kaersi', 'wosheng') AND category = '球阀'
            ORDER BY supplier_name, material_name, model_spec
            LIMIT 20;
        """)).fetchall()

        print(f"=== 天津卡尔斯与江苏沃圣球阀记录格式 (共查询前 20 条) ===")
        for r in rows:
            print(f"  厂家: {r[0]} | 品类: {r[1]} | 名称: {r[2]} | model_spec: {r[3]} | raw: {r[4]} | 单位: {r[5]} | 单价: {r[6]} | 备注: {r[7]}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
