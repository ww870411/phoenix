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
    print("=== tube_config.json supply_entities ===")
    for ent in config.get("supply_entities", []):
        print(f"  entity_id: {ent.get('entity_id')}, entity_name: {ent.get('entity_name')}, section_1_ids: {ent.get('section_1_ids')}")

    session = SessionLocal()
    try:
        print("\n=== tube.tube_material_price 中涉及华阳的数据 ===")
        rows = session.execute(text("""
            SELECT id, supply_entity_id, supplier_name, category, material_name, model_spec, unit, unit_price, applicable_sections, section_name_scope, remark
            FROM tube.tube_material_price
            WHERE supplier_name ILIKE '%华阳%' OR supply_entity_id = 'huayang'
            ORDER BY id;
        """)).fetchall()
        print(f"查到 {len(rows)} 条华阳记录:")
        for r in rows:
            print(f"  ID {r[0]}: [{r[1]}] {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | 单价: {r[7]} | 标段: {r[8]} ({r[9]}) | 备注: {r[10]}")

        print("\n=== 表中所有 supplier_name 和 supply_entity_id 分组统计 ===")
        groups = session.execute(text("""
            SELECT supply_entity_id, supplier_name, applicable_sections, section_name_scope, COUNT(*)
            FROM tube.tube_material_price
            GROUP BY supply_entity_id, supplier_name, applicable_sections, section_name_scope
            ORDER BY supply_entity_id, supplier_name;
        """)).fetchall()
        for g in groups:
            print(f"  {g[0]} | {g[1]} | {g[2]} ({g[3]}) | {g[4]} 条")

    finally:
        session.close()

if __name__ == "__main__":
    main()
