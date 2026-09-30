# -*- coding: utf-8 -*-
"""
检查数据库中 tube.tube_material_price 的结构、已有球阀/阀门数据以及河北泽越的数据。
"""
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

def main():
    session = SessionLocal()
    try:
        # 1. 检查表列字段
        cols = session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'tube' AND table_name = 'tube_material_price'
            ORDER BY ordinal_position;
        """)).fetchall()
        print("=== tube.tube_material_price 列结构 ===")
        for c in cols:
            print(f"  {c[0]:20s} {c[1]:15s} NULL:{c[2]} DEFAULT:{c[3]}")

        # 2. 检查是否有河北泽越或 zeyue
        zeyue_rows = session.execute(text("""
            SELECT id, supplier_name, supply_entity_id, material_kind, category, material_name, model_spec, unit, unit_price
            FROM tube.tube_material_price
            WHERE supply_entity_id = 'zeyue' OR supplier_name ILIKE '%泽越%'
            LIMIT 10;
        """)).fetchall()
        print(f"\n=== 数据库中现存河北泽越记录数: {len(zeyue_rows)} ===")
        for r in zeyue_rows:
            print(f"  {r}")

        # 3. 检查是否有球阀或阀门类别，查看其 material_kind
        valve_rows = session.execute(text("""
            SELECT supplier_name, supply_entity_id, material_kind, category, material_name, model_spec, unit, unit_price, applicable_sections, section_name_scope, remark
            FROM tube.tube_material_price
            WHERE category = '球阀'
            LIMIT 15;
        """)).fetchall()
        print(f"\n=== 数据库中现存球阀样例 (共查询前15条) ===")
        for v in valve_rows:
            print(f"  厂家: {v[0]} ({v[1]}) | 品类: {v[3]} | 名称: {v[4]} | 规格: {v[5]} | 单位: {v[6]} | 单价: {v[7]} | 标段: {v[8]} ({v[9]}) | 备注: {v[10]}")

        # 3.1 球阀各厂家数量与标段分布
        valve_stats = session.execute(text("""
            SELECT supplier_name, supply_entity_id, applicable_sections, section_name_scope, COUNT(*)
            FROM tube.tube_material_price
            WHERE category = '球阀'
            GROUP BY supplier_name, supply_entity_id, applicable_sections, section_name_scope;
        """)).fetchall()
        print(f"\n=== 数据库中现存球阀厂家与标段统计 ===")
        for s in valve_stats:
            print(f"  厂家: {s[0]} ({s[1]}) | 适用标段: {s[2]} ({s[3]}) | 条数: {s[4]}")
        print(f"\n=== 数据库中现存阀门相关品类 ===")
        for v in valve_rows:
            print(f"  大类 material_kind: {v[0]} | 品类 category: {v[1]} | 材料名称 material_name: {v[2]}")

        # 4. 检查 supply_entities 配置
        from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config
        cfg = load_tube_config()
        entities = cfg.get("supply_entities", [])
        print("\n=== tube_config.json 中的 supply_entities ===")
        for e in entities:
            print(f"  ID: {e.get('entity_id')} | 名称: {e.get('entity_name')} | 标段: {e.get('section_1_ids')}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
