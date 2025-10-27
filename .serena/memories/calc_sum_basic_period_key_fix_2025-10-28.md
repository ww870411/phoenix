时间：2025-10-28
问题：calc_sum_basic_data 中北海热电厂 sum_7d_biz × price_power_sales 结果为 0，但上游 sum_basic_data 与 constant_data 分别存在非零数值。
根因推断：period 映射不一致（period_map 使用 '25-26period' vs constant_data 使用 '25-26'），以及常量表与基础数据的组织键名可能分别使用英文/中文，导致 LEFT JOIN 未命中 → price_* 为 NULL → 计算项为 0。
改动：
1) backend/sql/create_view.sql：period_map 中 period 值改为 '25-26'/'24-25'，与 constant_data.period 对齐；
2) 移除无意义的 "JOIN v_scope_period sp ON TRUE"；
3) 常量连接放宽：ON (v.key1 = b.company OR v.key1 = b.company_cn) AND v.period = sp2.period，兼容公司英文/中文键名；
影响：二级物化视图 calc_sum_basic_data 计算项将能正确命中常量单价；
验证：
- 在测试库刷新视图并查询特定公司（北海热电厂）在 scope='sum_7d_biz' 下的 eco_power_supply_income 应为 > 0；
- 检查 v_sum_basic_long 中 b.company 与 constant_data 中 key1 实际值是否匹配预期；
回滚：如无需兼容中文键名，可将 OR 条件改回仅 b.company；period 映射保留为与 constant_data 一致的值。