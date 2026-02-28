时间：2026-02-28
用户确认：report_month 仅作参考字段；核心唯一性以 date, period, type, company, item 为准。
变更文件：
1) backend/sql/month_data_show.sql
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 保持唯一索引为 (company, item, date, period, type)。
- 修正唯一索引注释文本。
- 将 (date, company) 索引命名修正为 idx_month_data_show_date_company。
- 新增 report_month 单列索引 idx_month_data_show_report_month（参考查询）。
结果：
- 表约束与业务口径一致，索引命名与用途清晰。