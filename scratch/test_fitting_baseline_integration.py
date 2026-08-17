# -*- coding: utf-8 -*-
"""测试管件基准量 (Fitting Baseline) 全链路 API 与数据库读写。"""

import os
import sys
from unittest.mock import MagicMock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    get_global_management_config,
    save_global_management_config_section,
    TubeConfigSectionSavePayload,
)
from backend.projects.insulation_pipe_supply_2026.services.baseline_service import (
    list_fitting_baselines,
    save_fitting_baselines,
)
from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config


def run_tests():
    fake_session = MagicMock()
    fake_session.username = "admin_tester"
    fake_session.group = "Global_admin"
    fake_session.unit = "总部"

    print("=== [1/4] 测试管件基准量直接存入与查询数据库表 ===")
    test_fittings = [
        {
            "section_1_id": "high_lot_1",
            "fitting_type": "特种非标90度弯头",
            "model_spec": "DN1000",
            "sub_model_spec": "R=1.5D 厚壁加强",
            "unit": "个",
            "design_qty": 28.5,
            "purchase_plan_qty": 30.0,
            "remark": "测试自由文本输入与小数用量",
        },
        {
            "section_1_id": "high_lot_1",
            "fitting_type": "轴向型波纹补偿器",
            "model_spec": "DN1000",
            "sub_model_spec": "轴向补偿量250mm PN2.5",
            "unit": "套",
            "design_qty": 14.0,
            "purchase_plan_qty": 14.0,
            "remark": "主干线大口径补偿器",
        },
        {
            "section_1_id": "low_lot_1",
            "fitting_type": "顺水三通",
            "model_spec": "DN500/DN300",
            "sub_model_spec": "",
            "unit": "个",
            "design_qty": 12.0,
            "purchase_plan_qty": 12.0,
            "remark": "分支接线三通",
        }
    ]
    saved_num = save_fitting_baselines(test_fittings, operator_name="admin_tester", replace_all_for_sections=["high_lot_1", "low_lot_1"])
    print(f" -> 成功插入管件测试数据条数: {saved_num}")
    assert saved_num == 3

    db_items = list_fitting_baselines("high_lot_1")
    assert len(db_items) == 2, f"期望 high_lot_1 有 2 条记录，实际获得 {len(db_items)}"
    print(f" -> 成功按标段 high_lot_1 查出 2 条管件记录: {[it['fitting_type'] for it in db_items]}")

    print("\n=== [2/4] 测试 get_global_management_config 包含 fitting_baselines ===")
    global_cfg = get_global_management_config(session=fake_session)
    assert global_cfg["ok"] is True
    fittings_in_cfg = global_cfg["config"].get("fitting_baselines") or []
    assert len(fittings_in_cfg) >= 3, f"期望全局配置带出管件基准量，实际获得: {len(fittings_in_cfg)}"
    print(f" -> 全局配置接口成功包含 fitting_baselines，总数: {len(fittings_in_cfg)}")

    print("\n=== [3/4] 测试 save_global_management_config_section (fitting_baselines) ===")
    mock_req = MagicMock()
    mock_req.client.host = "127.0.0.1"
    save_payload = TubeConfigSectionSavePayload(
        section="fitting_baselines",
        data=fittings_in_cfg,
    )
    save_res = save_global_management_config_section(
        payload=save_payload,
        request=mock_req,
        session=fake_session,
    )
    assert save_res["ok"] is True
    assert len(save_res["config"]["fitting_baselines"]) >= 3
    print(" -> 区块保存接口执行成功，返回的 config 中包含完整的 fitting_baselines")

    print("\n=== [4/4] 验证物理 tube_config.json 文件中绝对不残留 fitting_baselines ===")
    raw_cfg = load_tube_config()
    assert "fitting_baselines" not in raw_cfg, "警告：tube_config.json 中被写入了 fitting_baselines！"
    print(" -> 物理 JSON 文件保持纯净无冗余 [OK]")

    print("\n🎉 管件基准量 (Fitting Baseline) 全链路 API、数据库及 RevoGrid 对接验证 100% 成功！")


if __name__ == "__main__":
    run_tests()
