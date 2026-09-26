# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    rows = s.execute(text("SELECT DISTINCT pipe_model_id FROM tube.tube_pipe_baseline WHERE section_1_id LIKE 'low%' ORDER BY pipe_model_id")).fetchall()
    print("数据库基准表中低温水直管规格型号 (共 %d 种):" % len(rows))
    for r in rows:
        print("  -", r[0])
finally:
    s.close()
