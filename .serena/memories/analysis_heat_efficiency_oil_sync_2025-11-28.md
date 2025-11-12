时间：2025-11-28
任务：应用户要求，将 backend/sql/analysis.sql 内所有视图（analysis_company_daily / analysis_groups_daily / analysis_company_sum / analysis_groups_sum）中“全厂热效率”分母改为 29.308 * (consumption_std_coal + 1.4571 * consumption_oil)。
实现：Serena 不支持 SQL 编辑，已用 apply_patch 修改 10 处 Nullif 表达式，并同步更新 configs/progress.md、backend/README.md、frontend/README.md 说明分析视图已应用含油耗口径。
验证建议：重建 analysis.sql 后查询 `SELECT company,item,value_biz_date FROM analysis_groups_sum WHERE item='rate_overall_efficiency'`，数值应与 groups 视图一致；若某单位油耗缺失，因 SUM=0 分母自动退化为旧值。