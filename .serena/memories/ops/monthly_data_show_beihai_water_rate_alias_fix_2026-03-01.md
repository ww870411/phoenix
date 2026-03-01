时间：2026-03-01
主题：北海发电水耗率/供热水耗率计算偏差修复

用户反馈：
- company=北海 时，发电水耗率/供热水耗率计算不正确。

根因：
- 两指标依赖热分摊比；热分摊比依赖耗标煤总量。
- 实际数据存在同义命名（如标煤耗量、煤折标煤量等），旧逻辑仅按单一名称取值，导致依赖缺失。

改动文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

后端实现：
- 新增 METRIC_ALIAS_MAP：
  - 耗标煤总量 -> 标煤耗量/煤折标煤量
  - 供热耗标煤量 -> 供热标准煤耗量
  - 发电耗标煤量 -> 发电标准煤耗量
  - 生产耗原煤量 -> 原煤耗量
  - 耗水量 -> 电厂耗水量
- _collect_required_base_items：依赖补查时将别名一并纳入。
- _compute_calculated_indicator.val：主指标为 0/缺失时，回退别名取值。

结果：
- 在指标命名不统一的情况下，水耗率相关计算链可正确命中依赖，结果显著更稳。