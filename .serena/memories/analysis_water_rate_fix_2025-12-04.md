日期：2025-12-04
范围：backend/sql/analysis.sql，configs/progress.md，backend/README.md，frontend/README.md。
触发原因："供热公司" 查询“供暖水单耗”无结果，发现 calc_rate_water_per_10k_m2 仅统计 consumption_station_water_supply。
变更摘要：
- 两处 calc_rate_water_per_10k_m2 CTE 均改为汇总 consumption_network_fill_water、consumption_station_fill_water、consumption_network_water，并继续用供暖收费面积归一化。
- configs/progress.md、后端 README、前端 README 记录该修复与验证方式。
回滚方式：若需要旧算法，将 CTE 的 CASE 条件改回单一 consumption_station_water_supply 并更新文档。