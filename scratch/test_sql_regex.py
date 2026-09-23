# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def test_sql_regex():
    s = SessionLocal()
    test_cases = [
        'Φ32×4.0/Φ118×3.0',
        'Φ108×4.0/Φ194×3.2',
        'Φ133×4.5/Φ219×3.5',
        'Φ219×6.0/Φ309×4.9',
        'Φ273×7.0/Φ400×6.3',
        'Φ325×7.0/Φ417×7.0',
        'Φ377×7.0/Φ471×7.0',
        'Φ57×5/Φ140×3.0',
        'Φ1120×13/Φ1260×16（甲供钢管）',
        'Φ38×4/Φ124×3（甲供钢管）',
    ]
    try:
        for tc in test_cases:
            # PostgreSQL 正则测试
            res = s.execute(text("SELECT regexp_replace(:val, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g');"), {"val": tc}).scalar()
            print(f"原值: {tc:<35} -> SQL正则结果: {res}")
    finally:
        s.close()

if __name__ == "__main__":
    test_sql_regex()
