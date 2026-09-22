# -*- coding: utf-8 -*-
"""
执行低温水 1~6 标段“联网平衡阀”基准量入库：
1. 解析《configs/9.21 物联网平衡阀询价单-数据整理2.xlsx》中的 94 条平衡阀记录；
2. 规范化字段：
   - 类别: '联网平衡阀'
   - 标准名称: '物联网平衡阀'
   - 计量单位: '套'
   - 系统类型: '低温水'
   - 解析 pressure_rating (如 PN16, PN25) 与 main_dn (如 25.0 ~ 200.0)；
3. 执行事务级幂等写入（UPSERT）至 PostgreSQL `tube.tube_fitting_baseline`；
4. 校验与核对入库结果并输出分标段统计。
"""

import os
import sys
import re
import openpyxl
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.baseline_service import ensure_baseline_tables

EXCEL_PATH = os.path.join(project_root, "configs", "9.21 物联网平衡阀询价单-数据整理2.xlsx")


def parse_excel_rows(excel_path: str):
    """解析 Excel 中的 94 条物联网平衡阀数据并标准化为参数化字段。"""
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["按标段+型号+地上地下聚合"]

    parsed_items = []

    for r in range(2, sheet.max_row + 1):
        cat_val = sheet.cell(row=r, column=1).value
        std_name = sheet.cell(row=r, column=2).value
        sec_id = sheet.cell(row=r, column=3).value
        spec_str = sheet.cell(row=r, column=4).value
        sub_spec = sheet.cell(row=r, column=5).value
        design_qty = sheet.cell(row=r, column=6).value
        plan_qty = sheet.cell(row=r, column=7).value

        if not sec_id or not spec_str:
            continue

        sec_id = str(sec_id).strip()
        spec_str = str(spec_str).strip()
        sub_spec = str(sub_spec).strip() if sub_spec else ""
        d_qty = float(design_qty or 0)
        p_qty = float(plan_qty or 0)

        # 解析 pressure_rating 和 main_dn，如 "PN16/DN25"
        pressure_rating = None
        main_dn = None
        pn_match = re.search(r"PN(\d+)", spec_str, re.IGNORECASE)
        if pn_match:
            pressure_rating = f"PN{pn_match.group(1)}"
        dn_match = re.search(r"DN(\d+)", spec_str, re.IGNORECASE)
        if dn_match:
            main_dn = float(dn_match.group(1))

        item = {
            "section_1_id": sec_id,
            "system_type": "低温水",
            "category": "联网平衡阀",  # 用户明确指定类别为“联网平衡阀”
            "standard_name": str(std_name).strip() if std_name else "物联网平衡阀",
            "model_spec": spec_str,
            "sub_model_spec": sub_spec,
            "unit": "套",  # 用户明确指定计量单位为“套”
            "design_qty": d_qty,
            "purchase_plan_qty": p_qty,
            "main_dn": main_dn,
            "sub_dn": None,
            "angle": None,
            "bending_radius_ratio": None,
            "bending_radius_m": None,
            "valve_model": None,
            "outer_diameter": None,
            "wall_thickness": None,
            "length_m": None,
            "pressure_rating": pressure_rating,
            "compensation_mm": None,
            "flow_direction": None,
            "raw_model_spec": spec_str,
            "raw_name": str(std_name).strip() if std_name else "物联网平衡阀",
            "remark": "2026-09-21 物联网平衡阀询价单入库",
            "operator_name": "system_import_20260921"
        }
    # 2026-09-22 业务规则更新：不论地上地下，相同 model_spec 属于同种物料，合并记录并累加数量
    merged_map = {}
    for it in parsed_items:
        key = (it["section_1_id"], it["system_type"], it["category"], it["standard_name"], it["model_spec"])
        if key not in merged_map:
            it["sub_model_spec"] = ""
            it["remark"] = "2026-09-21 物联网平衡阀询价单入库 (合并地上地下)"
            merged_map[key] = it
        else:
            merged_map[key]["design_qty"] += it["design_qty"]
            merged_map[key]["purchase_plan_qty"] += it["purchase_plan_qty"]

    return list(merged_map.values())


def main():
    print(f"🚀 开始执行联网平衡阀基准量导入流程...")
    parsed_items = parse_excel_rows(EXCEL_PATH)
    print(f"📋 [1/3] 从 Excel 解析得到 {len(parsed_items)} 条记录。")

    session = SessionLocal()
    try:
        # 1. 确保表结构存在与自愈
        ensure_baseline_tables()

        # 2. 检查导入前数据库中的总行数及平衡阀行数
        cnt_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_fitting_baseline;")).scalar() or 0
        balance_cnt_before = session.execute(text("SELECT COUNT(*) FROM tube.tube_fitting_baseline WHERE category = '联网平衡阀';")).scalar() or 0
        print(f"📊 [2/3] 导入前 tube.tube_fitting_baseline 总行数: {cnt_before}, '联网平衡阀'行数: {balance_cnt_before}")

        # 3. 批量幂等插入 (UPSERT)
        upsert_sql = """
            INSERT INTO tube.tube_fitting_baseline (
                section_1_id, system_type, category, standard_name, model_spec, sub_model_spec, unit,
                design_qty, purchase_plan_qty,
                main_dn, sub_dn, angle, bending_radius_ratio, bending_radius_m,
                valve_model, outer_diameter, wall_thickness, length_m,
                pressure_rating, compensation_mm, flow_direction, raw_model_spec, raw_name, remark, extra_params,
                created_by, updated_by, updated_at
            ) VALUES (
                :section_1_id, :system_type, :category, :standard_name, :model_spec, :sub_model_spec, :unit,
                :design_qty, :purchase_plan_qty,
                :main_dn, :sub_dn, :angle, :bending_radius_ratio, :bending_radius_m,
                :valve_model, :outer_diameter, :wall_thickness, :length_m,
                :pressure_rating, :compensation_mm, :flow_direction, :raw_model_spec, :raw_name, :remark, '{}'::jsonb,
                :operator_name, :operator_name, NOW()
            )
            ON CONFLICT (section_1_id, system_type, standard_name, model_spec, sub_model_spec) DO UPDATE SET
                category = EXCLUDED.category,
                unit = EXCLUDED.unit,
                design_qty = EXCLUDED.design_qty,
                purchase_plan_qty = EXCLUDED.purchase_plan_qty,
                main_dn = EXCLUDED.main_dn,
                sub_dn = EXCLUDED.sub_dn,
                angle = EXCLUDED.angle,
                bending_radius_ratio = EXCLUDED.bending_radius_ratio,
                bending_radius_m = EXCLUDED.bending_radius_m,
                valve_model = EXCLUDED.valve_model,
                outer_diameter = EXCLUDED.outer_diameter,
                wall_thickness = EXCLUDED.wall_thickness,
                length_m = EXCLUDED.length_m,
                pressure_rating = EXCLUDED.pressure_rating,
                compensation_mm = EXCLUDED.compensation_mm,
                flow_direction = EXCLUDED.flow_direction,
                raw_model_spec = EXCLUDED.raw_model_spec,
                raw_name = EXCLUDED.raw_name,
                remark = EXCLUDED.remark,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
        """

        for it in parsed_items:
            session.execute(text(upsert_sql), it)

        session.commit()
        print(f"✅ 成功提交事务！已入库 {len(parsed_items)} 条联网平衡阀记录。")

        # 4. 统计与核验
        cnt_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_fitting_baseline;")).scalar() or 0
        balance_cnt_after = session.execute(text("SELECT COUNT(*) FROM tube.tube_fitting_baseline WHERE category = '联网平衡阀';")).scalar() or 0
        print(f"🎉 [3/3] 导入后 tube.tube_fitting_baseline 总行数: {cnt_after} (净增: {cnt_after - cnt_before}), '联网平衡阀'行数: {balance_cnt_after}")

        summary_rows = session.execute(text("""
            SELECT section_1_id, system_type, category, COUNT(*) as cnt,
                   SUM(design_qty) as sum_design, SUM(purchase_plan_qty) as sum_plan
            FROM tube.tube_fitting_baseline
            WHERE category = '联网平衡阀'
            GROUP BY section_1_id, system_type, category
            ORDER BY section_1_id;
        """)).fetchall()

        print("\n📊 各标段入库数据汇总:")
        for r in summary_rows:
            print(f"  标段: {r[0]}, 系统: {r[1]}, 类别: {r[2]}, 条数: {r[3]}, 设计总量: {r[4]}, 采购计划总量: {r[5]}")

    except Exception as e:
        session.rollback()
        print(f"❌ 入库失败并已回滚，错误: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    main()
