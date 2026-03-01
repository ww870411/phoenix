时间戳：2026-03-01
任务：优化月报查询导出XLSX样式，并移除热力图/TopN子工作表。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

前端实现：
- 新增 finalizeSheet(sheet, columnWidths) 统一处理导出表：
  - 设置列宽；
  - 设置表头自动筛选（autofilter）。
- 导出字段优化：
  - 表头改为中文业务字段名；
  - 数值按页面展示格式导出（百分比、差值符号、统一小数位）。
- 子表调整：
  - 删除 `${当前口径}热力图` 和 `${当前口径}TopN` 两个工作表；
  - 保留并优化 `汇总信息/查询结果/对比明细/专业分析/气温日序同比/气温汇总`。

结果：
- 导出文件版式可读性提升；
- 子表结构与用户需求一致，不再包含热力图与TopN。