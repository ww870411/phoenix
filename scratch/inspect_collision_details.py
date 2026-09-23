# -*- coding: utf-8 -*-
import os
import sys
import re
from collections import defaultdict
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def normalize_pipe_spec(spec: str) -> str:
    if not spec:
        return ""
    return re.sub(r'(\d+)\.0+(?!\d)', r'\1', spec.strip())

def inspect_collisions():
    s = SessionLocal()
    try:
        print("=== 1. 计划表 tube.tube_daily_plan 冲突详情 ===")
        plan_rows = s.execute(text("""
            SELECT id, section_1_id, plan_date, pipe_model_id, plan_qty
            FROM tube.tube_daily_plan
            ORDER BY section_1_id, plan_date, pipe_model_id;
        """)).fetchall()

        plan_map = defaultdict(list)
        for r in plan_rows:
            norm_m = normalize_pipe_spec(r[3])
            plan_map[(r[1], str(r[2]), norm_m)].append(r)

        collisions = [item for item in plan_map.items() if len(item[1]) > 1 and any(normalize_pipe_spec(x[3]) != x[3] for x in item[1])]
        print(f"冲突总组数: {len(collisions)}")
        for (sec, dt, norm_m), recs in collisions[:5]:
            print(f"  标段={sec}, 日期={dt}, 归一化型号={norm_m}")
            for rc in recs:
                print(f"    id={rc[0]}, 原始型号={rc[3]}, 计划量={rc[4]}")

        print("\n=== 2. 消耗表 tube.tube_daily_usage 冲突详情 ===")
        usage_rows = s.execute(text("""
            SELECT id, section_1_id, usage_date, pipe_model_id, usage_qty, loss_qty
            FROM tube.tube_daily_usage
            ORDER BY section_1_id, usage_date, pipe_model_id;
        """)).fetchall()

        usage_map = defaultdict(list)
        for r in usage_rows:
            norm_m = normalize_pipe_spec(r[3])
            usage_map[(r[1], str(r[2]), norm_m)].append(r)

        u_collisions = [item for item in usage_map.items() if len(item[1]) > 1 and any(normalize_pipe_spec(x[3]) != x[3] for x in item[1])]
        print(f"冲突总组数: {len(u_collisions)}")
        for (sec, dt, norm_m), recs in u_collisions[:5]:
            print(f"  标段={sec}, 日期={dt}, 归一化型号={norm_m}")
            for rc in recs:
                print(f"    id={rc[0]}, 原始型号={rc[3]}, 使用量={rc[4]}, 损耗量={rc[5]}")

    finally:
        s.close()

if __name__ == "__main__":
    inspect_collisions()
