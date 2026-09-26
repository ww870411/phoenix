# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT category, material_name, model_spec, unit, count(id) as cnt
        FROM tube.tube_material_price 
        WHERE supply_entity_id = 'kaiyuan' AND category != '保温管' 
        GROUP BY category, material_name, model_spec, unit 
        HAVING count(id) > 1
    """)).fetchall()
    print("kaiyuan 在 tube_material_price 中重复的 (category, material_name, model_spec, unit):")
    for r in rows:
        print(f"  [{r[0]}] {r[1]} | {r[2]} | {r[3]} | 出现 {r[4]} 次")
        
    print("\n再看看 category 和 model_spec 重复的 (忽略 material_name):")
    rows2 = s.execute(text("""
        SELECT category, model_spec, unit, count(id) as cnt, array_agg(material_name)
        FROM tube.tube_material_price 
        WHERE supply_entity_id = 'kaiyuan' AND category != '保温管' 
        GROUP BY category, model_spec, unit 
        HAVING count(id) > 1
    """)).fetchall()
    for r in rows2:
        print(f"  [{r[0]}] {r[1]} | {r[2]} | 出现 {r[3]} 次 | 涉及材料名: {r[4]}")
finally:
    s.close()
