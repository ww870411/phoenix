# -*- coding: utf-8 -*-
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
        print("=== 检查管件基准表中是否有 HYSDT 或 L=2400 或 1100 相关的补偿器/支架 ===")
        rows = session.execute(text("""
            SELECT id, section_1_id, category, standard_name, model_spec, unit, design_qty
            FROM tube.tube_fitting_baseline
            WHERE model_spec ILIKE '%HYSDT%' 
               OR model_spec ILIKE '%2400%'
               OR model_spec ILIKE '%1100%'
               OR model_spec ILIKE '%1000%'
            LIMIT 30;
        """)).fetchall()
        print(f"匹配到 {len(rows)} 条基准记录:")
        for r in rows:
            print(f"  ID {r[0]}: 标段={r[1]} | 品类={r[2]} | 物资={r[3]} | 规格={r[4]} | 单位={r[5]} | 数量={r[6]}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
