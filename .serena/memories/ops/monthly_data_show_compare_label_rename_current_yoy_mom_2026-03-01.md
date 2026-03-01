时间戳：2026-03-01
任务：对比表字段命名优化：当前值->本期值、同比值->同期值、环比值->上期值。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 页面对比表表头替换为：本期值、同期值、上期值。
- XLSX 导出“对比明细”表头同步替换。
- 后端接口字段命名保持不变，仅前端展示层变更。

结果：
- 页面与导出命名一致，业务语义更清晰。