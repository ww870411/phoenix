时间：2026-03-01
主题：monthly_data_show 新增计划比（plan compare）

用户诉求：
- 在同比/环比之外，新增“计划比”，与当月 plan 对比。

改动文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

后端：
- QueryComparisonRow 新增 plan_value/plan_rate。
- QueryComparisonResponse 新增 plan_window_label。
- 新增 _fetch_plan_value_map：
  - 当前窗口按 type='plan' 抽取计划值；
  - 基础指标与计算指标都支持（计算指标通过计算引擎得到计划值）。
- query-comparison 返回 current 相对 plan 的偏差率。

前端：
- 口径切换新增 plan。
- 对比表新增 计划值/计划比 列。
- 热力图/TopN 的 rateValue 支持计划比。
- 分析要点增加计划比统计与Top项。
- 导出对比sheet新增 plan_value/plan_rate。

结果：
- 页面支持同比/环比/计划比三口径统一分析与导出。