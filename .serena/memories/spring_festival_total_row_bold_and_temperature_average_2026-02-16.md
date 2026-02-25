时间：2026-02-16
任务：在 /projects/daily_report_spring_festval_2026/spring-dashboard 页面中，强化两张表“合计”行显示，并修正气温合计算法。

变更文件清单：
1) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 页面模板：两张表的行渲染增加 class 绑定 `mini-table-total-row`（条件：row.isTotal）。
- 样式：新增 `.mini-table .mini-table-total-row td { font-weight: 700; }`，使“合计”行加粗。
- 算法：新增 `averageRowsByField(rows, field)`，将 `coalRowsWithTotal` 与 `complaintRowsWithTotal` 的 `temperature` 合计由求和改为算术平均。
- 其余字段保持 `sumRowsByField` 原汇总逻辑；净投诉量合计继续显示 `-`。

结果：
- 两张表“合计”行视觉上更显眼；
- 气温合计语义修正为区间平均温度，避免误用累加值。