## 2025-11-08 仪表盘统一数据容器
- 背景：前端仪表盘仍使用静态演示数据，准备与 `/dashboard` 接口联调需要统一的状态管理。
- 变更：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 引入 `dashboardData` reactive 容器，`loadDashboardData` 成功后写入 `show_date`、`push_date`、`generated_at` 以及各个 section 原始数据（剔除 `push_date`、`展示日期`）。
- 效果：当前 UI 行为不变，但后续可直接从 `dashboardData.sections` 读取温度、边际利润、库存等模块数据，从而逐步替换静态常量。