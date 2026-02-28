时间：2026-02-28
需求：在 backend/sql 下新增 SQL 文件，创建 month_data_show 表。
变更文件：
1) backend/sql/month_data_show.sql
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现摘要：
- 新建 month_data_show 表，字段包含：company,item,unit,value,date,period,type,report_month 以及 id/operation_time。
- 添加唯一索引：(report_month, company, item, date, period, type) 防止重复入库。
- 添加查询索引：(report_month, company) 与 (date)。
结果：
- 建表脚本可直接执行，满足 monthly_data_show 后续入库落表需要。