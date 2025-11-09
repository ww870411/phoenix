## 2025-11-17
- 位置：frontend/src/daily_report_25_26/pages/DashBoard.vue（模板 + 逻辑 + 样式）。
- 变更：
  - 在第八个 summary 卡片之后新增可折叠表格卡片（12 栅格宽度），列出供暖期关键指标；增加 `summary-card--span-full`、`summary-card__toggle`、`fold` transition 等样式与动画。
  - 折叠区采用定制 `<table>`，通过 `summaryFoldTable` 读取 `/dashboard` 返回的 `0.5卡片详细信数据表（折叠）` 节点；若接口缺失则自动回退到既有 headline 逻辑。列呈现“指标 / 口径 / 本日 / 本月累计 / 供暖期累计”，且每个指标展示“本期/同期”两行，确保单位、列宽与千分位格式一致。
- 后端：`backend/services/dashboard_expression.py` 新增 `_fill_summary_fold_section`，直接从 `calc_temperature_data` 与 `groups` 视图写入本日/本月/供暖期数据（含本期/同期），同时将供暖期平均气温改为基于 `calc_temperature_data` 聚合，供前端即取即用。
- 触发：Serena 暂不支持直接编辑 `.vue` 模板，依规范降级使用 `desktop-commander::read_file + apply_patch`。
- 回滚：恢复 `DashBoard.vue`、`backend/services/dashboard_expression.py` 到 2025-11-17 之前的提交或移除新增 computed/样式即可。