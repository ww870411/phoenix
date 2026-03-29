时间：2026-03-30
主题：主城区直接收入剔除内售热收入
变更文件：backend/sql/analysis.sql；backend/sql/groups.sql；configs/progress.md；frontend/README.md；backend/README.md。
背景：主城区边际利润与可比煤价边际利润已改为按主城区统一公式重算。用户进一步要求主城区 eco_direct_income 不再包含 eco_inner_heat_supply_income。
本次调整：
1. analysis.sql 中主城区日视图与累计视图的 eco_direct_income，改为仅汇总 eco_power_supply_income、eco_heating_supply_income、eco_hot_water_supply_income、eco_steam_supply_income。
2. groups.sql 中主城区展示页链路的 eco_direct_income 同步改为同样四项收入汇总。
3. 结果是数据分析页与全口径展示页两条链路都明确剔除了内售热收入。
验证状态：已静态检查 SQL 片段更新到位；未执行数据库刷新和实库核验，需用户在容器数据库中重放 analysis.sql 与 groups.sql 后验数。