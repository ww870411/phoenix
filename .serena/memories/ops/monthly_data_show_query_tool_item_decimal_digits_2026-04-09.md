时间：2026-04-09
任务：调整 monthly_data_show/query-tool 页面指定指标的默认显示小数位。
用户要求：页面显示中“供暖热耗率”默认保留 4 位小数；“耗酸量”“耗碱量”默认保留 2 位小数。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现说明：
- 将原先 `FOUR_DECIMAL_ITEMS` 的隐式规则改为显式映射 `ITEM_VALUE_DECIMAL_DIGITS`。
- 当前映射：`供暖热耗率=4`、`供暖水耗率=4`、`供暖电耗率=4`、`耗酸量=2`、`耗碱量=2`。
- `valueDecimalDigitsByItem()` 统一读取该映射；查询表格、比较区格式化、导出 Excel 数值格式继续复用同一规则。
降级说明：涉及 `.vue` 与 `.md` 文件修改，Serena 不适合执行这类结构化编辑，因此按 AGENTS 约定使用 `apply_patch`，并补写本记忆条目。
验证：前端 `npm run build` 通过。