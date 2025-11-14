日期：2025-12-04
范围：backend/sql/analysis.sql，configs/progress.md，backend/README.md，frontend/README.md。
触发原因：执行 analysis.sql 报错 column "sum_7d_biz" does not exist，需清理视图中已失效的聚合列。
变更摘要：
- 删除 yjy_power CTE 中引用的 sum_7d_*/sum_month_*/sum_ytd_* 聚合列，仅保留 value_biz_date/value_peer_date，恢复视图创建。
- 在 configs/progress.md、后端/前端 README 分别记录此次修复及影响。
回滚方式：若未来重新引入这些列，需要同时在 company CTE 补充同名字段再恢复聚合。