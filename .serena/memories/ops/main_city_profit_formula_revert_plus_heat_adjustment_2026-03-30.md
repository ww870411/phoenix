时间：2026-03-30
主题：主城区利润算法恢复为子口径利润求和后再加热量调整
变更文件：backend/sql/analysis.sql；backend/sql/groups.sql；configs/progress.md；frontend/README.md；backend/README.md。
用户最终要求：
1. 主城区边际利润恢复为北海、香海、供热三个子口径边际利润之和。
2. 主城区可比煤价边际利润恢复为北海、香海、供热三个子口径可比煤价边际利润之和。
3. 在上述基础上统一再做一步加工：+ 内购热成本 - 内售热收入。
本次实现：
- analysis.sql：主城区日视图与累计视图中的 eco_marginal_profit / eco_comparable_marginal_profit 改为直接对 base_zc 中子口径利润项求和，再叠加 eco_inner_purchased_heat_cost，减去 eco_inner_heat_supply_income。
- groups.sql：展示页链路同样改为对 eco_marginal_profit / eco_comparable_marginal_profit 求和，再叠加 eco_inner_purchased_heat_cost，减去 eco_inner_heat_supply_income，并覆盖 value/day7/month/ytd 各窗口。
验证状态：已静态复核 SQL 片段；未执行数据库重放与实库核验，需用户在容器数据库中重新执行 analysis.sql 与 groups.sql。