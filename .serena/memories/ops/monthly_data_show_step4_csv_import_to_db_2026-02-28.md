时间：2026-02-28
需求：新增“第4步”，完成 CSV 到数据库 month_data_show 的入库流程。
变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/daily_report_25_26/services/api.js
3) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
4) configs/progress.md
5) backend/README.md
6) frontend/README.md
实现摘要：
- 后端新增 POST /monthly-data-show/import-csv。
- 解析并校验 CSV（UTF-8，必需字段 company/item/unit/value/date/period/type/report_month）。
- 使用 UPSERT 写入 month_data_show：ON CONFLICT(company,item,date,period,type) DO UPDATE。
- 前端新增第4步卡片：选择 CSV -> 上传并入库 -> 显示处理条数。
结果：
- monthly_data_show 流程升级为 4 步，已覆盖 CSV 导出到数据库写入闭环。