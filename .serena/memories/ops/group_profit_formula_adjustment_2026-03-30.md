时间：2026-03-30
主题：集团全口径利润算法按主城区方式修正
变更文件：backend/sql/analysis.sql；backend/sql/groups.sql；configs/progress.md；frontend/README.md；backend/README.md。
背景：集团全口径原先与主城区早期实现一样，利润项在分组视图中直接透传各子口径利润之和，没有额外加工。
用户要求：集团全口径两个利润指标仿照主城区修正，均作 + (集团全口径)内购热成本 - (集团全口径)内售热收入。
本次实现：
1. analysis.sql：在 Group 的透传排除项中新增 eco_marginal_profit、eco_comparable_marginal_profit；在 Group 直接收入后新增两个显式利润 SELECT。
2. groups.sql：同样在 Group 的透传排除项中新增两个利润 item；新增 value/day7/month/ytd 各窗口的 Group 利润重算逻辑。
3. 最终公式：
   - Group eco_marginal_profit = 各子口径 eco_marginal_profit 之和 + eco_inner_purchased_heat_cost - eco_inner_heat_supply_income
   - Group eco_comparable_marginal_profit = 各子口径 eco_comparable_marginal_profit 之和 + eco_inner_purchased_heat_cost - eco_inner_heat_supply_income
验证状态：已完成静态代码复核；未执行数据库重放与实库核验，需用户在 Docker 数据库中重新执行 analysis.sql 与 groups.sql。