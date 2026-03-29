时间：2026-03-30
主题：主城区利润值仍异常的根因与修复
结论：用户在数据库执行 analysis.sql 与 groups.sql 后，主城区两个利润值仍不对，根因有两处。
1. analysis.sql / groups.sql 中主城区利润公式虽然名义上引用“直接收入”，但实际仍从 base_zc 直接汇总三个子单位的 eco_direct_income；而子单位 eco_direct_income 仍包含 eco_inner_heat_supply_income，因此即使主城区展示的 eco_direct_income 已剔除内售热，利润公式仍把内售热收入算进去了。
2. groups.sql 的利润公式曾使用旧成本 item key：eco_raw_coal_cost、eco_outer_power_cost、eco_water_cost、eco_metering_aux_material_cost；但 sum_basic_data.sql 实际输出的是 eco_coal_cost、eco_purchased_power_cost、eco_purchased_water_cost、eco_measurable_auxiliary_materials。
修复内容：
- analysis.sql：主城区边际利润与可比煤价边际利润改为直接汇总四项收入子项（eco_power_supply_income、eco_heating_supply_income、eco_hot_water_supply_income、eco_steam_supply_income）作为收入端，不再读 eco_direct_income。
- groups.sql：同样改为直接汇总四项收入子项；并将成本端 item key 改为 sum_basic_data 实际输出的标准命名。
文档同步：configs/progress.md、frontend/README.md、backend/README.md 已更新。
验证状态：仅完成静态修复与代码复核，未执行数据库重放与实库验数。用户需重新在容器数据库执行 analysis.sql 和 groups.sql。