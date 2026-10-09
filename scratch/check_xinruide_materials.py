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
        print(f"  entity_id: {ent.get('entity_id')}, entity_name: {ent.get('entity_name')}")

    session = SessionLocal()
    try:
        res = session.execute(text("""
            SELECT DISTINCT supply_entity_id, supplier_name
            FROM tube.tube_material_price
            WHERE supplier_name LIKE '%鑫瑞得%' OR supply_entity_id ILIKE '%XRD%' OR supply_entity_id ILIKE '%xinruide%'
        """)).fetchall()
        print("\nSuppliers matched in material_price:", res)

        for row in res:
            entity_id = row[0]
            print(f"\n--- Checking entity: {entity_id} ({row[1]}) ---")
            items = session.execute(text("""
                SELECT category, material_name, model_spec, unit, unit_price
                FROM tube.tube_material_price
                WHERE (supply_entity_id = :entity_id OR supplier_name = :entity_id)
                  AND category != '保温管'
                  AND (model_spec LIKE '%50%' OR category LIKE '%弯头%' OR material_name LIKE '%弯头%')
                ORDER BY category, material_name, model_spec
            """), {"entity_id": entity_id}).fetchall()
            for it in items:
                print(it)
    finally:
        session.close()

if __name__ == "__main__":
    main()
