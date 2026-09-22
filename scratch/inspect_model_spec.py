# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def main():
    s = SessionLocal()
    try:
        print("=== tube.tube_fitting_baseline sample (high_lot_3, high_lot_4) ===")
        b_rows = s.execute(text("""
            SELECT category, standard_name, model_spec, sub_model_spec, raw_model_spec 
            FROM tube.tube_fitting_baseline 
            WHERE section_1_id IN ('high_lot_3', 'high_lot_4') 
            LIMIT 10;
        """)).fetchall()
        for r in b_rows:
            print(f"cat={r[0]} | std_name={r[1]} | model_spec={r[2]} | sub={r[3]} | raw={r[4]}")

        print("\n=== tube.tube_material_price sample (kaiyuan 3,4标段) ===")
        p_rows = s.execute(text("""
            SELECT category, material_name, model_spec, raw_model_spec 
            FROM tube.tube_material_price 
            WHERE applicable_sections = 'high_lot_3,high_lot_4' 
            LIMIT 10;
        """)).fetchall()
        for r in p_rows:
            print(f"cat={r[0]} | mat_name={r[1]} | model_spec={r[2]} | raw_spec={r[3]}")

        print("\n=== tube.tube_pipe_baseline sample (high_lot_3, high_lot_4) ===")
        pipe_b = s.execute(text("""
            SELECT section_1_id, pipe_model_id, unit, design_qty 
            FROM tube.tube_pipe_baseline 
            WHERE section_1_id IN ('high_lot_3', 'high_lot_4') 
            LIMIT 10;
        """)).fetchall()
        for r in pipe_b:
            print(f"sec={r[0]} | pipe_model_id={r[1]} | unit={r[2]} | design_qty={r[3]}")

        print("\n=== tube.tube_material_price pipe sample (kaiyuan 3,4标段) ===")
        pipe_p = s.execute(text("""
            SELECT category, material_name, model_spec, raw_model_spec 
            FROM tube.tube_material_price 
            WHERE applicable_sections = 'high_lot_3,high_lot_4' AND material_kind = 'pipe'
            LIMIT 10;
        """)).fetchall()
        for r in pipe_p:
            print(f"cat={r[0]} | mat_name={r[1]} | model_spec={r[2]} | raw_spec={r[3]}")

    finally:
        s.close()

if __name__ == "__main__":
    main()
