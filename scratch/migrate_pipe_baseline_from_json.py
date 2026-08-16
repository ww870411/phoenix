# -*- coding: utf-8 -*-
"""执行从 tube_config.json 导入直管设计量与采购量基准至 tube.tube_pipe_baseline 数据库表。"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.services.baseline_service import (
    migrate_pipe_baselines_from_json,
    list_pipe_baselines,
)


def run_migration():
    print("=== 开始执行保温直管基准量数据迁移 (JSON -> PostgreSQL) ===")
    result = migrate_pipe_baselines_from_json(operator_name="json_initial_migration")
    print(f"JSON 配置文件中读取记录数: {result['json_source_count']} 条")
    print(f"成功导入/更新至数据表记录数: {result['imported_count']} 条")
    print(f"数据库表中当前有效总记录数: {result['total_db_count']} 条")

    print("\n--- 抽取前 5 条导入数据核对 ---")
    rows = list_pipe_baselines()
    for i, r in enumerate(rows[:5], 1):
        print(f"[{i}] 标段: {r['section_1_id']:<15} 型号: {r['pipe_model_id']:<25} 单位: {r['unit']} 设计量: {r['design_qty']} 计划采购量: {r['purchase_plan_qty']}")

    print("\n✅ 数据迁移顺利完成！")


if __name__ == "__main__":
    run_migration()
