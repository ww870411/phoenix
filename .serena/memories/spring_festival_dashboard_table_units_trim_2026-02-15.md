时间戳：2026-02-15
任务：春节看板两张表中，除气温外去除原煤消耗量/投诉量单位展示。

变更文件：
1) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

代码摘要：
- 原煤表格：本期/同期列从 formatMetric(..., '吨', 0) 调整为 formatMetric(..., '', 0)。
- 投诉表格：总投诉量/净投诉量列从 formatMetric(..., '件', 0) 调整为 formatMetric(..., '', 0)。
- 气温列保持 formatMetric(..., '℃', 1) 不变。

结果：
- 两张表仅气温显示单位，其他指标显示纯数字；合计行逻辑保持不变。