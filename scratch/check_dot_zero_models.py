# -*- coding: utf-8 -*-
"""检查所有数据库表与配置文件中型号包含 '.0' 的情况"""

import os
import sys
import re
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def normalize_pipe_spec(spec: str) -> str:
    """去除非有效小数 .0，例如 4.0 -> 4，118.0 -> 118，但保留 4.5, 3.2 等"""
    if not spec:
        return ""
    # 替换数字后跟着 .0 但后面不再是数字的场景，比如 4.0 -> 4
    # 使用正则: (\d+)\.0(?!\d)
    return re.sub(r'(\d+)\.0+(?!\d)', r'\1', spec.strip())

def scan_tables():
    s = SessionLocal()
    tables_to_check = [
        ("tube.tube_pipe_baseline", "pipe_model_id"),
        ("tube.tube_material_price", "model_spec"),
        ("tube.tube_delivery", "pipe_model_id"),
        ("tube.tube_daily_usage", "pipe_model_id"),
        ("tube.tube_daily_plan", "pipe_model_id"),
        ("tube.tube_supplier_inventory", "pipe_model_id"),
        ("tube.tube_fitting_baseline", "model_spec"),
    ]

    try:
        for tbl, col in tables_to_check:
            # 检查表是否存在
            exists = s.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = '{tbl.split(".")[0]}' AND table_name = '{tbl.split(".")[1]}'
                );
            """)).scalar()
            if not exists:
                print(f"Table {tbl} does not exist.")
                continue

            query = f"SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL AND {col} <> '' ORDER BY {col};"
            rows = [r[0] for r in s.execute(text(query)).fetchall()]
            
            with_dot_zero = [r for r in rows if ".0" in r]
            without_dot_zero = [r for r in rows if ".0" not in r]

            print(f"\n==================================================")
            print(f"表: {tbl} | 字段: {col}")
            print(f"不重复型号总数: {len(rows)}")
            print(f"其中包含 '.0' 的型号数: {len(with_dot_zero)}")
            print(f"其中不包含 '.0' 的型号数: {len(without_dot_zero)}")

            if with_dot_zero:
                print("--- 带 .0 的样本 (前 15 条) ---")
                for m in with_dot_zero[:15]:
                    norm = normalize_pipe_spec(m)
                    print(f"  原值: {m:<35} -> 规范化: {norm}")
                    
    finally:
        s.close()

if __name__ == "__main__":
    scan_tables()
