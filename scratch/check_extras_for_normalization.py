# -*- coding: utf-8 -*-
import os
import sys
import json
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def check_extras():
    s = SessionLocal()
    try:
        # 1. 检查 tube_delivery 的列
        cols = s.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'tube' AND table_name = 'tube_delivery';
        """)).fetchall()
        print("tube_delivery columns:", [c[0] for c in cols])

        # 2. 检查 tube_config.json
        cfg_path = os.path.join(project_root, "configs", "tube_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                content = f.read()
                print("tube_config.json contains '.0':", ".0" in content)
                if ".0" in content:
                    lines = [line.strip() for line in content.splitlines() if ".0" in line]
                    print(f"Sample lines with .0 in tube_config.json ({len(lines)} lines):", lines[:10])

        # 3. 检查 seeds 目录
        seeds_dir = os.path.join(project_root, "backend", "projects", "insulation_pipe_supply_2026", "seeds")
        for fn in os.listdir(seeds_dir):
            fp = os.path.join(seeds_dir, fn)
            if os.path.isfile(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    cnt = f.read()
                    print(f"Seed file {fn} contains '.0':", ".0" in cnt)

    finally:
        s.close()

if __name__ == "__main__":
    check_extras()
