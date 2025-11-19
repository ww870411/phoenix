# 2025-12-11 数据分析指标组自由组合
- 位置：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue
- 变更：移除 `metric_group_views` 驱动的禁用判断，`resolvedMetricGroups` 直接使用全部指标组；模板取消“当前视图不支持该组”提示，复选框不再被禁用。
- 行为：所有单位/分析模式下可任选任意指标组；若某些指标无返回数据（timeline/snapshot 缺值），沿用 `warnings` 与“以下指标暂缺数据”提示告知用户，无需再限制勾选行为。
- 文档：frontend/README.md 与 backend/README.md 补充说明该策略改动，progress.md 记录留痕。