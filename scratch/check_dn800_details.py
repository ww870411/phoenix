# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("SELECT id, category, material_name, model_spec, unit, unit_price, applicable_sections, section_name_scope FROM tube.tube_material_price WHERE supply_entity_id = 'kaiyuan' AND model_spec = 'DN800/DN800'")).fetchall()
    for r in rows:
        print(r)
finally:
    s.close()
