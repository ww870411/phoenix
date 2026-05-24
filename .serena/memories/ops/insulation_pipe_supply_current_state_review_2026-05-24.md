时间：2026-05-24
任务：阅读 `configs/5.24_tube项目建设方案_v5.2_物流链管理版.md`、`configs/5.24_tube项目完整构建流程计划_v5.2执行版.md`，并核对 `insulation_pipe_supply_2026` 当前代码状态。

结论摘要：
- 项目已从方案期进入“主流程已落地、正在做口径收口与 dashboard 补尾”的阶段。
- 业务主规则与代码当前一致的核心点：
  - 运行配置主源为 `backend_data/projects/insulation_pipe_supply_2026/tube_config.json`
  - `biz_date` / `plan_start_date` / `plan_editable_days` 由配置维护
  - 施工单位映射维护在 `construction_units.station_ids`
  - 基准量主数据来自 `baseline_presets`
  - `tube.tube_baseline_quantity` 不再作为运行依赖
  - 当前库存口径为“总到货 - 总使用量”
  - 三日净缺口只扣减 `pending_arrival`
  - 在途时长到“确认到货”截止，`cancelled` 不显示
- 当前配置文件实际值核对：`biz_date=2026-05-27`、`plan_start_date=2026-05-27`、`plan_editable_days=1`。
- 前端已落地 5 个页面：`dashboard`、`global_management`、`supply_management`、`demand_management`、`warehouse_management`；`TubeProjectPageRouterView.vue` 已完成页面 key 映射。
- 后端项目路由已注册到 `backend/api/v1/project_router_registry.py`，并通过 `backend/projects/insulation_pipe_supply_2026/api/router.py` 挂载 workspace 路由。
- 后端 API 已覆盖：配置摘要、全局配置维护、需求侧选项/基准量/计划/使用/物流记录/到货确认/施工接收、供给侧选项/供需汇总/发货/撤销、库管侧选项/台账/库管确认；dashboard 专项汇总接口尚未形成。
- `shared.js` 中 `useTubeRealtimeRefresh` 已实现页面激活、窗口聚焦、标签页可见时重拉配置；需求页、供给页、库管页、全局管理页均已接入该刷新机制。
- `DashboardView.vue` 当前仍是轻量占位式首版，只展示配置摘要与说明文案，尚未接入正式汇总卡片、图形和风险提示接口。

证据文件：
- `configs/5.24_tube项目建设方案_v5.2_物流链管理版.md`
- `configs/5.24_tube项目完整构建流程计划_v5.2执行版.md`
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `backend/projects/insulation_pipe_supply_2026/services/config_service.py`
- `backend/projects/insulation_pipe_supply_2026/services/demand_management_service.py`
- `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/*.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/shared.js`
- `backend_data/projects/insulation_pipe_supply_2026/tube_config.json`
