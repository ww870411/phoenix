# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    cols = s.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_material_price' ORDER BY ordinal_position")).fetchall()
    print("Columns:")
    for c in cols:
        print(" ", c[0], ":", c[1])
        
    supps = s.execute(text("SELECT supplier_name, count(id) FROM tube.tube_material_price GROUP BY supplier_name ORDER BY count(id) DESC")).fetchall()
    print("\nSuppliers in tube_material_price:")
    for sp in supps:
        print(" ", sp[0], ":", sp[1], "条")
finally:
    s.close()
