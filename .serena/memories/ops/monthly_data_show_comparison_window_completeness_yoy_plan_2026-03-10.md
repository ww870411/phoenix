时间：2026-03-10
需求：monthly_data_show 查询页“同比/环比/计划比（实时窗口）”改为“同比/计划窗口必须逐月完备才可比”。
业务结论：
- 查询主表仍按时间窗口聚合。
- 但同比值、计划值不能再采用“窗口内有局部数据就聚合”的策略。
- 若对应窗口内缺任一月份，则视为不可比，返回空值；避免把某一单月的同期/计划值冒充整段窗口结果。
- 环比逻辑本轮保持不变。
代码实现：
1) `backend/projects/monthly_data_show/api/workspace.py`
- `_fetch_compare_map(...)` 改为返回 `(result_map, complete_keys)`：
  - 保留原聚合结果；
  - 额外按月统计覆盖情况；
  - 基础指标只有在窗口每个月都存在时才记为 complete；
  - 计算指标只有在其所依赖的全部基础指标都逐月齐备时才记为 complete。
- `_fetch_plan_value_map(...)` 同样返回 `(result_map, complete_keys)`，对计划值执行逐月完备校验。
- `query_month_data_show_comparison(...)`：
  - 同比值仅在 `key in yoy_complete_keys` 时返回；
  - 计划值仅在 `plan_lookup_key in plan_complete_keys` 时返回；
  - 否则对应值与比率为 `null`。
2) 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`
降级说明：
- Serena 不支持直接编辑该非纯符号改动块及 Markdown，故按仓库规范使用 `apply_patch`。
验证：
- `python -m py_compile backend/projects/monthly_data_show/api/workspace.py` 通过。
- `cd frontend && npm run build` 通过。
回滚：
- 恢复 `_fetch_compare_map/_fetch_plan_value_map/query_month_data_show_comparison` 的旧返回结构与“只要窗口有值就聚合”的判定逻辑。