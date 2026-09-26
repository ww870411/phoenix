# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT DISTINCT fitting_type, model_spec 
        FROM tube.tube_fitting_delivery 
        LIMIT 20
    """)).fetchall()
    print("数据库发货表中管件样例 (tube_fitting_delivery):")
    for r in rows:
        print(f"  - [{r[0]}] {r[1]}")
        
    rows2 = s.execute(text("""
        SELECT category, standard_name, model_spec 
        FROM tube.tube_fitting_baseline 
        WHERE section_1_id LIKE 'low%'
        LIMIT 25
    """)).fetchall()
    print("\n数据库低温水基准表中管件样例 (tube_fitting_baseline):")
    for r in rows2:
        print(f"  - [{r[0]}] {r[1]} -> {r[2]}")
finally:
    s.close()
