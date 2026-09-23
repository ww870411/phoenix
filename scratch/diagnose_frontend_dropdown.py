# -*- coding: utf-8 -*-
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config
from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    _serialize_pipe_options,
    get_supply_management_demand_summary,
    get_supply_management_options,
)
from backend.api.v1.auth import AuthSession

class MockSession:
    def __init__(self, username="admin", group="Global_admin"):
        self.username = username
        self.group = group
        self.unit = None

def diagnose():
    payload = load_tube_config()
    print("=== 1. _serialize_pipe_options 返回的 pipe_models ===")
    pipe_models = _serialize_pipe_options(payload)
    print(f"总型号数: {len(pipe_models)}")
    jg_in_pipe_models = [p for p in pipe_models if "甲供" in p["pipe_model_id"]]
    print(f"其中包含甲供钢管: {len(jg_in_pipe_models)} 条")
    for p in jg_in_pipe_models:
        print(f"  {p['pipe_model_id']} (group: {p.get('category_group')})")

    print("\n=== 2. get_supply_management_demand_summary 返回的 rows ===")
    session_admin = MockSession(username="admin", group="Global_admin")
    resp = get_supply_management_demand_summary(session=session_admin)
    rows = resp.get("rows", [])
    print(f"demand-summary rows 数量: {len(rows)}")
    jg_rows = [r for r in rows if "甲供" in r.get("pipe_model_id", "")]
    print(f"其中甲供行数量: {len(jg_rows)} 条")
    for r in jg_rows:
        print(f"  sec={r.get('section_1_id')} | model={r.get('pipe_model_id')} | design={r.get('design_qty')}")

    print("\n=== 3. 模拟前端 SupplyManagementView.vue 计算属性 ===")
    # 前端全量型号 fullPipeModelOptions 构建逻辑:
    # modelMap 放入 allPipeModelOptions
    # summaryRows 中的 pipeModelId 也放入
    allPipeModelOptions = pipe_models
    summaryRows = [
        {
            "section1Id": r.get("section_1_id"),
            "pipeModelId": r.get("pipe_model_id"),
            "pipeModelName": r.get("pipe_model_name") or r.get("pipe_model_id"),
        }
        for r in rows
    ]

    # 测试不同 selectedSupplyEntityId
    # 天地龙:
    for test_entity_id in ["tiandilong", "kaiyuan", "xinruide", "tangshan_wanrun"]:
        sup_entity = next((e for e in payload.get("supply_entities", []) if e.get("entity_id") == test_entity_id), None)
        if not sup_entity:
            continue
        sec_ids = set(sup_entity.get("section_1_ids") or [])
        print(f"\n--- 供给主体: {test_entity_id} ({sup_entity.get('entity_name')}) ---")
        print(f"管辖标段: {sec_ids}")
        
        # 前端逻辑:
        # currentAssignedPipeModelIds:
        assigned_models = set()
        for r in summaryRows:
            if r["section1Id"] in sec_ids and r["pipeModelId"]:
                assigned_models.add(r["pipeModelId"])
        
        jg_assigned = [m for m in assigned_models if "甲供" in m]
        print(f"该供给主体下的可选型号总数: {len(assigned_models)}，其中甲供型号数: {len(jg_assigned)}")
        for m in jg_assigned:
            print(f"    * {m}")

    print("\n=== 4. 检查前端当前供给主体的切换状态 ===")
    options_resp = get_supply_management_options(session=session_admin)
    print(f"current_supply_entity_ids: {options_resp.get('current_supply_entity_ids')}")

if __name__ == "__main__":
    diagnose()
