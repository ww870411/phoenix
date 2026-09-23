# -*- coding: utf-8 -*-
"""
全库执行保温管型号去 '.0' 规范化清洗：
1. tube.tube_pipe_baseline
2. tube.tube_material_price (保温管类)
3. tube.tube_delivery
4. tube.tube_daily_plan (含重复记录合并求和)
5. tube.tube_daily_usage (含重复记录合并求和)
6. backend/projects/insulation_pipe_supply_2026/seeds/pipe_baselines_seed.json
"""

import os
import sys
import re
import json
from collections import defaultdict
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal


def normalize_pipe_spec(spec: str) -> str:
    """去除无意义的 .0，保留有效小数（如 4.5, 3.2, 4.9 等）"""
    if not spec:
        return ""
    return re.sub(r'(\d+)\.0+(?!\d)', r'\1', str(spec).strip())


def run_full_normalization():
    print("==========================================================")
    print("开始执行全库保温管型号去 '.0' 规范化与原子事务清洗")
    print("==========================================================")

    session = SessionLocal()
    try:
        # -----------------------------------------------------------------
        # 1. tube.tube_pipe_baseline
        # -----------------------------------------------------------------
        print("\n[Step 1/6] 清洗 tube.tube_pipe_baseline 表...")
        rows_baseline = session.execute(text("SELECT id, pipe_model_id FROM tube.tube_pipe_baseline;")).fetchall()
        baseline_updated = 0
        for id_, model in rows_baseline:
            norm_model = normalize_pipe_spec(model)
            if norm_model != model:
                session.execute(
                    text("UPDATE tube.tube_pipe_baseline SET pipe_model_id = :norm, updated_at = NOW() WHERE id = :id"),
                    {"norm": norm_model, "id": id_}
                )
                baseline_updated += 1
        print(f"  -> tube_pipe_baseline 更新完成: 共更新 {baseline_updated} 条记录")

        # -----------------------------------------------------------------
        # 2. tube.tube_material_price (保温管)
        # -----------------------------------------------------------------
        print("\n[Step 2/6] 清洗 tube.tube_material_price 表 (保温管类)...")
        rows_price = session.execute(text("""
            SELECT id, model_spec FROM tube.tube_material_price 
            WHERE material_kind = 'pipe' OR category = '保温管';
        """)).fetchall()
        price_updated = 0
        for id_, spec in rows_price:
            norm_spec = normalize_pipe_spec(spec)
            if norm_spec != spec:
                session.execute(
                    text("UPDATE tube.tube_material_price SET model_spec = :norm, updated_at = NOW() WHERE id = :id"),
                    {"norm": norm_spec, "id": id_}
                )
                price_updated += 1
        print(f"  -> tube_material_price 更新完成: 共更新 {price_updated} 条记录")

        # -----------------------------------------------------------------
        # 3. tube.tube_delivery
        # -----------------------------------------------------------------
        print("\n[Step 3/6] 清洗 tube.tube_delivery 表...")
        rows_delivery = session.execute(text("SELECT id, pipe_model_id FROM tube.tube_delivery;")).fetchall()
        delivery_updated = 0
        for id_, model in rows_delivery:
            norm_model = normalize_pipe_spec(model)
            if norm_model != model:
                session.execute(
                    text("UPDATE tube.tube_delivery SET pipe_model_id = :norm, updated_at = NOW() WHERE id = :id"),
                    {"norm": norm_model, "id": id_}
                )
                delivery_updated += 1
        print(f"  -> tube_delivery 更新完成: 共更新 {delivery_updated} 条记录")

        # -----------------------------------------------------------------
        # 4. tube.tube_daily_plan (含同标段同日期同型号合并去重)
        # -----------------------------------------------------------------
        print("\n[Step 4/6] 清洗并合并 tube.tube_daily_plan 表...")
        rows_plan = session.execute(text("""
            SELECT id, section_1_id, plan_date, pipe_model_id, plan_qty 
            FROM tube.tube_daily_plan;
        """)).fetchall()

        plan_groups = defaultdict(list)
        for r in rows_plan:
            norm_model = normalize_pipe_spec(r[3])
            plan_groups[(r[1], str(r[2]), norm_model)].append(r)

        plan_updated = 0
        plan_merged_groups = 0
        plan_deleted_rows = 0

        for (sec, dt, norm_model), items in plan_groups.items():
            if len(items) == 1:
                id_, _, _, old_model, _ = items[0]
                if old_model != norm_model:
                    session.execute(
                        text("UPDATE tube.tube_daily_plan SET pipe_model_id = :norm WHERE id = :id"),
                        {"norm": norm_model, "id": id_}
                    )
                    plan_updated += 1
            else:
                # 存在多条去 .0 后重叠的记录，先合并计算，再删除冗余，最后更新保留行
                plan_merged_groups += 1
                total_qty = sum(float(x[4] or 0) for x in items)
                # 优先保留已经是规范名称的行，否则保留第一行
                keep_item = next((x for x in items if x[3] == norm_model), items[0])
                keep_id = keep_item[0]
                delete_ids = [x[0] for x in items if x[0] != keep_id]

                # 1. 先删除其余重叠记录，释放唯一索引空间
                session.execute(
                    text("DELETE FROM tube.tube_daily_plan WHERE id = ANY(:del_ids)"),
                    {"del_ids": delete_ids}
                )
                # 2. 再更新保留行
                session.execute(
                    text("UPDATE tube.tube_daily_plan SET pipe_model_id = :norm, plan_qty = :qty WHERE id = :id"),
                    {"norm": norm_model, "qty": total_qty, "id": keep_id}
                )
                plan_updated += 1
                plan_deleted_rows += len(delete_ids)

        print(f"  -> tube_daily_plan 更新完成: 更新/规范化 {plan_updated} 条, 合并冲突组 {plan_merged_groups} 组, 移除重复记录 {plan_deleted_rows} 条")

        # -----------------------------------------------------------------
        # 5. tube.tube_daily_usage (含同标段同日期同型号合并去重)
        # -----------------------------------------------------------------
        print("\n[Step 5/6] 清洗并合并 tube.tube_daily_usage 表...")
        rows_usage = session.execute(text("""
            SELECT id, section_1_id, usage_date, pipe_model_id, usage_qty, loss_qty 
            FROM tube.tube_daily_usage;
        """)).fetchall()

        usage_groups = defaultdict(list)
        for r in rows_usage:
            norm_model = normalize_pipe_spec(r[3])
            usage_groups[(r[1], str(r[2]), norm_model)].append(r)

        usage_updated = 0
        usage_merged_groups = 0
        usage_deleted_rows = 0

        for (sec, dt, norm_model), items in usage_groups.items():
            if len(items) == 1:
                id_, _, _, old_model, _, _ = items[0]
                if old_model != norm_model:
                    session.execute(
                        text("UPDATE tube.tube_daily_usage SET pipe_model_id = :norm WHERE id = :id"),
                        {"norm": norm_model, "id": id_}
                    )
                    usage_updated += 1
            else:
                usage_merged_groups += 1
                total_usage = sum(float(x[4] or 0) for x in items)
                total_loss = sum(float(x[5] or 0) for x in items)
                keep_item = next((x for x in items if x[3] == norm_model), items[0])
                keep_id = keep_item[0]
                delete_ids = [x[0] for x in items if x[0] != keep_id]

                # 1. 先删除其余重叠记录
                session.execute(
                    text("DELETE FROM tube.tube_daily_usage WHERE id = ANY(:del_ids)"),
                    {"del_ids": delete_ids}
                )
                # 2. 再更新保留行
                session.execute(
                    text("UPDATE tube.tube_daily_usage SET pipe_model_id = :norm, usage_qty = :u_qty, loss_qty = :l_qty WHERE id = :id"),
                    {"norm": norm_model, "u_qty": total_usage, "l_qty": total_loss, "id": keep_id}
                )
                usage_updated += 1
                usage_deleted_rows += len(delete_ids)

        print(f"  -> tube_daily_usage 更新完成: 更新/规范化 {usage_updated} 条, 合并冲突组 {usage_merged_groups} 组, 移除重复记录 {usage_deleted_rows} 条")

        # 提交所有数据库变更
        session.commit()
        print("\n✅ 所有数据库表事务提交成功！")

        # -----------------------------------------------------------------
        # 6. 系统种子文件 pipe_baselines_seed.json
        # -----------------------------------------------------------------
        print("\n[Step 6/6] 清洗系统种子文件 seeds/pipe_baselines_seed.json...")
        seed_path = os.path.join(project_root, "backend", "projects", "insulation_pipe_supply_2026", "seeds", "pipe_baselines_seed.json")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        seed_updated = 0
        for item in seed_data:
            old_m = item.get("pipe_model_id", "")
            norm_m = normalize_pipe_spec(old_m)
            if norm_m != old_m:
                item["pipe_model_id"] = norm_m
                seed_updated += 1

        with open(seed_path, "w", encoding="utf-8") as f:
            json.dump(seed_data, f, ensure_ascii=False, indent=2)
        print(f"  -> 种子文件规范化完成: 共更新 {seed_updated} 项")

    except Exception as e:
        session.rollback()
        print(f"\n❌ 清洗过程发生异常，已原子回滚！错误详情: {e}")
        raise
    finally:
        session.close()

    print("\n==========================================================")
    print("全库清洗完成！准备执行清洗后健康核验...")
    print("==========================================================")


if __name__ == "__main__":
    run_full_normalization()
