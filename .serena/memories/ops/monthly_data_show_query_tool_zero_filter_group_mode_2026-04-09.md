时间：2026-04-09
任务：扩展 monthly_data_show/query-tool 的 0 值过滤方式，新增“全月份均为 0 才剔除”模式。
用户要求：在保留现有“某个月份值为 0 就剔除该条记录”的基础上，增加一种新方式：若某口径某指标在查询范围内所有月份都为 0，才剔除该指标；只要任一月份不为 0，则保留该口径该指标的全部月份记录。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- backend/projects/monthly_data_show/api/workspace.py
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. 前端
- 0值过滤面板由单一 checkbox 改为“开关 + 模式”组合。
- `filters` 新增 `excludeZeroMode`，默认 `row`。
- `buildPayload()` 新增 `exclude_zero_mode`。
- 当前模式文案：`逐条剔除 0 值`、`全月份均为 0 才剔除`。
2. 后端
- `QueryRequest` 新增 `exclude_zero_mode: str = "row"`。
- 新增 `_resolve_zero_filter_mode()`、`_zero_filter_group_key()`、`_filter_rows_by_zero_mode()`。
- `query_month_data_show()`：
  - `row` 模式下逐条过滤 `value == 0`；
  - `all_months_group` 模式下按“口径 + 指标 + 期间 + 类型 + 单位”分组，只在整组所有月份都为 0 时才过滤。
- `query_month_data_show_comparison()`：仅在 `row` 模式下继续过滤 `current_value == 0` 的比较行；`all_months_group` 模式不额外裁剪比较结果，避免与主查询月序逻辑冲突。
降级说明：本轮涉及 `.vue` 与 `.md` 文件编辑，Serena 不适合直接做结构化修改，因此按 AGENTS 约定使用 `apply_patch`，并以本记忆留痕。
验证：
- `py_compile` 编译 `backend/projects/monthly_data_show/api/workspace.py` 通过。
- `frontend` 目录执行 `npm run build` 通过。