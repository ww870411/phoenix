时间戳：2026-03-01
任务：月报查询页“热力图 + 波动TopN（绝对值）”增加统一切换开关（同比/环比/计划比）。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md
变更摘要：
- 前端查询页可视化区域新增统一按钮组（同比/环比/计划比），用于同步切换热力图和TopN视图口径。
- 补充 comparisonModeLabel 计算属性，统一驱动图表标题文案。
- 新增 mode-switch-group / mode-switch-btn / active 样式，提供激活态高亮。
- 更新进度文档与前后端README结构同步条目。
验证结论：
- comparisonModeLabel 已定义，模板引用不再存在未定义风险。
- rateValue(row) 已支持 yoy/mom/plan，统一切换会作用于热力图与TopN数据源。