时间：2025-10-28
问题：calc_sum_basic_trace 显示未取到常量数据（is_price_power_null=true）。定位发现常量视图使用了 center 优先（key1=COALESCE(center,company)），而公司级汇总按 company 维度连接，导致当常量有 center 值时 key1=中心名，company 连接失败；另外 period 字段存在 '25-26period'/空白等差异。
改动：
1) 新增 v_constants_company_first_norm（key1=COALESCE(company,center)），并规范化 item_key 与 period_key（提取 25-26、去除 'period' 后缀）。
2) calc_sum_basic_data 与 calc_sum_basic_trace 均改为连接 v_constants_company_first_norm，并以 v.period_key = sp2.period 连接；
3) calc_sum_gongre_branches_detail_data 仍连接 v_constants_center_first_norm，但 period 改为 period_key。
影响：公司维度计算能命中常量（即使 center 列非空）；period 统一匹配 '25-26' 等规范值；trace 视图能显示价格。
验证：
- 刷新视图后，trace 显示 price_power_sales 非空，power_income_calc>0；
- calc_sum_basic_data 中 eco_power_supply_income>0；
- center 维度的 calc_sum_gongre_branches_detail_data 不受影响（改为用 period_key 匹配）。
回滚：
- 将 company 维度的 join 切回 v_constants_center_first_norm，并用 v.period 替代 period_key；
- 删除 v_constants_company_first_norm。