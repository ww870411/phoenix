# 2026-05-24 tube项目审计问题第一轮修复

时间：2026-05-24

## 背景
基于 `configs/3.23 tube项目审计（agy）.md` 与用户确认，优先修复已验证存在的审计问题 1、2、4，并按代码逻辑确认问题 3 成立后一并修复。

## 变更文件
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `backend/projects/insulation_pipe_supply_2026/services/config_service.py`
- `backend/projects/insulation_pipe_supply_2026/services/demand_management_service.py`
- `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

## 修复摘要
1. 计划矩阵回显：`get_demand_management_plan_matrix` 改为按 `pipe_model_id::date` 扁平 key 读取 `list_plan_records` 返回值，修复查询回显恒为 0。
2. 施工单位权限：`resolve_accessible_station_ids` 新增解析 `construction_units` 的 `unit_id / unit_name / username / station_ids`，施工单位账号可正确获得换热站范围。
3. 净缺口公式：供给侧 `inbound_pipeline_qty` 从 `pending_arrival + pending_receive + pending_warehouse` 收口为仅统计 `pending_arrival`，避免与 `total_arrived_qty` / `station_inventory_qty` 双扣。
4. 基准量数据源：需求侧与供给侧不再查询 `tube.tube_baseline_quantity`，统一只读取 `backend_data/projects/insulation_pipe_supply_2026/tube_config.json` 的 `baseline_presets`。删除了仅用于读取该表的 `list_baseline_rows`、`list_baseline_rows_all`。

## 验证
- 运行 `python -m py_compile backend/projects/insulation_pipe_supply_2026/api/workspace.py backend/projects/insulation_pipe_supply_2026/services/config_service.py backend/projects/insulation_pipe_supply_2026/services/demand_management_service.py backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- 结果：通过，无语法错误。

## 结论
当前 tube 项目已完成第一轮审计问题修复，可以继续进行施工单位账号、计划回显和供给侧净缺口口径的联调验证。