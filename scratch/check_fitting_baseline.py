# -*- coding: utf-8 -*-
"""
查看 tube.tube_fitting_baseline 中是否有泽越或者球阀的设计基准。
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
        # 1. 检查 tube_fitting_baseline 中关于球阀的记录
        has_baseline = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'tube' AND table_name = 'tube_fitting_baseline'
            );
        """)).scalar()

        cols = session.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'tube' AND table_name = 'tube_fitting_baseline';
        """)).fetchall()
        print("tube_fitting_baseline 列名:", [c[0] for c in cols])

        rows = session.execute(text("""
            SELECT section_1_id, category, standard_name, model_spec, unit, design_qty
            FROM tube.tube_fitting_baseline
            WHERE category ILIKE '%球阀%' OR standard_name ILIKE '%球阀%'
            ORDER BY section_1_id, model_spec
            LIMIT 20;
        """)).fetchall()
        print(f"=== tube.tube_fitting_baseline 球阀样例 (共 {len(rows)} 条) ===")
        for r in rows:
            print(f"  标段: {r[0]} | 类别: {r[1]} | 名称: {r[2]} | 规格: {r[3]} | 单位: {r[4]} | 设计量: {r[5]}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
