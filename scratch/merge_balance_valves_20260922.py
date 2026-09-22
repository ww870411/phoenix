# -*- coding: utf-8 -*-
"""
合并 tube.tube_fitting_baseline 中的“物联网平衡阀”记录：
1. 业务背景：
   - 之前在 sub_model_spec 区分了“地上”和“地下”；
   - 经业务部门确认，不论地上地下，只要 model_spec 相同即为同种物料（仅用途不同）；
   - 因此将相同 model_spec 的物联网平衡阀合并为一条记录，相应数量（design_qty, purchase_plan_qty）累加，
     sub_model_spec 置为空字符串 ''。
2. 事务级操作：
   - 聚合计算当前 94 条平衡阀记录为 55 条合并记录；
   - 校验合并前后的设计总量和采购总量严格一致；
   - 事务内删除旧记录并写入合并后的新记录；
   - 输出详细的分标段、分规格合并前后对照表。
"""

import os
import sys
from decimal import Decimal
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal


def main():
    print("🚀 开始执行物联网平衡阀记录合并流程...")
    session = SessionLocal()
    try:
        # 1. 统计合并前数据
        stats_before = session.execute(text("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(design_qty), 0) as total_design,
                   COALESCE(SUM(purchase_plan_qty), 0) as total_plan
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀';
        """)).mappings().one()

        cnt_before = stats_before["cnt"]
        total_design_before = Decimal(str(stats_before["total_design"]))
        total_plan_before = Decimal(str(stats_before["total_plan"]))

        print(f"📊 [合并前统计]")
        print(f"   总记录数: {cnt_before} 行")
        print(f"   设计总量: {total_design_before} 套")
        print(f"   采购计划总量: {total_plan_before} 套")

        if cnt_before == 0:
            print("⚠️ 未找到任何联网平衡阀记录，无需合并。")
            return

        # 2. 查询需要聚合的数据
        aggregated_rows = session.execute(text("""
            SELECT
                section_1_id,
                system_type,
                category,
                standard_name,
                model_spec,
                '' AS sub_model_spec,
                unit,
                SUM(design_qty) AS design_qty,
                SUM(purchase_plan_qty) AS purchase_plan_qty,
                MAX(main_dn) AS main_dn,
                MAX(sub_dn) AS sub_dn,
                MAX(angle) AS angle,
                MAX(bending_radius_ratio) AS bending_radius_ratio,
                MAX(bending_radius_m) AS bending_radius_m,
                MAX(valve_model) AS valve_model,
                MAX(outer_diameter) AS outer_diameter,
                MAX(wall_thickness) AS wall_thickness,
                MAX(length_m) AS length_m,
                MAX(pressure_rating) AS pressure_rating,
                MAX(compensation_mm) AS compensation_mm,
                MAX(flow_direction) AS flow_direction,
                model_spec AS raw_model_spec,
                standard_name AS raw_name,
                '2026-09-21 物联网平衡阀询价单入库 (合并地上地下)' AS remark,
                '{}'::jsonb AS extra_params,
                'merge_script_20260922' AS created_by,
                'merge_script_20260922' AS updated_by,
                COUNT(*) AS source_row_cnt,
                STRING_AGG(DISTINCT sub_model_spec, ', ') AS source_subs
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀'
            GROUP BY section_1_id, system_type, category, standard_name, model_spec, unit
            ORDER BY section_1_id, model_spec;
        """)).mappings().all()

        print(f"\n📋 [聚合计算]")
        print(f"   聚合后记录数: {len(aggregated_rows)} 行")

        # 3. 校验总量一致性
        total_design_agg = sum(Decimal(str(r["design_qty"])) for r in aggregated_rows)
        total_plan_agg = sum(Decimal(str(r["purchase_plan_qty"])) for r in aggregated_rows)

        if total_design_agg != total_design_before or total_plan_agg != total_plan_before:
            raise ValueError(
                f"数据校验失败！聚合后数量与之前不符: "
                f"设计总量之前={total_design_before}, 之后={total_design_agg}; "
                f"采购计划之前={total_plan_before}, 之后={total_plan_agg}"
            )

        print(f"   数据一致性校验 100% 通过（设计总量={total_design_agg}, 采购计划总量={total_plan_agg}）")

        # 4. 事务级替换：先删除旧记录，再插入合并后记录
        print("\n⚙️ [执行事务写入]")
        deleted = session.execute(text("""
            DELETE FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀';
        """)).rowcount
        print(f"   已删除旧记录: {deleted} 行")

        insert_sql = """
            INSERT INTO tube.tube_fitting_baseline (
                section_1_id, system_type, category, standard_name, model_spec, sub_model_spec, unit,
                design_qty, purchase_plan_qty,
                main_dn, sub_dn, angle, bending_radius_ratio, bending_radius_m,
                valve_model, outer_diameter, wall_thickness, length_m,
                pressure_rating, compensation_mm, flow_direction, raw_model_spec, raw_name, remark, extra_params,
                created_by, updated_by, created_at, updated_at
            ) VALUES (
                :section_1_id, :system_type, :category, :standard_name, :model_spec, :sub_model_spec, :unit,
                :design_qty, :purchase_plan_qty,
                :main_dn, :sub_dn, :angle, :bending_radius_ratio, :bending_radius_m,
                :valve_model, :outer_diameter, :wall_thickness, :length_m,
                :pressure_rating, :compensation_mm, :flow_direction, :raw_model_spec, :raw_name, :remark, '{}'::jsonb,
                :created_by, :updated_by, NOW(), NOW()
            );
        """

        for row in aggregated_rows:
            p = dict(row)
            p.pop("extra_params", None)
            session.execute(text(insert_sql), p)

        session.commit()
        print(f"✅ 事务提交成功！已写入 {len(aggregated_rows)} 条合并后的物联网平衡阀记录。")

        # 5. 校验数据库最终结果
        stats_after = session.execute(text("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(design_qty), 0) as total_design,
                   COALESCE(SUM(purchase_plan_qty), 0) as total_plan
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀' OR standard_name = '物联网平衡阀';
        """)).mappings().one()

        print(f"\n🎉 [合并后最终核验]")
        print(f"   最终记录数: {stats_after['cnt']} 行")
        print(f"   最终设计总量: {stats_after['total_design']} 套")
        print(f"   最终采购计划量: {stats_after['total_plan']} 套")

        # 打印合并明细 (针对之前区分了地上地下的组)
        print("\n🔍 [合并明细清单（部分展示）]:")
        merged_groups = [r for r in aggregated_rows if r["source_row_cnt"] > 1]
        print(f"   共 {len(merged_groups)} 组原区分地上地下的规格已完成合并：")
        for g in merged_groups:
            print(f"   - 【{g['section_1_id']}】{g['model_spec']}: 合并前包含 [{g['source_subs']}] 2条记录 -> 合并后1条: 设计量={g['design_qty']}, 采购量={g['purchase_plan_qty']}")

    except Exception as e:
        session.rollback()
        print(f"❌ 执行失败并已回滚: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    main()
