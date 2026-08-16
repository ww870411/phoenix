# -*- coding: utf-8 -*-
"""测试全局管理配置接口 get_global_management_config 与 save_global_management_config_section。"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    get_global_management_config,
    save_global_management_config_section,
    TubeConfigSectionSavePayload,
)
from unittest.mock import MagicMock
from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config


def run_tests():
    fake_session = MagicMock()
    fake_session.username = "admin_tester"
    fake_session.group = "Global_admin"
    fake_session.unit = "总部"

    print("=== [1/3] 测试 get_global_management_config 读取全局配置 ===")
    res = get_global_management_config(session=fake_session)
    assert res["ok"] is True
    config = res["config"]
    assert "baseline_presets" in config, "返回的 config 中缺少 baseline_presets 键！"
    presets = config["baseline_presets"]
    print(f" -> 成功获取 baseline_presets 条数: {len(presets)}")
    assert len(presets) == 89, f"期望 89 条记录，实际获得 {len(presets)}"

    # 验证 high_lot_1 下的型号
    high_lot_1_items = [p for p in presets if p["section_1_id"] == "high_lot_1"]
    print(f" -> high_lot_1 标段基准量条数: {len(high_lot_1_items)}")
    assert len(high_lot_1_items) == 9

    print("\n=== [2/3] 验证 tube_config.json 物理文件中确实不包含 baseline_presets ===")
    raw_file_cfg = load_tube_config()
    assert "baseline_presets" not in raw_file_cfg, "警告：物理 JSON 文件中依然包含 baseline_presets！"
    print(" -> 物理 JSON 文件纯净无基准量冗余 [OK]")

    print("\n=== [3/3] 测试前端保存设计基准区块接口 ===")
    payload = TubeConfigSectionSavePayload(
        section="baseline_presets",
        data=presets,
    )
    mock_req = MagicMock()
    mock_req.client.host = "127.0.0.1"

    save_res = save_global_management_config_section(
        payload=payload,
        request=mock_req,
        session=fake_session,
    )
    assert save_res["ok"] is True
    assert len(save_res["config"]["baseline_presets"]) == 89
    print(" -> 保存接口执行成功，返回的 config 中包含完整的 89 条基准数据 [OK]")

    # 再次检查物理 JSON 文件依然没有被写入 baseline_presets
    raw_file_cfg_after = load_tube_config()
    assert "baseline_presets" not in raw_file_cfg_after, "警告：保存后物理 JSON 文件被意外写入了 baseline_presets！"
    print(" -> 保存后物理 JSON 文件依然保持纯净 [OK]")

    print("\n🎉 全局管理界面 API 对接验证 100% 成功！前端刷新页面即可完整看到所有标段基准量！")


if __name__ == "__main__":
    run_tests()
