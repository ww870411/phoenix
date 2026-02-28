时间：2026-02-28
需求：在“是否聚合口径”同栏新增“期间月份是否聚合”开关；不选则不聚合。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) backend/projects/monthly_data_show/api/workspace.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 前端新增 filters.aggregateMonths 开关与文案，并透传 aggregate_months。
- 后端 QueryRequest 增加 aggregate_months。
- 查询分组逻辑支持按月份区间聚合（aggregate_months=true 时不按 date/report_month 分组）。
- 该开关可与 aggregate_companies 同时生效。
结果：
- 用户可在月份区间下自由切换“逐月明细”与“区间聚合”。