时间：2026-05-24
主题：insulation_pipe_supply_2026 日期口径从单一 biz_date 拆分为 plan_start_date + show_date。

本次变更结论：
- `plan_start_date` 保留为采集窗口控制日期。
- 需求侧计划录入窗口固定显示 `plan_start_date ~ plan_start_date+2`。
- 实际使用量默认采集日期改为 `plan_start_date - 1`。
- 新增 `show_date` 作为展示窗口控制日期。
- 展示层滚动三日计划量按 `show_date ~ show_date+2` 汇总。
- 展示层实际使用、库存、累计量等默认展示到 `show_date - 1`。
- `biz_date` 旧逻辑已解除；代码保留对配置中旧 `biz_date` 的兼容回退，仅用于迁移读取。

代码修改：
- `backend/projects/insulation_pipe_supply_2026/services/config_service.py`
  - 新增 `get_configured_show_date(payload)`
  - 新增 `get_usage_collection_date(payload)`
  - `plan_start_date` 缺省值不再依赖旧 `biz_date`
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
  - `config-summary`、需求侧 options、供给侧 options、库管侧 options、全局管理配置返回新增/改用 `show_date`
  - 需求侧默认使用量日期改为 `usage_collection_date = plan_start_date - 1`
  - 全局管理配置区块保存从 `biz_date` 切换为 `show_date`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`
  - 配置项标签从 `biz_date` 改为 `show_date`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
  - 顶部口径展示改为“展示日期 / 计划起始日期 / 实际使用采集日期”
  - 实际使用量标题改绑 `usageDate`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
  - 顶部日期展示改为 `showDate`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
  - 顶部日期展示改为 `show_date`
- `backend_data/projects/insulation_pipe_supply_2026/tube_config.json`
  - 顶层日期键由 `biz_date` 更新为 `show_date`

文档同步：
- 已修改两份方案文档：
  - `configs/5.24_tube项目建设方案_v5.2_物流链管理版.md`
  - `configs/5.24_tube项目完整构建流程计划_v5.2执行版.md`
- 已同步：
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`

验证：
- `frontend` 执行 `npm run build` 通过。
- 后端尝试执行 compileall 语法检查，但 exec 环境创建进程失败，未完成该项自动验证。