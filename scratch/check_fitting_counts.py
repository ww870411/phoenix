# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT supply_entity_id, supplier_name, count(id) as cnt
        FROM tube.tube_material_price 
        WHERE category != '保温管' 
        GROUP BY supply_entity_id, supplier_name 
        ORDER BY count(id) DESC
    """)).fetchall()
    print("各厂家在 tube_material_price 中的管件项数:")
    for r in rows:
        print(f"  {r[0]:<12} | {r[1]:<20} | {r[2]} 项管件")
finally:
    s.close()
