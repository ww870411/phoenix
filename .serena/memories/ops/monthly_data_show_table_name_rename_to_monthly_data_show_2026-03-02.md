时间：2026-03-02
主题：monthly_data_show 表名纠偏（month_data_show -> monthly_data_show）

触发：用户已将数据库表改名为 monthly_data_show，程序仍引用旧表名 month_data_show。

改动：
1) backend/projects/monthly_data_show/api/workspace.py
- 查询、对比、筛选项、CSV 入库 UPSERT 的 SQL FROM/INSERT 统一改为 monthly_data_show
- import-csv 接口 summary 文案同步为 monthly_data_show

2) backend/sql/month_data_show.sql
- CREATE TABLE 目标改为 monthly_data_show
- 索引改为 idx_monthly_data_show_unique / idx_monthly_data_show_date_company，并绑定新表名

3) 前端文案
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 两处显示文本由 month_data_show 改为 monthly_data_show

验证：
- 代码级检索确认无运行时旧表名依赖
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过

结果：月报导入与查询主链已对齐新表名 monthly_data_show。