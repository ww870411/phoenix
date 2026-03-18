日期：2026-03-18
主题：daily_report_25_26 展示页第二阶段尝试：metrics 视图批量查询

背景：用户提供 `Group_sum_show_Sheet` 首屏 `_perf`：`total_ms=39422.66`、`prefetch_data_ms=39387.4`、`metrics_fetch_ms=39358.27`、`evaluate_rows_ms=33.99`。结论是瓶颈几乎全部在视图指标查询，不在前端或 Python 表达式计算，多进程求值不是当前优先项。

实施：
1. `backend/services/runtime_expression.py`
   - 新增 `_fetch_metrics_from_view_batch(session, table, companies, biz_date)`，支持通过 `company = ANY(:companies)` 对 `sum_basic_data` / `groups` 批量拉取多个公司指标。
   - 保留原 `_fetch_metrics_from_view(...)` 以便兼容，但 `render_spec(...)` 的主路径改为批量查询。
2. `render_spec(...)`
   - 对 `companies_needed` 先按主表路由分组（通常最多 `groups` 与 `sum_basic_data` 两组）。
   - 共享缓存命中的公司直接复用。
   - 未命中的公司改为每张表执行一次批量查询，再拆回 `metrics_by_company` 与 `shared_metrics_cache`。
   - constants 与温度极值逻辑保持不变，便于对照 perf 变化。
3. 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已更新。

验证：
- `python -m py_compile backend/services/runtime_expression.py backend/projects/daily_report_25_26/api/legacy_full.py` 通过。

预期：
- `metrics_fetch_count` 将从按公司次数下降到按表次数，`metrics_fetch_ms` 应明显下降。
- 后续需要用户再次刷新页面并回传新的 `[DisplayRuntimeView][perf]`。