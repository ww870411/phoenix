# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config

def main():
    config = load_tube_config()
    print("=== 供给实体中与天地龙相关的配置 ===")
    for sup in config.get("supply_entities", []):
        if "天地龙" in sup.get("entity_name", "") or "tiandilong" in sup.get("entity_id", "").lower():
            print(f"供给方: id={sup.get('entity_id')}, name={sup.get('entity_name')}, section_1_ids={sup.get('section_1_ids')}")

    print("\n=== 需求实体 demand_entities 中的 low_lot_6 ===")
    for dem in config.get("demand_entities", []):
        if dem.get("section_1_id") == "low_lot_6":
            print(f"标段: id={dem.get('section_1_id')}, name={dem.get('section_1_name')}")

    s = SessionLocal()
    try:
        print("\n=== tube.tube_pipe_baseline 中 low_lot_6 的已有记录 ===")
        rows = s.execute(text("""
            SELECT id, section_1_id, pipe_model_id, unit, design_qty, purchase_plan_qty, remark
            FROM tube.tube_pipe_baseline
            WHERE section_1_id = 'low_lot_6'
            ORDER BY id ASC;
        """)).fetchall()
        print(f"low_lot_6 现有记录数: {len(rows)}")
        for r in rows:
            print(f"id={r[0]}, sec={r[1]}, model={r[2]}, unit={r[3]}, design={r[4]}, plan={r[5]}, remark={r[6]}")

        print("\n=== tube.tube_pipe_baseline 中全部标段分布统计 ===")
        sec_counts = s.execute(text("""
            SELECT section_1_id, COUNT(*) 
            FROM tube.tube_pipe_baseline 
            GROUP BY section_1_id 
            ORDER BY section_1_id;
        """)).fetchall()
        for sec, cnt in sec_counts:
            print(f"标段: {sec} -> {cnt} 条")

        print("\n=== tube.tube_pipe_baseline 中是否有甲供钢管 ===")
        jg_baseline = s.execute(text("""
            SELECT id, section_1_id, pipe_model_id, design_qty, purchase_plan_qty
            FROM tube.tube_pipe_baseline
            WHERE pipe_model_id LIKE '%甲供%'
        """)).fetchall()
        print(f"现有基准表中甲供钢管记录数: {len(jg_baseline)}")
        for r in jg_baseline:
            print(f"  id={r[0]}, sec={r[1]}, model={r[2]}, design={r[3]}, plan={r[4]}")

        print("\n=== tube.tube_material_price 中全部甲供钢管记录 ===")
        jg_price = s.execute(text("""
            SELECT id, supplier_name, applicable_sections, material_kind, category, model_spec, unit_price
            FROM tube.tube_material_price
            WHERE model_spec LIKE '%甲供%'
        """)).fetchall()
        print(f"价格表中甲供钢管记录数: {len(jg_price)}")
        for r in jg_price:
            print(f"  id={r[0]}, sup={r[1]}, sec={r[2]}, kind={r[3]}, spec={r[5]}, price={r[6]}")

        print("\n=== tube_config.json 中的 pipe_models ===")
        pipe_models = config.get("pipe_models", [])
        print(f"pipe_models 数量: {len(pipe_models)}")
        for pm in pipe_models[:5]:
            print(f"  {pm}")

        print("\n=== 当前 tube_pipe_baseline 自增序列状态 ===")
        seq_val = s.execute(text("SELECT last_value, is_called FROM tube.tube_pipe_baseline_id_seq;")).fetchall()
        max_id = s.execute(text("SELECT MAX(id) FROM tube.tube_pipe_baseline;")).scalar()
        print(f"当前序列: {seq_val}, 最大 id: {max_id}")

    finally:
        s.close()

if __name__ == "__main__":
    main()
