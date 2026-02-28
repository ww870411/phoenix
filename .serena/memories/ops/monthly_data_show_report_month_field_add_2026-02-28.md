时间：2026-02-28
需求：monthly_data_show 导出新增 report_month 字段，表示月报来源月份（如 26.2 -> 2026-02-01）。
变更文件：
1) backend/projects/monthly_data_show/services/extractor.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现摘要：
- ALLOWED_FIELDS 新增 report_month。
- 新增 _build_report_month_text(report_year, report_month) 生成 YYYY-MM-01。
- 在普通提取行与常量注入行中均写入 report_month。
- 前端无需改动：字段清单由 inspect 动态返回，新增字段会自动出现在字段复选中。
结果：
- 导出 CSV 可携带 report_month，作为统一的数据来源月份字段。