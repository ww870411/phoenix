时间戳：2026-03-01
任务：隐藏“同比/环比/计划比（实时窗口）”对比列表中的期间/类型字段。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 对比表模板移除“期间”“类型”列（表头+单元格）。
- compare-table 最小宽度由 1080px 调整为 860px，减少横向空白。

结果：
- 对比列表视觉更简洁，重点聚焦口径/指标与对比值。