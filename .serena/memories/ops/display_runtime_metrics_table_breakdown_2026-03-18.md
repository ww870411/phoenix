日期：2026-03-18
主题：display runtime metrics 按表耗时细分

背景：第二阶段批量 metrics 查询后，用户复测 `Group_sum_show_Sheet`：`total_ms` 从约 39s 降到约 18s，`metrics_fetch_count` 从 9 降到 2，但 `metrics_fetch_ms` 仍约 17.9s，说明剩余瓶颈集中在两次批量查询本身。

实施：
1. `backend/services/runtime_expression.py`
   - 在 `_perf` 中新增 `metrics_fetch_ms_by_table` 与 `metrics_company_count_by_table`。
   - 每次按表批量调用 `_fetch_metrics_from_view_batch(...)` 时，记录该表耗时与涉及公司数。
2. 前端无需额外交互改动，继续通过控制台 `[DisplayRuntimeView][perf]` 查看新增字段。
3. 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已更新。

验证：
- `python -m py_compile backend/services/runtime_expression.py backend/projects/daily_report_25_26/api/legacy_full.py` 通过。

目的：
- 下一轮用户复测后，可直接判断 `groups` 与 `sum_basic_data` 哪张视图更慢，再决定是否需要查看执行计划、视图定义或索引。