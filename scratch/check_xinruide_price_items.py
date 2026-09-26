# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("""
        SELECT category, material_name, count(id) 
        FROM tube.tube_material_price 
        WHERE supplier_name LIKE '%鑫瑞得%' 
        GROUP BY category, material_name
        ORDER BY count(id) DESC
    """)).fetchall()
    print("鑫瑞得在 tube_material_price 中的物料分布 (共 158 条):")
    for r in rows:
        print(f"  - 类别: {r[0]} | 材料名: {r[1]} | 数量: {r[2]} 条")
finally:
    s.close()
