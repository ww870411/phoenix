时间：2025-10-28
触发：刷新二级物化视图 calc_sum_gongre_branches_detail_data 时出现错误：cannot refresh materialized view ... concurrently（缺失唯一索引）。
操作：
1) 在 backend/sql/create_view.sql 中为二级物化视图添加“无 WHERE 子句”的唯一索引：
   - calc_sum_basic_data → ux_calc_sum_basic_company_item_scope(company, item, scope)
   - calc_sum_gongre_branches_detail_data → ux_calc_sum_gongre_center_item_scope(center, item, scope)
2) 注释中明确索引目的：支持 REFRESH MATERIALIZED VIEW CONCURRENTLY。
影响范围：仅 SQL 视图脚本；不影响前端与后端 API。
回滚思路：如需停用并发刷新，可将 UNIQUE 改回普通索引或移除上述索引定义。
验证建议：
- 先执行 create_view.sql，确认两张物化视图创建后唯一索引存在（\d+ 查看索引）。
- 执行 REFRESH MATERIALIZED VIEW CONCURRENTLY calc_sum_basic_data; 与 calc_sum_gongre_branches_detail_data; 观察无 55000 错误。