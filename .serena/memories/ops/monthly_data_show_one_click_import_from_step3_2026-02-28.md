时间：2026-02-28
需求：新增“第3步结果一键入库”。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现摘要：
- 新增 lastExtractedCsvFile 状态。
- 第3步导出后将 blob 封装为 File 并缓存。
- 第4步新增“使用第3步结果一键入库”按钮，直接复用现有 importCsvToDatabase 流程。
- 同时保留手动选 CSV 入库入口。
结果：
- 用户可在导出后直接一键写入 month_data_show，减少重复上传操作。