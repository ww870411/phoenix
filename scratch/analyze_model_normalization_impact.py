# -*- coding: utf-8 -*-
"""深度分析型号去 '.0' 对各业务表唯一约束、主外键关联与数据合并的影响"""

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
    # 去除无意义的 .0，例如 4.0 -> 4, 118.0 -> 118, 7.0 -> 7，但保留 4.5, 3.2, 4.9 等
    return re.sub(r'(\d+)\.0+(?!\d)', r'\1', spec.strip())

def main():
    s = SessionLocal()
    try:
        print("=== 1. 检查 tube.tube_pipe_baseline 的型号去 .0 影响 ===")
        pipe_rows = s.execute(text("""
            SELECT id, section_1_id, pipe_model_id, design_qty, purchase_plan_qty, remark
            FROM tube.tube_pipe_baseline
            ORDER BY section_1_id, id;
        """)).fetchall()

        sec_model_map = defaultdict(list)
        needs_change_count = 0
        collision_groups = []

        for r in pipe_rows:
            id_, sec, model, d_qty, p_qty, remark = r
            norm_model = normalize_pipe_spec(model)
            if norm_model != model:
                needs_change_count += 1
            sec_model_map[(sec, norm_model)].append((id_, sec, model, norm_model, d_qty, p_qty, remark))

        for (sec, norm_m), records in sec_model_map.items():
            if len(records) > 1:
                collision_groups.append((sec, norm_m, records))

        print(f"总记录数: {len(pipe_rows)}")
        print(f"需要规范化修改的记录数 (原值带 .0): {needs_change_count}")
        print(f"同标段内去 .0 后发生冲突/重叠的分组数: {len(collision_groups)}")

        if collision_groups:
            print("🚨 警告：发现同标段内存在冲突记录（需要合并）：")
            for sec, norm_m, recs in collision_groups:
                print(f"  标段: {sec} | 目标型号: {norm_m}")
                for rc in recs:
                    print(f"    id={rc[0]} | 原型号: {rc[2]} | 设计量: {rc[4]} | 采购量: {rc[5]} | 备注: {rc[6]}")
        else:
            print("✅ 完美：tube_pipe_baseline 中没有任何同标段冲突！所有带 .0 的型号去 .0 后在所属标段内均唯一！")

        print("\n=== 2. 检查价格表 tube.tube_material_price 的直管型号影响 ===")
        price_pipe_rows = s.execute(text("""
            SELECT id, supplier_name, applicable_sections, model_spec, unit_price
            FROM tube.tube_material_price
            WHERE material_kind = 'pipe' OR category = '保温管'
            ORDER BY id;
        """)).fetchall()

        price_map = defaultdict(list)
        price_change_count = 0
        for pr in price_pipe_rows:
            pid, sup, sec, spec, price = pr
            norm_spec = normalize_pipe_spec(spec)
            if norm_spec != spec:
                price_change_count += 1
            price_map[(sup, sec, norm_spec)].append((pid, sup, sec, spec, norm_spec, price))

        print(f"价格表保温管总记录数: {len(price_pipe_rows)}")
        print(f"其中带 .0 需要规范化的记录数: {price_change_count}")
        price_collisions = [k for k, v in price_map.items() if len(v) > 1]
        print(f"价格表中同供应商同标段去 .0 后重叠冲突组数: {len(price_collisions)}")
        for k in price_collisions:
            print(f"  供应商: {k[0]} | 标段: {k[1]} | 目标型号: {k[2]}")
            for item in price_map[k]:
                print(f"    id={item[0]} | 原规格={item[3]} | 单价={item[5]}")

        print("\n=== 3. 检查发货表 tube.tube_delivery 影响 ===")
        deliv_rows = s.execute(text("""
            SELECT id, order_no, section_1_id, pipe_model_id, shipped_qty
            FROM tube.tube_delivery
            ORDER BY id;
        """)).fetchall()
        deliv_need_change = [r for r in deliv_rows if normalize_pipe_spec(r[3]) != r[3]]
        print(f"发货总单据数: {len(deliv_rows)}，其中需要去 .0 的记录数: {len(deliv_need_change)}")

        print("\n=== 4. 检查每日计划表 tube.tube_daily_plan 影响 ===")
        plan_rows = s.execute(text("""
            SELECT id, section_1_id, plan_date, pipe_model_id, plan_qty
            FROM tube.tube_daily_plan
            ORDER BY id;
        """)).fetchall()
        plan_need_change = [r for r in plan_rows if normalize_pipe_spec(r[3]) != r[3]]
        print(f"每日计划总记录数: {len(plan_rows)}，其中需要去 .0 的记录数: {len(plan_need_change)}")

        # 检查计划表联合唯一约束是否有冲突
        plan_map = defaultdict(list)
        for r in plan_rows:
            norm_m = normalize_pipe_spec(r[3])
            plan_map[(r[1], str(r[2]), norm_m)].append(r)
        plan_collisions = [k for k, v in plan_map.items() if len(v) > 1 and any(normalize_pipe_spec(x[3]) != x[3] for x in v)]
        print(f"计划表中去 .0 后同标段同日期重叠冲突组数: {len(plan_collisions)}")

        print("\n=== 5. 检查每日消耗表 tube.tube_daily_usage 影响 ===")
        usage_rows = s.execute(text("""
            SELECT id, section_1_id, usage_date, pipe_model_id, usage_qty
            FROM tube.tube_daily_usage
            ORDER BY id;
        """)).fetchall()
        usage_need_change = [r for r in usage_rows if normalize_pipe_spec(r[3]) != r[3]]
        print(f"每日消耗总记录数: {len(usage_rows)}，其中需要去 .0 的记录数: {len(usage_need_change)}")

        usage_map = defaultdict(list)
        for r in usage_rows:
            norm_m = normalize_pipe_spec(r[3])
            usage_map[(r[1], str(r[2]), norm_m)].append(r)
        usage_collisions = [k for k, v in usage_map.items() if len(v) > 1 and any(normalize_pipe_spec(x[3]) != x[3] for x in v)]
        print(f"消耗表中去 .0 后同标段同日期重叠冲突组数: {len(usage_collisions)}")

    finally:
        s.close()

if __name__ == "__main__":
    main()
