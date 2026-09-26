# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT category, material_name, model_spec, unit, unit_price 
        FROM tube.tube_material_price 
        WHERE supply_entity_id = 'xinruide' AND category != '保温管' 
        ORDER BY category, model_spec 
        LIMIT 10
    """)).fetchall()
    print("xinruide 样本:")
    for r in rows:
        print(f"  [{r[0]}] {r[1]} | {r[2]} | {r[3]} | 单价: {r[4]}")
finally:
    s.close()
