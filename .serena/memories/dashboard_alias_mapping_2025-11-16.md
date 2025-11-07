## 2025-11-16
- 在 `backend_data/数据结构_数据看板.json` 中新增 `口径别名`：`标煤耗量汇总(张屯)`→`标煤耗量`、`原煤耗量汇总(张屯)`→`原煤耗量`。
- `frontend/src/daily_report_25_26/pages/DashBoard.vue` 引入 `metricAliasMap/buildLabelVariants`，`resolveSection` 支持多别名，`cumulativeUnits`、累计卡片、投诉图表/表格及收入/标煤表格均按别名展示，底层仍取 `sum_consumption_amount_*_zhangtun` 数据。
- 目的：集团张屯汇总指标沿用既有中文口径，避免 UI 出现“(张屯)”标记，同时保持新汇总逻辑。