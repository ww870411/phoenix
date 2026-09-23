# -*- coding: utf-8 -*-
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.api.workspace import get_supply_management_demand_summary
from backend.services.auth import AuthSession

def test_api():
    # 模拟管理员或者天地龙会话
    admin_session = AuthSession(username="admin", role="admin", group="Global_admin")
    resp_admin = get_supply_management_demand_summary(session=admin_session)
    rows_admin = resp_admin.get("rows", [])
    print(f"管理员请求 demand-summary 返回总行数: {len(rows_admin)}")
    
    low_lot_6_rows = [r for r in rows_admin if r.get("section_1_id") == "low_lot_6"]
    print(f"其中 low_lot_6 的行数: {len(low_lot_6_rows)}")
    for r in low_lot_6_rows:
        is_jg = "【甲供】" if "甲供" in r.get("pipe_model_id", "") else ""
        print(f"  {r.get('pipe_model_id'):<35} {is_jg}")

    # 模拟天地龙账号
    tiandilong_session = AuthSession(username="tiandilong", role="supplier", group="tube_supplier_admin")
    resp_tdl = get_supply_management_demand_summary(session=tiandilong_session)
    rows_tdl = resp_tdl.get("rows", [])
    print(f"\n天地龙账号请求 demand-summary 返回总行数: {len(rows_tdl)}")

if __name__ == "__main__":
    test_api()
