# -*- coding: utf-8 -*-
"""
查询 tube.tube_material_price 表中的数据分布、品类、厂家与价格概况。
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
        # 1. 总行数与大类
        total_cnt = session.execute(text("SELECT COUNT(*) FROM tube.tube_material_price;")).scalar() or 0
        kind_stats = session.execute(text("""
            SELECT material_kind, COUNT(*) as cnt,
                   MIN(unit_price) as min_p, MAX(unit_price) as max_p,
                   ROUND(AVG(unit_price), 2) as avg_p
            FROM tube.tube_material_price
            GROUP BY material_kind;
        """)).fetchall()

        print(f"全表总行数: {total_cnt}")
        print("物料大类分布:")
        for k in kind_stats:
            print(f"  - 大类: {k[0]}, 记录数: {k[1]}, 单价区间: {k[2]} ~ {k[3]} 元 (均价: {k[4]} 元)")

        # 2. 厂家分布
        supplier_stats = session.execute(text("""
            SELECT supplier_name, supply_entity_id, material_kind, COUNT(*) as cnt
            FROM tube.tube_material_price
            GROUP BY supplier_name, supply_entity_id, material_kind
            ORDER BY supplier_name, material_kind;
        """)).fetchall()

        print("\n厂家供货范围与记录数:")
        for s in supplier_stats:
            print(f"  - 厂家: {s[0]} ({s[1]}), 大类: {s[2]}, 条数: {s[3]}")

        # 3. 物理品类分布
        cat_stats = session.execute(text("""
            SELECT category, material_kind, COUNT(*) as cnt,
                   MIN(unit_price) as min_p, MAX(unit_price) as max_p
            FROM tube.tube_material_price
            GROUP BY category, material_kind
            ORDER BY material_kind, cnt DESC;
        """)).fetchall()

        print("\n物理品类分类分布:")
        for c in cat_stats:
            print(f"  - 品类: {c[0]} (属于 {c[1]}), 条数: {c[2]}, 单价区间: {c[3]} ~ {c[4]} 元")

        # 4. 典型样本数据
        pipe_samples = session.execute(text("""
            SELECT supplier_name, category, material_name, model_spec, unit, unit_price
            FROM tube.tube_material_price
            WHERE material_kind = 'pipe'
            LIMIT 3;
        """)).fetchall()

        fitting_samples = session.execute(text("""
            SELECT supplier_name, category, material_name, model_spec, unit, unit_price
            FROM tube.tube_material_price
            WHERE material_kind = 'fitting'
            LIMIT 3;
        """)).fetchall()

        print("\n保温直管样本数据 (pipe):")
        for ps in pipe_samples:
            print(f"  - 厂家: {ps[0]} | 品类: {ps[1]} | 名称: {ps[2]} | 规格: {ps[3]} | 单位: {ps[4]} | 单价: {ps[5]} 元")

        print("\n管件样本数据 (fitting):")
        for fs in fitting_samples:
            print(f"  - 厂家: {fs[0]} | 品类: {fs[1]} | 名称: {fs[2]} | 规格: {fs[3]} | 单位: {fs[4]} | 单价: {fs[5]} 元")

    finally:
        session.close()


if __name__ == "__main__":
    main()
