时间：2025-10-28
问题：calc_sum_basic_data 中 BeiHai/北海热电厂 在 scope='sum_7d_biz' 下 eco_power_supply_income 为 0，而上游 amount_power_sales 与 price_power_sales 都非零。分析发现售电收入单位换算不当：数量为“万kWh”，单价为“元/kWh”，相乘即为“万元”，无需再 /10000。原公式多除以 10000 导致结果被四舍五入为 0。
改动：
- backend/sql/create_view.sql：
  - eco_power_supply_income 改为 (amount_power_sales * price_power_sales)（不再 /10000）。
  - eco_heat_supply_income 保持 /10000（GJ×元/GJ→元，再除以 10000）。
  - eco_direct_income 改为 售电收入（万元）+ 售热收入（万元），不再对合计统一 /10000。
影响：售电相关收入及直接收入数值将恢复至合理量级（万元），避免 0 值。
验证：
- 刷新视图后，查询 calc_sum_basic_data where (company='BeiHai' or company_cn='北海热电厂') and scope='sum_7d_biz' and item in ('eco_power_supply_income','eco_direct_income')；值应 > 0。
- 与 v_sum_basic_long + v_constants_center_first 的手工计算对比，一致。
回滚：如后续确认 amount_power_sales 单位不是“万kWh”，可恢复 /10000 或按单位字段做动态换算。