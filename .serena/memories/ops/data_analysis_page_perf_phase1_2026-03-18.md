日期：2026-03-18
主题：daily_report_25_26 数据分析页第一阶段分段计时

背景：用户确认数据分析页性能也较差，希望先分析。经梳理后判断，该页不同于展示页的单一重视图问题，而是前端多单位串行 + 后端组合查询串行叠加。用户同意先按建议增加计时，而不是直接盲改查询。

实施：
1. `backend/projects/daily_report_25_26/api/legacy_full.py`
   - `DataAnalysisQueryPayload` 新增 `profile: bool = False`。
   - `_execute_data_analysis_query_legacy(...)` 在 `profile=true` 时返回 `_perf`。
   - `_perf` 包含：
     - `main_analysis_query_ms`
     - `constant_query_ms`
     - `temperature_query_ms`
     - `analysis_timeline_ms`
     - `temperature_timeline_ms`
     - `previous_period_query_ms`
     - `plan_comparison_ms`
     - `rows_assembly_ms`
     - `ai_report_enqueue_ms`
     - `total_ms`
   - 同时记录上下文：`unit_key`、`scope_key`、`is_beihai_sub_scope`、`analysis_mode`、`timeline_days`、`selected_metrics_count`、`analysis_metric_count`、`constant_metric_count`、`temperature_metric_count`。
2. `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
   - `runAnalysis()` 请求默认带 `profile: true`。
   - 每个单位查询完成后，在浏览器控制台输出 `[DataAnalysisView][perf]`、`unitKey`、`unitLabel`、`perf`。
3. 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已更新。

验证：
- `python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py` 通过。
- `frontend` 执行 `npm run build` 通过。

前置说明：
- 由于 `legacy_full.py` 在本会话中多次出现 `apply_patch` 沙箱刷新失败，本轮对该文件的个别编辑降级使用了 Desktop Commander 的结构化编辑；范围仅限导入、请求模型与计时字段插入，未改业务口径。