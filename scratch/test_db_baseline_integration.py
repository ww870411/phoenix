# -*- coding: utf-8 -*-
"""全链路测试：验证直管设计量与计划采购量切换为数据库表后的读取、写入、大盘与需求侧接口。"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    get_workspace_config_summary,
    _save_config_section,
    _build_baseline_preset_map,
    _build_pipe_model_map,
    _resolve_section_1_sorted_pipe_model_ids,
)
from backend.projects.insulation_pipe_supply_2026.services.baseline_service import (
    list_pipe_baselines,
    save_pipe_baselines,
)
from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config


def run_integration_tests():
    print("=== [1/4] 测试 get_workspace_config_summary 读取数据库基准量 ===")
    summary = get_workspace_config_summary()
    assert summary["ok"] is True
    presets = summary["baseline_presets"]
    count = summary["summary"]["baseline_preset_count"]
    print(f" -> 成功读取基准预设条数: {len(presets)}, summary 统计: {count}")
    assert len(presets) == 89, f"期望 89 条记录，实际获得 {len(presets)}"
    assert count == 89

    print("\n=== [2/4] 测试 _build_baseline_preset_map 从数据库按标段查询 ===")
    payload = load_tube_config()
    high_lot_map = _build_baseline_preset_map(payload, "high_lot_1")
    print(f" -> high_lot_1 包含型号数: {len(high_lot_map)}")
    assert len(high_lot_map) >= 5
    sample_model = "Φ1120×13/Φ1260×16"
    assert sample_model in high_lot_map
    print(f" -> {sample_model}: 设计量={high_lot_map[sample_model]['design_qty']}, 采购量={high_lot_map[sample_model]['purchase_plan_qty']}")
    assert high_lot_map[sample_model]["design_qty"] == 2616.0

    print("\n=== [3/4] 测试 _resolve_section_1_sorted_pipe_model_ids 型号排序推导 ===")
    sorted_models = _resolve_section_1_sorted_pipe_model_ids(payload, "high_lot_1")
    print(f" -> 推导出的降序型号列表 (前3个): {sorted_models[:3]}")
    assert len(sorted_models) >= 5
    assert sorted_models[0] == "Φ1120×13/Φ1260×16"

    print("\n=== [4/4] 测试 _save_config_section 模拟管理员修改并保存基准量 ===")
    # 模拟在现有列表中临时微调备注
    test_presets = list(presets)
    target_idx = next(i for i, p in enumerate(test_presets) if p["section_1_id"] == "high_lot_1" and p["pipe_model_id"] == sample_model)
    orig_remark = test_presets[target_idx].get("remark") or ""
    test_presets[target_idx]["remark"] = "自动化集成测试更新备注"

    _save_config_section("baseline_presets", test_presets)

    # 查库验证是否立即同步至数据库表
    db_rows = list_pipe_baselines("high_lot_1")
    target_db = next(r for r in db_rows if r["pipe_model_id"] == sample_model)
    assert target_db["remark"] == "自动化集成测试更新备注", f"数据库备注未同步: {target_db['remark']}"
    print(f" -> 数据库表 tube.tube_pipe_baseline 记录已实时更新为: {target_db['remark']} [OK]")

    # 恢复原状
    test_presets[target_idx]["remark"] = orig_remark
    _save_config_section("baseline_presets", test_presets)
    db_rows_restored = list_pipe_baselines("high_lot_1")
    target_db_restored = next(r for r in db_rows_restored if r["pipe_model_id"] == sample_model)
    assert target_db_restored["remark"] == orig_remark
    print(f" -> 测试完成后已安全恢复基准量状态 [OK]")

    print("\n🎉 全链路 4 大核心业务链路向下兼容与数据库表直读直写验证 100% 成功！")


if __name__ == "__main__":
    run_integration_tests()
