时间：2026-03-01
需求：导入页提取完成后展示规则命中统计。
实现：
1) backend/projects/monthly_data_show/api/workspace.py
- extract-csv 接口将提取统计写入响应头：
  - X-Monthly-Semi-Calculated-Completed
  - X-Monthly-Jinpu-Heating-Area-Adjusted
  - X-Monthly-Extracted-Total-Rows
- 增加 Access-Control-Expose-Headers，确保前端可读。
2) frontend/src/projects/daily_report_25_26/services/api.js
- extractMonthlyDataShowCsv 读取上述响应头并返回 stats。
3) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 提取成功文案追加显示三项统计。
验证：
- python -m py_compile workspace.py extractor.py 通过。