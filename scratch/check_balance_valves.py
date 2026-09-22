# -*- coding: utf-8 -*-
"""
查询 tube.tube_fitting_baseline 中关于“联网平衡阀”/“物联网平衡阀”的现有记录详情。
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
        rows = session.execute(text("""
            SELECT id, section_1_id, system_type, category, standard_name, model_spec, sub_model_spec,
                   unit, design_qty, purchase_plan_qty, main_dn, pressure_rating, remark
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀'
            ORDER BY section_1_id, model_spec, sub_model_spec;
        """)).fetchall()

        print(f"总计找到 {len(rows)} 条联网平衡阀记录：")
        sub_specs = set()
        for r in rows:
            sub_specs.add(r[6])
            print(f"ID={r[0]}: 标段={r[1]}, 系统={r[2]}, 名称={r[4]}, 规格={r[5]}, 子规格='{r[6]}', 单位={r[7]}, 设计量={r[8]}, 采购量={r[9]}")

        print(f"\n所有出现的 sub_model_spec: {sub_specs}")

        # 检查如果按 section_1_id, system_type, standard_name, model_spec 聚合，会有多少条记录
        grouped = session.execute(text("""
            SELECT section_1_id, system_type, standard_name, model_spec,
                   COUNT(*) as row_count,
                   SUM(design_qty) as total_design,
                   SUM(purchase_plan_qty) as total_plan,
                   STRING_AGG(DISTINCT sub_model_spec, ', ') as sub_specs
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀'
            GROUP BY section_1_id, system_type, standard_name, model_spec
            ORDER BY section_1_id, model_spec;
        """)).fetchall()

        print(f"\n按 (section_1_id, system_type, standard_name, model_spec) 合并后预计条数: {len(grouped)}")
        has_multi = [g for g in grouped if g[4] > 1]
        print(f"其中包含多个子规格需要合并的型号组数: {len(has_multi)}")
        for g in has_multi[:10]:
            print(f"  标段={g[0]}, 规格={g[3]}, 行数={g[4]}, 涉及子规格=[{g[7]}], 设计总量={g[5]}, 采购总量={g[6]}")

        # 查询非联网平衡阀的 sub_model_spec 常见形态
        other_samples = session.execute(text("""
            SELECT category, standard_name, COUNT(*) as cnt,
                   COUNT(DISTINCT sub_model_spec) as distinct_sub,
                   ARRAY_AGG(DISTINCT sub_model_spec) FILTER (WHERE sub_model_spec IS NOT NULL AND sub_model_spec != '') as sample_subs
            FROM tube.tube_fitting_baseline
            WHERE category != '联网平衡阀'
            GROUP BY category, standard_name
            LIMIT 10;
        """)).fetchall()
        # 检查发货记录中平衡阀的具体内容
        delivery_rows = session.execute(text("""
            SELECT *
            FROM tube.tube_fitting_delivery
            WHERE fitting_type LIKE '%平衡阀%';
        """)).mappings().all()
        print(f"\ntube_fitting_delivery 发货记录详情 (共 {len(delivery_rows)} 条):")
        for dr in delivery_rows:
            print(dict(dr))

    finally:
        session.close()


if __name__ == "__main__":
    main()
