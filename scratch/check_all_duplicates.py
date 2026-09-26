# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT supply_entity_id, category, model_spec, unit, count(id) as cnt
        FROM tube.tube_material_price 
        WHERE category != '保温管' 
        GROUP BY supply_entity_id, category, model_spec, unit 
        HAVING count(id) > 1
    """)).fetchall()
    print("全库存在重复 (supply_entity_id, category, model_spec, unit) 的情况:")
    for r in rows:
        print(f"  {r[0]:<12} | {r[1]} | {r[2]} | {r[3]} | 重复 {r[4]} 次")
finally:
    s.close()
