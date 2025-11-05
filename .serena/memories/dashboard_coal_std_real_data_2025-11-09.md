# 2025-11-09 标煤消耗量板块接入
- 时间：2025-11-09
- 变更文件：
  - `frontend/src/daily_report_25_26/pages/DashBoard.vue`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
- 摘要：仪表盘“标煤消耗量对比”改为读取 `/dashboard` 的“5.标煤耗量”节点，新增 `coalStdSection/coalStdSeries` 计算属性，图表/表格与摘要卡片显示本期/同期数据并附带两位小数标签；缺失时回退演示数据。
- 验证：加载真实 dashboard 数据后，图表中的“本期/同期”柱、表格及顶部“集团标煤消耗”卡片均与接口数据一致，标签和 tooltip 显示两位小数。